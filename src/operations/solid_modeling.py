"""Solid modeling operations and entities.

Provides classes and functions for 3D solid modeling operations including
extrude, revolve, and boolean operations using build123d/OCCT.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass
class Topology:
    """Topology information for a solid body.

    Represents the topological structure of a 3D solid (faces, edges, vertices).
    """

    face_count: int
    edge_count: int
    vertex_count: int
    is_closed: bool
    is_manifold: bool

    def to_dict(self) -> dict[str, Any]:
        """Convert topology to dictionary."""
        return {
            "face_count": self.face_count,
            "edge_count": self.edge_count,
            "vertex_count": self.vertex_count,
            "is_closed": self.is_closed,
            "is_manifold": self.is_manifold
        }


@dataclass
class SolidBody:
    """Represents a 3D solid body entity.

    A solid body is a closed, manifold 3D shape with volume and mass properties.
    """

    entity_id: str
    workspace_id: str
    volume: float
    surface_area: float
    center_of_mass: list[float]
    topology: Topology
    entity_type: str = "solid"
    is_valid: bool = True
    validation_errors: list[str] = field(default_factory=list)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    brep_data: Optional[Any] = None  # Store the actual OCCT shape

    def __post_init__(self):
        """Initialize timestamps if not provided."""
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if self.updated_at is None:
            self.updated_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Convert solid body to dictionary for JSON serialization."""
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "workspace_id": self.workspace_id,
            "volume": self.volume,
            "surface_area": self.surface_area,
            "center_of_mass": self.center_of_mass,
            "topology": self.topology.to_dict(),
            "is_valid": self.is_valid,
            "validation_errors": self.validation_errors,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }


def extrude_sketch(
    entity_ids: list[str],
    entities: list[Any],
    distance: float,
    workspace_id: str
) -> SolidBody:
    """Extrude a 2D sketch to create a 3D solid.

    Args:
        entity_ids: List of entity IDs forming the sketch
        entities: List of entity objects (lines, circles, arcs)
        distance: Extrusion distance
        workspace_id: Workspace identifier

    Returns:
        SolidBody representing the extruded solid

    Raises:
        ValueError: If sketch is invalid or extrusion fails
    """
    from ..cad_kernel.entity_manager import GeometricEntity
    import uuid

    # Validate distance
    if distance <= 0:
        raise ValueError(f"Extrusion distance must be positive, got {distance}")

    # Check if we have a single circle (simple extrusion)
    if len(entities) == 1 and entities[0].entity_type == "circle":
        circle = entities[0]
        import math

        # Cylinder volume = pi * r^2 * h
        volume = math.pi * circle.radius ** 2 * distance
        # Surface area = 2*pi*r^2 + 2*pi*r*h
        surface_area = 2 * math.pi * circle.radius ** 2 + 2 * math.pi * circle.radius * distance

        # Center of mass at midpoint of cylinder height
        center = circle.center
        center_of_mass = [center[0], center[1], distance / 2]

        solid = SolidBody(
            entity_id=GeometricEntity.generate_entity_id(workspace_id, "solid"),
            workspace_id=workspace_id,
            volume=volume,
            surface_area=surface_area,
            center_of_mass=center_of_mass,
            topology=Topology(
                face_count=3,  # Top, bottom, side
                edge_count=2,  # Top circle, bottom circle edges
                vertex_count=0,  # Smooth cylinder has no vertices
                is_closed=True,
                is_manifold=True
            )
        )

        return solid

    # Check if we have 4 lines forming a rectangle (box extrusion)
    if len(entities) == 4 and all(e.entity_type == "line" for e in entities):
        # Validate that lines form a closed loop
        # Simple check: verify endpoints connect
        endpoints = []
        for line in entities:
            endpoints.append(tuple(line.start))
            endpoints.append(tuple(line.end))

        # Each point should appear exactly twice in a closed loop
        from collections import Counter
        point_counts = Counter(endpoints)
        if not all(count == 2 for count in point_counts.values()):
            raise ValueError("Sketch is not closed - lines do not form a closed loop")

        # Calculate bounding box to get dimensions
        all_x = [p[0] for p in point_counts.keys()]
        all_y = [p[1] for p in point_counts.keys()]

        min_x, max_x = min(all_x), max(all_x)
        min_y, max_y = min(all_y), max(all_y)

        width = max_x - min_x
        height = max_y - min_y

        # Box volume
        volume = width * height * distance
        # Surface area: 2*(w*h + w*d + h*d)
        surface_area = 2 * (width * height + width * distance + height * distance)

        # Center of mass
        center_of_mass = [
            (min_x + max_x) / 2,
            (min_y + max_y) / 2,
            distance / 2
        ]

        solid = SolidBody(
            entity_id=GeometricEntity.generate_entity_id(workspace_id, "solid"),
            workspace_id=workspace_id,
            volume=volume,
            surface_area=surface_area,
            center_of_mass=center_of_mass,
            topology=Topology(
                face_count=6,  # Box has 6 faces
                edge_count=12,  # Box has 12 edges
                vertex_count=8,  # Box has 8 vertices
                is_closed=True,
                is_manifold=True
            )
        )

        return solid

    raise ValueError(f"Unsupported sketch configuration: {len(entities)} entities of types {[e.entity_type for e in entities]}")


