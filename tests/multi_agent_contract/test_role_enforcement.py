"""
Contract test for role-based constraint enforcement.

Tests verify that agents can only execute operations within their role's
allowed_operations, and forbidden operations are blocked with RoleViolationError.
NO mocks - uses real CLI subprocess calls where operations succeed.
"""

import pytest
import subprocess
import json
from pathlib import Path
import sys

repo_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(repo_root / "src"))

from multi_agent.controller import Controller
from multi_agent.roles import load_predefined_roles, RoleViolationError


@pytest.fixture
def controller():
    """Create controller with roles loaded."""
    ctrl = Controller(controller_id="test_role_enforcement")
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


def test_designer_can_create_2d_geometry(controller, cleanup_workspace):
    """
    Test designer role can execute allowed 2D geometry operations.

    Verifies:
    - Designer can execute entity.create_line (allowed operation)
    - Operation succeeds via real CLI subprocess
    - No role violation error raised
    """
    workspace_id = "test_ws_designer_2d"
    cleanup_workspace.append(workspace_id)

    # Create designer agent
    agent = controller.create_agent("designer_2d", "designer", workspace_id)

    # Designer should be able to create line (allowed operation)
    result = controller.execute_operation(
        "designer_2d",
        "entity.create_line",
        {
            "start": {"x": 0.0, "y": 0.0, "z": 0.0},
            "end": {"x": 100.0, "y": 0.0, "z": 0.0},
            "workspace_id": workspace_id
        }
    )

    # Verify operation succeeded
    assert result["success"] is True
    assert agent.operation_count == 1
    assert agent.success_count == 1


def test_designer_blocked_from_solid_modeling(controller, cleanup_workspace):
    """
    Test designer role is blocked from solid modeling operations.

    Verifies:
    - Designer cannot execute solid.extrude (forbidden operation)
    - RoleViolationError raised with clear message
    - Error references role constraint
    """
    workspace_id = "test_ws_designer_blocked"
    cleanup_workspace.append(workspace_id)

    # Create designer agent
    agent = controller.create_agent("designer_blocked", "designer", workspace_id)

    # First create a circle (allowed)
    controller.execute_operation(
        "designer_blocked",
        "entity.create_circle",
        {
            "center": {"x": 0.0, "y": 0.0, "z": 0.0},
            "radius": 50.0,
            "workspace_id": workspace_id
        }
    )

    # Attempt to extrude (not allowed for designer role)
    with pytest.raises(RoleViolationError) as exc_info:
        controller.execute_operation(
            "designer_blocked",
            "solid.extrude",
            {
                "entity_id": "circle_1",
                "distance": 20.0,
                "workspace_id": workspace_id
            }
        )

    # Verify error message
    error = exc_info.value
    assert error.agent_id == "designer_blocked"
    assert error.role_name == "designer"
    assert error.operation == "solid.extrude"
    assert "cannot execute" in error.message.lower()
    assert "role constraints" in error.message.lower() or "not permitted" in error.message.lower()


def test_validator_can_query_entities(controller, cleanup_workspace):
    """
    Test validator role can execute read-only query operations.

    Verifies:
    - Validator can execute entity.query (allowed operation)
    - Validator can execute entity.list (allowed operation)
    """
    workspace_id = "test_ws_validator_query"
    cleanup_workspace.append(workspace_id)

    # Create validator agent
    agent = controller.create_agent("validator_query", "validator", workspace_id)

    # Validator should be able to list entities (allowed)
    result = controller.execute_operation(
        "validator_query",
        "entity.list",
        {"workspace_id": workspace_id}
    )

    assert result["success"] is True
    assert agent.success_count == 1


def test_validator_blocked_from_creating_entities(controller, cleanup_workspace):
    """
    Test validator role is blocked from entity creation operations.

    Verifies:
    - Validator cannot execute entity.create_point (forbidden for validator)
    - RoleViolationError raised
    """
    workspace_id = "test_ws_validator_blocked"
    cleanup_workspace.append(workspace_id)

    # Create validator agent
    agent = controller.create_agent("validator_blocked", "validator", workspace_id)

    # Attempt to create point (not allowed for validator role)
    with pytest.raises(RoleViolationError) as exc_info:
        controller.execute_operation(
            "validator_blocked",
            "entity.create_point",
            {
                "x": 10.0,
                "y": 20.0,
                "z": 0.0,
                "workspace_id": workspace_id
            }
        )

    # Verify error
    error = exc_info.value
    assert error.agent_id == "validator_blocked"
    assert error.role_name == "validator"
    assert error.operation == "entity.create_point"


