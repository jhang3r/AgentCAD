"""Geometric constraint classes for constraint solving.

This module defines various geometric constraints that can be applied
to entities, along with methods to check satisfaction and compute residuals.
"""
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from src.cad_kernel.geometry_core import get_geometry_core


@dataclass
class Constraint:
    """Base class for geometric constraints.

    Attributes:
        constraint_id: Unique constraint identifier
        workspace_id: Workspace identifier
        constraint_type: Type of constraint
        entity_ids: List of constrained entity IDs
        entities: List of actual entity objects (for solving)
        satisfaction_status: Current status (satisfied, violated, redundant)
        tolerance: Satisfaction tolerance
        created_at: Creation timestamp
    """

    constraint_id: str
    workspace_id: str
    entity_ids: list[str]
    constraint_type: str = ""
    entities: list[Any] = field(default_factory=list)
    satisfaction_status: str = "violated"
    tolerance: float = 1e-6
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        """Initialize after dataclass creation."""
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at

    def check_satisfaction(self) -> tuple[bool, float]:
        """Check if constraint is satisfied.

        Returns:
            Tuple of (is_satisfied, error_magnitude)
        """
        raise NotImplementedError("Subclasses must implement check_satisfaction")

    def compute_residual(self) -> float:
        """Compute constraint residual (how much it's violated).

        Returns:
            Residual value (0 = satisfied)
        """
        raise NotImplementedError("Subclasses must implement compute_residual")

    def to_dict(self) -> dict:
        """Convert constraint to dictionary representation."""
        return {
            "constraint_id": self.constraint_id,
            "constraint_type": self.constraint_type,
            "workspace_id": self.workspace_id,
            "constrained_entities": self.entity_ids,
            "satisfaction_status": self.satisfaction_status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class ParallelConstraint(Constraint):
    """Parallel constraint between two lines.

    Requires two lines to be parallel (direction vectors parallel).
    """

    constraint_type: str = "parallel"

    def check_satisfaction(self) -> tuple[bool, float]:
        """Check if lines are parallel."""
        if len(self.entities) != 2:
            return False, float('inf')

        line1, line2 = self.entities[0], self.entities[1]

        # Get direction vectors
        dir1 = line1.direction_vector
        dir2 = line2.direction_vector

        # Compute cross product magnitude (should be 0 for parallel lines in 2D)
        # For 2D: cross product = dir1[0]*dir2[1] - dir1[1]*dir2[0]
        cross = abs(dir1[0] * dir2[1] - dir1[1] * dir2[0])

        is_satisfied = cross < self.tolerance
        return is_satisfied, cross

    def compute_residual(self) -> float:
        """Compute parallel constraint residual."""
        _, error = self.check_satisfaction()
        return error


@dataclass
class PerpendicularConstraint(Constraint):
    """Perpendicular constraint between two lines.

    Requires two lines to be perpendicular (dot product = 0).
    """

    constraint_type: str = "perpendicular"

    def check_satisfaction(self) -> tuple[bool, float]:
        """Check if lines are perpendicular."""
        if len(self.entities) != 2:
            return False, float('inf')

        line1, line2 = self.entities[0], self.entities[1]

        # Get direction vectors
        dir1 = line1.direction_vector
        dir2 = line2.direction_vector

        # Compute dot product (should be 0 for perpendicular lines)
        dot = sum(d1 * d2 for d1, d2 in zip(dir1, dir2))

        is_satisfied = abs(dot) < self.tolerance
        return is_satisfied, abs(dot)

    def compute_residual(self) -> float:
        """Compute perpendicular constraint residual."""
        _, error = self.check_satisfaction()
        return error


@dataclass
class CoincidentConstraint(Constraint):
    """Coincident constraint between two points.

    Requires two points to be at the same location.
    """

    constraint_type: str = "coincident"

    def check_satisfaction(self) -> tuple[bool, float]:
        """Check if points are coincident."""
        if len(self.entities) != 2:
            return False, float('inf')

        point1, point2 = self.entities[0], self.entities[1]

        # Compute distance between points
        geometry_core = get_geometry_core()
        distance = geometry_core.calculate_distance(
            point1.coordinates, point2.coordinates
        )

        is_satisfied = distance < self.tolerance
        return is_satisfied, distance

    def compute_residual(self) -> float:
        """Compute coincident constraint residual."""
        _, error = self.check_satisfaction()
        return error


@dataclass
class DistanceConstraint(Constraint):
    """Distance constraint between two points or entities.

    Requires distance between two entities to match target distance.
    """

    constraint_type: str = "distance"
    target_distance: float = 0.0

    def check_satisfaction(self) -> tuple[bool, float]:
        """Check if distance matches target."""
        if len(self.entities) != 2:
            return False, float('inf')

        entity1, entity2 = self.entities[0], self.entities[1]

        # Get coordinates (works for points, for lines use start points)
        if hasattr(entity1, 'coordinates'):
            coord1 = entity1.coordinates
        elif hasattr(entity1, 'start'):
            coord1 = entity1.start
        else:
            return False, float('inf')

        if hasattr(entity2, 'coordinates'):
            coord2 = entity2.coordinates
        elif hasattr(entity2, 'start'):
            coord2 = entity2.start
        else:
            return False, float('inf')

        # Compute actual distance
        geometry_core = get_geometry_core()
        actual_distance = geometry_core.calculate_distance(coord1, coord2)

        # Compute error
        error = abs(actual_distance - self.target_distance)

        is_satisfied = error < self.tolerance
        return is_satisfied, error

    def compute_residual(self) -> float:
        """Compute distance constraint residual."""
        _, error = self.check_satisfaction()
        return error

    def to_dict(self) -> dict:
        """Convert constraint to dictionary representation."""
        base_dict = super().to_dict()
        base_dict["parameters"] = {"distance": self.target_distance}
        return base_dict


@dataclass
class AngleConstraint(Constraint):
    """Angle constraint between two lines.

    Requires angle between two lines to match target angle.
    """

    constraint_type: str = "angle"
    target_angle: float = 0.0  # In radians

    def check_satisfaction(self) -> tuple[bool, float]:
        """Check if angle matches target."""
        if len(self.entities) != 2:
            return False, float('inf')

        line1, line2 = self.entities[0], self.entities[1]

        # Get direction vectors
        dir1 = line1.direction_vector
        dir2 = line2.direction_vector

        # Compute dot product and magnitudes
        dot = sum(d1 * d2 for d1, d2 in zip(dir1, dir2))
        mag1 = math.sqrt(sum(d**2 for d in dir1))
        mag2 = math.sqrt(sum(d**2 for d in dir2))

        # Compute angle
        cos_angle = dot / (mag1 * mag2)
        # Clamp to [-1, 1] to avoid numerical errors
        cos_angle = max(-1.0, min(1.0, cos_angle))
        actual_angle = math.acos(cos_angle)

        # Compute error
        error = abs(actual_angle - self.target_angle)

        is_satisfied = error < self.tolerance
        return is_satisfied, error

    def compute_residual(self) -> float:
        """Compute angle constraint residual."""
        _, error = self.check_satisfaction()
        return error

    def to_dict(self) -> dict:
        """Convert constraint to dictionary representation."""
        base_dict = super().to_dict()
        base_dict["parameters"] = {"angle": self.target_angle}
        return base_dict


@dataclass
class TangentConstraint(Constraint):
    """Tangent constraint between a line and a circle/arc.

    Requires a line to be tangent to a circle or arc.
    """

    constraint_type: str = "tangent"

    def check_satisfaction(self) -> tuple[bool, float]:
        """Check if line is tangent to circle.

        A line is tangent to a circle if the distance from the circle's
        center to the line equals the circle's radius.
        """
        if not self.entities or len(self.entities) < 2:
            return False, float('inf')

        # Determine which is line and which is circle
        line = None
        circle = None
        for entity in self.entities:
            if entity.entity_type == "line":
                line = entity
            elif entity.entity_type == "circle":
                circle = entity

        if line is None or circle is None:
            return False, float('inf')

        # Calculate distance from circle center to line
        # Line: start + t*(end-start), t in [0,1]
        # Point-to-line distance formula
        import math
        start = line.start
        end = line.end
        center = circle.center

        # Vector from start to end
        dx = end[0] - start[0]
        dy = end[1] - start[1]

        # Vector from start to center
        cx = center[0] - start[0]
        cy = center[1] - start[1]

        # Project center onto line
        line_len_sq = dx*dx + dy*dy
        if line_len_sq < 1e-10:
            # Degenerate line
            return False, float('inf')

        t = (cx*dx + cy*dy) / line_len_sq

        # Closest point on line (not clamped to segment)
        closest_x = start[0] + t*dx
        closest_y = start[1] + t*dy

        # Distance from center to line
        dist = math.sqrt((center[0] - closest_x)**2 + (center[1] - closest_y)**2)

        # Error is difference between distance and radius
        error = abs(dist - circle.radius)

        # Satisfied if distance equals radius (within tolerance)
        is_satisfied = error < 0.01

        return is_satisfied, error

    def compute_residual(self) -> float:
        """Compute tangent constraint residual."""
        _, error = self.check_satisfaction()
        return error


@dataclass
class RadiusConstraint(Constraint):
    """Radius constraint for circles/arcs.

    Requires a circle or arc to have a specific radius.
    """

    constraint_type: str = "radius"
    target_radius: float = 0.0

    def check_satisfaction(self) -> tuple[bool, float]:
        """Check if radius matches target."""
        if len(self.entities) != 1:
            return False, float('inf')

        circle = self.entities[0]

        if not hasattr(circle, 'radius'):
            return False, float('inf')

        error = abs(circle.radius - self.target_radius)

        is_satisfied = error < self.tolerance
        return is_satisfied, error

    def compute_residual(self) -> float:
        """Compute radius constraint residual."""
        _, error = self.check_satisfaction()
        return error

    def to_dict(self) -> dict:
        """Convert constraint to dictionary representation."""
        base_dict = super().to_dict()
        base_dict["parameters"] = {"radius": self.target_radius}
        return base_dict
