"""Integration tests for geometry operations with real OCCT.

These tests verify that geometric entities are created correctly
using the actual geometry kernel (OCCT via build123d).

NO MOCKS - Real OCCT integration only.
"""
import math
import uuid

import pytest

from src.operations.primitives_2d import Point2D, Line2D, Circle2D
from src.operations.primitives_3d import Point3D, Line3D


def generate_entity_id(entity_type: str) -> str:
    """Helper to generate entity IDs."""
    unique_id = str(uuid.uuid4())[:8]
    return f"main:{entity_type}_{unique_id}"


class TestPointCreation:
    """Test point creation with real OCCT."""

    def test_create_point_2d(self):
        """Test 2D point creation and coordinate verification."""
        point = Point2D(
            entity_id=generate_entity_id("point"),
            workspace_id="main",
            coordinates=[10.0, 20.0]
        )

        # Verify coordinates (2D points get z=0)
        assert point.coordinates == [10.0, 20.0, 0.0]
        assert point.entity_type == "point"

        # Verify validation passes
        valid, error = point.validate()
        assert valid
        assert error is None

    def test_create_point_3d(self):
        """Test 3D point creation and coordinate verification."""
        point = Point3D(
            entity_id=generate_entity_id("point"),
            workspace_id="main",
            coordinates=[10.0, 20.0, 30.0]
        )

        # Verify coordinates
        assert point.coordinates == [10.0, 20.0, 30.0]
        assert point.entity_type == "point"

        # Verify validation passes
        valid, error = point.validate()
        assert valid
        assert error is None

    def test_point_validation_out_of_bounds(self):
        """Test point validation with coordinates exceeding bounds."""
        point = Point2D(
            entity_id=generate_entity_id("point"),
            workspace_id="main",
            coordinates=[2e6, 20.0]  # Exceeds [-1e6, 1e6]
        )

        valid, error = point.validate()
        assert not valid
        assert "bounds" in error.lower()

    def test_point_validation_non_finite(self):
        """Test point validation with non-finite coordinates."""
        point = Point2D(
            entity_id=generate_entity_id("point"),
            workspace_id="main",
            coordinates=[10.0, float('inf')]
        )

        valid, error = point.validate()
        assert not valid
        assert "finite" in error.lower()

    def test_point_to_dict(self):
        """Test point serialization to dict."""
        point = Point2D(
            entity_id="main:point_test123",
            workspace_id="main",
            coordinates=[5.0, 10.0]
        )

        data = point.to_dict()

        assert data["entity_id"] == "main:point_test123"
        assert data["entity_type"] == "point"
        assert data["workspace_id"] == "main"
        assert data["coordinates"] == [5.0, 10.0, 0.0]
        assert "created_at" in data
        assert "updated_at" in data


class TestLineCreation:
    """Test line creation with real OCCT."""

    def test_create_line_2d(self):
        """Test 2D line creation, length, and direction_vector verification."""
        line = Line2D(
            entity_id=generate_entity_id("line"),
            workspace_id="main",
            start=[0.0, 0.0],
            end=[3.0, 4.0]
        )

        # Verify coordinates (2D lines get z=0)
        assert line.start == [0.0, 0.0, 0.0]
        assert line.end == [3.0, 4.0, 0.0]
        assert line.entity_type == "line"

        # Verify length calculation (3-4-5 triangle)
        assert abs(line.length - 5.0) < 1e-6

        # Verify direction vector
        direction = line.direction_vector
        assert len(direction) == 3
        # Should be normalized: [3/5, 4/5, 0]
        assert abs(direction[0] - 0.6) < 1e-6
        assert abs(direction[1] - 0.8) < 1e-6
        assert abs(direction[2] - 0.0) < 1e-6

        # Verify validation passes
        valid, error = line.validate()
        assert valid
        assert error is None

    def test_create_line_3d(self):
        """Test 3D line creation, length, and direction_vector verification."""
        line = Line3D(
            entity_id=generate_entity_id("line"),
            workspace_id="main",
            start=[0.0, 0.0, 0.0],
            end=[1.0, 1.0, 1.0]
        )

        # Verify coordinates
        assert line.start == [0.0, 0.0, 0.0]
        assert line.end == [1.0, 1.0, 1.0]

        # Verify length calculation
        expected_length = math.sqrt(3)
        assert abs(line.length - expected_length) < 1e-6

        # Verify direction vector is normalized
        direction = line.direction_vector
        magnitude = math.sqrt(sum(d**2 for d in direction))
        assert abs(magnitude - 1.0) < 1e-6

    def test_line_degenerate(self):
        """Test line validation with degenerate line (start == end)."""
        line = Line2D(
            entity_id=generate_entity_id("line"),
            workspace_id="main",
            start=[5.0, 5.0],
            end=[5.0, 5.0]
        )

        valid, error = line.validate()
        assert not valid
        assert "degenerate" in error.lower()

    def test_line_dimension_mismatch(self):
        """Test line validation with mismatched dimensions."""
        # Create line with explicitly mismatched dimensions (4D end, which won't be auto-padded)
        line = Line2D(
            entity_id=generate_entity_id("line"),
            workspace_id="main",
            start=[0.0, 0.0],
            end=[1.0, 1.0, 1.0, 1.0]  # 4D end - invalid
        )

        valid, error = line.validate()
        assert not valid
        assert "dimension" in error.lower()

    def test_line_to_dict(self):
        """Test line serialization to dict."""
        line = Line2D(
            entity_id="main:line_test456",
            workspace_id="main",
            start=[0.0, 0.0],
            end=[10.0, 0.0]
        )

        data = line.to_dict()

        assert data["entity_id"] == "main:line_test456"
        assert data["entity_type"] == "line"
        assert data["workspace_id"] == "main"
        assert data["start"] == [0.0, 0.0, 0.0]
        assert data["end"] == [10.0, 0.0, 0.0]
        assert data["length"] == 10.0
        assert "direction_vector" in data
        assert "created_at" in data


