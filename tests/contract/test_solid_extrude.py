"""Contract test for solid.extrude JSON-RPC interface.

Tests verify the JSON-RPC contract for extrude operations,
ensuring correct request/response format and error handling.

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


def test_extrude_rectangle_success():
    """Test extruding a simple rectangular sketch."""
    # Create a rectangular sketch (4 lines forming a closed loop)
    # Bottom line
    line1_response = call_cli({
        "jsonrpc": "2.0",
        "method": "entity.create.line",
        "params": {"start": [0.0, 0.0], "end": [10.0, 0.0]},
        "id": 1
    })
    line1_id = line1_response["result"]["data"]["entity_id"]

    # Right line
    line2_response = call_cli({
        "jsonrpc": "2.0",
        "method": "entity.create.line",
        "params": {"start": [10.0, 0.0], "end": [10.0, 5.0]},
        "id": 2
    })
    line2_id = line2_response["result"]["data"]["entity_id"]

    # Top line
    line3_response = call_cli({
        "jsonrpc": "2.0",
        "method": "entity.create.line",
        "params": {"start": [10.0, 5.0], "end": [0.0, 5.0]},
        "id": 3
    })
    line3_id = line3_response["result"]["data"]["entity_id"]

    # Left line
    line4_response = call_cli({
        "jsonrpc": "2.0",
        "method": "entity.create.line",
        "params": {"start": [0.0, 5.0], "end": [0.0, 0.0]},
        "id": 4
    })
    line4_id = line4_response["result"]["data"]["entity_id"]

    # Extrude the sketch
    request = {
        "jsonrpc": "2.0",
        "method": "solid.extrude",
        "params": {
            "entity_ids": [line1_id, line2_id, line3_id, line4_id],
            "distance": 10.0
        },
        "id": 5
    }

    response = call_cli(request)

    # Verify JSON-RPC response structure
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 5
    assert "result" in response

    result = response["result"]
    assert result["status"] == "success"
    assert "data" in result

    # Verify solid data
    data = result["data"]
    assert "entity_id" in data
    assert data["entity_id"].startswith("main:solid_")
    assert data["entity_type"] == "solid"
    assert "volume" in data
    assert data["volume"] > 0
    assert "surface_area" in data
    assert data["surface_area"] > 0
    assert "topology" in data

    # Verify topology
    topology = data["topology"]
    assert "face_count" in topology
    assert topology["face_count"] >= 6  # Box has 6 faces
    assert "is_closed" in topology
    assert topology["is_closed"] is True
    assert "is_manifold" in topology
    assert topology["is_manifold"] is True


def test_extrude_circle_success():
    """Test extruding a circle to create a cylinder."""
    # Create a circle
    circle_response = call_cli({
        "jsonrpc": "2.0",
        "method": "entity.create.circle",
        "params": {"center": [0.0, 0.0], "radius": 5.0},
        "id": 1
    })
    circle_id = circle_response["result"]["data"]["entity_id"]

    # Extrude the circle
    request = {
        "jsonrpc": "2.0",
        "method": "solid.extrude",
        "params": {
            "entity_ids": [circle_id],
            "distance": 20.0
        },
        "id": 2
    }

    response = call_cli(request)

    assert response["result"]["status"] == "success"
    data = response["result"]["data"]
    assert data["entity_type"] == "solid"
    assert data["volume"] > 0
    # Cylinder volume = pi * r^2 * h = pi * 25 * 20 ≈ 1570.8
    assert abs(data["volume"] - 1570.8) < 10


def test_extrude_invalid_distance():
    """Test extrude with invalid (zero or negative) distance."""
    # Create a circle
    circle_response = call_cli({
        "jsonrpc": "2.0",
        "method": "entity.create.circle",
        "params": {"center": [0.0, 0.0], "radius": 5.0},
        "id": 1
    })
    circle_id = circle_response["result"]["data"]["entity_id"]

    # Try to extrude with zero distance
    request = {
        "jsonrpc": "2.0",
        "method": "solid.extrude",
        "params": {
            "entity_ids": [circle_id],
            "distance": 0.0
        },
        "id": 2
    }

    response = call_cli(request)

    assert "error" in response
    error = response["error"]
    assert error["code"] == -32602  # INVALID_PARAMETER


def test_extrude_missing_params():
    """Test extrude with missing required parameters."""
    request = {
        "jsonrpc": "2.0",
        "method": "solid.extrude",
        "params": {
            "entity_ids": ["main:circle_test"]
            # Missing distance
        },
        "id": 1
    }

    response = call_cli(request)

    assert "error" in response
    error = response["error"]
    assert error["code"] == -32602  # INVALID_PARAMETER
    assert "distance" in error["message"].lower()


def test_extrude_open_sketch():
    """Test extrude with open (non-closed) sketch."""
    # Create two lines that don't form a closed loop
    line1_response = call_cli({
        "jsonrpc": "2.0",
        "method": "entity.create.line",
        "params": {"start": [0.0, 0.0], "end": [10.0, 0.0]},
        "id": 1
    })
    line1_id = line1_response["result"]["data"]["entity_id"]

    line2_response = call_cli({
        "jsonrpc": "2.0",
        "method": "entity.create.line",
        "params": {"start": [10.0, 0.0], "end": [10.0, 5.0]},
        "id": 2
    })
    line2_id = line2_response["result"]["data"]["entity_id"]

    # Try to extrude (should fail - sketch not closed)
    request = {
        "jsonrpc": "2.0",
        "method": "solid.extrude",
        "params": {
            "entity_ids": [line1_id, line2_id],
            "distance": 10.0
        },
        "id": 3
    }

    response = call_cli(request)

    assert "error" in response
    error = response["error"]
    # Should be INVALID_PARAMETER, INVALID_GEOMETRY, or OPERATION_INVALID
    assert error["code"] in [-32602, -32603, -32005]  # INVALID_PARAMETER, INVALID_GEOMETRY, or OPERATION_INVALID
