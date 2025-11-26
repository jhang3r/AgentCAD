"""Contract test for workspace.create JSON-RPC interface.

Tests verify the JSON-RPC contract for creating workspaces,
ensuring proper isolation for multi-agent collaboration.

TDD: These tests should FAIL until implementation is complete.
"""
import json
import subprocess
import sys
import uuid
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


def test_workspace_create_success():
    """Test creating a new workspace."""
    workspace_name = f"agent_test_workspace_{uuid.uuid4().hex[:8]}"
    request = {
        "jsonrpc": "2.0",
        "method": "workspace.create",
        "params": {
            "workspace_name": workspace_name,
            "base_workspace_id": "main"
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

    # Verify workspace data
    data = result["data"]
    assert "workspace_id" in data
    assert data["workspace_name"] == workspace_name
    assert data["workspace_type"] == "agent_branch"
    assert data["base_workspace_id"] == "main"
    assert data["branch_status"] == "clean"
    assert data["entity_count"] == 0
    assert data["operation_count"] == 0
    assert "created_at" in data


def test_workspace_create_missing_params():
    """Test creating workspace with missing parameters."""
    request = {
        "jsonrpc": "2.0",
        "method": "workspace.create",
        "params": {
            # Missing workspace_name
            "base_workspace_id": "main"
        },
        "id": 1
    }

    response = call_cli(request)

    assert "error" in response
    error = response["error"]
    assert error["code"] == -32602  # INVALID_PARAMETER
    assert "workspace_name" in error["message"].lower()


def test_workspace_create_invalid_base():
    """Test creating workspace with non-existent base workspace."""
    request = {
        "jsonrpc": "2.0",
        "method": "workspace.create",
        "params": {
            "workspace_name": "test_ws",
            "base_workspace_id": "nonexistent_workspace"
        },
        "id": 1
    }

    response = call_cli(request)

    assert "error" in response
    error = response["error"]
    assert error["code"] in [-32001, -32602]  # ENTITY_NOT_FOUND or INVALID_PARAMETER


def test_workspace_list_success():
    """Test listing all workspaces."""
    # First create a workspace
    create_response = call_cli({
        "jsonrpc": "2.0",
        "method": "workspace.create",
        "params": {
            "workspace_name": "list_test_ws",
            "base_workspace_id": "main"
        },
        "id": 1
    })

    # Then list workspaces
    request = {
        "jsonrpc": "2.0",
        "method": "workspace.list",
        "params": {},
        "id": 2
    }

    response = call_cli(request)

    assert response["result"]["status"] == "success"
    data = response["result"]["data"]
    assert "workspaces" in data
    assert isinstance(data["workspaces"], list)
    # Should have at least main and the one we just created
    assert len(data["workspaces"]) >= 2

    # Verify workspace structure
    main_ws = next((ws for ws in data["workspaces"] if ws["workspace_id"] == "main"), None)
    assert main_ws is not None
    assert main_ws["workspace_type"] == "main"


def test_workspace_switch_success():
    """Test switching active workspace."""
    workspace_name = f"switch_test_ws_{uuid.uuid4().hex[:8]}"
    # Create a workspace
    create_response = call_cli({
        "jsonrpc": "2.0",
        "method": "workspace.create",
        "params": {
            "workspace_name": workspace_name,
            "base_workspace_id": "main"
        },
        "id": 1
    })

    workspace_id = create_response["result"]["data"]["workspace_id"]

    # Switch to the new workspace
    request = {
        "jsonrpc": "2.0",
        "method": "workspace.switch",
        "params": {
            "workspace_id": workspace_id
        },
        "id": 2
    }

    response = call_cli(request)

    assert response["result"]["status"] == "success"
    data = response["result"]["data"]
    assert data["workspace_id"] == workspace_id
    assert data["workspace_name"] == workspace_name


def test_workspace_status_success():
    """Test querying workspace status."""
    request = {
        "jsonrpc": "2.0",
        "method": "workspace.status",
        "params": {
            "workspace_id": "main"
        },
        "id": 1
    }

    response = call_cli(request)

    assert response["result"]["status"] == "success"
    data = response["result"]["data"]
    assert data["workspace_id"] == "main"
    assert "entity_count" in data
    assert "operation_count" in data
    assert "branch_status" in data
    assert "can_merge" in data
