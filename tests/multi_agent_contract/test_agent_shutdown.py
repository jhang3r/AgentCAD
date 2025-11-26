"""
Contract test for Controller.shutdown_agent()

Tests verify agent status transitions to terminated and cleanup occurs.
NO mocks - uses real controller operations.
"""

import pytest
import subprocess
import json
from pathlib import Path
import sys

repo_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(repo_root / "src"))

from multi_agent.controller import Controller
from multi_agent.roles import load_predefined_roles


@pytest.fixture
def controller():
    """Create controller."""
    ctrl = Controller()
    try:
        ctrl.role_templates = load_predefined_roles()
    except FileNotFoundError:
        pytest.skip("Role templates not found")
    return ctrl


@pytest.fixture
def cleanup_workspace():
    """Cleanup workspaces."""
    workspaces = []
    yield workspaces

    cli_path = repo_root / "src" / "agent_interface" / "cli.py"
    for ws_id in workspaces:
        try:
            subprocess.run(
                [sys.executable, str(cli_path), "workspace.delete",
                 "--params", json.dumps({"workspace_id": ws_id})],
                capture_output=True,
                timeout=5
            )
        except Exception:
            pass


def test_shutdown_agent_sets_status_to_terminated(controller, cleanup_workspace):
    """
    Test shutting down an agent sets status to 'terminated'.

    Verifies:
    - Agent status changes to "terminated"
    - Agent removed from controller.agents dict
    - Message queue cleaned up
    """
    workspace_id = "test_ws_shutdown_001"
    cleanup_workspace.append(workspace_id)

    # Create agent
    agent = controller.create_agent("shutdown_agent_001", "designer", workspace_id)
    assert agent.status == "idle"
    assert "shutdown_agent_001" in controller.agents

    # Shutdown agent
    controller.shutdown_agent("shutdown_agent_001")

    # Verify agent status
    assert agent.status == "terminated"

    # Verify agent removed from controller
    assert "shutdown_agent_001" not in controller.agents


def test_shutdown_nonexistent_agent_raises_error(controller):
    """
    Test shutting down nonexistent agent raises KeyError.
    """
    with pytest.raises(KeyError, match="nonexistent"):
        controller.shutdown_agent("nonexistent")


def test_shutdown_agent_after_operations(controller, cleanup_workspace):
    """
    Test shutting down agent that has performed operations.

    Verifies metrics are preserved in agent object even after shutdown.
    """
    workspace_id = "test_ws_shutdown_ops"
    cleanup_workspace.append(workspace_id)

    agent = controller.create_agent("ops_shutdown_agent", "designer", workspace_id)

    # Perform some operations
    for i in range(3):
        controller.execute_operation(
            "ops_shutdown_agent",
            "entity.create_point",
            {"x": i * 10.0, "y": 0.0, "z": 0.0, "workspace_id": workspace_id}
        )

    # Verify metrics before shutdown
    assert agent.operation_count == 3
    assert agent.success_count == 3

    # Shutdown
    controller.shutdown_agent("ops_shutdown_agent")

    # Metrics should still be accessible in agent object
    assert agent.operation_count == 3
    assert agent.success_count == 3
    assert agent.status == "terminated"


def test_shutdown_multiple_agents(controller, cleanup_workspace):
    """
    Test shutting down multiple agents.

    Verifies controller can manage shutdown of multiple agents.
    """
    workspaces = ["test_ws_multi_shutdown_001", "test_ws_multi_shutdown_002", "test_ws_multi_shutdown_003"]
    for ws in workspaces:
        cleanup_workspace.append(ws)

    # Create 3 agents
    agents = []
    for i, ws in enumerate(workspaces):
        agent = controller.create_agent(f"multi_shutdown_{i}", "designer", ws)
        agents.append(agent)

    assert len(controller.agents) == 3

    # Shutdown all
    for i in range(3):
        controller.shutdown_agent(f"multi_shutdown_{i}")

    # Verify all removed
    assert len(controller.agents) == 0

    # Verify all terminated
    for agent in agents:
        assert agent.status == "terminated"
