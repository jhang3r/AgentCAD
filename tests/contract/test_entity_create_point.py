"""Contract test for entity.create.point JSON-RPC interface.

Tests verify the JSON-RPC contract for point creation, ensuring correct
request/response format, parameter validation, and error handling.

TDD: These tests should FAIL until implementation is complete.
"""
import json
import subprocess
import sys
from pathlib import Path


def call_cli(request: dict) -> dict:
    """Helper to call CLI with JSON-RPC request.

    Args:
        request: JSON-RPC request dict

    Returns:
        JSON-RPC response dict
    """
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


def test_create_point_2d_success():
    """Test successful 2D point creation."""
    request = {
        "jsonrpc": "2.0",
        "method": "entity.create.point",
        "params": {
            "coordinates": [10.0, 20.0]
        },
        "id": 1
    }

    response = call_cli(request)

    # Verify JSON-RPC response structure
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 1
    assert "result" in response

    # Verify result structure
    result = response["result"]
    assert result["status"] == "success"
    assert "data" in result

    # Verify data structure
    data = result["data"]
    assert "entity_id" in data
    assert data["entity_id"].startswith("main:point_")
    assert data["coordinates"] == [10.0, 20.0, 0.0]  # 2D points get z=0
    assert data["entity_type"] == "point"
    assert "workspace_id" in data


def test_create_point_3d_success():
    """Test successful 3D point creation."""
    request = {
        "jsonrpc": "2.0",
        "method": "entity.create.point",
        "params": {
            "coordinates": [10.0, 20.0, 30.0]
        },
        "id": 2
    }

    response = call_cli(request)

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 2
    result = response["result"]
    assert result["status"] == "success"
    data = result["data"]
    assert data["coordinates"] == [10.0, 20.0, 30.0]


def test_create_point_invalid_coordinates():
    """Test point creation with invalid number of coordinates."""
    request = {
        "jsonrpc": "2.0",
        "method": "entity.create.point",
        "params": {
            "coordinates": [10.0]  # Invalid: only 1 coordinate
        },
        "id": 3
    }

    response = call_cli(request)

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 3
    assert "error" in response

    error = response["error"]
    assert error["code"] == -32602  # INVALID_PARAMETER
    assert "coordinates" in error["message"].lower()


def test_create_point_non_finite_coordinates():
    """Test point creation with non-finite coordinates."""
    request = {
        "jsonrpc": "2.0",
        "method": "entity.create.point",
        "params": {
            "coordinates": [10.0, float('inf'), 30.0]
        },
        "id": 4
    }

    response = call_cli(request)

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 4
    assert "error" in response

    error = response["error"]
    assert error["code"] == -32603  # INVALID_GEOMETRY
    assert "finite" in error["message"].lower()


def test_create_point_out_of_bounds():
    """Test point creation with coordinates exceeding bounds."""
    request = {
        "jsonrpc": "2.0",
        "method": "entity.create.point",
        "params": {
            "coordinates": [2e6, 20.0, 30.0]  # Exceeds [-1e6, 1e6]
        },
        "id": 5
    }

    response = call_cli(request)

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 5
    assert "error" in response

    error = response["error"]
    assert error["code"] == -32603  # INVALID_GEOMETRY
    assert "bounds" in error["message"].lower()


def test_create_point_missing_params():
    """Test point creation with missing required parameters."""
    request = {
        "jsonrpc": "2.0",
        "method": "entity.create.point",
        "params": {},
        "id": 6
    }

    response = call_cli(request)

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 6
    assert "error" in response

    error = response["error"]
    assert error["code"] == -32602  # INVALID_PARAMETER
    assert "coordinates" in error["message"].lower()
