"""CLI main entry point for JSON-RPC agent interface."""
import sys
from pathlib import Path
from typing import Any, Optional

from ..cad_kernel.entity_manager import EntityManager
from ..cad_kernel.geometry_core import get_geometry_core
from ..cad_kernel.workspace import WorkspaceManager
from ..operations.history import HistoryManager, HistoryEntry
from ..persistence.database import Database
from ..persistence.entity_store import EntityStore
from ..persistence.operation_log import OperationLog
from ..persistence.workspace_store import WorkspaceStore
from ..utils.logger import get_logger
from ..utils.performance_tracker import PerformanceTracker
from .agent_metrics import MetricsTracker
from .command_parser import CommandParser
from .error_handler import ErrorCode, ErrorHandler
from .response_builder import ResponseBuilder


class CLI:
    """Main CLI application for agent interaction."""

    def __init__(self, workspace_dir: str = "data/workspaces/main"):
        """Initialize CLI with database and core components.

        Args:
            workspace_dir: Directory for workspace data
        """
        # Initialize database
        workspace_path = Path(workspace_dir)
        workspace_path.mkdir(parents=True, exist_ok=True)
        db_path = workspace_path / "database.db"

        self.database = Database(db_path)
        self.database.initialize_schema()

        # Initialize persistence layer
        self.entity_store = EntityStore(self.database)
        self.workspace_store = WorkspaceStore(self.database)
        self.operation_log = OperationLog(self.database)

        # Initialize core components
        self.entity_manager = EntityManager(self.entity_store)
        self.workspace_manager = WorkspaceManager(self.workspace_store)
        self.geometry_core = get_geometry_core()

        # Initialize agent interface components
        self.parser = CommandParser()
        self.response_builder = ResponseBuilder()
        self.error_handler = ErrorHandler()
        self.logger = get_logger()
        self.history_manager = HistoryManager()
        self.metrics_tracker = MetricsTracker()

        # Ensure main workspace exists
        main_workspace = self.workspace_store.get_workspace("main")
        if main_workspace is None:
            self.workspace_store.create_workspace(
                workspace_id="main",
                workspace_name="Main Workspace",
                workspace_type="main",
                branch_status="clean"
            )

        # Set default active workspace to main
        try:
            self.workspace_manager.set_active_workspace("main")
        except ValueError:
            pass  # If still fails, continue without active workspace

        # Initialize constraint solver components
        from ..constraint_solver.constraint_graph import ConstraintGraph
        from ..constraint_solver.solver_core import ConstraintSolver

        self.constraint_graph = ConstraintGraph(workspace_id="main")
        self.constraint_solver = ConstraintSolver()

        # Load existing constraints from database
        self._load_constraints_from_database()

        # Method dispatch table
        self.methods = {
            "entity.create.point": self._handle_create_point,
            "entity.create.line": self._handle_create_line,
            "entity.create.circle": self._handle_create_circle,
            "entity.query": self._handle_entity_query,
            "entity.list": self._handle_entity_list,
            "constraint.apply": self._handle_constraint_apply,
            "constraint.status": self._handle_constraint_status,
            "solid.extrude": self._handle_solid_extrude,
            "solid.boolean": self._handle_solid_boolean,
            "workspace.create": self._handle_workspace_create,
            "workspace.list": self._handle_workspace_list,
            "workspace.switch": self._handle_workspace_switch,
            "workspace.status": self._handle_workspace_status,
            "workspace.merge": self._handle_workspace_merge,
            "workspace.resolve_conflict": self._handle_workspace_resolve_conflict,
            "history.list": self._handle_history_list,
            "history.undo": self._handle_history_undo,
            "history.redo": self._handle_history_redo,
            "file.export": self._handle_file_export,
            "file.import": self._handle_file_import,
            "agent.metrics": self._handle_agent_metrics,
            "scenario.run": self._handle_scenario_run,
        }
        
        # Add backward-compatible aliases for 2-part method names
        self.methods["entity.create_point"] = self._handle_create_point
        self.methods["entity.create_line"] = self._handle_create_line
        self.methods["entity.create_circle"] = self._handle_create_circle

    def _load_constraints_from_database(self) -> None:
        """Load existing constraints from database into constraint graph."""
        import json
        from ..operations.constraints import (
            ParallelConstraint,
            PerpendicularConstraint,
            CoincidentConstraint,
            DistanceConstraint,
            AngleConstraint,
            TangentConstraint,
            RadiusConstraint,
        )
        from ..operations.primitives_2d import Point2D, Line2D, Circle2D

        cursor = self.database.connection.cursor()
        cursor.execute("""
            SELECT constraint_id, constraint_type, workspace_id, constrained_entities, parameters
            FROM constraints
            WHERE workspace_id = ?
        """, ("main",))

        for row in cursor.fetchall():
            constraint_id, constraint_type, workspace_id, constrained_entities_json, parameters_json = row
            entity_ids = json.loads(constrained_entities_json)
            parameters = json.loads(parameters_json) if parameters_json else {}

            # Reconstruct entities
            entities = []
            for entity_id in entity_ids:
                entity_data = self.entity_manager.get_entity(entity_id)
                if entity_data is None:
                    continue

                entity_type = entity_data.entity_type
                props = entity_data.properties

                if entity_type == "point":
                    entity = Point2D(
                        entity_id=entity_data.entity_id,
                        workspace_id=entity_data.workspace_id,
                        coordinates=props.get("coordinates", [])
                    )
                elif entity_type == "line":
                    entity = Line2D(
                        entity_id=entity_data.entity_id,
                        workspace_id=entity_data.workspace_id,
                        start=props.get("start", []),
                        end=props.get("end", [])
                    )
                elif entity_type == "circle":
                    entity = Circle2D(
                        entity_id=entity_data.entity_id,
                        workspace_id=entity_data.workspace_id,
                        center=props.get("center", []),
                        radius=props.get("radius", 0.0)
                    )
                else:
                    continue

                # Add entity to graph
                if entity_id not in self.constraint_graph.entities:
                    self.constraint_graph.add_entity(entity)

                entities.append(entity)

            # Create constraint
            constraint_classes = {
                "parallel": ParallelConstraint,
                "perpendicular": PerpendicularConstraint,
                "coincident": CoincidentConstraint,
                "distance": DistanceConstraint,
                "angle": AngleConstraint,
                "tangent": TangentConstraint,
                "radius": RadiusConstraint,
            }

            if constraint_type not in constraint_classes:
                continue

            constraint_class = constraint_classes[constraint_type]
            kwargs = {
                "constraint_id": constraint_id,
                "workspace_id": workspace_id,
                "entity_ids": entity_ids,
                "entities": entities,
            }

            # Add type-specific parameters
            if constraint_type == "distance":
                kwargs["target_distance"] = parameters.get("distance", 0.0)
            elif constraint_type == "angle":
                kwargs["target_angle"] = parameters.get("angle", 0.0)
            elif constraint_type == "radius":
                kwargs["target_radius"] = parameters.get("radius", 0.0)

            constraint = constraint_class(**kwargs)
            self.constraint_graph.add_constraint(constraint)

    def run(self) -> None:
        """Run CLI main loop, reading from stdin and writing to stdout."""
        self.logger.info("CLI starting", agent_mode=True)

        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue

            response = self.process_request(line)
            sys.stdout.write(response)
            sys.stdout.flush()

    def process_request(self, json_string: str) -> str:
        """Process a single JSON-RPC request.

        Args:
            json_string: JSON-RPC request string

        Returns:
            JSON-RPC response string (NDJSON format)
        """
        # Parse request
        request, error_response = self.parser.parse(json_string)

        if error_response:
            # Parsing failed
            return self.response_builder.format_ndjson(str(error_response).replace("'", '"'))

        # Dispatch to method handler
        if request.method not in self.methods:
            return self.response_builder.send_error(
                request.id,
                ErrorCode.INVALID_COMMAND,
                f"Unknown method: {request.method}",
                {"available_methods": list(self.methods.keys())}
            )

        # Execute method with performance tracking
        tracker = PerformanceTracker()
        tracker.start(request.method)

        try:
            handler = self.methods[request.method]
            result_data = handler(request)
            execution_time_ms = tracker.stop()

            # Record successful operation in metrics
            self.metrics_tracker.record_operation(
                agent_id="default_agent",
                operation_type=request.method,
                success=True
            )

            return self.response_builder.send_success(
                request.id,
                result_data,
                operation_type=request.method,
                execution_time_ms=execution_time_ms
            )

        except KeyError as e:
            execution_time_ms = tracker.get_elapsed_ms()
            self.logger.error(f"Missing parameter: {str(e)}", method=request.method)

            # Record failed operation in metrics
            self.metrics_tracker.record_operation(
                agent_id="default_agent",
                operation_type=request.method,
                success=False,
                error_code=ErrorCode.INVALID_PARAMETER,
                error_message=f"Missing required parameter: {str(e)}"
            )

            return self.response_builder.send_error(
                request.id,
                ErrorCode.INVALID_PARAMETER,
                f"Missing required parameter: {str(e)}"
            )

        except ValueError as e:
            execution_time_ms = tracker.get_elapsed_ms()
            self.logger.error(f"Invalid parameter: {str(e)}", method=request.method)

            # Check error type - more specific checks first
            error_msg = str(e)
            if "conflict" in error_msg.lower():
                error_code = ErrorCode.CONSTRAINT_CONFLICT
            elif "not found" in error_msg.lower():
                error_code = ErrorCode.ENTITY_NOT_FOUND
            elif "invalid constraint type" in error_msg.lower():
                error_code = ErrorCode.INVALID_CONSTRAINT
            elif any(word in error_msg.lower() for word in ["finite", "bounds", "degenerate"]):
                error_code = ErrorCode.INVALID_GEOMETRY
            elif "dimension" in error_msg.lower():
                error_code = ErrorCode.INVALID_PARAMETER
            else:
                error_code = ErrorCode.INVALID_PARAMETER

            # Record failed operation in metrics
            self.metrics_tracker.record_operation(
                agent_id="default_agent",
                operation_type=request.method,
                success=False,
                error_code=error_code,
                error_message=error_msg
            )

            return self.response_builder.send_error(
                request.id,
                error_code,
                error_msg
            )

        except Exception as e:
            execution_time_ms = tracker.get_elapsed_ms()
            self.logger.error(f"Method execution failed: {str(e)}", method=request.method)

            # Record failed operation in metrics
            self.metrics_tracker.record_operation(
                agent_id="default_agent",
                operation_type=request.method,
                success=False,
                error_code=ErrorCode.GEOMETRY_ENGINE_ERROR,
                error_message=str(e)
            )

            return self.response_builder.send_error(
                request.id,
                ErrorCode.GEOMETRY_ENGINE_ERROR,
                str(e)
            )

    def _get_active_workspace_id(self) -> str:
        """Get active workspace ID, defaulting to main.

        Returns:
            Workspace ID
        """
        workspace = self.workspace_manager.get_active_workspace()
        return workspace.workspace_id if workspace else "main"

    def _handle_create_point(self, request) -> dict[str, Any]:
        """Handle entity.create.point request.

        Args:
            request: Parsed JSON-RPC request

        Returns:
            Result data dictionary

        Raises:
            KeyError: If required parameters missing
            ValueError: If parameters invalid
        """
        # Extract parameters - support both formats
        # Format 1: coordinates array [x, y, z]
        # Format 2: individual x, y, z parameters (backward compatibility)
        coordinates = self.parser.get_param(request, "coordinates")
        
        if coordinates is None:
            # Try individual x, y, z parameters
            x = self.parser.get_param(request, "x")
            y = self.parser.get_param(request, "y")
            z = self.parser.get_param(request, "z", default=0.0)
            
            if x is not None and y is not None:
                coordinates = [x, y, z]
            else:
                raise KeyError("Missing required parameter: coordinates (or x, y, z)")

        # Validate coordinates
        is_valid, error_msg = self.geometry_core.validate_point(coordinates)
        if not is_valid:
            raise ValueError(error_msg)

        # Normalize to 3D coordinates
        if len(coordinates) == 2:
            coordinates = [coordinates[0], coordinates[1], 0.0]

        # Get workspace_id - allow override via parameter
        workspace_id = self.parser.get_param(request, "workspace_id")
        if workspace_id is None:
            workspace_id = self._get_active_workspace_id()
        else:
            # Resolve full workspace ID if short name provided
            ws = self.workspace_manager.get_workspace(workspace_id)
            if ws:
                workspace_id = ws.workspace_id
            elif ":" not in workspace_id:
                # Try with default_agent prefix
                full_id = f"default_agent:{workspace_id}"
                ws = self.workspace_manager.get_workspace(full_id)
                if ws:
                    workspace_id = ws.workspace_id
        agent_id = request.params.get("agent_id", "default_agent")

        # Create entity
        properties = {"coordinates": coordinates}
        bounding_box = self.geometry_core.calculate_bounding_box([coordinates])

        entity = self.entity_manager.create_entity(
            entity_type="point",
            workspace_id=workspace_id,
            agent_id=agent_id,
            properties=properties,
            bounding_box=bounding_box
        )

        return {
            "entity_id": entity.entity_id,
            "entity_type": entity.entity_type,
            "workspace_id": workspace_id,
            "coordinates": coordinates
        }

    def _handle_create_line(self, request) -> dict[str, Any]:
        """Handle entity.create.line request."""
        start = self.parser.get_param(request, "start", required=True)
        end = self.parser.get_param(request, "end", required=True)
        
        # Support both formats: array [x,y,z] or object {x, y, z}
        if isinstance(start, dict):
            start = [start.get("x", 0.0), start.get("y", 0.0), start.get("z", 0.0)]
        if isinstance(end, dict):
            end = [end.get("x", 0.0), end.get("y", 0.0), end.get("z", 0.0)]

        # Validate line
        is_valid, error_msg = self.geometry_core.validate_line(start, end)
        if not is_valid:
            raise ValueError(error_msg)

        # Normalize to 3D coordinates
        if len(start) == 2:
            start = [start[0], start[1], 0.0]
        if len(end) == 2:
            end = [end[0], end[1], 0.0]

        workspace_id = self.parser.get_param(request, "workspace_id")
        if workspace_id is None:
            workspace_id = self._get_active_workspace_id()
        else:
            # Resolve full workspace ID if short name provided
            ws = self.workspace_manager.get_workspace(workspace_id)
            if ws:
                workspace_id = ws.workspace_id
        agent_id = request.params.get("agent_id", "default_agent")

        # Calculate properties
        length = self.geometry_core.calculate_distance(start, end)
        direction_vector = self.geometry_core.calculate_direction_vector(start, end)

        properties = {
            "start": start,
            "end": end,
            "length": length,
            "direction_vector": direction_vector
        }
        bounding_box = self.geometry_core.calculate_bounding_box([start, end])

        entity = self.entity_manager.create_entity(
            entity_type="line",
            workspace_id=workspace_id,
            agent_id=agent_id,
            properties=properties,
            bounding_box=bounding_box
        )

        return {
            "entity_id": entity.entity_id,
            "entity_type": entity.entity_type,
            "workspace_id": workspace_id,
            "start": start,
            "end": end,
            "length": length,
            "direction_vector": direction_vector
        }

    def _handle_create_circle(self, request) -> dict[str, Any]:
        """Handle entity.create.circle request."""
        center = self.parser.get_param(request, "center", required=True)
        radius = self.parser.get_param(request, "radius", required=True)
        
        # Support both formats: array [x,y,z] or object {x, y, z}
        if isinstance(center, dict):
            center = [center.get("x", 0.0), center.get("y", 0.0), center.get("z", 0.0)]

        # Validate circle
        is_valid, error_msg = self.geometry_core.validate_circle(center, radius)
        if not is_valid:
            raise ValueError(error_msg)

        # Normalize to 3D coordinates
        if len(center) == 2:
            center = [center[0], center[1], 0.0]

        workspace_id = self.parser.get_param(request, "workspace_id")
        if workspace_id is None:
            workspace_id = self._get_active_workspace_id()
        else:
            # Resolve full workspace ID if short name provided
            ws = self.workspace_manager.get_workspace(workspace_id)
            if ws:
                workspace_id = ws.workspace_id
        agent_id = request.params.get("agent_id", "default_agent")

        # Calculate properties
        area = self.geometry_core.calculate_circle_area(radius)
        circumference = self.geometry_core.calculate_circle_circumference(radius)

        properties = {
            "center": center,
            "radius": radius,
            "area": area,
            "circumference": circumference
        }

        # Bounding box for circle
        dim = len(center)
        min_coords = [center[i] - radius for i in range(dim)]
        max_coords = [center[i] + radius for i in range(dim)]
        while len(min_coords) < 3:
            min_coords.append(0.0)
        while len(max_coords) < 3:
            max_coords.append(0.0)
        bounding_box = {"min": min_coords[:3], "max": max_coords[:3]}

        entity = self.entity_manager.create_entity(
            entity_type="circle",
            workspace_id=workspace_id,
            agent_id=agent_id,
            properties=properties,
            bounding_box=bounding_box
        )

        return {
            "entity_id": entity.entity_id,
            "entity_type": entity.entity_type,
            "workspace_id": workspace_id,
            "center": center,
            "radius": radius,
            "area": area,
            "circumference": circumference
        }

    def _handle_entity_query(self, request) -> dict[str, Any]:
        """Handle entity.query request."""
        import json
        entity_id = self.parser.get_param(request, "entity_id", required=True)

        # First try entity_manager (for 2D entities)
        entity = self.entity_manager.get_entity(entity_id)

        if entity is not None:
            # Get base entity dict
            entity_dict = entity.to_dict()

            # Add geometry-specific properties from entity properties
            if "properties" in entity_dict and entity_dict["properties"]:
                props = entity_dict["properties"]

                # For points: add coordinates
                if entity_dict["entity_type"] == "point" and "coordinates" in props:
                    entity_dict["coordinates"] = props["coordinates"]

                # For lines: add start, end, length, direction_vector
                elif entity_dict["entity_type"] == "line":
                    if "start" in props:
                        entity_dict["start"] = props["start"]
                    if "end" in props:
                        entity_dict["end"] = props["end"]
                    if "length" in props:
                        entity_dict["length"] = props["length"]
                    if "direction_vector" in props:
                        entity_dict["direction_vector"] = props["direction_vector"]

                # For circles: add center, radius, area, circumference
                elif entity_dict["entity_type"] == "circle":
                    if "center" in props:
                        entity_dict["center"] = props["center"]
                    if "radius" in props:
                        entity_dict["radius"] = props["radius"]
                    if "area" in props:
                        entity_dict["area"] = props["area"]
                    if "circumference" in props:
                        entity_dict["circumference"] = props["circumference"]

                # For solids: spread all properties to top level
                elif entity_dict["entity_type"] == "solid":
                    entity_dict.update(props)
                    del entity_dict["properties"]  # Remove nested properties

            return entity_dict

        # If not in entity_manager, try database (for solids)
        workspace_id = self._get_active_workspace_id()
        cursor = self.database.connection.cursor()
        cursor.execute("""
            SELECT entity_id, entity_type, workspace_id, properties, is_valid, validation_errors, created_at
            FROM entities
            WHERE entity_id = ? AND workspace_id = ?
        """, (entity_id, workspace_id))
        row = cursor.fetchone()

        if row is None:
            raise ValueError(f"Entity '{entity_id}' not found")

        eid, etype, wid, properties_json, is_valid, validation_errors_json, created_at = row

        # Parse JSON fields with proper error handling
        try:
            props = json.loads(properties_json) if properties_json else {}
        except (json.JSONDecodeError, TypeError) as e:
            raise ValueError(f"Failed to parse properties for entity '{entity_id}': {e}")

        try:
            validation_errors = json.loads(validation_errors_json) if validation_errors_json else []
        except (json.JSONDecodeError, TypeError) as e:
            raise ValueError(f"Failed to parse validation_errors for entity '{entity_id}': {e}")

        # Build entity dict
        entity_dict = {
            "entity_id": eid,
            "entity_type": etype,
            "workspace_id": wid,
            "is_valid": bool(is_valid),  # Convert SQLite integer to boolean
            "validation_errors": validation_errors,
            "created_at": created_at
        }

        # For solids, spread properties to top level (volume, surface_area, etc.)
        if etype == "solid":
            entity_dict.update(props)
        else:
            entity_dict["properties"] = props

        return entity_dict

    def _handle_entity_list(self, request) -> dict[str, Any]:
        """Handle entity.list request."""
        # Allow workspace_id to be specified, otherwise use active workspace
        workspace_id = self.parser.get_param(request, "workspace_id")
        if workspace_id is None:
            workspace_id = self._get_active_workspace_id()
        else:
            # Resolve full workspace ID if short name provided
            ws = self.workspace_manager.get_workspace(workspace_id)
            if ws:
                workspace_id = ws.workspace_id
            elif ":" not in workspace_id:
                # Try with default_agent prefix
                full_id = f"default_agent:{workspace_id}"
                ws = self.workspace_manager.get_workspace(full_id)
                if ws:
                    workspace_id = ws.workspace_id
        # Accept both "entity_type" and "filter_type" for compatibility
        entity_type = self.parser.get_param(request, "entity_type")
        if entity_type is None:
            entity_type = self.parser.get_param(request, "filter_type")
        limit = self.parser.get_param(request, "limit", default=100)
        offset = self.parser.get_param(request, "offset", default=0)

        entities, total_count = self.entity_manager.list_entities(
            workspace_id=workspace_id,
            entity_type=entity_type,
            limit=limit,
            offset=offset
        )

        return {
            "entities": entities,
            "total_count": total_count,
            "limit": limit,
            "offset": offset
        }

    def _handle_constraint_apply(self, request) -> dict[str, Any]:
        """Handle constraint.apply request."""
        from ..operations.constraints import (
            ParallelConstraint,
            PerpendicularConstraint,
            CoincidentConstraint,
            DistanceConstraint,
            AngleConstraint,
            TangentConstraint,
            RadiusConstraint,
        )
        from ..cad_kernel.entity_manager import GeometricEntity

        # Parse parameters
        constraint_type = self.parser.get_param(request, "constraint_type", required=True)
        entity_ids = self.parser.get_param(request, "entity_ids", required=True)
        parameters = self.parser.get_param(request, "parameters", default={})

        # Validate constraint type
        valid_types = ["parallel", "perpendicular", "coincident", "distance", "angle", "tangent", "radius"]
        if constraint_type not in valid_types:
            raise ValueError(f"Invalid constraint type: {constraint_type}. Valid types: {', '.join(valid_types)}")

        # Get entities and reconstruct proper entity classes
        from ..operations.primitives_2d import Point2D, Line2D, Circle2D
        from ..operations.primitives_3d import Point3D, Line3D

        entities = []
        for entity_id in entity_ids:
            entity_data = self.entity_manager.get_entity(entity_id)
            if entity_data is None:
                raise ValueError(f"Entity '{entity_id}' not found")

            # Reconstruct proper entity class from database data
            entity_type = entity_data.entity_type
            props = entity_data.properties

            if entity_type == "point":
                entity = Point2D(
                    entity_id=entity_data.entity_id,
                    workspace_id=entity_data.workspace_id,
                    coordinates=props.get("coordinates", [])
                )
            elif entity_type == "line":
                entity = Line2D(
                    entity_id=entity_data.entity_id,
                    workspace_id=entity_data.workspace_id,
                    start=props.get("start", []),
                    end=props.get("end", [])
                )
            elif entity_type == "circle":
                entity = Circle2D(
                    entity_id=entity_data.entity_id,
                    workspace_id=entity_data.workspace_id,
                    center=props.get("center", []),
                    radius=props.get("radius", 0.0)
                )
            else:
                raise ValueError(f"Unsupported entity type for constraints: {entity_type}")

            # Add to constraint graph if not already there
            if entity_id not in self.constraint_graph.entities:
                self.constraint_graph.add_entity(entity)

            entities.append(entity)

        # Generate constraint ID
        workspace_id = self._get_active_workspace_id()
        constraint_id = GeometricEntity.generate_entity_id(workspace_id, "constraint")

        # Create constraint based on type
        constraint_classes = {
            "parallel": ParallelConstraint,
            "perpendicular": PerpendicularConstraint,
            "coincident": CoincidentConstraint,
            "distance": DistanceConstraint,
            "angle": AngleConstraint,
            "tangent": TangentConstraint,
            "radius": RadiusConstraint,
        }

        constraint_class = constraint_classes[constraint_type]

        # Create constraint with parameters
        kwargs = {
            "constraint_id": constraint_id,
            "workspace_id": workspace_id,
            "entity_ids": entity_ids,
            "entities": entities,
        }

        # Add type-specific parameters
        if constraint_type == "distance":
            kwargs["target_distance"] = parameters.get("distance", 0.0)
        elif constraint_type == "angle":
            kwargs["target_angle"] = parameters.get("angle", 0.0)
        elif constraint_type == "radius":
            kwargs["target_radius"] = parameters.get("radius", 0.0)

        constraint = constraint_class(**kwargs)

        # Check for conflicts
        has_conflict, conflicting_id = self.constraint_graph.check_conflict(constraint)
        if has_conflict:
            conflicting = self.constraint_graph.get_constraint(conflicting_id)
            raise ValueError(
                f"Constraint conflicts with existing {conflicting.constraint_type} "
                f"constraint {conflicting_id}"
            )

        # Add constraint to graph
        self.constraint_graph.add_constraint(constraint)

        # Check satisfaction
        is_satisfied, error = constraint.check_satisfaction()
        constraint.satisfaction_status = "satisfied" if is_satisfied else "violated"

        # Persist constraint to database
        import json
        from datetime import datetime, timezone
        cursor = self.database.connection.cursor()
        cursor.execute("""
            INSERT INTO constraints (
                constraint_id, constraint_type, workspace_id, constrained_entities,
                parameters, satisfaction_status, degrees_of_freedom_removed,
                created_at, created_by_agent
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            constraint_id,
            constraint_type,
            workspace_id,
            json.dumps(entity_ids),
            json.dumps(parameters),
            constraint.satisfaction_status,
            1,  # Simple DOF calculation
            datetime.now(timezone.utc).isoformat(),
            "agent"
        ))

        # Insert entity-constraint relationships
        for ent_id in entity_ids:
            cursor.execute("""
                INSERT INTO entity_constraints (entity_id, constraint_id)
                VALUES (?, ?)
            """, (ent_id, constraint_id))

        self.database.connection.commit()

        # Return constraint data
        result = constraint.to_dict()
        result["satisfaction_error"] = error

        return result

    def _handle_constraint_status(self, request) -> dict[str, Any]:
        """Handle constraint.status request."""
        # Check if querying specific constraint
        constraint_id = self.parser.get_param(request, "constraint_id")
        entity_id = self.parser.get_param(request, "entity_id")
        include_dof = self.parser.get_param(request, "include_dof_analysis", default=False)

        if constraint_id:
            # Query specific constraint
            constraint = self.constraint_graph.get_constraint(constraint_id)
            if constraint is None:
                raise ValueError(f"Constraint '{constraint_id}' not found")

            # Update status
            is_satisfied, error = constraint.check_satisfaction()
            constraint.satisfaction_status = "satisfied" if is_satisfied else "violated"

            result = constraint.to_dict()
            result["satisfaction_error"] = error
            return result

        elif entity_id:
            # Query constraints for specific entity
            constraints = self.constraint_graph.get_constraints_for_entity(entity_id)

            # Update status for all constraints
            constraint_list = []
            for constraint in constraints:
                is_satisfied, error = constraint.check_satisfaction()
                constraint.satisfaction_status = "satisfied" if is_satisfied else "violated"

                constraint_dict = constraint.to_dict()
                constraint_dict["satisfaction_error"] = error
                constraint_list.append(constraint_dict)

            return {"constraints": constraint_list}

        else:
            # List all constraints
            constraint_list = []
            for constraint in self.constraint_graph.constraints.values():
                is_satisfied, error = constraint.check_satisfaction()
                constraint.satisfaction_status = "satisfied" if is_satisfied else "violated"

                constraint_dict = constraint.to_dict()
                constraint_dict["satisfaction_error"] = error
                constraint_list.append(constraint_dict)

            result = {"constraints": constraint_list}

            # Add DOF analysis if requested
            if include_dof:
                dof_stats = self.constraint_graph.count_degrees_of_freedom()
                result["dof_analysis"] = dof_stats

            return result

    def _handle_solid_extrude(self, request) -> dict[str, Any]:
        """Handle solid.extrude request."""
        from ..operations.solid_modeling import extrude_sketch, validate_topology
        from ..operations.primitives_2d import Line2D, Circle2D

        # Parse parameters - support both entity_id (singular) and entity_ids (plural)
        entity_ids = self.parser.get_param(request, "entity_ids")
        if entity_ids is None:
            # Try singular form
            entity_id = self.parser.get_param(request, "entity_id", required=True)
            entity_ids = [entity_id]
        distance = self.parser.get_param(request, "distance", required=True)

        # Validate distance
        if not isinstance(distance, (int, float)) or distance <= 0:
            raise ValueError(f"Extrusion distance must be a positive number, got {distance}")

        # Get entities and reconstruct proper entity classes
        entities = []
        for entity_id in entity_ids:
            entity_data = self.entity_manager.get_entity(entity_id)
            if entity_data is None:
                raise ValueError(f"Entity '{entity_id}' not found")

            # Reconstruct proper entity class from database data
            entity_type = entity_data.entity_type
            props = entity_data.properties

            if entity_type == "line":
                entity = Line2D(
                    entity_id=entity_data.entity_id,
                    workspace_id=entity_data.workspace_id,
                    start=props.get("start", []),
                    end=props.get("end", [])
                )
            elif entity_type == "circle":
                entity = Circle2D(
                    entity_id=entity_data.entity_id,
                    workspace_id=entity_data.workspace_id,
                    center=props.get("center", []),
                    radius=props.get("radius", 0.0)
                )
            else:
                raise ValueError(f"Cannot extrude entity of type '{entity_type}'. Only lines and circles supported.")

            entities.append(entity)

        # Perform extrude operation
        workspace_id = self._get_active_workspace_id()
        solid = extrude_sketch(entity_ids, entities, distance, workspace_id)

        # Validate topology
        is_valid, errors = validate_topology(solid)
        solid.is_valid = is_valid
        solid.validation_errors = errors

        # Persist solid to database
        import json
        from datetime import datetime, timezone

        # Calculate bounding box (approximate for now)
        com = solid.center_of_mass
        # Simple approximation: extend from center of mass by half the box size
        # This will be improved when using real OCCT
        bbox = {
            "min": [com[0] - 10, com[1] - 10, com[2] - 10],
            "max": [com[0] + 10, com[1] + 10, com[2] + 10]
        }

        cursor = self.database.connection.cursor()
        cursor.execute("""
            INSERT INTO entities (
                entity_id, entity_type, workspace_id, properties, bounding_box,
                is_valid, validation_errors, created_at, modified_at, created_by_agent
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            solid.entity_id,
            "solid",
            solid.workspace_id,
            json.dumps({
                "volume": solid.volume,
                "surface_area": solid.surface_area,
                "center_of_mass": solid.center_of_mass,
                "topology": solid.topology.to_dict()
            }),
            json.dumps(bbox),
            solid.is_valid,
            json.dumps(solid.validation_errors),
            solid.created_at,
            solid.updated_at,
            "agent"
        ))

        self.database.connection.commit()

        # Log operation
        self.logger.info(
            f"Extruded solid {solid.entity_id}",
            volume=solid.volume,
            distance=distance
        )

        # Return solid data
        return solid.to_dict()

    def _handle_solid_boolean(self, request) -> dict[str, Any]:
        """Handle solid.boolean request."""
        from ..operations.solid_modeling import SolidBody, Topology, boolean_operation, validate_topology

        # Parse parameters
        operation = self.parser.get_param(request, "operation", required=True)
        entity_ids = self.parser.get_param(request, "entity_ids", required=True)

        # Validate operation
        valid_operations = ["union", "subtract", "intersect"]
        if operation not in valid_operations:
            raise ValueError(f"Invalid operation '{operation}'. Valid operations: {', '.join(valid_operations)}")

        # Validate entity count
        if len(entity_ids) < 2:
            raise ValueError(f"Boolean operations require at least 2 entities, got {len(entity_ids)}")

        # Get solid entities from database
        import json
        workspace_id = self._get_active_workspace_id()
        cursor = self.database.connection.cursor()

        solids = []
        for entity_id in entity_ids:
            # Read directly from database
            cursor.execute("""
                SELECT entity_id, entity_type, workspace_id, properties, is_valid, validation_errors
                FROM entities
                WHERE entity_id = ? AND workspace_id = ?
            """, (entity_id, workspace_id))
            row = cursor.fetchone()

            if row is None:
                raise ValueError(f"Entity '{entity_id}' not found")

            eid, etype, wid, properties_json, is_valid, validation_errors_json = row

            if etype != "solid":
                raise ValueError(f"Entity '{entity_id}' is not a solid (type: {etype})")

            # Parse properties
            props = json.loads(properties_json) if properties_json else {}
            topology_data = props.get("topology", {})

            # Parse validation errors
            validation_errors = json.loads(validation_errors_json) if validation_errors_json else []

            solid = SolidBody(
                entity_id=eid,
                workspace_id=wid,
                volume=props.get("volume", 0.0),
                surface_area=props.get("surface_area", 0.0),
                center_of_mass=props.get("center_of_mass", [0.0, 0.0, 0.0]),
                topology=Topology(
                    face_count=topology_data.get("face_count", 0),
                    edge_count=topology_data.get("edge_count", 0),
                    vertex_count=topology_data.get("vertex_count", 0),
                    is_closed=topology_data.get("is_closed", False),
                    is_manifold=topology_data.get("is_manifold", False)
                ),
                is_valid=is_valid,
                validation_errors=validation_errors
            )

            solids.append(solid)

        # Perform boolean operation
        result_solid = boolean_operation(operation, solids, workspace_id)

        # Validate topology
        is_valid, errors = validate_topology(result_solid)
        result_solid.is_valid = is_valid
        result_solid.validation_errors = errors

        # Persist result to database
        import json
        from datetime import datetime, timezone

        # Calculate bounding box
        com = result_solid.center_of_mass
        bbox = {
            "min": [com[0] - 10, com[1] - 10, com[2] - 10],
            "max": [com[0] + 10, com[1] + 10, com[2] + 10]
        }

        cursor = self.database.connection.cursor()
        cursor.execute("""
            INSERT INTO entities (
                entity_id, entity_type, workspace_id, properties, bounding_box,
                is_valid, validation_errors, created_at, modified_at, created_by_agent
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            result_solid.entity_id,
            "solid",
            result_solid.workspace_id,
            json.dumps({
                "volume": result_solid.volume,
                "surface_area": result_solid.surface_area,
                "center_of_mass": result_solid.center_of_mass,
                "topology": result_solid.topology.to_dict()
            }),
            json.dumps(bbox),
            result_solid.is_valid,
            json.dumps(result_solid.validation_errors),
            result_solid.created_at,
            result_solid.updated_at,
            "agent"
        ))

        self.database.connection.commit()

        # Log operation
        self.logger.info(
            f"Boolean {operation} created solid {result_solid.entity_id}",
            operation=operation,
            volume=result_solid.volume
        )

        # Return result data
        return result_solid.to_dict()

    def _handle_workspace_create(self, request) -> dict[str, Any]:
        """Handle workspace.create request."""
        # Parse parameters
        workspace_name = self.parser.get_param(request, "workspace_name", required=True)
        base_workspace_id = self.parser.get_param(request, "base_workspace_id", default="main")
        agent_id = request.params.get("agent_id", "default_agent")

        # Verify base workspace exists
        base_workspace = self.workspace_manager.get_workspace(base_workspace_id)
        if base_workspace is None:
            raise ValueError(f"Base workspace '{base_workspace_id}' not found")

        # Create workspace
        workspace = self.workspace_manager.create_workspace(
            workspace_name=workspace_name,
            workspace_type="agent_branch",
            base_workspace_id=base_workspace_id,
            owning_agent_id=agent_id
        )

        # Log operation
        self.logger.info(
            f"Created workspace {workspace.workspace_id}",
            workspace_name=workspace_name,
            base=base_workspace_id
        )

        return workspace.to_dict()

    def _handle_workspace_list(self, request) -> dict[str, Any]:
        """Handle workspace.list request."""
        workspaces = self.workspace_manager.list_workspaces()

        return {
            "workspaces": [ws.to_dict() for ws in workspaces]
        }

    def _handle_workspace_switch(self, request) -> dict[str, Any]:
        """Handle workspace.switch request."""
        workspace_id = self.parser.get_param(request, "workspace_id", required=True)

        # Switch to the workspace
        workspace = self.workspace_manager.set_active_workspace(workspace_id)

        # Log operation
        self.logger.info(f"Switched to workspace {workspace_id}")

        return workspace.to_dict()

    def _handle_workspace_status(self, request) -> dict[str, Any]:
        """Handle workspace.status request."""
        workspace_id = self.parser.get_param(request, "workspace_id")

        # If no workspace specified, use active workspace
        if workspace_id is None:
            workspace = self.workspace_manager.get_active_workspace()
            if workspace is None:
                raise ValueError("No active workspace")
        else:
            workspace = self.workspace_manager.get_workspace(workspace_id)
            if workspace is None:
                raise ValueError(f"Workspace '{workspace_id}' not found")

        # Get entity count for this workspace
        cursor = self.database.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM entities WHERE workspace_id = ?", (workspace.workspace_id,))
        entity_count = cursor.fetchone()[0]

        # Get operation count
        cursor.execute("SELECT COUNT(*) FROM operations WHERE workspace_id = ?", (workspace.workspace_id,))
        operation_count = cursor.fetchone()[0]

        # Update workspace counts
        workspace.entity_count = entity_count
        workspace.operation_count = operation_count

        result = workspace.to_dict()
        result["can_merge"] = workspace.can_merge()

        return result

    def _handle_workspace_merge(self, request) -> dict[str, Any]:
        """Handle workspace.merge request."""
        # Support both parameter naming conventions
        source_workspace_id = self.parser.get_param(request, "source_workspace_id")  
        if source_workspace_id is None:
            source_workspace_id = self.parser.get_param(request, "source_workspace", required=True)
        
        target_workspace_id = self.parser.get_param(request, "target_workspace_id")
        if target_workspace_id is None:
            target_workspace_id = self.parser.get_param(request, "target_workspace", required=True)

        # Verify workspaces exist
        source_workspace = self.workspace_manager.get_workspace(source_workspace_id)
        if source_workspace is None:
            raise ValueError(f"Source workspace '{source_workspace_id}' not found")
        source_workspace_id = source_workspace.workspace_id

        target_workspace = self.workspace_manager.get_workspace(target_workspace_id)
        if target_workspace is None:
            raise ValueError(f"Target workspace '{target_workspace_id}' not found")
        target_workspace_id = target_workspace.workspace_id

        # Check if source can be merged
        if not source_workspace.can_merge():
            raise ValueError(f"Workspace '{source_workspace_id}' cannot be merged (status: {source_workspace.branch_status})")

        # Perform merge: copy entities from source to target
        cursor = self.database.connection.cursor()

        # Get all entities from source workspace
        cursor.execute("""
            SELECT entity_id, entity_type, properties, bounding_box,
                   is_valid, validation_errors, created_at, modified_at, created_by_agent
            FROM entities
            WHERE workspace_id = ?
        """, (source_workspace_id,))

        entities_added = 0
        conflicts = []

        # Restore original query
        cursor.execute("""
            SELECT entity_id, entity_type, properties, bounding_box,
                   is_valid, validation_errors, created_at, modified_at, created_by_agent
            FROM entities
            WHERE workspace_id = ?
        """, (source_workspace_id,))

        for row in cursor.fetchall():
            entity_id, entity_type, properties, bbox, is_valid, val_errors, created_at, modified_at, created_by = row

            # Generate new entity ID for target workspace
            import uuid
            base_id = entity_id.split('_', 1)[1] if '_' in entity_id else str(uuid.uuid4())[:8]
            new_entity_id = f"{target_workspace_id}:{entity_type}_{base_id}"

            # Check if entity already exists in target (conflict detection)
            cursor.execute("SELECT entity_id FROM entities WHERE entity_id = ?", (new_entity_id,))
            if cursor.fetchone():
                conflicts.append({
                    "entity_id": new_entity_id,
                    "conflict_type": "entity_exists",
                    "source_workspace": source_workspace_id,
                    "target_workspace": target_workspace_id
                })
                continue

            # Insert entity into target workspace
            cursor.execute("""
                INSERT INTO entities (
                    entity_id, entity_type, workspace_id, properties, bounding_box,
                    is_valid, validation_errors, created_at, modified_at, created_by_agent
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (new_entity_id, entity_type, target_workspace_id, properties, bbox,
                  is_valid, val_errors, created_at, modified_at, created_by))

            entities_added += 1

        self.database.connection.commit()

        # Update workspace status
        self.workspace_manager.update_branch_status(source_workspace_id, "merged")

        # Log operation
        self.logger.info(
            f"Merged workspace {source_workspace_id} into {target_workspace_id}",
            entities_added=entities_added,
            conflicts=len(conflicts)
        )

        return {
            "merge_result": "success" if len(conflicts) == 0 else "has_conflicts",
            "source_workspace_id": source_workspace_id,
            "target_workspace_id": target_workspace_id,
            "entities_added": entities_added,
            "conflicts": conflicts
        }

    def _handle_workspace_resolve_conflict(self, request) -> dict[str, Any]:
        """Handle workspace.resolve_conflict request.

        Resolves merge conflicts by applying a resolution strategy.

        Args:
            entity_id: The conflicting entity ID
            source_workspace_id: Source workspace in conflict
            target_workspace_id: Target workspace in conflict
            strategy: Resolution strategy ('keep_source', 'keep_target', 'manual_merge')
            merged_properties: Optional properties for manual_merge strategy

        Returns:
            Resolution result with applied strategy
        """
        entity_id = self.parser.get_param(request, "entity_id", required=True)
        source_workspace_id = self.parser.get_param(request, "source_workspace_id", required=True)
        target_workspace_id = self.parser.get_param(request, "target_workspace_id", required=True)
        strategy = self.parser.get_param(request, "strategy", required=True)
        merged_properties = self.parser.get_param(request, "merged_properties", default=None)

        # Validate strategy
        valid_strategies = ["keep_source", "keep_target", "manual_merge"]
        if strategy not in valid_strategies:
            raise ValueError(f"Invalid strategy '{strategy}'. Valid: {', '.join(valid_strategies)}")

        # Get entity from source workspace
        cursor = self.database.connection.cursor()
        cursor.execute("""
            SELECT entity_type, properties, bounding_box, is_valid, validation_errors,
                   created_at, modified_at, created_by_agent
            FROM entities
            WHERE entity_id = ? AND workspace_id = ?
        """, (entity_id, source_workspace_id))

        source_row = cursor.fetchone()
        if not source_row:
            raise ValueError(f"Entity '{entity_id}' not found in source workspace '{source_workspace_id}'")

        # Get entity from target workspace (if exists)
        cursor.execute("""
            SELECT entity_type, properties, bounding_box, is_valid, validation_errors,
                   created_at, modified_at, created_by_agent
            FROM entities
            WHERE entity_id = ? AND workspace_id = ?
        """, (entity_id, target_workspace_id))

        target_row = cursor.fetchone()

        # Apply resolution strategy
        if strategy == "keep_source":
            # Use source entity, overwrite target
            entity_type, properties, bbox, is_valid, val_errors, created_at, modified_at, created_by = source_row
            resolution_note = "Kept source entity"

        elif strategy == "keep_target":
            # Keep target entity as-is
            if not target_row:
                raise ValueError(f"Cannot keep target - entity '{entity_id}' not found in target workspace")
            entity_type, properties, bbox, is_valid, val_errors, created_at, modified_at, created_by = target_row
            resolution_note = "Kept target entity"
            # No update needed
            return {
                "resolution_status": "resolved",
                "entity_id": entity_id,
                "strategy": strategy,
                "resolution_note": resolution_note
            }

        elif strategy == "manual_merge":
            # Use manually merged properties
            if merged_properties is None:
                raise ValueError("manual_merge strategy requires merged_properties parameter")

            import json
            entity_type, _, bbox, is_valid, val_errors, created_at, _, created_by = source_row
            properties = json.dumps(merged_properties)
            modified_at = datetime.now(timezone.utc).isoformat()
            resolution_note = "Applied manual merge"

        # Update or insert entity in target workspace
        import json
        from datetime import datetime, timezone

        if target_row:
            # Update existing entity
            cursor.execute("""
                UPDATE entities
                SET properties = ?, modified_at = ?
                WHERE entity_id = ? AND workspace_id = ?
            """, (properties, datetime.now(timezone.utc).isoformat(), entity_id, target_workspace_id))
        else:
            # Insert new entity
            cursor.execute("""
                INSERT INTO entities (
                    entity_id, entity_type, workspace_id, properties, bounding_box,
                    is_valid, validation_errors, created_at, modified_at, created_by_agent
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (entity_id, entity_type, target_workspace_id, properties, bbox,
                  is_valid, val_errors, created_at, modified_at, created_by))

        self.database.connection.commit()

        # Log resolution
        self.logger.info(
            f"Resolved conflict for entity {entity_id}",
            strategy=strategy,
            source_workspace=source_workspace_id,
            target_workspace=target_workspace_id
        )

        return {
            "resolution_status": "resolved",
            "entity_id": entity_id,
            "strategy": strategy,
            "resolution_note": resolution_note
        }

    def _handle_file_export(self, request) -> dict[str, Any]:
        """Handle file.export request."""
        # Parse parameters
        file_path = self.parser.get_param(request, "file_path", required=True)
        format_type = self.parser.get_param(request, "format", required=True)
        entity_ids = self.parser.get_param(request, "entity_ids", default=None)

        # Validate format
        supported_formats = ["json", "stl"]
        if format_type not in supported_formats:
            raise ValueError(f"Unsupported format '{format_type}'. Supported: {', '.join(supported_formats)}")

        workspace_id = self._get_active_workspace_id()

        # Get entities to export
        if entity_ids is None:
            # Export all entities in workspace
            cursor = self.database.connection.cursor()
            cursor.execute("""
                SELECT entity_id, entity_type, properties
                FROM entities
                WHERE workspace_id = ?
            """, (workspace_id,))
            rows = cursor.fetchall()

            entities = []
            for entity_id, entity_type, properties_json in rows:
                import json
                properties = json.loads(properties_json) if properties_json else {}
                entities.append({
                    "entity_id": entity_id,
                    "entity_type": entity_type,
                    **properties
                })
        else:
            # Export specific entities
            cursor = self.database.connection.cursor()
            entities = []
            for entity_id in entity_ids:
                # Read from database directly to handle all entity types including solids
                cursor.execute("""
                    SELECT entity_id, entity_type, properties
                    FROM entities
                    WHERE entity_id = ? AND workspace_id = ?
                """, (entity_id, workspace_id))
                row = cursor.fetchone()
                if row:
                    eid, etype, properties_json = row
                    import json
                    properties = json.loads(properties_json) if properties_json else {}
                    entities.append({
                        "entity_id": eid,
                        "entity_type": etype,
                        **properties
                    })

        # Export based on format
        if format_type == "json":
            from ..file_io.json_handler import export_json
            result = export_json(entities, file_path)
        elif format_type == "stl":
            from ..file_io.stl_handler import export_stl
            # Filter to only solid entities
            solids = [e for e in entities if e.get("entity_type") == "solid"]
            if len(solids) == 0:
                raise ValueError("No solid entities to export to STL")
            result = export_stl(solids, file_path)
        else:
            raise ValueError(f"Unsupported format: {format_type}")

        # Log operation
        self.logger.info(
            f"Exported {result['entity_count'] if 'entity_count' in result else len(entities)} entities to {file_path}",
            format=format_type
        )

        return result

    def _handle_file_import(self, request) -> dict[str, Any]:
        """Handle file.import request."""
        # Parse parameters
        file_path = self.parser.get_param(request, "file_path", required=True)
        format_type = self.parser.get_param(request, "format", required=True)

        # Validate format
        supported_formats = ["json"]
        if format_type not in supported_formats:
            raise ValueError(f"Unsupported import format '{format_type}'. Supported: {', '.join(supported_formats)}")

        # Import based on format
        if format_type == "json":
            from ..file_io.json_handler import import_json
            result = import_json(file_path)

            # Optionally persist imported entities
            # For now, just return the import report
        else:
            raise ValueError(f"Unsupported format: {format_type}")

        # Log operation
        self.logger.info(
            f"Imported {result['entity_count']} entities from {file_path}",
            format=format_type
        )

        return result

    def _handle_history_list(self, request) -> dict[str, Any]:
        """Handle history.list request."""
        workspace_id = self._get_active_workspace_id()
        history = self.history_manager.get_history(workspace_id)

        # Parse pagination parameters
        limit = self.parser.get_param(request, "limit", default=10)
        offset = self.parser.get_param(request, "offset", default=0)
        include_future = self.parser.get_param(request, "include_future", default=False)

        operations = history.list_operations(
            limit=limit,
            offset=offset,
            include_future=include_future
        )

        return {
            "operations": operations,
            "current_position": history.get_current_position(),
            "total_count": history.get_total_count(),
            "can_undo": history.can_undo(),
            "can_redo": history.can_redo()
        }

    def _handle_history_undo(self, request) -> dict[str, Any]:
        """Handle history.undo request."""
        workspace_id = self._get_active_workspace_id()
        history = self.history_manager.get_history(workspace_id)

        if not history.can_undo():
            raise ValueError("No operations to undo")

        # Get operation to undo
        operation = history.get_undo_operation()
        if operation is None:
            raise ValueError("No operations to undo")

        # For now, we don't have inverse operations implemented
        # So we just mark it as undone and return info
        # Full implementation would execute inverse operation
        history.mark_undo_complete()

        return {
            "undone_operation": operation.to_dict(),
            "new_position": history.get_current_position(),
            "can_undo": history.can_undo(),
            "can_redo": history.can_redo(),
            "note": "Undo/redo is conceptual only - inverse operations not yet implemented"
        }

    def _handle_history_redo(self, request) -> dict[str, Any]:
        """Handle history.redo request."""
        workspace_id = self._get_active_workspace_id()
        history = self.history_manager.get_history(workspace_id)

        if not history.can_redo():
            raise ValueError("No operations to redo")

        # Get operation to redo
        operation = history.get_redo_operation()
        if operation is None:
            raise ValueError("No operations to redo")

        # For now, we don't have operation replay implemented
        # So we just mark it as redone and return info
        history.mark_redo_complete()

        return {
            "redone_operation": operation.to_dict(),
            "new_position": history.get_current_position(),
            "can_undo": history.can_undo(),
            "can_redo": history.can_redo(),
            "note": "Undo/redo is conceptual only - operation replay not yet implemented"
        }

    def _handle_agent_metrics(self, request) -> dict[str, Any]:
        """Handle agent.metrics request."""
        # Get agent ID from params (default to "default_agent")
        agent_id = self.parser.get_param(request, "agent_id", default="default_agent")

        # Get metrics for the agent
        metrics = self.metrics_tracker.get_agent_metrics(agent_id)

        return metrics.to_dict()

    def _handle_scenario_run(self, request) -> dict[str, Any]:
        """Handle scenario.run request.

        Runs a built-in test scenario and validates results.

        Built-in scenarios:
        - create_point: Create a 3D point and validate coordinates
        - create_box: Create 4 lines forming a square, extrude to box, validate volume
        - boolean_union: Create two boxes, union them, validate volume
        - constrained_sketch: Create perpendicular lines with constraint
        - workspace_branch: Create and merge workspace branches

        Returns:
            Scenario execution results with validation
        """
        scenario_name = self.parser.get_param(request, "scenario_name", required=True)

        # Define available scenarios
        scenarios = {
            "create_point": self._scenario_create_point,
            "create_box": self._scenario_create_box,
            "boolean_union": self._scenario_boolean_union,
            "constrained_sketch": self._scenario_constrained_sketch,
            "workspace_branch": self._scenario_workspace_branch,
        }

        if scenario_name not in scenarios:
            raise ValueError(f"Unknown scenario '{scenario_name}'. Available: {', '.join(scenarios.keys())}")

        # Run scenario
        scenario_func = scenarios[scenario_name]
        result = scenario_func()

        return {
            "scenario_name": scenario_name,
            "status": result["status"],
            "steps_executed": result["steps"],
            "validation_results": result["validations"],
            "execution_summary": result["summary"]
        }

    def _scenario_create_point(self) -> dict[str, Any]:
        """Scenario: Create a 3D point and validate."""
        steps = []
        validations = []

        # Step 1: Create point
        point = self.entity_manager.create_point([10.0, 20.0, 30.0], workspace_id=self._get_active_workspace_id())
        steps.append("Created point at [10, 20, 30]")

        # Validate coordinates
        coords = point.coordinates
        expected = [10.0, 20.0, 30.0]
        if coords == expected:
            validations.append({"check": "coordinates", "status": "pass", "expected": expected, "actual": coords})
        else:
            validations.append({"check": "coordinates", "status": "fail", "expected": expected, "actual": coords})

        status = "pass" if all(v["status"] == "pass" for v in validations) else "fail"
        return {
            "status": status,
            "steps": steps,
            "validations": validations,
            "summary": f"Created point with {len(validations)} validations, all passed" if status == "pass" else "Point creation failed validation"
        }

    def _scenario_create_box(self) -> dict[str, Any]:
        """Scenario: Create a box from 4 lines and extrude."""
        steps = []
        validations = []
        workspace_id = self._get_active_workspace_id()

        # Step 1: Create 4 lines forming a square
        line1 = self.entity_manager.create_line([0, 0], [10, 0], workspace_id=workspace_id)
        line2 = self.entity_manager.create_line([10, 0], [10, 10], workspace_id=workspace_id)
        line3 = self.entity_manager.create_line([10, 10], [0, 10], workspace_id=workspace_id)
        line4 = self.entity_manager.create_line([0, 10], [0, 0], workspace_id=workspace_id)
        steps.append("Created 4 lines forming a 10x10 square")

        # Step 2: Extrude to create box
        from ..operations.solid_modeling import SolidModeling
        solid_ops = SolidModeling(self.entity_manager)
        solid = solid_ops.extrude(
            entity_ids=[line1.entity_id, line2.entity_id, line3.entity_id, line4.entity_id],
            distance=10.0,
            workspace_id=workspace_id
        )
        steps.append("Extruded square to height 10.0")

        # Validate volume (10x10x10 = 1000)
        expected_volume = 1000.0
        actual_volume = solid.volume
        tolerance = 0.1
        if abs(actual_volume - expected_volume) < tolerance:
            validations.append({"check": "volume", "status": "pass", "expected": expected_volume, "actual": actual_volume})
        else:
            validations.append({"check": "volume", "status": "fail", "expected": expected_volume, "actual": actual_volume})

        status = "pass" if all(v["status"] == "pass" for v in validations) else "fail"
        return {
            "status": status,
            "steps": steps,
            "validations": validations,
            "summary": f"Created box with volume {actual_volume:.2f}, expected {expected_volume}"
        }

    def _scenario_boolean_union(self) -> dict[str, Any]:
        """Scenario: Create two boxes and union them."""
        steps = []
        validations = []
        workspace_id = self._get_active_workspace_id()

        # Step 1: Create first box
        from ..operations.solid_modeling import SolidModeling
        solid_ops = SolidModeling(self.entity_manager)

        # Box 1: 10x10x10
        l1 = self.entity_manager.create_line([0, 0], [10, 0], workspace_id=workspace_id)
        l2 = self.entity_manager.create_line([10, 0], [10, 10], workspace_id=workspace_id)
        l3 = self.entity_manager.create_line([10, 10], [0, 10], workspace_id=workspace_id)
        l4 = self.entity_manager.create_line([0, 10], [0, 0], workspace_id=workspace_id)
        box1 = solid_ops.extrude([l1.entity_id, l2.entity_id, l3.entity_id, l4.entity_id], 10.0, workspace_id)
        steps.append("Created box 1: 10x10x10 (volume=1000)")

        # Step 2: Create second box (overlapping)
        l5 = self.entity_manager.create_line([5, 0], [15, 0], workspace_id=workspace_id)
        l6 = self.entity_manager.create_line([15, 0], [15, 10], workspace_id=workspace_id)
        l7 = self.entity_manager.create_line([15, 10], [5, 10], workspace_id=workspace_id)
        l8 = self.entity_manager.create_line([5, 10], [5, 0], workspace_id=workspace_id)
        box2 = solid_ops.extrude([l5.entity_id, l6.entity_id, l7.entity_id, l8.entity_id], 10.0, workspace_id)
        steps.append("Created box 2: 10x10x10 at offset (volume=1000)")

        # Step 3: Union
        result = solid_ops.boolean_union([box1.entity_id, box2.entity_id], workspace_id)
        steps.append("Performed boolean union")

        # Validate: Union of two overlapping boxes
        # Box 1: 0-10, Box 2: 5-15 = total width 15, height 10, depth 10 = 1500
        expected_volume = 1500.0
        actual_volume = result.volume
        tolerance = 50.0  # Allow some tolerance for simplified geometry
        if abs(actual_volume - expected_volume) < tolerance:
            validations.append({"check": "union_volume", "status": "pass", "expected": expected_volume, "actual": actual_volume})
        else:
            validations.append({"check": "union_volume", "status": "fail", "expected": expected_volume, "actual": actual_volume})

        status = "pass" if all(v["status"] == "pass" for v in validations) else "fail"
        return {
            "status": status,
            "steps": steps,
            "validations": validations,
            "summary": f"Union volume {actual_volume:.2f}, expected {expected_volume}"
        }

    def _scenario_constrained_sketch(self) -> dict[str, Any]:
        """Scenario: Create perpendicular lines with constraint."""
        steps = []
        validations = []
        workspace_id = self._get_active_workspace_id()

        # Step 1: Create two perpendicular lines
        line1 = self.entity_manager.create_line([0, 0], [10, 0], workspace_id=workspace_id)
        line2 = self.entity_manager.create_line([0, 0], [0, 10], workspace_id=workspace_id)
        steps.append("Created two perpendicular lines")

        # Step 2: Apply perpendicular constraint
        from ..operations.constraints import PerpendicularConstraint
        constraint = PerpendicularConstraint(
            constraint_id=f"{workspace_id}:constraint_perp",
            entity_ids=[line1.entity_id, line2.entity_id],
            workspace_id=workspace_id
        )
        self.constraint_graph.add_constraint(constraint)
        steps.append("Applied perpendicular constraint")

        # Step 3: Check satisfaction
        is_satisfied, error = constraint.check_satisfaction(self.entity_manager)
        validations.append({
            "check": "constraint_satisfied",
            "status": "pass" if is_satisfied else "fail",
            "expected": True,
            "actual": is_satisfied,
            "error": error if not is_satisfied else None
        })

        status = "pass" if all(v["status"] == "pass" for v in validations) else "fail"
        return {
            "status": status,
            "steps": steps,
            "validations": validations,
            "summary": f"Constraint {'satisfied' if is_satisfied else 'violated'}"
        }

    def _scenario_workspace_branch(self) -> dict[str, Any]:
        """Scenario: Create and merge workspace branches."""
        steps = []
        validations = []

        # Step 1: Create branch workspace
        branch_name = "test_branch"
        branch_ws = self.workspace_manager.create_workspace(branch_name, "agent_branch", "main", "test_agent")
        steps.append(f"Created branch workspace '{branch_name}'")

        # Step 2: Verify workspace exists
        retrieved = self.workspace_manager.get_workspace(branch_ws.workspace_id)
        if retrieved is not None:
            validations.append({"check": "workspace_created", "status": "pass", "expected": True, "actual": True})
        else:
            validations.append({"check": "workspace_created", "status": "fail", "expected": True, "actual": False})

        steps.append("Verified workspace exists")

        # Step 3: List workspaces
        workspaces = self.workspace_manager.list_workspaces()
        workspace_ids = [ws.workspace_id for ws in workspaces]
        if branch_ws.workspace_id in workspace_ids:
            validations.append({"check": "workspace_in_list", "status": "pass", "expected": True, "actual": True})
        else:
            validations.append({"check": "workspace_in_list", "status": "fail", "expected": True, "actual": False})

        steps.append("Verified workspace appears in list")

        status = "pass" if all(v["status"] == "pass" for v in validations) else "fail"
        return {
            "status": status,
            "steps": steps,
            "validations": validations,
            "summary": f"Workspace branching test completed with {len(validations)} checks"
        }


def main():
    """Main entry point for CLI application.

    Supports two modes:
    1. JSON-RPC mode (no args): Reads JSON-RPC requests from stdin
    2. Command-line mode (with args): Processes single command from argv
    """
    import argparse
    import json
    import os

    # Read workspace directory from environment variable if set
    workspace_dir = os.environ.get("MULTI_AGENT_WORKSPACE_DIR", "data/workspaces/main")
    cli = CLI(workspace_dir=workspace_dir)
    
    # Check if command-line arguments provided (legacy mode for tests)
    if len(sys.argv) > 1:
        # Command-line mode: parse arguments
        parser = argparse.ArgumentParser(description='CAD CLI Interface')
        parser.add_argument('method', help='JSON-RPC method name')
        parser.add_argument('--workspace_id', help='Workspace ID')
        parser.add_argument('--workspace_name', help='Workspace name')
        parser.add_argument('--source_workspace', help='Source workspace')
        parser.add_argument('--target_workspace', help='Target workspace')
        parser.add_argument('--workspace_dir', help='Workspace directory path')
        parser.add_argument('--x', type=float, help='X coordinate')
        parser.add_argument('--y', type=float, help='Y coordinate')
        parser.add_argument('--z', type=float, help='Z coordinate', default=0.0)
        parser.add_argument('--params', help='JSON params string')
        
        args = parser.parse_args()
        
        # Build JSON-RPC request from arguments
        params = {}
        if args.params:
            params = json.loads(args.params)
        else:
            # Extract params from known arguments
            if args.workspace_id:
                params['workspace_id'] = args.workspace_id
            if args.workspace_name:
                params['workspace_name'] = args.workspace_name
            elif args.workspace_id:
                # Fallback: use workspace_id as name if name not provided
                params['workspace_name'] = args.workspace_id
            if args.source_workspace:
                params['source_workspace'] = args.source_workspace
            if args.target_workspace:
                params['target_workspace'] = args.target_workspace
            if args.x is not None and args.y is not None:
                params['x'] = args.x
                params['y'] = args.y
                params['z'] = args.z
        
        # Create JSON-RPC request
        request_json = json.dumps({
            "jsonrpc": "2.0",
            "method": args.method,
            "params": params,
            "id": 1
        })
        
        # Initialize CLI with specified directory (check env var if not provided)
        workspace_dir = args.workspace_dir or os.environ.get("MULTI_AGENT_WORKSPACE_DIR")
        cli = CLI(workspace_dir=workspace_dir) if workspace_dir else CLI()

        try:
            # Process request and output result
            response = cli.process_request(request_json)
            print(response, end='')
        finally:
            # Ensure database connection is properly closed
            cli.database.close()
    else:
        # JSON-RPC mode: read from stdin
        # Check environment variable for workspace_dir in JSON-RPC mode
        import os
        workspace_dir = os.environ.get("MULTI_AGENT_WORKSPACE_DIR")
        cli = CLI(workspace_dir=workspace_dir) if workspace_dir else CLI()

        try:
            cli.run()
        finally:
            # Ensure database connection is properly closed
            cli.database.close()


if __name__ == "__main__":
    main()
