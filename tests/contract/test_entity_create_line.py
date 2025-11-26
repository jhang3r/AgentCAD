"""Contract test for entity.create.line JSON-RPC interface.

Tests verify the JSON-RPC contract for line creation, ensuring correct
request/response format, parameter validation, and error handling.

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


def test_create_line_2d_success():
    """Test successful 2D line creation."""
    request = {
        "jsonrpc": "2.0",
        "method": "entity.create.line",
        "params": {
            "start": [0.0, 0.0],
            "end": [10.0, 10.0]
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
    assert data["entity_id"].startswith("main:line_")
    assert data["entity_type"] == "line"
    assert data["start"] == [0.0, 0.0, 0.0]  # 2D lines get z=0
    assert data["end"] == [10.0, 10.0, 0.0]
    assert "length" in data
    assert data["length"] > 0
    assert "direction_vector" in data
    assert len(data["direction_vector"]) == 3


def test_create_line_3d_success():
    """Test successful 3D line creation."""
    request = {
        "jsonrpc": "2.0",
        "method": "entity.create.line",
        "params": {
            "start": [0.0, 0.0, 0.0],
            "end": [10.0, 10.0, 10.0]
        },
        "id": 2
    }

    response = call_cli(request)

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 2
    result = response["result"]
    assert result["status"] == "success"
    data = result["data"]
    assert data["start"] == [0.0, 0.0, 0.0]
    assert data["end"] == [10.0, 10.0, 10.0]

    # Verify length calculation
    expected_length = (10**2 + 10**2 + 10**2) ** 0.5
    assert abs(data["length"] - expected_length) < 1e-6


def test_create_line_degenerate():
    """Test line creation with start == end (degenerate)."""
    request = {
        "jsonrpc": "2.0",
        "method": "entity.create.line",
        "params": {
            "start": [10.0, 20.0],
            "end": [10.0, 20.0]  # Same as start
        },
        "id": 3
    }

    response = call_cli(request)

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 3
    assert "error" in response

    error = response["error"]
    assert error["code"] == -32603  # INVALID_GEOMETRY
    assert "degenerate" in error["message"].lower()


def test_create_line_dimension_mismatch():
    """Test line creation with mismatched dimensions."""
    request = {
        "jsonrpc": "2.0",
        "method": "entity.create.line",
        "params": {
            "start": [0.0, 0.0],  # 2D
            "end": [10.0, 10.0, 10.0]  # 3D
        },
        "id": 4
    }

    response = call_cli(request)

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 4
    assert "error" in response

    error = response["error"]
    assert error["code"] == -32602  # INVALID_PARAMETER
    assert "dimension" in error["message"].lower()


def test_create_line_invalid_start():
    """Test line creation with invalid start point."""
    request = {
        "jsonrpc": "2.0",
        "method": "entity.create.line",
        "params": {
            "start": [float('nan'), 0.0],
            "end": [10.0, 10.0]
        },
        "id": 5
    }

    response = call_cli(request)

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 5
    assert "error" in response

    error = response["error"]
    assert error["code"] == -32603  # INVALID_GEOMETRY


def test_create_line_missing_params():
    """Test line creation with missing parameters."""
    request = {
        "jsonrpc": "2.0",
        "method": "entity.create.line",
        "params": {
            "start": [0.0, 0.0]
            # Missing "end"
        },
        "id": 6
    }

    response = call_cli(request)

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 6
    assert "error" in response

    error = response["error"]
    assert error["code"] == -32602  # INVALID_PARAMETER
