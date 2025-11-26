"""Geometric math utility functions."""
import math
from typing import List


def distance(point1: List[float], point2: List[float]) -> float:
    """Calculate Euclidean distance between two points.

    Args:
        point1: First point coordinates
        point2: Second point coordinates

    Returns:
        Distance between points

    Raises:
        ValueError: If points have different dimensions
    """
    if len(point1) != len(point2):
        raise ValueError("Points must have same dimension")

    return math.sqrt(sum((p1 - p2) ** 2 for p1, p2 in zip(point1, point2)))


def normalize_vector(vector: List[float]) -> List[float]:
    """Normalize a vector to unit length.

    Args:
        vector: Vector to normalize

    Returns:
        Normalized unit vector

    Raises:
        ValueError: If vector is zero-length
    """
    magnitude = math.sqrt(sum(v ** 2 for v in vector))
    if magnitude < 1e-10:
        raise ValueError("Cannot normalize zero-length vector")

    return [v / magnitude for v in vector]


def dot_product(vector1: List[float], vector2: List[float]) -> float:
    """Calculate dot product of two vectors.

    Args:
        vector1: First vector
        vector2: Second vector

    Returns:
        Dot product

    Raises:
        ValueError: If vectors have different dimensions
    """
    if len(vector1) != len(vector2):
        raise ValueError("Vectors must have same dimension")

    return sum(v1 * v2 for v1, v2 in zip(vector1, vector2))


def cross_product(vector1: List[float], vector2: List[float]) -> List[float]:
    """Calculate cross product of two 3D vectors.

    Args:
        vector1: First 3D vector
        vector2: Second 3D vector

    Returns:
        Cross product vector

    Raises:
        ValueError: If vectors are not 3D
    """
    if len(vector1) != 3 or len(vector2) != 3:
        raise ValueError("Cross product requires 3D vectors")

    return [
        vector1[1] * vector2[2] - vector1[2] * vector2[1],
        vector1[2] * vector2[0] - vector1[0] * vector2[2],
        vector1[0] * vector2[1] - vector1[1] * vector2[0]
    ]


def angle_between(vector1: List[float], vector2: List[float]) -> float:
    """Calculate angle between two vectors in radians.

    Args:
        vector1: First vector
        vector2: Second vector

    Returns:
        Angle in radians [0, π]
    """
    v1_normalized = normalize_vector(vector1)
    v2_normalized = normalize_vector(vector2)

    dot = dot_product(v1_normalized, v2_normalized)

    # Clamp to [-1, 1] to handle floating point errors
    dot = max(-1.0, min(1.0, dot))

    return math.acos(dot)


def are_parallel(vector1: List[float], vector2: List[float], tolerance: float = 1e-6) -> bool:
    """Check if two vectors are parallel.

    Args:
        vector1: First vector
        vector2: Second vector
        tolerance: Angle tolerance in radians

    Returns:
        True if vectors are parallel (angle ≈ 0 or π)
    """
    angle = angle_between(vector1, vector2)
    return angle < tolerance or abs(angle - math.pi) < tolerance


def are_perpendicular(vector1: List[float], vector2: List[float], tolerance: float = 1e-6) -> bool:
    """Check if two vectors are perpendicular.

    Args:
        vector1: First vector
        vector2: Second vector
        tolerance: Angle tolerance in radians

    Returns:
        True if vectors are perpendicular (angle ≈ π/2)
    """
    angle = angle_between(vector1, vector2)
    return abs(angle - math.pi / 2) < tolerance
