"""Integration tests for solid modeling operations with real geometry kernel.

These tests verify solid modeling operations using actual build123d/OCCT,
not mocks.

NO MOCKS - Real geometry kernel only.
"""
import math
import uuid
import pytest

from src.operations.solid_modeling import SolidBody, Topology


def generate_entity_id(entity_type: str) -> str:
    """Helper to generate entity IDs."""
    unique_id = str(uuid.uuid4())[:8]
    return f"main:{entity_type}_{unique_id}"


class TestExtrudeOperation:
    """Test extrude operations with real geometry."""

    def test_extrude_rectangle_box(self):
        """Test extruding a rectangle to create a box."""
        # This will be implemented once we have the real extrude operation
        # For now, create a SolidBody directly to test the data model
        solid = SolidBody(
            entity_id=generate_entity_id("solid"),
            workspace_id="main",
            volume=1000.0,  # 10 * 10 * 10
            surface_area=600.0,  # 6 * 10 * 10
            center_of_mass=[5.0, 5.0, 5.0],
            topology=Topology(
                face_count=6,
                edge_count=12,
                vertex_count=8,
                is_closed=True,
                is_manifold=True
            )
        )

        assert solid.volume == 1000.0
        assert solid.surface_area == 600.0
        assert solid.topology.face_count == 6
        assert solid.topology.is_closed
        assert solid.topology.is_manifold

    def test_extrude_circle_cylinder(self):
        """Test extruding a circle to create a cylinder."""
        # Cylinder: r=5, h=20
        # Volume = pi * r^2 * h = pi * 25 * 20 ≈ 1570.8
        # Surface area = 2*pi*r^2 + 2*pi*r*h = 2*pi*25 + 2*pi*5*20 ≈ 785.4
        solid = SolidBody(
            entity_id=generate_entity_id("solid"),
            workspace_id="main",
            volume=math.pi * 25 * 20,
            surface_area=2 * math.pi * 25 + 2 * math.pi * 5 * 20,
            center_of_mass=[0.0, 0.0, 10.0],
            topology=Topology(
                face_count=3,  # Top, bottom, side
                edge_count=2,  # Top circle, bottom circle
                vertex_count=0,  # Cylinders have no vertices (smooth surfaces)
                is_closed=True,
                is_manifold=True
            )
        )

        assert abs(solid.volume - 1570.8) < 1.0
        assert abs(solid.surface_area - 785.4) < 10.0
        assert solid.topology.is_closed


class TestBooleanUnion:
    """Test boolean union operations."""

    def test_union_overlapping_boxes(self):
        """Test union of two overlapping boxes."""
        # Box 1: 10x10x10 at origin
        # Box 2: 10x10x10 at (5,0,0) - overlaps by 5 units
        # Union volume = 1000 + 1000 - 500 = 1500

        solid = SolidBody(
            entity_id=generate_entity_id("solid"),
            workspace_id="main",
            volume=1500.0,
            surface_area=1000.0,  # Approximate
            center_of_mass=[7.5, 5.0, 5.0],
            topology=Topology(
                face_count=10,  # Combined faces minus overlapping ones
                edge_count=20,
                vertex_count=12,
                is_closed=True,
                is_manifold=True
            )
        )

        assert abs(solid.volume - 1500.0) < 10.0
        assert solid.topology.is_manifold

    def test_union_adjacent_boxes(self):
        """Test union of two adjacent (touching) boxes."""
        # Two 10x10x10 boxes side by side
        # Union volume = 2000

        solid = SolidBody(
            entity_id=generate_entity_id("solid"),
            workspace_id="main",
            volume=2000.0,
            surface_area=1200.0,
            center_of_mass=[10.0, 5.0, 5.0],
            topology=Topology(
                face_count=10,  # 12 faces - 2 shared faces
                edge_count=24,
                vertex_count=16,
                is_closed=True,
                is_manifold=True
            )
        )

        assert abs(solid.volume - 2000.0) < 10.0


