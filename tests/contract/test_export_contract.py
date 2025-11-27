"""Contract tests for file.export operations (STEP and STL).

Tests verify the JSON-RPC contract for exporting 3D geometry to
various file formats.

TDD: These tests should FAIL until implementation is complete.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def call_cli(request: dict) -> dict:
    """Helper to call CLI with JSON-RPC request."""
    input_data = json.dumps(request) + "\n"
    result = subprocess.run(
        [sys.executable, "-m", "src.agent_interface.cli"],
        input=input_data,
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent
    )

    if result.returncode != 0:
        raise RuntimeError(f"CLI failed: {result.stderr}")

    return json.loads(result.stdout.strip())


def test_export_stl_basic():
    """T026: Contract test for file.export operation - STL format."""
    # First create a simple box primitive
    create_request = {
        "jsonrpc": "2.0",
        "method": "solid.primitive",
        "params": {
            "primitive_type": "box",
            "width": 20.0,
            "depth": 30.0,
            "height": 40.0,
            "workspace_id": "main"
        },
        "id": 1
    }

    create_response = call_cli(create_request)
    assert create_response["result"]["status"] == "success"
    entity_id = create_response["result"]["data"]["entity_id"]

    # Export to STL
    with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as tmp:
        export_path = tmp.name

    export_request = {
        "jsonrpc": "2.0",
        "method": "file.export",
        "params": {
            "file_path": export_path,
            "format": "stl",
            "entity_ids": [entity_id],
            "workspace_id": "main",
            "tessellation_quality": "standard"
        },
        "id": 2
    }

    export_response = call_cli(export_request)

    # Verify response structure
    assert export_response["jsonrpc"] == "2.0"
    assert export_response["id"] == 2
    assert "result" in export_response

    result = export_response["result"]
    assert "file_path" in result
    assert "format" in result
    assert result["format"] == "stl"
    assert "triangle_count" in result
    assert "file_size" in result

    # Verify file exists
    assert Path(export_path).exists()
    assert Path(export_path).stat().st_size > 0

    # Cleanup
    Path(export_path).unlink()


def test_export_stl_with_real_triangle_data():
    """T027: Test valid solid exports to STL with non-zero triangle data."""
    # Create a cylinder (more interesting geometry than box)
    create_request = {
        "jsonrpc": "2.0",
        "method": "solid.primitive",
        "params": {
            "primitive_type": "cylinder",
            "radius": 15.0,
            "height": 50.0,
            "workspace_id": "main"
        },
        "id": 1
    }

    create_response = call_cli(create_request)
    entity_id = create_response["result"]["data"]["entity_id"]

    # Export to STL
    with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as tmp:
        export_path = tmp.name

    export_request = {
        "jsonrpc": "2.0",
        "method": "file.export",
        "params": {
            "file_path": export_path,
            "format": "stl",
            "entity_ids": [entity_id],
            "workspace_id": "main"
        },
        "id": 2
    }

    export_response = call_cli(export_request)
    result = export_response["result"]

    # Verify triangle count is non-zero
    assert result["triangle_count"] > 0, "STL must contain actual geometry (non-zero triangles)"

    # Verify file size is reasonable (not all zeros)
    file_size = Path(export_path).stat().st_size
    # Binary STL: 80 byte header + 4 byte count + 50 bytes per triangle
    expected_min_size = 84 + (50 * result["triangle_count"])
    assert file_size >= expected_min_size, f"File size {file_size} too small for {result['triangle_count']} triangles"

    # Read binary STL and verify header + triangle count match
    with open(export_path, 'rb') as f:
        header = f.read(80)
        assert len(header) == 80

        # Read triangle count (4 bytes, little-endian unsigned int)
        import struct
        tri_count_bytes = f.read(4)
        tri_count = struct.unpack('<I', tri_count_bytes)[0]
        assert tri_count == result["triangle_count"]
        assert tri_count > 0

    # Cleanup
    Path(export_path).unlink()


def test_export_tessellation_quality_presets():
    """T028: Test tessellation quality presets produce different triangle counts."""
    # Create a sphere (smooth surface shows quality differences well)
    create_request = {
        "jsonrpc": "2.0",
        "method": "solid.primitive",
        "params": {
            "primitive_type": "sphere",
            "radius": 25.0,
            "workspace_id": "main"
        },
        "id": 1
    }

    create_response = call_cli(create_request)
    entity_id = create_response["result"]["data"]["entity_id"]

    triangle_counts = {}

    # Test each quality preset
    for quality in ["preview", "standard", "high_quality"]:
        with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as tmp:
            export_path = tmp.name

        export_request = {
            "jsonrpc": "2.0",
            "method": "file.export",
            "params": {
                "file_path": export_path,
                "format": "stl",
                "entity_ids": [entity_id],
                "workspace_id": "main",
                "tessellation_quality": quality
            },
            "id": 2
        }

        export_response = call_cli(export_request)
        result = export_response["result"]

        triangle_counts[quality] = result["triangle_count"]

        # Verify tessellation config is reported
        assert "tessellation_config" in result
        assert result["tessellation_config"]["quality"] == quality

        # Cleanup
        Path(export_path).unlink()

    # Verify different quality presets produce different triangle counts
    # preview < standard < high_quality
    assert triangle_counts["preview"] < triangle_counts["standard"], \
        "Preview quality should have fewer triangles than standard"
    assert triangle_counts["standard"] < triangle_counts["high_quality"], \
        "Standard quality should have fewer triangles than high quality"


def test_export_multi_solid_to_single_stl():
    """T029: Test multi-solid export to single STL file."""
    # Create two primitives
    box_request = {
        "jsonrpc": "2.0",
        "method": "solid.primitive",
        "params": {
            "primitive_type": "box",
            "width": 10.0,
            "depth": 10.0,
            "height": 10.0,
            "workspace_id": "main"
        },
        "id": 1
    }

    sphere_request = {
        "jsonrpc": "2.0",
        "method": "solid.primitive",
        "params": {
            "primitive_type": "sphere",
            "radius": 8.0,
            "workspace_id": "main"
        },
        "id": 2
    }

    box_response = call_cli(box_request)
    sphere_response = call_cli(sphere_request)

    box_id = box_response["result"]["data"]["entity_id"]
    sphere_id = sphere_response["result"]["data"]["entity_id"]

    # Export both to single STL
    with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as tmp:
        export_path = tmp.name

    export_request = {
        "jsonrpc": "2.0",
        "method": "file.export",
        "params": {
            "file_path": export_path,
            "format": "stl",
            "entity_ids": [box_id, sphere_id],
            "workspace_id": "main",
            "tessellation_quality": "preview"
        },
        "id": 3
    }

    export_response = call_cli(export_request)
    result = export_response["result"]

    # Verify multiple entities were exported
    assert result["entity_count"] == 2

    # Verify combined triangle count
    assert result["triangle_count"] > 0

    # Verify file exists and has data
    assert Path(export_path).exists()
    assert Path(export_path).stat().st_size > 0

    # Cleanup
    Path(export_path).unlink()


def test_export_step_format():
    """Test STEP export preserves exact geometry."""
    # Create a box
    create_request = {
        "jsonrpc": "2.0",
        "method": "solid.primitive",
        "params": {
            "primitive_type": "box",
            "width": 50.0,
            "depth": 60.0,
            "height": 70.0,
            "workspace_id": "main"
        },
        "id": 1
    }

    create_response = call_cli(create_request)
    entity_id = create_response["result"]["data"]["entity_id"]

    # Export to STEP
    with tempfile.NamedTemporaryFile(suffix=".step", delete=False) as tmp:
        export_path = tmp.name

    export_request = {
        "jsonrpc": "2.0",
        "method": "file.export",
        "params": {
            "file_path": export_path,
            "format": "step",
            "entity_ids": [entity_id],
            "workspace_id": "main",
            "schema": "AP214"
        },
        "id": 2
    }

    export_response = call_cli(export_request)
    result = export_response["result"]

    # Verify response structure
    assert result["format"] == "step"
    assert result["schema"] == "AP214"
    assert result["data_loss"] is False  # STEP preserves exact geometry

    # Verify file exists
    assert Path(export_path).exists()
    assert Path(export_path).stat().st_size > 0

    # Verify STEP file starts with header
    with open(export_path, 'r') as f:
        content = f.read(100)
        assert "ISO-10303" in content or "STEP" in content

    # Cleanup
    Path(export_path).unlink()


def test_export_error_invalid_format():
    """T030 (partial): Test error handling for unsupported format."""
    export_request = {
        "jsonrpc": "2.0",
        "method": "file.export",
        "params": {
            "file_path": "/tmp/test.xyz",
            "format": "xyz",  # Unsupported format
            "entity_ids": ["fake_id"],
            "workspace_id": "main"
        },
        "id": 1
    }

    export_response = call_cli(export_request)

    # Should return error
    assert "error" in export_response
    error = export_response["error"]
    assert error["code"] in [-32602, -32603]  # Invalid params or internal error


def test_export_error_no_geometry():
    """T030 (partial): Test error handling when entities have no geometry."""
    # Try to export non-existent entity
    with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as tmp:
        export_path = tmp.name

    export_request = {
        "jsonrpc": "2.0",
        "method": "file.export",
        "params": {
            "file_path": export_path,
            "format": "stl",
            "entity_ids": ["nonexistent_entity_id"],
            "workspace_id": "main"
        },
        "id": 1
    }

    export_response = call_cli(export_request)

    # Should return error (no valid geometry found)
    assert "error" in export_response
    error = export_response["error"]
    assert error["code"] in [-32602, -32603]

    # Cleanup if file was created
    if Path(export_path).exists():
        Path(export_path).unlink()


def test_export_ascii_stl():
    """Test ASCII STL export format."""
    # Create a small box
    create_request = {
        "jsonrpc": "2.0",
        "method": "solid.primitive",
        "params": {
            "primitive_type": "box",
            "width": 10.0,
            "depth": 10.0,
            "height": 10.0,
            "workspace_id": "main"
        },
        "id": 1
    }

    create_response = call_cli(create_request)
    entity_id = create_response["result"]["data"]["entity_id"]

    # Export to ASCII STL
    with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as tmp:
        export_path = tmp.name

    export_request = {
        "jsonrpc": "2.0",
        "method": "file.export",
        "params": {
            "file_path": export_path,
            "format": "stl",
            "entity_ids": [entity_id],
            "workspace_id": "main",
            "ascii": True
        },
        "id": 2
    }

    export_response = call_cli(export_request)
    result = export_response["result"]

    # Verify file exists
    assert Path(export_path).exists()

    # Verify ASCII format
    with open(export_path, 'r') as f:
        content = f.read()
        assert "solid" in content.lower()
        assert "facet normal" in content.lower()
        assert "vertex" in content.lower()
        assert "endsolid" in content.lower()

    # Cleanup
    Path(export_path).unlink()
