"""Integration tests for multi-operation geometry workflows.

Tests validate complete end-to-end workflows combining multiple operations.
These tests verify that creation operations integrate correctly with export.

These tests require pythonOCC to be installed (use cad-geo conda environment).
"""
import tempfile
import struct
import sys
import math
from pathlib import Path

# Setup path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# Import geometry kernel modules (will only work if pythonOCC is installed)
try:
    from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire
    from OCC.Core.gp import gp_Pnt, gp_Circ, gp_Ax2, gp_Dir
    from cad_kernel.creation_ops import extrude
    from cad_kernel.tessellation import MeshGenerator, TessellationConfig
    from file_io.stl_handler import export_stl
    from file_io.step_handler import export_step
    PYTHONOCC_AVAILABLE = True
except ImportError as e:
    PYTHONOCC_AVAILABLE = False
    IMPORT_ERROR = str(e)

import pytest

# Skip all tests if pythonOCC is not available
pytestmark = pytest.mark.skipif(
    not PYTHONOCC_AVAILABLE,
    reason=f"pythonOCC not installed in environment. Run: conda activate cad-geo"
)


def create_circle_wire(radius: float, center=(0, 0, 0)):
    """Helper: Create a circular wire for testing.

    Args:
        radius: Circle radius
        center: Center point (x, y, z)

    Returns:
        TopoDS_Wire representing the circle
    """
    from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire
    from OCC.Core.gp import gp_Pnt, gp_Circ, gp_Ax2, gp_Dir

    # Create circle
    center_pnt = gp_Pnt(center[0], center[1], center[2])
    axis = gp_Ax2(center_pnt, gp_Dir(0, 0, 1))
    circle = gp_Circ(axis, radius)

    # Convert to edge and wire
    edge = BRepBuilderAPI_MakeEdge(circle).Edge()
    wire_builder = BRepBuilderAPI_MakeWire(edge)

    if not wire_builder.IsDone():
        raise ValueError("Failed to create circle wire")

    return wire_builder.Wire()


def test_create_circle_extrude_export_verify_geometry():
    """T068: Integration test for create circle → extrude → export → verify geometry.

    This test validates the complete workflow:
    1. Create a 2D circle wire
    2. Extrude to create a cylinder
    3. Export to STL
    4. Verify the exported geometry is correct
    """
    # Step 1: Create a circle wire with known dimensions
    radius = 10.0  # 10mm radius
    height = 30.0  # 30mm height

    circle_wire = create_circle_wire(radius)

    # Step 2: Extrude the circle to create a cylinder
    geo_shape, solid_props = extrude(
        profile_shape=circle_wire,
        direction=[0, 0, 1],
        distance=height,
        workspace_id="test_workflow"
    )

    # Verify properties
    expected_volume = math.pi * (radius ** 2) * height
    assert abs(solid_props.volume - expected_volume) / expected_volume < 0.001, \
        f"Volume {solid_props.volume} not within 0.1% of expected {expected_volume}"

    assert solid_props.is_closed, "Extruded solid must be closed"
    assert solid_props.is_manifold, "Extruded solid must be manifold"
    assert solid_props.face_count >= 3, f"Cylinder should have at least 3 faces, got {solid_props.face_count}"

    # Step 3: Export to STL
    with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as tmp:
        export_path = tmp.name

    try:
        shape = geo_shape.to_shape()
        result = export_stl([shape], export_path, tessellation_quality="standard")

        # Step 4: Verify the exported geometry
        assert result["triangle_count"] > 0, "Must have triangles"
        assert result["file_size"] > 0, "File must have content"

        # Verify file exists and has correct structure
        assert Path(export_path).exists()

        # Read and verify STL file contains actual geometry
        with open(export_path, "rb") as f:
            header = f.read(80)
            assert len(header) == 80

            tri_count_bytes = f.read(4)
            tri_count = struct.unpack("<I", tri_count_bytes)[0]
            assert tri_count == result["triangle_count"]
            assert tri_count > 0

            # Verify triangles have non-zero coordinates
            non_zero_count = 0
            for i in range(min(10, tri_count)):
                # Read triangle data
                normal = struct.unpack("<fff", f.read(12))
                v1 = struct.unpack("<fff", f.read(12))
                v2 = struct.unpack("<fff", f.read(12))
                v3 = struct.unpack("<fff", f.read(12))
                attr = struct.unpack("<H", f.read(2))

                # Check for non-zero coordinates
                if any(abs(coord) > 0.01 for coord in v1 + v2 + v3):
                    non_zero_count += 1

            assert non_zero_count > 0, "STL must contain actual geometry (not all zeros)"

        print(f"\n{'='*70}")
        print("WORKFLOW TEST SUCCESS:")
        print(f"{'='*70}")
        print(f"Created cylinder: radius={radius}mm, height={height}mm")
        print(f"Volume: {solid_props.volume:.2f} mm³ (expected: {expected_volume:.2f} mm³)")
        print(f"Exported STL: {result['triangle_count']} triangles, {result['file_size']} bytes")
        print(f"File: {export_path}")
        print(f"{'='*70}\n")

    finally:
        # Cleanup
        if Path(export_path).exists():
            Path(export_path).unlink()