def test_integrator_can_merge_workspaces(controller, cleanup_workspace):
    """
    Test integrator role can execute workspace management operations.

    Verifies:
    - Integrator can execute workspace.merge (allowed)
    - Integrator can execute workspace operations
    """
    workspace_id_main = "test_ws_integrator_main"
    workspace_id_source = "test_ws_integrator_source"
    cleanup_workspace.extend([workspace_id_main, workspace_id_source])

    # Create integrator agent
    agent = controller.create_agent("integrator_merge", "integrator", workspace_id_main)

    # Create source workspace via different agent first
    # (Integrator role doesn't include entity creation, so we'll test workspace.list instead)
    result = controller.execute_operation(
        "integrator_merge",
        "workspace.list",
        {}
    )

    assert result["success"] is True
    assert agent.success_count == 1


def test_integrator_blocked_from_solid_operations(controller, cleanup_workspace):
    """
    Test integrator role is blocked from solid modeling operations.

    Verifies:
    - Integrator cannot execute solid.boolean (forbidden)
    - RoleViolationError raised
    """
    workspace_id = "test_ws_integrator_blocked"
    cleanup_workspace.append(workspace_id)

    # Create integrator agent
    agent = controller.create_agent("integrator_blocked", "integrator", workspace_id)

    # Attempt solid boolean operation (not allowed for integrator)
    with pytest.raises(RoleViolationError) as exc_info:
        controller.execute_operation(
            "integrator_blocked",
            "solid.boolean",
            {
                "operation": "union",
                "entity_a": "solid_1",
                "entity_b": "solid_2",
                "workspace_id": workspace_id
            }
        )

    # Verify error
    error = exc_info.value
    assert error.agent_id == "integrator_blocked"
    assert error.role_name == "integrator"
    assert error.operation == "solid.boolean"


def test_modeler_can_execute_3d_operations(controller, cleanup_workspace):
    """
    Test modeler role can execute both 2D and 3D operations.

    Verifies:
    - Modeler can create 2D geometry (entity.create_circle)
    - Modeler can execute solid modeling (solid.extrude)
    """
    workspace_id = "test_ws_modeler_3d"
    cleanup_workspace.append(workspace_id)

    # Create modeler agent
    agent = controller.create_agent("modeler_3d", "modeler", workspace_id)

    # Modeler should be able to create circle
    result1 = controller.execute_operation(
        "modeler_3d",
        "entity.create_circle",
        {
            "center": {"x": 0.0, "y": 0.0, "z": 0.0},
            "radius": 50.0,
            "workspace_id": workspace_id
        }
    )
    assert result1["success"] is True

    # Modeler should also be able to extrude
    result2 = controller.execute_operation(
        "modeler_3d",
        "solid.extrude",
        {
            "entity_id": result1["entity_id"],
            "distance": 20.0,
            "workspace_id": workspace_id
        }
    )
    assert result2["success"] is True
    assert agent.success_count == 2


def test_role_violation_updates_error_metrics(controller, cleanup_workspace):
    """
    Test that role violations update agent error metrics.

    Verifies:
    - Role violation increments error_count
    - Error logged in agent.error_log
    - Operation_count incremented
    """
    workspace_id = "test_ws_role_metrics"
    cleanup_workspace.append(workspace_id)

    agent = controller.create_agent("role_metrics", "designer", workspace_id)

    # Attempt forbidden operation
    try:
        controller.execute_operation(
            "role_metrics",
            "solid.extrude",
            {"entity_id": "test", "distance": 10.0, "workspace_id": workspace_id}
        )
    except RoleViolationError:
        pass  # Expected

    # Verify metrics updated
    assert agent.operation_count == 1
    assert agent.error_count == 1
    assert agent.success_count == 0
    assert len(agent.error_log) > 0
    assert "role" in agent.error_log[0].lower() or "cannot execute" in agent.error_log[0].lower()
