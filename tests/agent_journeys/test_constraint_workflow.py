"""Agent journey test for constraint solving workflow.

This test simulates an AI agent's journey through applying and
checking geometric constraints, verifying the complete workflow.

Tests follow TDD principles and use real solver (no mocks).
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


def test_constraint_workflow():
    """Test complete agent workflow: create lines → apply constraint → check status.

    Simulates an AI agent learning to work with constraints:
    1. Create two lines
    2. Apply perpendicular constraint
    3. Check constraint status
    4. Verify constraint is satisfied
    """
    # Step 1: Agent creates first line (horizontal)
    line1_request = {
        "jsonrpc": "2.0",
        "method": "entity.create.line",
        "params": {
            "start": [0.0, 0.0],
            "end": [10.0, 0.0]
        },
        "id": 1
    }

    line1_response = call_cli(line1_request)
    assert line1_response["result"]["status"] == "success"
    line1_id = line1_response["result"]["data"]["entity_id"]

    # Step 2: Agent creates second line (vertical)
    line2_request = {
        "jsonrpc": "2.0",
        "method": "entity.create.line",
        "params": {
            "start": [0.0, 0.0],
            "end": [0.0, 10.0]
        },
        "id": 2
    }

    line2_response = call_cli(line2_request)
    assert line2_response["result"]["status"] == "success"
    line2_id = line2_response["result"]["data"]["entity_id"]

    # Step 3: Agent applies perpendicular constraint
    constraint_request = {
        "jsonrpc": "2.0",
        "method": "constraint.apply",
        "params": {
            "constraint_type": "perpendicular",
            "entity_ids": [line1_id, line2_id]
        },
        "id": 3
    }

    constraint_response = call_cli(constraint_request)
    assert constraint_response["result"]["status"] == "success"

    constraint_data = constraint_response["result"]["data"]
    constraint_id = constraint_data["constraint_id"]
    assert constraint_data["constraint_type"] == "perpendicular"
    assert constraint_data["satisfaction_status"] == "satisfied"  # Lines are already perpendicular

    # Step 4: Agent checks constraint status
    status_request = {
        "jsonrpc": "2.0",
        "method": "constraint.status",
        "params": {
            "constraint_id": constraint_id
        },
        "id": 4
    }

    status_response = call_cli(status_request)
    assert status_response["result"]["status"] == "success"

    status_data = status_response["result"]["data"]
    assert status_data["constraint_id"] == constraint_id
    assert status_data["satisfaction_status"] == "satisfied"


def test_agent_learns_from_constraint_conflict():
    """Test agent receives helpful error feedback for constraint conflicts.

    Simulates an agent making mistakes with conflicting constraints:
    1. Apply parallel constraint
    2. Try to apply conflicting perpendicular constraint
    3. Receive structured error
    """
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
        "params": {"start": [0.0, 5.0], "end": [10.0, 5.0]},
        "id": 2
    })
    line2_id = line2_response["result"]["data"]["entity_id"]

    # Apply parallel constraint
    parallel_response = call_cli({
        "jsonrpc": "2.0",
        "method": "constraint.apply",
        "params": {
            "constraint_type": "parallel",
            "entity_ids": [line1_id, line2_id]
        },
        "id": 3
    })
    assert parallel_response["result"]["status"] == "success"

    # Try to apply conflicting perpendicular constraint
    perp_request = {
        "jsonrpc": "2.0",
        "method": "constraint.apply",
        "params": {
            "constraint_type": "perpendicular",
            "entity_ids": [line1_id, line2_id]
        },
        "id": 4
    }

    perp_response = call_cli(perp_request)

    # Should receive error
    assert "error" in perp_response
    error = perp_response["error"]
    assert error["code"] == -32002  # CONSTRAINT_CONFLICT
    assert "conflict" in error["message"].lower()


def test_agent_queries_constraints_for_entity():
    """Test agent can query all constraints affecting an entity."""
    # Create entities and apply constraints
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

    # Query constraints for line1
    query_request = {
        "jsonrpc": "2.0",
        "method": "constraint.status",
        "params": {
            "entity_id": line1_id
        },
        "id": 4
    }

    query_response = call_cli(query_request)
    assert query_response["result"]["status"] == "success"

    data = query_response["result"]["data"]
    assert "constraints" in data
    assert len(data["constraints"]) >= 1

    # Verify line1 is in the constraint
    constraints = data["constraints"]
    assert any(line1_id in c["constrained_entities"] for c in constraints)