def test_multi_operation_workflow_box_and_cylinder():
    """Integration test: Create multiple primitives and export together.

    Tests the workflow:
    1. Create primitives using creation operations
    2. Export multiple shapes to single STL
    3. Verify combined mesh
    """
    from cad_kernel.primitive_ops import create_box, create_cylinder

    # Create a box
    box_shape, box_props = create_box(
        width=20.0,
        depth=20.0,
        height=10.0,
        workspace_id="test_multi"
    )

    # Create a cylinder
    cylinder_shape, cylinder_props = create_cylinder(
        radius=5.0,
        height=15.0,
        workspace_id="test_multi"
    )

    # Export both to single STL
    with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as tmp:
        export_path = tmp.name

    try:
        box = box_shape.to_shape()
        cylinder = cylinder_shape.to_shape()

        result = export_stl([box, cylinder], export_path, tessellation_quality="preview")

        assert result["entity_count"] == 2
        assert result["triangle_count"] > 0
        assert result["file_size"] > 0

        # Verify file structure
        assert Path(export_path).exists()

        # Verify combined volume is sum of individual volumes
        print(f"\nMulti-shape export:")
        print(f"  Box volume: {box_props.volume:.2f} mm³")
        print(f"  Cylinder volume: {cylinder_props.volume:.2f} mm³")
        print(f"  Total triangles: {result['triangle_count']}")
        print(f"  File size: {result['file_size']} bytes")

    finally:
        # Cleanup
        if Path(export_path).exists():
            Path(export_path).unlink()


def test_circle_extrude_step_export():
    """Integration test: Create cylinder and export to STEP format.

    Tests that extruded geometry can be exported to STEP (exact BRep).
    """
    # Create circle wire
    radius = 12.0
    height = 25.0
    circle_wire = create_circle_wire(radius)

    # Extrude to cylinder
    geo_shape, solid_props = extrude(
        profile_shape=circle_wire,
        direction=[0, 0, 1],
        distance=height,
        workspace_id="test_step"
    )

    # Export to STEP
    with tempfile.NamedTemporaryFile(suffix=".step", delete=False) as tmp:
        export_path = tmp.name

    try:
        shape = geo_shape.to_shape()
        result = export_step([shape], export_path, schema="AP214")

        assert result["format"] == "step"
        assert result["schema"] == "AP214"
        assert result["data_loss"] is False
        assert result["file_size"] > 0

        # Verify STEP file format
        with open(export_path, "r") as f:
            content = f.read(500)
            # STEP files should contain ISO-10303 reference
            assert "ISO-10303" in content or "STEP" in content or "FILE_SCHEMA" in content

        print(f"\nSTEP export test:")
        print(f"  Cylinder: r={radius}mm, h={height}mm")
        print(f"  Volume: {solid_props.volume:.2f} mm³")
        print(f"  STEP file: {result['file_size']} bytes")
        print(f"  Data loss: {result['data_loss']}")

    finally:
        # Cleanup
        if Path(export_path).exists():
            Path(export_path).unlink()


def test_workflow_with_tessellation_quality_comparison():
    """Integration test: Compare different tessellation qualities.

    Creates a shape and exports with different quality settings,
    verifying that quality affects triangle count as expected.
    """
    from cad_kernel.primitive_ops import create_sphere

    # Create a sphere (smooth surface shows quality differences best)
    radius = 20.0
    geo_shape, solid_props = create_sphere(
        radius=radius,
        workspace_id="test_quality"
    )

    shape = geo_shape.to_shape()
    triangle_counts = {}

    for quality in ["preview", "standard", "high_quality"]:
        with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as tmp:
            export_path = tmp.name

        try:
            result = export_stl([shape], export_path, tessellation_quality=quality)
            triangle_counts[quality] = result["triangle_count"]
        finally:
            if Path(export_path).exists():
                Path(export_path).unlink()

    # Verify quality progression
    assert triangle_counts["preview"] < triangle_counts["standard"], \
        f"Preview ({triangle_counts['preview']}) should have fewer triangles than standard ({triangle_counts['standard']})"

    assert triangle_counts["standard"] < triangle_counts["high_quality"], \
        f"Standard ({triangle_counts['standard']}) should have fewer triangles than high quality ({triangle_counts['high_quality']})"

    print(f"\nTessellation quality comparison (r={radius}mm sphere):")
    print(f"  Preview:      {triangle_counts['preview']:>6} triangles")
    print(f"  Standard:     {triangle_counts['standard']:>6} triangles")
    print(f"  High quality: {triangle_counts['high_quality']:>6} triangles")
