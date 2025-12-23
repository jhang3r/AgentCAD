"""
Shared state management using local Supabase (PostgreSQL) for multi-agent humanoid design system.
Provides thread-safe, transactional access for parallel agent execution.
"""

import os
import json
from pathlib import Path
from typing import Any, Dict, Optional, List
from datetime import datetime, timedelta
from contextlib import contextmanager
import uuid

from supabase import create_client, Client
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from psycopg2.pool import ThreadedConnectionPool

load_dotenv()


class SharedState:
    """Manages shared state between agents via Supabase/PostgreSQL database."""

    def __init__(self, execution_id: Optional[str] = None):
        """
        Initialize shared state connection.

        Args:
            execution_id: Unique ID for this agent execution (for tracking related activities)
        """
        self.execution_id = execution_id or str(uuid.uuid4())

        # Database connection
        self.db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/agentcad")

        # Connection pool for concurrent access
        self._pool = None
        self._init_connection_pool()

    def _init_connection_pool(self):
        """Initialize PostgreSQL connection pool."""
        try:
            self._pool = ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                dsn=self.db_url
            )
        except Exception as e:
            print(f"Error initializing connection pool: {e}")
            raise

    @contextmanager
    def get_connection(self):
        """Context manager for getting a database connection from the pool."""
        conn = self._pool.getconn()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            self._pool.putconn(conn)

    def close(self):
        """Close all database connections."""
        if self._pool:
            self._pool.closeall()

    # ==================== LOCK MANAGEMENT ====================

    def acquire_lock(self, resource_type: str, resource_name: str, agent_name: str, timeout_seconds: int = 300) -> bool:
        """
        Acquire a lock on a resource for exclusive access.

        Args:
            resource_type: Type of resource ('subsystem', 'conflict', 'global_constraints')
            resource_name: Name of the specific resource
            agent_name: Name of the agent acquiring the lock
            timeout_seconds: How long the lock is valid

        Returns:
            True if lock acquired, False if already locked
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # Clean up expired locks first
                cur.execute("SELECT cleanup_expired_locks()")

                # Try to insert lock
                expires_at = datetime.utcnow() + timedelta(seconds=timeout_seconds)
                try:
                    cur.execute("""
                        INSERT INTO agent_locks (resource_type, resource_name, locked_by, execution_id, expires_at)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (resource_type, resource_name, agent_name, self.execution_id, expires_at))
                    return True
                except psycopg2.IntegrityError:
                    # Lock already exists
                    return False

    def release_lock(self, resource_type: str, resource_name: str):
        """Release a lock on a resource."""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM agent_locks
                    WHERE resource_type = %s AND resource_name = %s AND execution_id = %s
                """, (resource_type, resource_name, self.execution_id))

    # ==================== GLOBAL CONSTRAINTS ====================

    def get_global_constraints(self) -> Optional[Dict[str, Any]]:
        """Get the latest global design constraints."""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM global_constraints
                    ORDER BY version DESC LIMIT 1
                """)
                result = cur.fetchone()
                return dict(result) if result else None

    def update_global_constraints(self, constraints: Dict[str, Any], agent_name: str = "system_architect"):
        """
        Update global constraints with a new version.

        Args:
            constraints: Dictionary containing constraint data
            agent_name: Name of agent making the update
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # Get current version
                cur.execute("SELECT COALESCE(MAX(version), 0) + 1 as next_version FROM global_constraints")
                next_version = cur.fetchone()[0]

                cur.execute("""
                    INSERT INTO global_constraints
                    (version, total_mass_kg_max, total_cost_usd_max, height_m, voltage_v, budget_allocations)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    next_version,
                    constraints.get('total_mass_kg_max'),
                    constraints.get('total_cost_usd_max'),
                    constraints.get('height_m'),
                    constraints.get('voltage_v'),
                    Json(constraints.get('budget_allocations', {}))
                ))

                self.log_agent_activity(agent_name, "updated_global_constraints", {
                    "version": next_version
                })

    # ==================== SUBSYSTEMS ====================

    def get_subsystem_status(self, subsystem: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific subsystem."""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM subsystems WHERE name = %s
                """, (subsystem,))
                result = cur.fetchone()
                return dict(result) if result else None

    def update_subsystem_status(self, subsystem: str, status: Dict[str, Any]):
        """
        Update status of a specific subsystem.

        Args:
            subsystem: Name of the subsystem
            status: Dictionary containing status fields
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE subsystems SET
                        state = %s,
                        current_mass_kg = %s,
                        current_cost_usd = %s,
                        current_power_w = %s,
                        iteration = COALESCE(%s, iteration + 1),
                        within_budget = %s,
                        metadata = %s,
                        last_agent_execution_id = %s,
                        updated_at = NOW()
                    WHERE name = %s
                """, (
                    status.get('state'),
                    status.get('current_mass_kg', 0),
                    status.get('current_cost_usd', 0),
                    status.get('current_power_w', 0),
                    status.get('iteration'),
                    status.get('within_budget', True),
                    Json(status.get('metadata', {})),
                    self.execution_id,
                    subsystem
                ))

    def get_all_subsystem_statuses(self) -> List[Dict[str, Any]]:
        """Get status of all subsystems."""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM system_status ORDER BY name")
                return [dict(row) for row in cur.fetchall()]

    # ==================== REQUIREMENTS ====================

    def get_subsystem_requirements(self, subsystem: str, version: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Get requirements for a subsystem.

        Args:
            subsystem: Name of the subsystem
            version: Specific version (None for latest)
        """
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if version:
                    cur.execute("""
                        SELECT * FROM subsystem_requirements
                        WHERE subsystem_name = %s AND version = %s
                    """, (subsystem, version))
                else:
                    cur.execute("""
                        SELECT * FROM subsystem_requirements
                        WHERE subsystem_name = %s
                        ORDER BY version DESC LIMIT 1
                    """, (subsystem,))
                result = cur.fetchone()
                return dict(result) if result else None

    def update_subsystem_requirements(self, subsystem: str, requirements: Dict[str, Any], created_by: str = "system_architect"):
        """
        Update requirements for a subsystem.

        Args:
            subsystem: Name of the subsystem
            requirements: Requirements data
            created_by: Agent creating these requirements
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # Get next version
                cur.execute("""
                    SELECT COALESCE(MAX(version), 0) + 1 as next_version
                    FROM subsystem_requirements WHERE subsystem_name = %s
                """, (subsystem,))
                next_version = cur.fetchone()[0]

                cur.execute("""
                    INSERT INTO subsystem_requirements (subsystem_name, version, requirements, created_by)
                    VALUES (%s, %s, %s, %s)
                """, (subsystem, next_version, Json(requirements), created_by))

    # ==================== INTERFACES ====================

    def get_subsystem_interfaces(self, subsystem: str, version: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Get interface definitions published by a subsystem."""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if version:
                    cur.execute("""
                        SELECT * FROM subsystem_interfaces
                        WHERE subsystem_name = %s AND version = %s
                    """, (subsystem, version))
                else:
                    cur.execute("""
                        SELECT * FROM subsystem_interfaces
                        WHERE subsystem_name = %s
                        ORDER BY version DESC LIMIT 1
                    """, (subsystem,))
                result = cur.fetchone()
                return dict(result) if result else None

    def update_subsystem_interfaces(self, subsystem: str, interfaces: Dict[str, Any]):
        """Update interface definitions for a subsystem."""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # Get next version
                cur.execute("""
                    SELECT COALESCE(MAX(version), 0) + 1 as next_version
                    FROM subsystem_interfaces WHERE subsystem_name = %s
                """, (subsystem,))
                next_version = cur.fetchone()[0]

                cur.execute("""
                    INSERT INTO subsystem_interfaces (subsystem_name, version, interfaces)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (subsystem_name, version)
                    DO UPDATE SET interfaces = EXCLUDED.interfaces, updated_at = NOW()
                """, (subsystem, next_version, Json(interfaces)))

    # ==================== DESIGNS ====================

    def get_subsystem_design(self, subsystem: str, version: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Get detailed design data for a subsystem."""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if version:
                    cur.execute("""
                        SELECT * FROM subsystem_designs
                        WHERE subsystem_name = %s AND version = %s
                    """, (subsystem, version))
                else:
                    cur.execute("""
                        SELECT * FROM subsystem_designs
                        WHERE subsystem_name = %s
                        ORDER BY version DESC LIMIT 1
                    """, (subsystem,))
                result = cur.fetchone()
                return dict(result) if result else None

    def update_subsystem_design(self, subsystem: str, design_data: Dict[str, Any]):
        """Update detailed design data for a subsystem."""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # Get next version
                cur.execute("""
                    SELECT COALESCE(MAX(version), 0) + 1 as next_version
                    FROM subsystem_designs WHERE subsystem_name = %s
                """, (subsystem,))
                next_version = cur.fetchone()[0]

                cur.execute("""
                    INSERT INTO subsystem_designs (subsystem_name, version, design_data)
                    VALUES (%s, %s, %s)
                """, (subsystem, next_version, Json(design_data)))

    # ==================== CONFLICTS ====================

    def log_conflict(self, severity: str, source: str, target: str, description: str,
                    details: Dict[str, Any] = None, priority: int = 3, blocks: List[str] = None) -> int:
        """
        Log a constraint conflict.

        Args:
            severity: Conflict severity (critical, high, medium, low)
            source: Source agent name
            target: Target agent name
            description: Conflict description
            details: Additional details
            priority: Priority level (1=critical, 2=high, 3=medium, 4=low)
            blocks: List of agent names that are blocked

        Returns:
            Conflict ID
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # Get next conflict ID
                cur.execute("SELECT COALESCE(MAX(conflict_id), 0) + 1 as next_id FROM conflicts")
                conflict_id = cur.fetchone()[0]

                cur.execute("""
                    INSERT INTO conflicts (
                        conflict_id, severity, priority, source_agent, target_agent,
                        description, details, blocks_agents
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    conflict_id,
                    severity,
                    priority,
                    source,
                    target,
                    description,
                    Json(details or {}),
                    blocks or []
                ))

                self.log_agent_activity(source, "conflict_created", {
                    "conflict_id": conflict_id,
                    "severity": severity,
                    "target": target
                })

                return conflict_id

    def resolve_conflict(self, conflict_id: int, resolution: str, resolved_by: str):
        """Mark a conflict as resolved."""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE conflicts SET
                        status = 'resolved',
                        resolution = %s,
                        resolved_at = NOW(),
                        resolved_by = %s
                    WHERE conflict_id = %s
                """, (resolution, resolved_by, conflict_id))

                self.log_agent_activity(resolved_by, "conflict_resolved", {
                    "conflict_id": conflict_id
                })

    def get_active_conflicts(self, agent_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all active conflicts, optionally filtered by agent.

        Args:
            agent_name: Filter by agent involved in conflict
        """
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if agent_name:
                    cur.execute("""
                        SELECT * FROM conflicts
                        WHERE status = 'open'
                        AND (source_agent = %s OR target_agent = %s OR %s = ANY(blocks_agents))
                        ORDER BY priority, created_at
                    """, (agent_name, agent_name, agent_name))
                else:
                    cur.execute("""
                        SELECT * FROM conflicts
                        WHERE status = 'open'
                        ORDER BY priority, created_at
                    """)
                return [dict(row) for row in cur.fetchall()]

    # ==================== ACTIVITY LOGGING ====================

    def log_agent_activity(self, agent_name: str, activity: str, details: Dict[str, Any] = None):
        """Log agent activity for monitoring."""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO agent_activity_logs (agent_name, activity, details, execution_id)
                    VALUES (%s, %s, %s, %s)
                """, (agent_name, activity, Json(details or {}), self.execution_id))

    def get_recent_activity(self, limit: int = 50, agent_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recent agent activity logs."""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if agent_name:
                    cur.execute("""
                        SELECT * FROM agent_activity_logs
                        WHERE agent_name = %s
                        ORDER BY timestamp DESC LIMIT %s
                    """, (agent_name, limit))
                else:
                    cur.execute("""
                        SELECT * FROM agent_activity_logs
                        ORDER BY timestamp DESC LIMIT %s
                    """, (limit,))
                return [dict(row) for row in cur.fetchall()]

    # ==================== CAD GEOMETRY STORAGE ====================

    def store_cad_component(self, component_name: str, component_type: str, subsystem: str,
                           geometry_data: bytes, file_format: str = "STEP",
                           metadata: Dict[str, Any] = None, created_by: str = None) -> str:
        """
        Store a CAD component (.STEP file) in the database.

        Args:
            component_name: Name of the component (e.g., "femur_right", "hip_joint")
            component_type: Type ('bone', 'joint', 'motor_mount', 'gear', 'custom')
            subsystem: Which subsystem owns this component
            geometry_data: Binary STEP file data
            file_format: File format (default 'STEP')
            metadata: Additional metadata (mass, material, dimensions, etc.)
            created_by: Agent creating this component

        Returns:
            Component UUID
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # Get next version
                cur.execute("""
                    SELECT COALESCE(MAX(version), 0) + 1 as next_version
                    FROM cad_components WHERE component_name = %s
                """, (component_name,))
                next_version = cur.fetchone()[0]

                cur.execute("""
                    INSERT INTO cad_components (
                        component_name, component_type, subsystem_name, version,
                        file_format, geometry_data, file_size_bytes, metadata, created_by
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    component_name,
                    component_type,
                    subsystem,
                    next_version,
                    file_format,
                    psycopg2.Binary(geometry_data),
                    len(geometry_data),
                    Json(metadata or {}),
                    created_by or self.execution_id
                ))

                component_id = cur.fetchone()[0]

                self.log_agent_activity(created_by or "unknown", "cad_component_stored", {
                    "component_name": component_name,
                    "component_type": component_type,
                    "version": next_version,
                    "size_bytes": len(geometry_data)
                })

                return str(component_id)

    def get_cad_component(self, component_name: str, version: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Retrieve a CAD component from the database.

        Args:
            component_name: Name of the component
            version: Specific version (None for latest)

        Returns:
            Dictionary with component data including geometry_data as bytes
        """
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if version:
                    cur.execute("""
                        SELECT * FROM cad_components
                        WHERE component_name = %s AND version = %s
                    """, (component_name, version))
                else:
                    cur.execute("""
                        SELECT * FROM cad_components
                        WHERE component_name = %s
                        ORDER BY version DESC LIMIT 1
                    """, (component_name,))

                result = cur.fetchone()
                if result:
                    component = dict(result)
                    # Convert memoryview to bytes
                    if 'geometry_data' in component:
                        component['geometry_data'] = bytes(component['geometry_data'])
                    return component
                return None

    def get_subsystem_components(self, subsystem: str) -> List[Dict[str, Any]]:
        """Get all CAD components for a subsystem."""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT component_name, component_type, version, file_format,
                           file_size_bytes, metadata, created_at
                    FROM cad_components
                    WHERE subsystem_name = %s
                    ORDER BY component_type, component_name, version DESC
                """, (subsystem,))
                return [dict(row) for row in cur.fetchall()]

    def export_cad_component_to_file(self, component_name: str, output_path: str, version: Optional[int] = None):
        """
        Export a CAD component to a file.

        Args:
            component_name: Name of the component
            output_path: Where to write the file
            version: Specific version (None for latest)
        """
        component = self.get_cad_component(component_name, version)
        if not component:
            raise ValueError(f"Component '{component_name}' not found")

        with open(output_path, 'wb') as f:
            f.write(component['geometry_data'])

        return component['metadata']

    def store_cad_assembly(self, assembly_name: str, subsystem: str,
                          assembly_tree: Dict[str, Any], created_by: str = None) -> str:
        """
        Store a CAD assembly definition.

        Args:
            assembly_name: Name of the assembly
            subsystem: Which subsystem owns this
            assembly_tree: Hierarchical component structure with transforms
            created_by: Agent creating this

        Returns:
            Assembly UUID
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # Get next version
                cur.execute("""
                    SELECT COALESCE(MAX(version), 0) + 1 as next_version
                    FROM cad_assemblies WHERE assembly_name = %s
                """, (assembly_name,))
                next_version = cur.fetchone()[0]

                cur.execute("""
                    INSERT INTO cad_assemblies (assembly_name, subsystem_name, version, assembly_tree, created_by)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """, (assembly_name, subsystem, next_version, Json(assembly_tree), created_by or self.execution_id))

                return str(cur.fetchone()[0])

    def add_component_to_library(self, part_number: str, manufacturer: str, part_name: str,
                                 category: str, specifications: Dict[str, Any],
                                 cost_usd: float = None, mass_kg: float = None,
                                 geometry_id: str = None, **kwargs) -> str:
        """
        Add a component to the reusable library (motors, bearings, fasteners).

        Args:
            part_number: Manufacturer part number
            manufacturer: Manufacturer name
            part_name: Descriptive name
            category: 'bearing', 'motor', 'fastener', 'sensor', 'battery'
            specifications: All technical specs
            cost_usd: Cost in USD
            mass_kg: Mass in kg
            geometry_id: Link to CAD geometry (optional)
            **kwargs: Additional fields (datasheet_url, supplier_url, etc.)

        Returns:
            Component library UUID
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO component_library (
                        part_number, manufacturer, part_name, category, specifications,
                        cost_usd, mass_kg, geometry_id, datasheet_url, supplier_url
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (part_number) DO UPDATE SET
                        cost_usd = EXCLUDED.cost_usd,
                        mass_kg = EXCLUDED.mass_kg,
                        in_stock = true
                    RETURNING id
                """, (
                    part_number,
                    manufacturer,
                    part_name,
                    category,
                    Json(specifications),
                    cost_usd,
                    mass_kg,
                    geometry_id,
                    kwargs.get('datasheet_url'),
                    kwargs.get('supplier_url')
                ))

                return str(cur.fetchone()[0])

    def search_component_library(self, category: str = None, **filters) -> List[Dict[str, Any]]:
        """
        Search the component library.

        Args:
            category: Filter by category
            **filters: Additional filters (e.g., max_cost_usd=500, min_mass_kg=0.1)

        Returns:
            List of matching components
        """
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = "SELECT * FROM component_library WHERE in_stock = true"
                params = []

                if category:
                    query += " AND category = %s"
                    params.append(category)

                if 'max_cost_usd' in filters:
                    query += " AND cost_usd <= %s"
                    params.append(filters['max_cost_usd'])

                if 'min_mass_kg' in filters:
                    query += " AND mass_kg >= %s"
                    params.append(filters['min_mass_kg'])

                query += " ORDER BY category, part_number"

                cur.execute(query, params)
                return [dict(row) for row in cur.fetchall()]
