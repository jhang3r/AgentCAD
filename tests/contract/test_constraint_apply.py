"""Contract test for constraint.apply JSON-RPC interface.

Tests verify the JSON-RPC contract for applying geometric constraints,
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


def test_apply_perpendicular_constraint_success():
    """Test applying perpendicular constraint between two lines."""
    # Create two lines first
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
        "params": {"start": [0.0, 0.0], "end": [0.0, 10.0]},
        "id": 2
    })
    line2_id = line2_response["result"]["data"]["entity_id"]

    # Apply perpendicular constraint
    request = {
        "jsonrpc": "2.0",
        "method": "constraint.apply",
        "params": {
            "constraint_type": "perpendicular",
            "entity_ids": [line1_id, line2_id]
        },
        "id": 3
    }

    response = call_cli(request)

    # Verify JSON-RPC response structure
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 3
    assert "result" in response

    result = response["result"]
    assert result["status"] == "success"
    assert "data" in result

    # Verify constraint data
    data = result["data"]
    assert "constraint_id" in data
    assert data["constraint_id"].startswith("main:constraint_")
    assert data["constraint_type"] == "perpendicular"
    assert data["satisfaction_status"] in ["satisfied", "violated"]
    assert "constrained_entities" in data
    assert line1_id in data["constrained_entities"]
    assert line2_id in data["constrained_entities"]


def test_apply_parallel_constraint_success():
    """Test applying parallel constraint between two lines."""
    # Create two parallel lines
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
        "params": {"start": [0.0, 5.0], "end": [10.0, 5.0]},
        "id": 2
    })
    line2_id = line2_response["result"]["data"]["entity_id"]

    # Apply parallel constraint
    request = {
        "jsonrpc": "2.0",
        "method": "constraint.apply",
        "params": {
            "constraint_type": "parallel",
            "entity_ids": [line1_id, line2_id]
        },
        "id": 3
    }

    response = call_cli(request)

    assert response["result"]["status"] == "success"
    data = response["result"]["data"]
    assert data["constraint_type"] == "parallel"
    assert data["satisfaction_status"] == "satisfied"


def test_apply_distance_constraint_success():
    """Test applying distance constraint between two points."""
    # Create two points
    point1_response = call_cli({
        "jsonrpc": "2.0",
        "method": "entity.create.point",
        "params": {"coordinates": [0.0, 0.0]},
        "id": 1
    })
    point1_id = point1_response["result"]["data"]["entity_id"]

    point2_response = call_cli({
        "jsonrpc": "2.0",
        "method": "entity.create.point",
        "params": {"coordinates": [3.0, 4.0]},
        "id": 2
    })
    point2_id = point2_response["result"]["data"]["entity_id"]

    # Apply distance constraint (should be 5.0)
    request = {
        "jsonrpc": "2.0",
        "method": "constraint.apply",
        "params": {
            "constraint_type": "distance",
            "entity_ids": [point1_id, point2_id],
            "parameters": {"distance": 5.0}
        },
        "id": 3
    }

    response = call_cli(request)

    assert response["result"]["status"] == "success"
    data = response["result"]["data"]
    assert data["constraint_type"] == "distance"
    assert "parameters" in data
    assert data["parameters"]["distance"] == 5.0


def test_apply_constraint_conflict():
    """Test detecting constraint conflicts (parallel + perpendicular on same lines)."""
    # Create two lines
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
        "params": {"start": [0.0, 0.0], "end": [10.0, 10.0]},
        "id": 2
    })
    line2_id = line2_response["result"]["data"]["entity_id"]

    # Apply parallel constraint
    call_cli({
        "jsonrpc": "2.0",
        "method": "constraint.apply",
        "params": {
            "constraint_type": "parallel",
            "entity_ids": [line1_id, line2_id]
        },
        "id": 3
    })

    # Try to apply conflicting perpendicular constraint
    request = {
        "jsonrpc": "2.0",
        "method": "constraint.apply",
        "params": {
            "constraint_type": "perpendicular",
            "entity_ids": [line1_id, line2_id]
        },
        "id": 4
    }

    response = call_cli(request)

    # Should return error
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 4
    assert "error" in response

    error = response["error"]
    assert error["code"] == -32002  # CONSTRAINT_CONFLICT
    assert "conflict" in error["message"].lower()


def test_apply_constraint_invalid_entities():
    """Test applying constraint with non-existent entities."""
    request = {
        "jsonrpc": "2.0",
        "method": "constraint.apply",
        "params": {
            "constraint_type": "parallel",
            "entity_ids": ["main:nonexistent_1", "main:nonexistent_2"]
        },
        "id": 1
    }

    response = call_cli(request)

    assert "error" in response
    error = response["error"]
    assert error["code"] == -32001  # ENTITY_NOT_FOUND


def test_apply_constraint_missing_params():
    """Test applying constraint without required parameters."""
    request = {
        "jsonrpc": "2.0",
        "method": "constraint.apply",
        "params": {
            "constraint_type": "parallel"
            # Missing entity_ids
        },
        "id": 1
    }

    response = call_cli(request)

    assert "error" in response
    error = response["error"]
    assert error["code"] == -32602  # INVALID_PARAMETER
    assert "entity_ids" in error["message"].lower()


def test_apply_constraint_invalid_type():
    """Test applying constraint with invalid constraint type."""
    # Create two lines
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
        "params": {"start": [0.0, 0.0], "end": [0.0, 10.0]},
        "id": 2
    })
    line2_id = line2_response["result"]["data"]["entity_id"]

    request = {
        "jsonrpc": "2.0",
        "method": "constraint.apply",
        "params": {
            "constraint_type": "invalid_constraint_type",
            "entity_ids": [line1_id, line2_id]
        },
        "id": 3
    }

    response = call_cli(request)

    assert "error" in response
    error = response["error"]
    assert error["code"] == -32004  # INVALID_CONSTRAINT
