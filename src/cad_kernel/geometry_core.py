"""OCCT geometry kernel wrapper and initialization."""
import math
from typing import Optional, Tuple


class GeometryCore:
    """Wrapper for OpenCascade Technology (OCCT) geometry kernel.

    This class provides a simplified interface to OCCT functionality
    for creating and manipulating geometric entities.
    """

    def __init__(self):
        """Initialize OCCT geometry kernel environment."""
        self._initialized = False
        self._coordinate_system = "cartesian"
        self._tolerance = 1e-6  # Default geometric tolerance in mm

    def initialize(self) -> None:
        """Initialize OCCT environment and coordinate system.

        Note: build123d handles OCCT initialization internally.
        This method prepares our wrapper's state.
        """
        self._initialized = True

    def is_initialized(self) -> bool:
        """Check if geometry kernel is initialized.

        Returns:
            True if initialized
        """
        return self._initialized

    def get_tolerance(self) -> float:
        """Get current geometric tolerance.

        Returns:
            Tolerance value in mm
        """
        return self._tolerance

    def set_tolerance(self, tolerance: float) -> None:
        """Set geometric tolerance for operations.

        Args:
            tolerance: New tolerance value in mm (must be positive)

        Raises:
            ValueError: If tolerance is not positive
        """
        if tolerance <= 0:
            raise ValueError("Tolerance must be positive")
        self._tolerance = tolerance

    def validate_point(self, coordinates: list[float]) -> Tuple[bool, Optional[str]]:
        """Validate point coordinates.

        Args:
            coordinates: Point coordinates [x, y] or [x, y, z]

        Returns:
            Tuple of (is_valid, error_message)
        """
        if len(coordinates) not in (2, 3):
            return False, "Point must have 2 or 3 coordinates"

        for i, coord in enumerate(coordinates):
            if not math.isfinite(coord):
                return False, f"Coordinate {i} is not finite (got {coord})"
            if abs(coord) > 1e6:
                return False, f"Coordinate {i} exceeds bounds [-1e6, 1e6] (got {coord})"

        return True, None

    def validate_line(
        self,
        start: list[float],
        end: list[float]
    ) -> Tuple[bool, Optional[str]]:
        """Validate line segment definition.

        Args:
            start: Start point coordinates
            end: End point coordinates

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Validate both points
        valid, error = self.validate_point(start)
        if not valid:
            return False, f"Invalid start point: {error}"

        valid, error = self.validate_point(end)
        if not valid:
            return False, f"Invalid end point: {error}"

        # Check start != end (no degenerate lines)
        if len(start) != len(end):
            return False, "Start and end points must have same dimension"

        distance = self.calculate_distance(start, end)
        if distance < self._tolerance:
            return False, f"Line is degenerate (length {distance} < tolerance {self._tolerance})"

        return True, None

    def validate_circle(
        self,
        center: list[float],
        radius: float
    ) -> Tuple[bool, Optional[str]]:
        """Validate circle definition.

        Args:
            center: Center point coordinates
            radius: Circle radius

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Validate center point
        valid, error = self.validate_point(center)
        if not valid:
            return False, f"Invalid center point: {error}"

        # Validate radius
        if not math.isfinite(radius):
            return False, f"Radius is not finite (got {radius})"

        if radius <= self._tolerance:
            return False, f"Radius must be > {self._tolerance} (got {radius})"

        if radius > 1e6:
            return False, f"Radius exceeds maximum 1e6 (got {radius})"

        return True, None

    def calculate_distance(self, point1: list[float], point2: list[float]) -> float:
        """Calculate Euclidean distance between two points.

        Args:
            point1: First point coordinates
            point2: Second point coordinates

        Returns:
            Distance between points
        """
        if len(point1) != len(point2):
            raise ValueError("Points must have same dimension")

        sum_squares = sum((p1 - p2) ** 2 for p1, p2 in zip(point1, point2))
        return math.sqrt(sum_squares)

    def calculate_direction_vector(
        self,
        start: list[float],
        end: list[float]
    ) -> list[float]:
        """Calculate normalized direction vector from start to end.

        Args:
            start: Start point coordinates
            end: End point coordinates

        Returns:
            Normalized direction vector
        """
        distance = self.calculate_distance(start, end)
        if distance < self._tolerance:
            raise ValueError("Cannot compute direction for degenerate line")

        return [(e - s) / distance for s, e in zip(start, end)]

    def calculate_bounding_box(
        self,
        points: list[list[float]]
    ) -> dict[str, list[float]]:
        """Calculate axis-aligned bounding box for a set of points.

        Args:
            points: List of point coordinates

        Returns:
            Bounding box dict with 'min' and 'max' keys
        """
        if not points:
            raise ValueError("Cannot compute bounding box for empty point set")

        dimension = len(points[0])
        min_coords = [min(p[i] for p in points) for i in range(dimension)]
        max_coords = [max(p[i] for p in points) for i in range(dimension)]

        # Ensure 3D bounding box
        while len(min_coords) < 3:
            min_coords.append(0.0)
        while len(max_coords) < 3:
            max_coords.append(0.0)

        return {"min": min_coords[:3], "max": max_coords[:3]}

    def calculate_circle_area(self, radius: float) -> float:
        """Calculate circle area.

        Args:
            radius: Circle radius

        Returns:
            Area (π × radius²)
        """
        return math.pi * radius * radius

    def calculate_circle_circumference(self, radius: float) -> float:
        """Calculate circle circumference.

        Args:
            radius: Circle radius

        Returns:
            Circumference (2π × radius)
        """
        return 2 * math.pi * radius


# Global geometry kernel instance
_geometry_core: Optional[GeometryCore] = None


def get_geometry_core() -> GeometryCore:
    """Get or create global geometry kernel instance.

    Returns:
        Initialized GeometryCore instance
    """
    global _geometry_core
    if _geometry_core is None:
        _geometry_core = GeometryCore()
        _geometry_core.initialize()
    return _geometry_core
