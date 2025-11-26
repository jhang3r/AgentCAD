"""3D geometric primitive entities.

This module defines classes for 3D geometric entities including
3D points and lines with computed properties.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from src.cad_kernel.geometry_core import get_geometry_core


@dataclass
class Point3D:
    """3D point entity.

    Attributes:
        entity_id: Unique entity identifier
        workspace_id: Workspace identifier
        coordinates: [x, y, z] coordinates
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

        # Ensure 3D points have exactly 3 coordinates
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
class Line3D:
    """3D line entity.

    Attributes:
        entity_id: Unique entity identifier
        workspace_id: Workspace identifier
        start: Start point [x, y, z] coordinates
        end: End point [x, y, z] coordinates
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

        # Ensure 3D lines have exactly 3 coordinates
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
