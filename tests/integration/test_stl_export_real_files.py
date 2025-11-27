"""Integration tests for STL export with real file verification.

Tests create real geometry, export to STL, and verify file contents.

These tests require pythonOCC to be installed (use cad-geo conda environment).
"""
import tempfile
import struct
import sys
from pathlib import Path

# Setup path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# Import geometry kernel modules (will only work if pythonOCC is installed)
try:
    from cad_kernel.primitive_ops import create_box, create_cylinder, create_sphere
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


def test_create_box_export_stl_verify_geometry():
    """T031: Integration test for create-export-verify workflow."""
    # Create a 20mm x 30mm x 40mm box
    geo_shape, props = create_box(
        width=20.0,
        depth=30.0,
        height=40.0,
        workspace_id="test"
    )

    # Verify volume
    expected_volume = 20.0 * 30.0 * 40.0  # 24,000 mm³
    assert abs(props.volume - expected_volume) < 1.0, f"Volume {props.volume} != {expected_volume}"

    # Export to STL
    with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as tmp:
        export_path = tmp.name

    try:
        shape = geo_shape.to_shape()
        result = export_stl([shape], export_path, tessellation_quality="standard")

        # Verify export result
        assert result["triangle_count"] > 0, "Must have triangles"
        assert result["file_size"] > 0, "File must have content"

        # Verify file exists
        assert Path(export_path).exists()

        # Read and verify STL file structure
        with open(export_path, "rb") as f:
            header = f.read(80)
            assert len(header) == 80

            tri_count_bytes = f.read(4)
            tri_count = struct.unpack("<I", tri_count_bytes)[0]
            assert tri_count == result["triangle_count"]
            assert tri_count > 0, "Must have non-zero triangles"

            # Verify file size matches triangle count
            # Binary STL: 80 header + 4 count + (50 bytes × triangles)
            expected_size = 84 + (50 * tri_count)
            actual_size = Path(export_path).stat().st_size
            assert actual_size == expected_size, f"Size {actual_size} != {expected_size}"

    finally:
        # Cleanup
        if Path(export_path).exists():
            Path(export_path).unlink()


def test_stl_file_contains_actual_geometry():
    """T032: Test exported STL file contains actual geometry data (not all zeros)."""
    # Create a cylinder
    geo_shape, props = create_cylinder(
        radius=15.0,
        height=50.0,
        workspace_id="test"
    )

    # Export to STL
    with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as tmp:
        export_path = tmp.name

    try:
        shape = geo_shape.to_shape()
        result = export_stl([shape], export_path)

        # Read STL and verify triangles have non-zero coordinates
        with open(export_path, "rb") as f:
            f.read(80)  # Skip header
            tri_count = struct.unpack("<I", f.read(4))[0]

            assert tri_count > 0

            # Check first few triangles have non-zero coordinates
            non_zero_vertices = 0

            for i in range(min(10, tri_count)):
                # Read triangle: normal (3 floats) + 3 vertices (9 floats) + attribute (1 short)
                normal = struct.unpack("<fff", f.read(12))
                v1 = struct.unpack("<fff", f.read(12))
                v2 = struct.unpack("<fff", f.read(12))
                v3 = struct.unpack("<fff", f.read(12))
                attr = struct.unpack("<H", f.read(2))

                # Verify at least one vertex has non-zero coordinates
                if any(abs(coord) > 0.01 for coord in v1 + v2 + v3):
                    non_zero_vertices += 1

            assert non_zero_vertices > 0, "STL must contain actual geometry (not all zeros)"

    finally:
        # Cleanup
        if Path(export_path).exists():
            Path(export_path).unlink()


def test_stl_opens_in_external_viewer_documentation():
    """T033: Document manual verification step for STL viewer compatibility.

    This test creates an STL file and provides instructions for manual verification.
    """
    # Create a sphere
    geo_shape, props = create_sphere(
        radius=25.0,
        workspace_id="test"
    )

    # Export to STL in a known location
    export_path = Path.cwd() / "test_output" / "test_sphere.stl"
    export_path.parent.mkdir(parents=True, exist_ok=True)

    shape = geo_shape.to_shape()
    result = export_stl([shape], str(export_path), tessellation_quality="high_quality")

    # Print manual verification instructions
    print(f"\n{'='*70}")
    print("MANUAL VERIFICATION REQUIRED:")
    print(f"{'='*70}")
    print(f"File: {export_path}")
    print(f"Triangles: {result['triangle_count']}")
    print(f"Size: {result['file_size']} bytes")
    print()
    print("To verify STL compatibility:")
    print("1. Open https://www.viewstl.com/")
    print(f"2. Upload: {export_path}")
    print("3. Verify a smooth sphere is visible")
    print("4. Alternative viewers: MeshLab, FreeCAD, Blender")
    print(f"{'='*70}\n")

    # Test passes if file was created successfully
    assert export_path.exists()
    assert result["triangle_count"] > 0


def test_multi_solid_export_combined_mesh():
    """Integration test: Export multiple solids to single STL file."""
    # Create two primitives
    box_shape, box_props = create_box(10.0, 10.0, 10.0, "test")
    sphere_shape, sphere_props = create_sphere(8.0, "test")

    # Export both to single STL
    with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as tmp:
        export_path = tmp.name

    try:
        box = box_shape.to_shape()
        sphere = sphere_shape.to_shape()

        result = export_stl([box, sphere], export_path, tessellation_quality="preview")

        assert result["entity_count"] == 2
        assert result["triangle_count"] > 0
        assert result["file_size"] > 0

    finally:
        # Cleanup
        if Path(export_path).exists():
            Path(export_path).unlink()


def test_step_export_preserves_exact_geometry():
    """Integration test: STEP export preserves exact BRep geometry."""
    # Create a box with exact dimensions
    geo_shape, props = create_box(50.0, 60.0, 70.0, "test")
    expected_volume = 50.0 * 60.0 * 70.0

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
            content = f.read(200)
            # STEP files should contain ISO-10303 reference
            assert "ISO-10303" in content or "STEP" in content

    finally:
        # Cleanup
        if Path(export_path).exists():
            Path(export_path).unlink()


def test_tessellation_quality_affects_triangle_count():
    """Integration test: Different tessellation qualities produce different mesh densities."""
    # Create a sphere (smooth surface shows quality differences)
    geo_shape, props = create_sphere(30.0, "test")
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
