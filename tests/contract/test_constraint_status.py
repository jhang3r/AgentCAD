"""Contract test for constraint.status JSON-RPC interface.

Tests verify the JSON-RPC contract for querying constraint status,
including satisfaction status and degrees of freedom analysis.

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


def test_constraint_status_success():
    """Test querying constraint status after applying constraint."""
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

    # Apply constraint
    apply_response = call_cli({
        "jsonrpc": "2.0",
        "method": "constraint.apply",
        "params": {
            "constraint_type": "perpendicular",
            "entity_ids": [line1_id, line2_id]
        },
        "id": 3
    })
    constraint_id = apply_response["result"]["data"]["constraint_id"]

    # Query constraint status
    request = {
        "jsonrpc": "2.0",
        "method": "constraint.status",
        "params": {
            "constraint_id": constraint_id
        },
        "id": 4
    }

    response = call_cli(request)

    # Verify JSON-RPC response structure
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 4
    assert "result" in response

    result = response["result"]
    assert result["status"] == "success"
    assert "data" in result

    # Verify constraint status data
    data = result["data"]
    assert data["constraint_id"] == constraint_id
    assert data["constraint_type"] == "perpendicular"
    assert data["satisfaction_status"] in ["satisfied", "violated", "redundant"]
    assert "constrained_entities" in data


def test_constraint_status_list_all():
    """Test listing all constraints in workspace."""
    # Create entities and constraints
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

    # Apply multiple constraints
    call_cli({
        "jsonrpc": "2.0",
        "method": "constraint.apply",
        "params": {
            "constraint_type": "perpendicular",
            "entity_ids": [line1_id, line2_id]
        },
        "id": 3
    })

    # List all constraints
    request = {
        "jsonrpc": "2.0",
        "method": "constraint.status",
        "params": {},
        "id": 4
    }

    response = call_cli(request)

    assert response["result"]["status"] == "success"
    data = response["result"]["data"]
    assert "constraints" in data
    assert isinstance(data["constraints"], list)
    assert len(data["constraints"]) >= 1


def test_constraint_status_with_dof_analysis():
    """Test constraint status includes degrees of freedom analysis."""
    # Create a simple sketch with under-constrained entities
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
        "params": {"coordinates": [10.0, 0.0]},
        "id": 2
    })
    point2_id = point2_response["result"]["data"]["entity_id"]

    # Apply distance constraint
    call_cli({
        "jsonrpc": "2.0",
        "method": "constraint.apply",
        "params": {
            "constraint_type": "distance",
            "entity_ids": [point1_id, point2_id],
            "parameters": {"distance": 10.0}
        },
        "id": 3
    })

    # Query workspace-level status with DOF analysis
    request = {
        "jsonrpc": "2.0",
        "method": "constraint.status",
        "params": {
            "include_dof_analysis": True
        },
        "id": 4
    }

    response = call_cli(request)

    assert response["result"]["status"] == "success"
    data = response["result"]["data"]

    # Should include DOF analysis
    if "dof_analysis" in data:
        dof = data["dof_analysis"]
        assert "total_dof" in dof
        assert "constrained_dof" in dof
        assert "remaining_dof" in dof
        assert dof["remaining_dof"] >= 0


def test_constraint_status_not_found():
    """Test querying non-existent constraint."""
    request = {
        "jsonrpc": "2.0",
        "method": "constraint.status",
        "params": {
            "constraint_id": "main:constraint_nonexistent"
        },
        "id": 1
    }

    response = call_cli(request)

    assert "error" in response
    error = response["error"]
    assert error["code"] == -32001  # ENTITY_NOT_FOUND (constraints are entities too)
    assert "not found" in error["message"].lower()


def test_constraint_status_for_entity():
    """Test querying all constraints affecting a specific entity."""
    # Create lines and apply constraints
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

    # Apply constraint
    call_cli({
        "jsonrpc": "2.0",
        "method": "constraint.apply",
        "params": {
            "constraint_type": "perpendicular",
            "entity_ids": [line1_id, line2_id]
        },
        "id": 3
    })

    # Query constraints for specific entity
    request = {
        "jsonrpc": "2.0",
        "method": "constraint.status",
        "params": {
            "entity_id": line1_id
        },
        "id": 4
    }

    response = call_cli(request)

    assert response["result"]["status"] == "success"
    data = response["result"]["data"]
    assert "constraints" in data

    # Verify line1 is in at least one constraint
    constraints = data["constraints"]
    assert len(constraints) >= 1
    assert any(line1_id in c.get("constrained_entities", []) for c in constraints)