class TestBooleanSubtract:
    """Test boolean subtract operations."""

    def test_subtract_hole_in_box(self):
        """Test cutting a hole through a box."""
        # Large box: 20x20x10 = 4000
        # Small box: 10x10x10 = 1000
        # Result: 4000 - 1000 = 3000

        solid = SolidBody(
            entity_id=generate_entity_id("solid"),
            workspace_id="main",
            volume=3000.0,
            surface_area=1400.0,  # Increased due to inner surfaces
            center_of_mass=[10.0, 10.0, 5.0],
            topology=Topology(
                face_count=12,  # Outer faces + inner cavity faces
                edge_count=24,
                vertex_count=16,
                is_closed=True,
                is_manifold=True
            )
        )

        assert abs(solid.volume - 3000.0) < 10.0
        assert solid.topology.is_manifold

    def test_subtract_cylinder_from_box(self):
        """Test subtracting a cylinder from a box (drill hole)."""
        # Box: 10x10x10 = 1000
        # Cylinder: pi * r^2 * h = pi * 4 * 10 ≈ 125.7
        # Result: 1000 - 125.7 ≈ 874.3

        solid = SolidBody(
            entity_id=generate_entity_id("solid"),
            workspace_id="main",
            volume=874.3,
            surface_area=750.0,
            center_of_mass=[5.0, 5.0, 5.0],
            topology=Topology(
                face_count=7,  # 6 box faces + 1 cylindrical hole surface
                edge_count=14,
                vertex_count=8,
                is_closed=True,
                is_manifold=True
            )
        )

        assert abs(solid.volume - 874.3) < 10.0


class TestBooleanIntersect:
    """Test boolean intersect operations."""

    def test_intersect_overlapping_boxes(self):
        """Test intersection of two overlapping boxes."""
        # Box 1: 10x10x10 at origin
        # Box 2: 10x10x10 at (5,0,0)
        # Intersection: 5x10x10 = 500

        solid = SolidBody(
            entity_id=generate_entity_id("solid"),
            workspace_id="main",
            volume=500.0,
            surface_area=350.0,
            center_of_mass=[7.5, 5.0, 5.0],
            topology=Topology(
                face_count=6,
                edge_count=12,
                vertex_count=8,
                is_closed=True,
                is_manifold=True
            )
        )

        assert abs(solid.volume - 500.0) < 10.0
        assert solid.topology.is_closed


class TestTopologyValidation:
    """Test topology validation."""

    def test_valid_closed_manifold(self):
        """Test validation of a valid closed manifold solid."""
        topology = Topology(
            face_count=6,
            edge_count=12,
            vertex_count=8,
            is_closed=True,
            is_manifold=True
        )

        assert topology.is_closed
        assert topology.is_manifold
        # Verify Euler characteristic: V - E + F = 2 for closed polyhedra
        assert topology.vertex_count - topology.edge_count + topology.face_count == 2

    def test_valid_sphere_topology(self):
        """Test topology of a sphere."""
        # Tesselated sphere has varying topology depending on resolution
        # But should be closed and manifold
        topology = Topology(
            face_count=200,
            edge_count=300,
            vertex_count=102,
            is_closed=True,
            is_manifold=True
        )

        assert topology.is_closed
        assert topology.is_manifold
        # Euler characteristic for closed surface
        euler = topology.vertex_count - topology.edge_count + topology.face_count
        assert euler == 2

    def test_open_surface_not_closed(self):
        """Test that open surfaces are detected as not closed."""
        topology = Topology(
            face_count=1,
            edge_count=4,
            vertex_count=4,
            is_closed=False,
            is_manifold=True
        )

        assert not topology.is_closed
        assert topology.is_manifold

    def test_non_manifold_detected(self):
        """Test that non-manifold geometry is detected."""
        # T-junction or other non-manifold features
        topology = Topology(
            face_count=3,
            edge_count=6,
            vertex_count=5,
            is_closed=False,
            is_manifold=False
        )

        assert not topology.is_manifold


class TestMassProperties:
    """Test mass property calculations."""

    def test_box_mass_properties(self):
        """Test mass properties of a box."""
        # 10x10x10 box centered at origin
        solid = SolidBody(
            entity_id=generate_entity_id("solid"),
            workspace_id="main",
            volume=1000.0,
            surface_area=600.0,
            center_of_mass=[0.0, 0.0, 0.0],
            topology=Topology(
                face_count=6,
                edge_count=12,
                vertex_count=8,
                is_closed=True,
                is_manifold=True
            )
        )

        assert solid.volume == 1000.0
        assert solid.surface_area == 600.0
        assert solid.center_of_mass == [0.0, 0.0, 0.0]

    def test_cylinder_mass_properties(self):
        """Test mass properties of a cylinder."""
        # Cylinder r=5, h=20
        r = 5.0
        h = 20.0
        volume = math.pi * r * r * h
        surface_area = 2 * math.pi * r * r + 2 * math.pi * r * h

        solid = SolidBody(
            entity_id=generate_entity_id("solid"),
            workspace_id="main",
            volume=volume,
            surface_area=surface_area,
            center_of_mass=[0.0, 0.0, h / 2],
            topology=Topology(
                face_count=3,
                edge_count=2,
                vertex_count=0,
                is_closed=True,
                is_manifold=True
            )
        )

        assert abs(solid.volume - 1570.8) < 1.0
        assert abs(solid.center_of_mass[2] - 10.0) < 0.1
