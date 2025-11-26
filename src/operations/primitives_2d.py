"""2D geometric primitive entities.

This module defines classes for 2D geometric entities including
points, lines, circles, and arcs with computed properties.
"""
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from src.cad_kernel.geometry_core import get_geometry_core


@dataclass
class Point2D:
    """2D point entity.

    Attributes:
        entity_id: Unique entity identifier
        workspace_id: Workspace identifier
        coordinates: [x, y] coordinates
        entity_type: Always "point"
    """

    entity_id: str
    workspace_id: str
    coordinates: list[float] = field(default_factory=list)
    entity_type: str = "point"
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        """Initialize after dataclass creation."""
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at

        # Ensure 2D points have z=0
        if len(self.coordinates) == 2:
            self.coordinates.append(0.0)

    def to_dict(self) -> dict:
        """Convert entity to dictionary representation.

        Returns:
            Dict with entity data
        """
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "workspace_id": self.workspace_id,
            "coordinates": self.coordinates,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def validate(self) -> tuple[bool, Optional[str]]:
        """Validate point geometry.

        Returns:
            Tuple of (is_valid, error_message)
        """
        geometry_core = get_geometry_core()
        return geometry_core.validate_point(self.coordinates)


@dataclass
class Line2D:
    """2D line entity.

    Attributes:
        entity_id: Unique entity identifier
        workspace_id: Workspace identifier
        start: Start point [x, y] coordinates
        end: End point [x, y] coordinates
        entity_type: Always "line"
    """

    entity_id: str
    workspace_id: str
    start: list[float] = field(default_factory=list)
    end: list[float] = field(default_factory=list)
    entity_type: str = "line"
    created_at: str = ""
    updated_at: str = ""
    _length: Optional[float] = None
    _direction_vector: Optional[list[float]] = None

    def __post_init__(self):
        """Initialize after dataclass creation."""
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at

        # Ensure 2D lines have z=0
        if len(self.start) == 2:
            self.start.append(0.0)
        if len(self.end) == 2:
            self.end.append(0.0)

    @property
    def length(self) -> float:
        """Calculate line length.

        Returns:
            Length of the line
        """
        if self._length is None:
            geometry_core = get_geometry_core()
            self._length = geometry_core.calculate_distance(self.start, self.end)
        return self._length

    @property
    def direction_vector(self) -> list[float]:
        """Calculate normalized direction vector.

        Returns:
            Normalized direction vector [dx, dy, dz]
        """
        if self._direction_vector is None:
            geometry_core = get_geometry_core()
            self._direction_vector = geometry_core.calculate_direction_vector(
                self.start, self.end
            )
        return self._direction_vector

    def to_dict(self) -> dict:
        """Convert entity to dictionary representation.

        Returns:
            Dict with entity data
        """
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "workspace_id": self.workspace_id,
            "start": self.start,
            "end": self.end,
            "length": self.length,
            "direction_vector": self.direction_vector,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def validate(self) -> tuple[bool, Optional[str]]:
        """Validate line geometry.

        Returns:
            Tuple of (is_valid, error_message)
        """
        geometry_core = get_geometry_core()

        # Check dimension match
        if len(self.start) != len(self.end):
            return False, "Start and end points must have same dimension"

        return geometry_core.validate_line(self.start, self.end)


@dataclass
class Circle2D:
    """2D circle entity.

    Attributes:
        entity_id: Unique entity identifier
        workspace_id: Workspace identifier
        center: Center point [x, y] coordinates
        radius: Circle radius
        entity_type: Always "circle"
    """

    entity_id: str
    workspace_id: str
    center: list[float] = field(default_factory=list)
    radius: float = 0.0
    entity_type: str = "circle"
    created_at: str = ""
    updated_at: str = ""
    _area: Optional[float] = None
    _circumference: Optional[float] = None

    def __post_init__(self):
        """Initialize after dataclass creation."""
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at

        # Ensure 2D circles have z=0
        if len(self.center) == 2:
            self.center.append(0.0)

    @property
    def area(self) -> float:
        """Calculate circle area.

        Returns:
            Area (π × radius²)
        """
        if self._area is None:
            geometry_core = get_geometry_core()
            self._area = geometry_core.calculate_circle_area(self.radius)
        return self._area

    @property
    def circumference(self) -> float:
        """Calculate circle circumference.

        Returns:
            Circumference (2π × radius)
        """
        if self._circumference is None:
            geometry_core = get_geometry_core()
            self._circumference = geometry_core.calculate_circle_circumference(
                self.radius
            )
        return self._circumference

    def to_dict(self) -> dict:
        """Convert entity to dictionary representation.

        Returns:
            Dict with entity data
        """
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "workspace_id": self.workspace_id,
            "center": self.center,
            "radius": self.radius,
            "area": self.area,
            "circumference": self.circumference,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def validate(self) -> tuple[bool, Optional[str]]:
        """Validate circle geometry.

        Returns:
            Tuple of (is_valid, error_message)
        """
        geometry_core = get_geometry_core()
        return geometry_core.validate_circle(self.center, self.radius)


@dataclass
class Arc2D:
    """2D arc entity.

    Attributes:
        entity_id: Unique entity identifier
        workspace_id: Workspace identifier
        center: Center point [x, y] coordinates
        radius: Arc radius
        start_angle: Start angle in radians
        end_angle: End angle in radians
        entity_type: Always "arc"
    """

    entity_id: str
    workspace_id: str
    center: list[float] = field(default_factory=list)
    radius: float = 0.0
    start_angle: float = 0.0
    end_angle: float = 0.0
    entity_type: str = "arc"
    created_at: str = ""
    updated_at: str = ""
    _arc_length: Optional[float] = None

    def __post_init__(self):
        """Initialize after dataclass creation."""
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at

        # Ensure 2D arcs have z=0
        if len(self.center) == 2:
            self.center.append(0.0)

    @property
    def arc_length(self) -> float:
        """Calculate arc length.

        Returns:
            Length of the arc
        """
        if self._arc_length is None:
            angle_span = abs(self.end_angle - self.start_angle)
            self._arc_length = self.radius * angle_span
        return self._arc_length

    def to_dict(self) -> dict:
        """Convert entity to dictionary representation.

        Returns:
            Dict with entity data
        """
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "workspace_id": self.workspace_id,
            "center": self.center,
            "radius": self.radius,
            "start_angle": self.start_angle,
            "end_angle": self.end_angle,
            "arc_length": self.arc_length,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def validate(self) -> tuple[bool, Optional[str]]:
        """Validate arc geometry.

        Returns:
            Tuple of (is_valid, error_message)
        """
        geometry_core = get_geometry_core()

        # Validate circle properties first
        valid, error = geometry_core.validate_circle(self.center, self.radius)
        if not valid:
            return False, error

        # Validate angles
        if not math.isfinite(self.start_angle):
            return False, f"Start angle is not finite (got {self.start_angle})"
        if not math.isfinite(self.end_angle):
            return False, f"End angle is not finite (got {self.end_angle})"

        if abs(self.end_angle - self.start_angle) < 1e-6:
            return False, "Arc angle span must be > 0"

        return True, None
