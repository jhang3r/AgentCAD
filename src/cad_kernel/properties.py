"""Geometric property computation for 3D solids using Open CASCADE."""
from datetime import datetime
from typing import Optional

from OCC.Core.TopoDS import TopoDS_Shape
from OCC.Core.GProp import GProp_GProps
from OCC.Core.BRepGProp import (
    brepgprop_VolumeProperties,
    brepgprop_SurfaceProperties
)
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopAbs import TopAbs_FACE, TopAbs_EDGE, TopAbs_VERTEX
from OCC.Core.BRep import BRep_Tool
from OCC.Core.BRepCheck import BRepCheck_Analyzer

from .exceptions import PropertyComputationError


class SolidProperties:
    """Computed geometric properties for 3D solids.

    This class computes and caches properties like volume, surface area,
    center of mass, bounding box, and topology information.
    """

    def __init__(
        self,
        entity_id: str,
        volume: float = 0.0,
        surface_area: float = 0.0,
        center_of_mass_x: float = 0.0,
        center_of_mass_y: float = 0.0,
        center_of_mass_z: float = 0.0,
        bounding_box_min_x: float = 0.0,
        bounding_box_min_y: float = 0.0,
        bounding_box_min_z: float = 0.0,
        bounding_box_max_x: float = 0.0,
        bounding_box_max_y: float = 0.0,
        bounding_box_max_z: float = 0.0,
        face_count: int = 0,
        edge_count: int = 0,
        vertex_count: int = 0,
        is_closed: bool = False,
        is_manifold: bool = False,
        computed_at: Optional[str] = None
    ):
        """Initialize solid properties.

        Args:
            entity_id: Reference to CAD entity
            volume: Volume in cubic units
            surface_area: Surface area in square units
            center_of_mass_x: COM X coordinate
            center_of_mass_y: COM Y coordinate
            center_of_mass_z: COM Z coordinate
            bounding_box_min_x: Bounding box minimum X
            bounding_box_min_y: Bounding box minimum Y
            bounding_box_min_z: Bounding box minimum Z
            bounding_box_max_x: Bounding box maximum X
            bounding_box_max_y: Bounding box maximum Y
            bounding_box_max_z: Bounding box maximum Z
            face_count: Number of faces
            edge_count: Number of edges
            vertex_count: Number of vertices
            is_closed: Whether solid is closed
            is_manifold: Whether solid is manifold
            computed_at: Timestamp when computed
        """
        self.entity_id = entity_id
        self.volume = volume
        self.surface_area = surface_area
        self.center_of_mass_x = center_of_mass_x
        self.center_of_mass_y = center_of_mass_y
        self.center_of_mass_z = center_of_mass_z
        self.bounding_box_min_x = bounding_box_min_x
        self.bounding_box_min_y = bounding_box_min_y
        self.bounding_box_min_z = bounding_box_min_z
        self.bounding_box_max_x = bounding_box_max_x
        self.bounding_box_max_y = bounding_box_max_y
        self.bounding_box_max_z = bounding_box_max_z
        self.face_count = face_count
        self.edge_count = edge_count
        self.vertex_count = vertex_count
        self.is_closed = is_closed
        self.is_manifold = is_manifold
        self.computed_at = computed_at or datetime.utcnow().isoformat()

    @classmethod
    def compute_from_shape(cls, entity_id: str, shape: TopoDS_Shape) -> "SolidProperties":
        """Compute all geometric properties from an Open CASCADE shape.

        Args:
            entity_id: Entity ID this shape belongs to
            shape: TopoDS_Shape to analyze

        Returns:
            SolidProperties instance with computed values

        Raises:
            PropertyComputationError: If property computation fails
        """
        try:
            # Compute volume properties (volume, center of mass)
            volume_props = GProp_GProps()
            brepgprop_VolumeProperties(shape, volume_props)
            volume = volume_props.Mass()
            com = volume_props.CentreOfMass()
            center_of_mass_x = com.X()
            center_of_mass_y = com.Y()
            center_of_mass_z = com.Z()

            # Compute surface area
            surface_props = GProp_GProps()
            brepgprop_SurfaceProperties(shape, surface_props)
            surface_area = surface_props.Mass()

            # Compute bounding box
            from OCC.Core.Bnd import Bnd_Box
            from OCC.Core.BRepBndLib import brepbndlib_Add

            bbox = Bnd_Box()
            brepbndlib_Add(shape, bbox)
            if not bbox.IsVoid():
                xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()
            else:
                xmin = ymin = zmin = xmax = ymax = zmax = 0.0

            # Count topology elements
            face_count = cls._count_topology(shape, TopAbs_FACE)
            edge_count = cls._count_topology(shape, TopAbs_EDGE)
            vertex_count = cls._count_topology(shape, TopAbs_VERTEX)

            # Check if closed and manifold
            analyzer = BRepCheck_Analyzer(shape)
            is_valid = analyzer.IsValid()

            # A solid is closed if it's a valid solid
            # Check using BRep_Tool
            is_closed = False
            is_manifold = is_valid  # Simplified: valid shapes are typically manifold

            try:
                from OCC.Core.BRepClass3d import BRepClass3d_SolidClassifier
                # If we can create a solid classifier, it's likely a closed solid
                classifier = BRepClass3d_SolidClassifier(shape)
                is_closed = True
            except Exception:
                is_closed = False

            return cls(
                entity_id=entity_id,
                volume=volume,
                surface_area=surface_area,
                center_of_mass_x=center_of_mass_x,
                center_of_mass_y=center_of_mass_y,
                center_of_mass_z=center_of_mass_z,
                bounding_box_min_x=xmin,
                bounding_box_min_y=ymin,
                bounding_box_min_z=zmin,
                bounding_box_max_x=xmax,
                bounding_box_max_y=ymax,
                bounding_box_max_z=zmax,
                face_count=face_count,
                edge_count=edge_count,
                vertex_count=vertex_count,
                is_closed=is_closed,
                is_manifold=is_manifold,
                computed_at=datetime.utcnow().isoformat()
            )

        except Exception as e:
            raise PropertyComputationError(
                f"Failed to compute properties for entity {entity_id}: {e}"
            )

    @staticmethod
    def _count_topology(shape: TopoDS_Shape, topology_type) -> int:
        """Count topology elements of a specific type in shape.

        Args:
            shape: Shape to explore
            topology_type: Type to count (TopAbs_FACE, TopAbs_EDGE, etc.)

        Returns:
            Count of topology elements
        """
        count = 0
        explorer = TopExp_Explorer(shape, topology_type)
        while explorer.More():
            count += 1
            explorer.Next()
        return count

    def matches_tolerance(
        self,
        expected_volume: Optional[float] = None,
        tolerance: float = 0.001
    ) -> bool:
        """Check if computed properties match expected values within tolerance.

        Args:
            expected_volume: Expected volume value
            tolerance: Relative tolerance (default 0.1% = 0.001)

        Returns:
            True if properties match within tolerance
        """
        if expected_volume is not None:
            relative_error = abs(self.volume - expected_volume) / expected_volume
            if relative_error > tolerance:
                return False
        return True

    def to_dict(self) -> dict:
        """Convert to dictionary for database storage.

        Returns:
            Dictionary with all property fields
        """
        return {
            "entity_id": self.entity_id,
            "volume": self.volume,
            "surface_area": self.surface_area,
            "center_of_mass_x": self.center_of_mass_x,
            "center_of_mass_y": self.center_of_mass_y,
            "center_of_mass_z": self.center_of_mass_z,
            "bounding_box_min_x": self.bounding_box_min_x,
            "bounding_box_min_y": self.bounding_box_min_y,
            "bounding_box_min_z": self.bounding_box_min_z,
            "bounding_box_max_x": self.bounding_box_max_x,
            "bounding_box_max_y": self.bounding_box_max_y,
            "bounding_box_max_z": self.bounding_box_max_z,
            "face_count": self.face_count,
            "edge_count": self.edge_count,
            "vertex_count": self.vertex_count,
            "is_closed": self.is_closed,
            "is_manifold": self.is_manifold,
            "computed_at": self.computed_at
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SolidProperties":
        """Create SolidProperties from dictionary (database record).

        Args:
            data: Dictionary with property fields

        Returns:
            SolidProperties instance
        """
        return cls(
            entity_id=data["entity_id"],
            volume=data["volume"],
            surface_area=data["surface_area"],
            center_of_mass_x=data["center_of_mass_x"],
            center_of_mass_y=data["center_of_mass_y"],
            center_of_mass_z=data["center_of_mass_z"],
            bounding_box_min_x=data["bounding_box_min_x"],
            bounding_box_min_y=data["bounding_box_min_y"],
            bounding_box_min_z=data["bounding_box_min_z"],
            bounding_box_max_x=data["bounding_box_max_x"],
            bounding_box_max_y=data["bounding_box_max_y"],
            bounding_box_max_z=data["bounding_box_max_z"],
            face_count=data["face_count"],
            edge_count=data["edge_count"],
            vertex_count=data["vertex_count"],
            is_closed=data["is_closed"],
            is_manifold=data["is_manifold"],
            computed_at=data["computed_at"]
        )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"SolidProperties(entity={self.entity_id}, "
            f"volume={self.volume:.2f}, faces={self.face_count})"
        )
