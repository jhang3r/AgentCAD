"""
Contract test for Controller.create_agent()

Tests verify agent creation with correct role and workspace via real CLI
workspace.create subprocess call. NO mocks - uses actual CLI invocation.
"""

import pytest
import subprocess
import json
from pathlib import Path
import sys

# Add src to path for imports
repo_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(repo_root / "src"))

from multi_agent.controller import Controller
from multi_agent.roles import load_predefined_roles


@pytest.fixture
def controller():
    """Create a controller instance with predefined roles loaded."""
    ctrl = Controller(controller_id="test_controller", max_concurrent_agents=5)

    # Load predefined roles
    try:
        ctrl.role_templates = load_predefined_roles()
    except FileNotFoundError:
        pytest.skip("Role templates file not found - run from repository root")

    return ctrl


@pytest.fixture
def cleanup_workspace():
    """Cleanup test workspaces after test."""
    workspaces_to_clean = []

    yield workspaces_to_clean

    # Cleanup: delete test workspaces via CLI
    cli_path = repo_root / "src" / "agent_interface" / "cli.py"
    for workspace_id in workspaces_to_clean:
        try:
            subprocess.run(
                [sys.executable, str(cli_path), "workspace.delete", "--params",
                 json.dumps({"workspace_id": workspace_id})],
                capture_output=True,
                timeout=5
            )
        except Exception:
            pass  # Ignore cleanup errors


def test_create_agent_with_designer_role(controller, cleanup_workspace):
    """
    Test creating an agent with designer role.

    Verifies:
    - Agent created with correct agent_id
    - Agent assigned correct role (designer)
    - Workspace created via real CLI workspace.create subprocess call
    - Agent added to controller.agents dict
    - Agent status is "idle"
    - Agent metrics initialized to zero
    """
    workspace_id = "test_ws_designer_001"
    cleanup_workspace.append(workspace_id)

    # Create agent with designer role
    agent = controller.create_agent(
        agent_id="designer_001",
        role_name="designer",
        workspace_id=workspace_id
    )

    # Verify agent properties
    assert agent.agent_id == "designer_001"
    assert agent.role.name == "designer"
    assert agent.workspace_id == workspace_id
    assert agent.status == "idle"
    assert agent.operation_count == 0
    assert agent.success_count == 0
    assert agent.error_count == 0
    assert len(agent.created_entities) == 0

    # Verify agent added to controller
    assert "designer_001" in controller.agents
    assert controller.agents["designer_001"] is agent

    # Verify workspace exists via CLI query
    result = subprocess.run(
        [sys.executable, "-m", "src.agent_interface.cli", "workspace.list"],
        capture_output=True,
        text=True,
        timeout=5,
        cwd=repo_root
    )
    assert result.returncode == 0

    # Parse JSON-RPC response
    response = json.loads(result.stdout)
    workspace_list = response.get("result", {}).get("data", {}).get("workspaces", [])
    workspace_ids = [ws.get("workspace_id") for ws in workspace_list]
    # Check if workspace exists (either exact match or with agent prefix)
    workspace_found = (workspace_id in workspace_ids or
                      any(ws_id.endswith(workspace_id) for ws_id in workspace_ids))
    assert workspace_found, f"Workspace {workspace_id} not found in {workspace_ids}"


def test_create_agent_with_modeler_role(controller, cleanup_workspace):
    """
    Test creating an agent with modeler role.

    Verifies modeler role assignment and different workspace.
    """
    workspace_id = "test_ws_modeler_001"
    cleanup_workspace.append(workspace_id)

    agent = controller.create_agent(
        agent_id="modeler_001",
        role_name="modeler",
        workspace_id=workspace_id
    )

    assert agent.agent_id == "modeler_001"
    assert agent.role.name == "modeler"
    assert agent.workspace_id == workspace_id
    assert "entity.create_point" in agent.role.allowed_operations
    assert "solid.extrude" in agent.role.allowed_operations


def test_create_agent_duplicate_id_raises_error(controller, cleanup_workspace):
    """
    Test that creating an agent with duplicate ID raises ValueError.
    """
    workspace_id = "test_ws_dup_001"
    cleanup_workspace.append(workspace_id)

    # Create first agent
    controller.create_agent(
        agent_id="duplicate_id",
        role_name="designer",
        workspace_id=workspace_id
    )

    # Attempt to create second agent with same ID
    with pytest.raises(ValueError, match="already exists"):
        controller.create_agent(
            agent_id="duplicate_id",
            role_name="modeler",
            workspace_id="test_ws_dup_002"
        )


def test_create_agent_invalid_role_raises_error(controller):
    """
    Test that creating an agent with invalid role raises ValueError.
    """
    with pytest.raises(ValueError, match="Invalid role"):
        controller.create_agent(
            agent_id="invalid_role_agent",
            role_name="nonexistent_role",
            workspace_id="test_ws_invalid"
        )


def test_create_multiple_agents(controller, cleanup_workspace):
    """
    Test creating multiple agents with different roles and workspaces.

    Verifies controller can manage multiple agents simultaneously.
    """
    agents_data = [
        ("designer_multi_001", "designer", "test_ws_multi_001"),
        ("modeler_multi_001", "modeler", "test_ws_multi_002"),
        ("validator_multi_001", "validator", "test_ws_multi_003"),
    ]

    for workspace_id in [data[2] for data in agents_data]:
        cleanup_workspace.append(workspace_id)

    # Create all agents
    for agent_id, role_name, workspace_id in agents_data:
        agent = controller.create_agent(agent_id, role_name, workspace_id)
        assert agent.agent_id == agent_id
        assert agent.role.name == role_name

    # Verify all agents in controller
    assert len(controller.agents) == 3
    for agent_id, _, _ in agents_data:
        assert agent_id in controller.agents
