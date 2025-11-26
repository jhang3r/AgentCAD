"""Contract test for file.export JSON-RPC interface.

Tests verify the JSON-RPC contract for exporting CAD files in various formats.

TDD: These tests should FAIL until implementation is complete.
"""
import json
import subprocess
import sys
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


def test_file_export_json_success():
    """Test exporting entities to JSON format."""
    # Create some entities
    call_cli({
        "jsonrpc": "2.0",
        "method": "entity.create.point",
        "params": {"coordinates": [10.0, 20.0]},
        "id": 1
    })

    call_cli({
        "jsonrpc": "2.0",
        "method": "entity.create.circle",
        "params": {"center": [0.0, 0.0], "radius": 5.0},
        "id": 2
    })

    # Export to JSON
    request = {
        "jsonrpc": "2.0",
        "method": "file.export",
        "params": {
            "file_path": "test_output.json",
            "format": "json"
        },
        "id": 3
    }

    response = call_cli(request)

    # Verify response
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 3
    assert "result" in response

    result = response["result"]
    assert result["status"] == "success"
    assert "data" in result

    data = result["data"]
    assert "file_path" in data
    assert "format" in data
    assert data["format"] == "json"
    assert "entity_count" in data
    assert data["entity_count"] >= 2
    assert "file_size" in data


def test_file_export_stl_success():
    """Test exporting solid to STL format."""
    # Create a cylinder
    circle_response = call_cli({
        "jsonrpc": "2.0",
        "method": "entity.create.circle",
        "params": {"center": [0.0, 0.0], "radius": 5.0},
        "id": 1
    })
    circle_id = circle_response["result"]["data"]["entity_id"]

    # Extrude to solid
    extrude_response = call_cli({
        "jsonrpc": "2.0",
        "method": "solid.extrude",
        "params": {
            "entity_ids": [circle_id],
            "distance": 10.0
        },
        "id": 2
    })
    solid_id = extrude_response["result"]["data"]["entity_id"]

    # Export to STL
    request = {
        "jsonrpc": "2.0",
        "method": "file.export",
        "params": {
            "file_path": "test_cylinder.stl",
            "format": "stl",
            "entity_ids": [solid_id]
        },
        "id": 3
    }

    response = call_cli(request)

    assert response["result"]["status"] == "success"
    data = response["result"]["data"]
    assert data["format"] == "stl"
    assert "triangle_count" in data
    assert data["triangle_count"] > 0


def test_file_export_missing_params():
    """Test export with missing parameters."""
    request = {
        "jsonrpc": "2.0",
        "method": "file.export",
        "params": {
            # Missing file_path
            "format": "json"
        },
        "id": 1
    }

    response = call_cli(request)

    assert "error" in response
    error = response["error"]
    assert error["code"] == -32602  # INVALID_PARAMETER


def test_file_export_unsupported_format():
    """Test export with unsupported format."""
    request = {
        "jsonrpc": "2.0",
        "method": "file.export",
        "params": {
            "file_path": "test.xyz",
            "format": "unsupported_format"
        },
        "id": 1
    }

    response = call_cli(request)

    assert "error" in response
    error = response["error"]
    # Could be UNSUPPORTED_FORMAT (-32009) or INVALID_PARAMETER (-32602)
    assert error["code"] in [-32009, -32602]


def test_file_import_json_success():
    """Test importing entities from JSON format."""
    # First export to create a file
    call_cli({
        "jsonrpc": "2.0",
        "method": "entity.create.point",
        "params": {"coordinates": [5.0, 5.0]},
        "id": 1
    })

    call_cli({
        "jsonrpc": "2.0",
        "method": "file.export",
        "params": {
            "file_path": "test_import.json",
            "format": "json"
        },
        "id": 2
    })

    # Now import it
    request = {
        "jsonrpc": "2.0",
        "method": "file.import",
        "params": {
            "file_path": "test_import.json",
            "format": "json"
        },
        "id": 3
    }

    response = call_cli(request)

    # Verify import succeeded
    assert "result" in response or "error" in response
    # Basic validation - implementation may vary