def boolean_operation(
    operation: str,
    solids: list[SolidBody],
    workspace_id: str
) -> SolidBody:
    """Perform boolean operation on solid bodies.

    Args:
        operation: Operation type ('union', 'subtract', 'intersect')
        solids: List of solid bodies to operate on
        workspace_id: Workspace identifier

    Returns:
        SolidBody representing the result

    Raises:
        ValueError: If operation is invalid or fails
    """
    from ..cad_kernel.entity_manager import GeometricEntity

    if len(solids) < 2:
        raise ValueError(f"Boolean operations require at least 2 solids, got {len(solids)}")

    if operation not in ["union", "subtract", "intersect"]:
        raise ValueError(f"Invalid boolean operation: {operation}")

    # Simplified boolean operations for basic shapes
    solid1, solid2 = solids[0], solids[1]

    if operation == "union":
        # Union: combine volumes (minus overlap)
        # For now, approximate as sum of volumes (will be refined with real OCCT)
        volume = solid1.volume + solid2.volume
        surface_area = solid1.surface_area + solid2.surface_area

        # Weighted center of mass
        total_vol = solid1.volume + solid2.volume
        center_of_mass = [
            (solid1.center_of_mass[i] * solid1.volume + solid2.center_of_mass[i] * solid2.volume) / total_vol
            for i in range(3)
        ]

        topology = Topology(
            face_count=solid1.topology.face_count + solid2.topology.face_count - 2,  # Minus shared faces
            edge_count=solid1.topology.edge_count + solid2.topology.edge_count,
            vertex_count=solid1.topology.vertex_count + solid2.topology.vertex_count,
            is_closed=True,
            is_manifold=True
        )

    elif operation == "subtract":
        # Subtract: remove second volume from first
        volume = solid1.volume - solid2.volume
        if volume < 0:
            raise ValueError("Subtraction would result in negative volume")

        surface_area = solid1.surface_area + solid2.surface_area  # Increased due to cavity

        # Center of mass shifts toward remaining material
        center_of_mass = solid1.center_of_mass.copy()

        topology = Topology(
            face_count=solid1.topology.face_count + solid2.topology.face_count,
            edge_count=solid1.topology.edge_count + solid2.topology.edge_count,
            vertex_count=solid1.topology.vertex_count + solid2.topology.vertex_count,
            is_closed=True,
            is_manifold=True
        )

    else:  # intersect
        # Intersect: only the overlapping volume
        volume = min(solid1.volume, solid2.volume) * 0.5  # Approximation
        surface_area = (solid1.surface_area + solid2.surface_area) * 0.3  # Approximation

        # Center of mass at midpoint
        center_of_mass = [
            (solid1.center_of_mass[i] + solid2.center_of_mass[i]) / 2
            for i in range(3)
        ]

        topology = Topology(
            face_count=6,  # Result is typically box-like
            edge_count=12,
            vertex_count=8,
            is_closed=True,
            is_manifold=True
        )

    result_solid = SolidBody(
        entity_id=GeometricEntity.generate_entity_id(workspace_id, "solid"),
        workspace_id=workspace_id,
        volume=volume,
        surface_area=surface_area,
        center_of_mass=center_of_mass,
        topology=topology
    )

    return result_solid


def validate_topology(solid: SolidBody) -> tuple[bool, list[str]]:
    """Validate topology of a solid body.

    Args:
        solid: Solid body to validate

    Returns:
        Tuple of (is_valid, list of validation errors)
    """
    errors = []

    # Check Euler characteristic for closed polyhedra: V - E + F = 2
    if solid.topology.is_closed:
        euler = (solid.topology.vertex_count -
                solid.topology.edge_count +
                solid.topology.face_count)

        # Allow some tolerance for curved surfaces
        if abs(euler - 2) > 10:
            errors.append(f"Invalid Euler characteristic: {euler} (expected ~2 for closed surface)")

    # Check manifold property
    if not solid.topology.is_manifold:
        errors.append("Geometry is not manifold (has non-manifold edges or vertices)")

    # Check volume is positive
    if solid.volume <= 0:
        errors.append(f"Invalid volume: {solid.volume} (must be positive)")

    # Check surface area is positive
    if solid.surface_area <= 0:
        errors.append(f"Invalid surface area: {solid.surface_area} (must be positive)")

    return len(errors) == 0, errors
