"""Open CASCADE geometry engine wrapper for shape serialization and validation."""
import uuid
from datetime import datetime
from typing import Optional

from OCC.Core.TopoDS import TopoDS_Shape
from OCC.Core.BRepTools import BRepTools_ShapeSet
from OCC.Core.BRepCheck import BRepCheck_Analyzer
from OCC.Core.TopAbs import (
    TopAbs_SOLID,
    TopAbs_SHELL,
    TopAbs_FACE,
    TopAbs_WIRE,
    TopAbs_EDGE,
    TopAbs_VERTEX,
    TopAbs_COMPOUND
)

from .exceptions import InvalidGeometryError, ShapeSerializationError


class GeometryShape:
    """Wrapper for Open CASCADE TopoDS_Shape with serialization support.

    This class provides:
    - BRep serialization/deserialization for database storage
    - Shape validation using BRepCheck_Analyzer
    - Shape type detection and management
    """

    # Shape type mapping
    SHAPE_TYPES = {
        TopAbs_SOLID: "SOLID",
        TopAbs_SHELL: "SHELL",
        TopAbs_FACE: "FACE",
        TopAbs_WIRE: "WIRE",
        TopAbs_EDGE: "EDGE",
        TopAbs_VERTEX: "VERTEX",
        TopAbs_COMPOUND: "COMPOUND"
    }

    def __init__(
        self,
        shape_id: str,
        shape_type: str,
        brep_data: str,
        is_valid: bool,
        created_at: str,
        workspace_id: str
    ):
        """Initialize geometry shape from database record.

        Args:
            shape_id: Unique shape identifier
            shape_type: Shape type (SOLID, SHELL, FACE, etc.)
            brep_data: Serialized BRep string
            is_valid: Whether shape passed validation
            created_at: Creation timestamp
            workspace_id: Owning workspace ID
        """
        self.shape_id = shape_id
        self.shape_type = shape_type
        self.brep_data = brep_data
        self.is_valid = is_valid
        self.created_at = created_at
        self.workspace_id = workspace_id
        self._cached_shape: Optional[TopoDS_Shape] = None

    @classmethod
    def from_shape(
        cls,
        shape: TopoDS_Shape,
        workspace_id: str,
        validate: bool = True
    ) -> "GeometryShape":
        """Create GeometryShape from Open CASCADE TopoDS_Shape.

        Args:
            shape: Open CASCADE shape object
            workspace_id: Workspace this shape belongs to
            validate: Whether to validate shape (default True)

        Returns:
            GeometryShape instance

        Raises:
            InvalidGeometryError: If validation fails and validate=True
            ShapeSerializationError: If BRep serialization fails
        """
        # Validate shape if requested
        is_valid = True
        if validate:
            analyzer = BRepCheck_Analyzer(shape)
            is_valid = analyzer.IsValid()
            if not is_valid:
                raise InvalidGeometryError(
                    f"Shape validation failed. Shape is not valid according to BRepCheck_Analyzer."
                )

        # Determine shape type
        shape_type = cls._get_shape_type(shape)

        # Serialize to BRep format
        try:
            import tempfile
            import os
            from OCC.Core.BRepTools import breptools_Write

            # Use temporary file for serialization
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.brep', delete=False) as tmp:
                tmp_path = tmp.name

            try:
                # Write shape to temporary file
                breptools_Write(shape, tmp_path)

                # Read back as string
                with open(tmp_path, 'r') as f:
                    brep_data = f.read()
            finally:
                # Clean up temporary file
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

        except Exception as e:
            raise ShapeSerializationError(f"Failed to serialize shape to BRep: {e}")

        # Generate unique ID and timestamp
        shape_id = str(uuid.uuid4())
        created_at = datetime.utcnow().isoformat()

        # Create instance
        instance = cls(
            shape_id=shape_id,
            shape_type=shape_type,
            brep_data=brep_data,
            is_valid=is_valid,
            created_at=created_at,
            workspace_id=workspace_id
        )
        instance._cached_shape = shape  # Cache the shape to avoid deserializing
        return instance

    def to_shape(self) -> TopoDS_Shape:
        """Deserialize BRep data to Open CASCADE TopoDS_Shape.

        Returns:
            TopoDS_Shape reconstructed from BRep data

        Raises:
            ShapeSerializationError: If deserialization fails
        """
        # Return cached shape if available
        if self._cached_shape is not None:
            return self._cached_shape

        # Deserialize from BRep
        try:
            import tempfile
            import os
            from OCC.Core.BRepTools import breptools_Read
            from OCC.Core.TopoDS import TopoDS_Shape as TopoDS_Shape_Constructor

            # Use temporary file for deserialization
            with tempfile.NamedTemporaryFile(mode='w', suffix='.brep', delete=False) as tmp:
                tmp.write(self.brep_data)
                tmp_path = tmp.name

            try:
                # Read shape from temporary file
                reconstructed_shape = TopoDS_Shape_Constructor()
                from OCC.Core.BRep import BRep_Builder
                builder = BRep_Builder()
                breptools_Read(reconstructed_shape, tmp_path, builder)

                # Cache for future use
                self._cached_shape = reconstructed_shape
                return reconstructed_shape
            finally:
                # Clean up temporary file
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

        except Exception as e:
            raise ShapeSerializationError(
                f"Failed to deserialize BRep data for shape {self.shape_id}: {e}"
            )

    def validate(self) -> bool:
        """Validate shape topology using BRepCheck_Analyzer.

        Returns:
            True if shape is valid, False otherwise
        """
        try:
            shape = self.to_shape()
            analyzer = BRepCheck_Analyzer(shape)
            self.is_valid = analyzer.IsValid()
            return self.is_valid
        except Exception:
            self.is_valid = False
            return False

    @staticmethod
    def _get_shape_type(shape: TopoDS_Shape) -> str:
        """Determine the type of an Open CASCADE shape.

        Args:
            shape: TopoDS_Shape to inspect

        Returns:
            Shape type string (SOLID, SHELL, FACE, etc.)
        """
        shape_enum = shape.ShapeType()
        return GeometryShape.SHAPE_TYPES.get(shape_enum, "UNKNOWN")

    def to_dict(self) -> dict:
        """Convert to dictionary for database storage.

        Returns:
            Dictionary with all shape fields
        """
        return {
            "shape_id": self.shape_id,
            "shape_type": self.shape_type,
            "brep_data": self.brep_data,
            "is_valid": self.is_valid,
            "created_at": self.created_at,
            "workspace_id": self.workspace_id
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GeometryShape":
        """Create GeometryShape from dictionary (database record).

        Args:
            data: Dictionary with shape fields

        Returns:
            GeometryShape instance
        """
        return cls(
            shape_id=data["shape_id"],
            shape_type=data["shape_type"],
            brep_data=data["brep_data"],
            is_valid=data["is_valid"],
            created_at=data["created_at"],
            workspace_id=data["workspace_id"]
        )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"GeometryShape(id={self.shape_id[:8]}..., "
            f"type={self.shape_type}, valid={self.is_valid})"
        )