class TestCircleCreation:
    """Test circle creation with real OCCT."""

    def test_create_circle_2d(self):
        """Test 2D circle creation, area, and circumference verification."""
        circle = Circle2D(
            entity_id=generate_entity_id("circle"),
            workspace_id="main",
            center=[10.0, 20.0],
            radius=5.0
        )

        # Verify properties
        assert circle.center == [10.0, 20.0, 0.0]
        assert circle.radius == 5.0
        assert circle.entity_type == "circle"

        # Verify area calculation
        expected_area = math.pi * 5.0 ** 2
        assert abs(circle.area - expected_area) < 1e-6

        # Verify circumference calculation
        expected_circumference = 2 * math.pi * 5.0
        assert abs(circle.circumference - expected_circumference) < 1e-6

        # Verify validation passes
        valid, error = circle.validate()
        assert valid
        assert error is None

    def test_circle_zero_radius(self):
        """Test circle validation with zero radius."""
        circle = Circle2D(
            entity_id=generate_entity_id("circle"),
            workspace_id="main",
            center=[5.0, 5.0],
            radius=0.0
        )

        valid, error = circle.validate()
        assert not valid
        assert "radius" in error.lower()

    def test_circle_negative_radius(self):
        """Test circle validation with negative radius."""
        circle = Circle2D(
            entity_id=generate_entity_id("circle"),
            workspace_id="main",
            center=[5.0, 5.0],
            radius=-3.0
        )

        valid, error = circle.validate()
        assert not valid
        assert "radius" in error.lower()

    def test_circle_invalid_center(self):
        """Test circle validation with invalid center."""
        circle = Circle2D(
            entity_id=generate_entity_id("circle"),
            workspace_id="main",
            center=[float('nan'), 5.0],
            radius=3.0
        )

        valid, error = circle.validate()
        assert not valid
        assert "finite" in error.lower()

    def test_circle_to_dict(self):
        """Test circle serialization to dict."""
        circle = Circle2D(
            entity_id="main:circle_test789",
            workspace_id="main",
            center=[0.0, 0.0],
            radius=10.0
        )

        data = circle.to_dict()

        assert data["entity_id"] == "main:circle_test789"
        assert data["entity_type"] == "circle"
        assert data["workspace_id"] == "main"
        assert data["center"] == [0.0, 0.0, 0.0]
        assert data["radius"] == 10.0
        assert "area" in data
        assert "circumference" in data
        assert "created_at" in data

    def test_circle_large_radius(self):
        """Test circle with large but valid radius."""
        circle = Circle2D(
            entity_id=generate_entity_id("circle"),
            workspace_id="main",
            center=[0.0, 0.0],
            radius=1000.0
        )

        valid, error = circle.validate()
        assert valid

        # Verify computed properties work with large values
        assert circle.area > 0
        assert circle.circumference > 0
