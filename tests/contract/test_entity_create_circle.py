"""Contract test for entity.create.circle JSON-RPC interface.

Tests verify the JSON-RPC contract for circle creation, ensuring correct
request/response format, parameter validation, and error handling.

TDD: These tests should FAIL until implementation is complete.
"""
import json
import math
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


def test_create_circle_2d_success():
    """Test successful 2D circle creation."""
    request = {
        "jsonrpc": "2.0",
        "method": "entity.create.circle",
        "params": {
            "center": [10.0, 20.0],
            "radius": 5.0
        },
        "id": 1
    }

    response = call_cli(request)

    # Verify JSON-RPC response structure
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 1
    assert "result" in response

    result = response["result"]
    assert result["status"] == "success"
    assert "data" in result

    # Verify data structure
    data = result["data"]
    assert "entity_id" in data
    assert data["entity_id"].startswith("main:circle_")
    assert data["entity_type"] == "circle"
    assert data["center"] == [10.0, 20.0, 0.0]  # 2D circles get z=0
    assert data["radius"] == 5.0

    # Verify computed properties
    assert "area" in data
    expected_area = math.pi * 5.0 ** 2
    assert abs(data["area"] - expected_area) < 1e-6

    assert "circumference" in data
    expected_circumference = 2 * math.pi * 5.0
    assert abs(data["circumference"] - expected_circumference) < 1e-6


def test_create_circle_3d_success():
    """Test successful 3D circle creation."""
    request = {
        "jsonrpc": "2.0",
        "method": "entity.create.circle",
        "params": {
            "center": [10.0, 20.0, 30.0],
            "radius": 7.5
        },
        "id": 2
    }

    response = call_cli(request)

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 2
    result = response["result"]
    assert result["status"] == "success"
    data = result["data"]
    assert data["center"] == [10.0, 20.0, 30.0]
    assert data["radius"] == 7.5


def test_create_circle_zero_radius():
    """Test circle creation with zero radius."""
    request = {
        "jsonrpc": "2.0",
        "method": "entity.create.circle",
        "params": {
            "center": [10.0, 20.0],
            "radius": 0.0
        },
        "id": 3
    }

    response = call_cli(request)

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 3
    assert "error" in response

    error = response["error"]
    assert error["code"] in [-32602, -32603]  # INVALID_PARAMETER or INVALID_GEOMETRY
    assert "radius" in error["message"].lower()


def test_create_circle_negative_radius():
    """Test circle creation with negative radius."""
    request = {
        "jsonrpc": "2.0",
        "method": "entity.create.circle",
        "params": {
            "center": [10.0, 20.0],
            "radius": -5.0
        },
        "id": 4
    }

    response = call_cli(request)

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 4
    assert "error" in response

    error = response["error"]
    assert error["code"] in [-32602, -32603]  # INVALID_PARAMETER or INVALID_GEOMETRY
    assert "radius" in error["message"].lower()


def test_create_circle_infinite_radius():
    """Test circle creation with infinite radius."""
    request = {
        "jsonrpc": "2.0",
        "method": "entity.create.circle",
        "params": {
            "center": [10.0, 20.0],
            "radius": float('inf')
        },
        "id": 5
    }

    response = call_cli(request)

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 5
    assert "error" in response

    error = response["error"]
    assert error["code"] == -32603  # INVALID_GEOMETRY
    assert "finite" in error["message"].lower()


def test_create_circle_invalid_center():
    """Test circle creation with invalid center point."""
    request = {
        "jsonrpc": "2.0",
        "method": "entity.create.circle",
        "params": {
            "center": [10.0],  # Invalid: only 1 coordinate
            "radius": 5.0
        },
        "id": 6
    }

    response = call_cli(request)

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 6
    assert "error" in response

    error = response["error"]
    assert error["code"] == -32602  # INVALID_PARAMETER


def test_create_circle_missing_params():
    """Test circle creation with missing parameters."""
    request = {
        "jsonrpc": "2.0",
        "method": "entity.create.circle",
        "params": {
            "center": [10.0, 20.0]
            # Missing "radius"
        },
        "id": 7
    }

    response = call_cli(request)

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 7
    assert "error" in response

    error = response["error"]
    assert error["code"] == -32602  # INVALID_PARAMETER
    assert "radius" in error["message"].lower()
