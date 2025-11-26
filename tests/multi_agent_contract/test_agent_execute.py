"""
Contract test for Controller.execute_operation()

Tests verify operation execution via real CLI subprocess and agent metrics updates.
NO mocks - uses actual JSON-RPC CLI invocations.
"""

import pytest
import subprocess
import json
from pathlib import Path
import sys

# Add src to path
repo_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(repo_root / "src"))

from multi_agent.controller import Controller
from multi_agent.roles import load_predefined_roles


@pytest.fixture
def controller():
    """Create controller with roles loaded."""
    ctrl = Controller(controller_id="test_controller_exec")
    try:
        ctrl.role_templates = load_predefined_roles()
    except FileNotFoundError:
        pytest.skip("Role templates not found")
    return ctrl


@pytest.fixture
def cleanup_workspace():
    """Cleanup test workspaces."""
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


def test_execute_operation_creates_entity(controller, cleanup_workspace):
    """
    Test executing entity.create_point operation via agent.

    Verifies:
    - Operation executes via real CLI subprocess
    - Agent metrics updated (operation_count, success_count)
    - Created entity tracked in agent.created_entities
    - Agent last_active timestamp updated
    - Operation result returned correctly
    """
    workspace_id = "test_ws_exec_001"
    cleanup_workspace.append(workspace_id)

    # Create agent
    agent = controller.create_agent("exec_agent_001", "designer", workspace_id)

    # Execute operation - create point
    result = controller.execute_operation(
        agent_id="exec_agent_001",
        operation="entity.create_point",
        params={"x": 10.0, "y": 20.0, "z": 0.0, "workspace_id": workspace_id}
    )

    # Verify operation result
    assert result["success"] is True
    assert "entity_id" in result

    # Verify agent metrics updated
    agent = controller.agents["exec_agent_001"]
    assert agent.operation_count == 1
    assert agent.success_count == 1
    assert agent.error_count == 0
    assert len(agent.created_entities) == 1
    assert result["entity_id"] in agent.created_entities

    # Verify last_active updated
    import time
    assert agent.last_active > time.time() - 5  # Within last 5 seconds


def test_execute_multiple_operations_updates_metrics(controller, cleanup_workspace):
    """
    Test executing multiple operations updates metrics correctly.

    Verifies cumulative metrics tracking across multiple operations.
    """
    workspace_id = "test_ws_exec_multi"
    cleanup_workspace.append(workspace_id)

    agent = controller.create_agent("multi_exec_agent", "designer", workspace_id)

    # Execute 3 operations
    for i in range(3):
        result = controller.execute_operation(
            "multi_exec_agent",
            "entity.create_point",
            {"x": i * 10.0, "y": i * 10.0, "z": 0.0, "workspace_id": workspace_id}
        )
        assert result["success"] is True

    # Verify metrics
    agent = controller.agents["multi_exec_agent"]
    assert agent.operation_count == 3
    assert agent.success_count == 3
    assert agent.error_count == 0
    assert len(agent.created_entities) == 3


def test_execute_operation_on_nonexistent_agent_raises_error(controller):
    """
    Test executing operation on nonexistent agent raises KeyError.
    """
    with pytest.raises(KeyError, match="nonexistent_agent"):
        controller.execute_operation(
            "nonexistent_agent",
            "entity.create_point",
            {"x": 0.0, "y": 0.0, "z": 0.0}
        )


def test_execute_operation_failed_operation_updates_error_count(controller, cleanup_workspace):
    """
    Test that failed operations update error_count and error_log.

    Executes an operation that will fail (invalid parameters) and verifies
    error tracking.
    """
    workspace_id = "test_ws_exec_fail"
    cleanup_workspace.append(workspace_id)

    agent = controller.create_agent("fail_agent", "designer", workspace_id)

    # Execute operation with invalid params (should fail)
    try:
        controller.execute_operation(
            "fail_agent",
            "entity.create_point",
            {"invalid_param": "value"}  # Missing required x, y, z
        )
    except Exception:
        pass  # Expected to fail

    # Verify error metrics updated
    agent = controller.agents["fail_agent"]
    assert agent.operation_count == 1
    assert agent.error_count == 1
    assert agent.success_count == 0
    assert len(agent.error_log) > 0


def test_execute_operation_with_modeler_role(controller, cleanup_workspace):
    """
    Test executing solid modeling operation with modeler role.

    Verifies modeler can execute extrude operations.
    """
    workspace_id = "test_ws_modeler_exec"
    cleanup_workspace.append(workspace_id)

    agent = controller.create_agent("modeler_exec", "modeler", workspace_id)

    # First create a circle to extrude
    result1 = controller.execute_operation(
        "modeler_exec",
        "entity.create_circle",
        {
            "center": {"x": 0.0, "y": 0.0, "z": 0.0},
            "radius": 50.0,
            "workspace_id": workspace_id
        }
    )
    assert result1["success"] is True

    # Then extrude it
    result2 = controller.execute_operation(
        "modeler_exec",
        "solid.extrude",
        {
            "entity_id": result1["entity_id"],
            "distance": 20.0,
            "workspace_id": workspace_id
        }
    )
    assert result2["success"] is True

    # Verify metrics
    agent = controller.agents["modeler_exec"]
    assert agent.operation_count == 2
    assert agent.success_count == 2
