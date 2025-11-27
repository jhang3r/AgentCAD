"""Unified export manager for all CAD file formats.

Coordinates STEP and STL exports by retrieving geometry from database
and routing to appropriate format handlers.
"""
import time
from typing import List, Dict, Any, Optional
from pathlib import Path

from OCC.Core.TopoDS import TopoDS_Shape

# Import format handlers
from .step_handler import export_step
from .stl_handler import export_stl


class ExportManager:
    """Manage CAD file exports across multiple formats."""

    SUPPORTED_FORMATS = ["step", "stl"]

    def __init__(self, database_connection):
        """Initialize export manager.

        Args:
            database_connection: Database connection for retrieving geometry
        """
        self.db = database_connection

    def export_entities(
        self,
        entity_ids: List[str],
        file_path: str,
        format: str,
        workspace_id: str,
        **format_options
    ) -> Dict[str, Any]:
        """Export entities to specified format.

        Args:
            entity_ids: List of entity IDs to export
            file_path: Output file path
            format: Export format (step, stl)
            workspace_id: Workspace containing entities
            **format_options: Format-specific options:
                - STL: tessellation_quality, ascii
                - STEP: schema

        Returns:
            Export report dictionary

        Raises:
            ValueError: If format not supported or entities not found
            RuntimeError: If export fails
        """
        start_time = time.time()

        # Validate format
        format_lower = format.lower()
        if format_lower not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported export format: {format}. "
                f"Supported: {', '.join(self.SUPPORTED_FORMATS)}"
            )

        # Retrieve geometry shapes from database
        shapes = self._get_shapes_for_entities(entity_ids, workspace_id)

        if not shapes:
            raise ValueError(f"No valid geometry found for entities: {entity_ids}")

        # Route to appropriate format handler
        if format_lower == "step":
            result = self._export_step(shapes, file_path, **format_options)
        elif format_lower == "stl":
            result = self._export_stl(shapes, file_path, **format_options)
        else:
            raise ValueError(f"Format handler not implemented: {format}")

        # Add execution time
        execution_time_ms = int((time.time() - start_time) * 1000)
        result["execution_time_ms"] = execution_time_ms

        return result

    def export_workspace(
        self,
        workspace_id: str,
        file_path: str,
        format: str,
        **format_options
    ) -> Dict[str, Any]:
        """Export all solids in workspace to specified format.

        Args:
            workspace_id: Workspace ID
            file_path: Output file path
            format: Export format (step, stl)
            **format_options: Format-specific options

        Returns:
            Export report dictionary

        Raises:
            ValueError: If workspace has no solids
            RuntimeError: If export fails
        """
        # Get all solid entity IDs in workspace
        entity_ids = self._get_workspace_solids(workspace_id)

        if not entity_ids:
            raise ValueError(f"No solids found in workspace: {workspace_id}")

        return self.export_entities(
            entity_ids=entity_ids,
            file_path=file_path,
            format=format,
            workspace_id=workspace_id,
            **format_options
        )

    def _get_shapes_for_entities(
        self,
        entity_ids: List[str],
        workspace_id: str
    ) -> List[TopoDS_Shape]:
        """Retrieve TopoDS_Shape objects for entity IDs.

        Args:
            entity_ids: List of entity IDs
            workspace_id: Workspace ID

        Returns:
            List of TopoDS_Shape objects
        """
        from ..cad_kernel.geometry_engine import GeometryShape

        shapes = []
        cursor = self.db.cursor()

        for entity_id in entity_ids:
            # Get shape_id from entity
            cursor.execute(
                "SELECT shape_id FROM entities WHERE entity_id = ? AND workspace_id = ?",
                (entity_id, workspace_id)
            )
            row = cursor.fetchone()

            if not row or not row[0]:
                continue  # Skip entities without geometry

            shape_id = row[0]

            # Get geometry shape from database
            cursor.execute(
                """
                SELECT shape_id, shape_type, brep_data, is_valid, created_at, workspace_id
                FROM geometry_shapes
                WHERE shape_id = ?
                """,
                (shape_id,)
            )
            shape_row = cursor.fetchone()

            if not shape_row:
                continue

            # Reconstruct GeometryShape
            geo_shape = GeometryShape(
                shape_id=shape_row[0],
                shape_type=shape_row[1],
                brep_data=shape_row[2],
                is_valid=bool(shape_row[3]),
                created_at=shape_row[4],
                workspace_id=shape_row[5]
            )

            # Deserialize to TopoDS_Shape
            try:
                shape = geo_shape.to_shape()
                shapes.append(shape)
            except Exception as e:
                # Log error but continue with other shapes
                print(f"Warning: Failed to deserialize shape {shape_id}: {e}")
                continue

        return shapes

    def _get_workspace_solids(self, workspace_id: str) -> List[str]:
        """Get all solid entity IDs in workspace.

        Args:
            workspace_id: Workspace ID

        Returns:
            List of entity IDs with geometry
        """
        cursor = self.db.cursor()
        cursor.execute(
            """
            SELECT entity_id FROM entities
            WHERE workspace_id = ? AND shape_id IS NOT NULL
            ORDER BY created_at
            """,
            (workspace_id,)
        )
        return [row[0] for row in cursor.fetchall()]

    def _export_step(
        self,
        shapes: List[TopoDS_Shape],
        file_path: str,
        schema: str = "AP214"
    ) -> Dict[str, Any]:
        """Export shapes to STEP format.

        Args:
            shapes: List of TopoDS_Shape objects
            file_path: Output file path
            schema: STEP schema (AP203, AP214, AP242)

        Returns:
            Export report dictionary
        """
        return export_step(shapes, file_path, schema=schema)

    def _export_stl(
        self,
        shapes: List[TopoDS_Shape],
        file_path: str,
        tessellation_quality: str = "standard",
        ascii: bool = False
    ) -> Dict[str, Any]:
        """Export shapes to STL format.

        Args:
            shapes: List of TopoDS_Shape objects
            file_path: Output file path
            tessellation_quality: Quality preset (preview, standard, high_quality)
            ascii: Whether to use ASCII format

        Returns:
            Export report dictionary
        """
        return export_stl(
            shapes,
            file_path,
            tessellation_quality=tessellation_quality,
            ascii_format=ascii
        )
