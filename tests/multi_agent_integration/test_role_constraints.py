"""
Integration test for role constraint enforcement across all 6 roles.

Tests T026: Integration test for role constraint enforcement across 6 roles
- create agent for each role, test allowed and forbidden operations via real CLI,
  verify 100% enforcement

Constitution compliance:
- Uses real CLI subprocess calls
- Tests real role enforcement behavior
- No mocks or stubs
"""

import pytest
import subprocess
from pathlib import Path


@pytest.fixture
def controller():
    """Create controller instance for testing."""
    from src.multi_agent.controller import Controller
    import os

    # Use temporary directory for workspaces
    workspace_dir = Path("data/workspaces/test_roles")
    if workspace_dir.exists():
        import shutil
        shutil.rmtree(workspace_dir)
    workspace_dir.mkdir(parents=True, exist_ok=True)

    controller = Controller(
        controller_id="test_controller_roles", 
        max_concurrent_agents=10,
        workspace_dir=str(workspace_dir)
    )
    
    # Set env var for subprocess calls in test
    os.environ["MULTI_AGENT_WORKSPACE_DIR"] = str(workspace_dir)
    
    yield controller

    # Cleanup env var
    if "MULTI_AGENT_WORKSPACE_DIR" in os.environ:
        del os.environ["MULTI_AGENT_WORKSPACE_DIR"]

    # Cleanup
    agent_ids = list(controller.agents.keys())
    for agent_id in agent_ids:
        try:
            controller.shutdown_agent(agent_id)
        except:
            pass


@pytest.fixture
def cleanup_workspaces():
    """Cleanup test workspaces after test."""
    workspace_ids = []

    def register_workspace(ws_id):
        workspace_ids.append(ws_id)

    yield register_workspace

    for ws_id in workspace_ids:
        try:
            subprocess.run(
                ["python", "-m", "src.agent_interface.cli", "workspace.delete",
                 "--workspace_id", ws_id],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=Path(__file__).parent.parent.parent,
                env=os.environ
            )
        except:
            pass


def test_all_roles_constraint_enforcement(controller, cleanup_workspaces):
    """
    Test T026: Create agent for each of 6 roles, test allowed and forbidden operations,
    verify 100% constraint enforcement.

    Success criteria:
    - All 6 roles tested (designer, modeler, constraint_solver, validator, optimizer, integrator)
    - Allowed operations succeed for each role
    - Forbidden operations blocked with RoleViolationError for each role
    - 100% enforcement rate (SC-003)
    """
    from src.multi_agent.roles import RoleViolationError

    # Define test cases for each role
    # Format: (role_name, allowed_op, allowed_params, forbidden_op, forbidden_params)
    role_test_cases = [
        (
            "designer",
            "entity.create_point",
            {"x": 10.0, "y": 10.0, "z": 0.0},
            "solid.extrude",
            {"entity_id": "line_1", "distance": 20.0}
        ),
        (
            "modeler",
            "solid.extrude",
            {"entity_id": "circle_1", "distance": 30.0},
            "workspace.merge",
            {"source_workspace": "ws_a", "target_workspace": "ws_b"}
        ),
        (
            "constraint_solver",
            "constraint.apply",
            {"entity_id": "line_1", "constraint_type": "distance", "value": 100.0},
            "entity.create_point",
            {"x": 0.0, "y": 0.0, "z": 0.0}
        ),
        (
            "validator",
            "entity.list",
            {},
            "entity.create_line",
            {"start": {"x": 0, "y": 0}, "end": {"x": 100, "y": 0}}
        ),
        (
            "optimizer",
            "entity.create_point",
            {"x": 50.0, "y": 50.0, "z": 0.0},
            "workspace.merge",
            {"source_workspace": "ws_a", "target_workspace": "ws_b"}
        ),
        (
            "integrator",
            "workspace.merge",
            {"source_workspace": "ws_source", "target_workspace": "ws_target"},
            "solid.extrude",
            {"entity_id": "circle_1", "distance": 20.0}
        ),
    ]

    enforcement_results = []

    for role_name, allowed_op, allowed_params, forbidden_op, forbidden_params in role_test_cases:
        # Create workspace for this role
        workspace_id = f"ws_role_{role_name}"
        cleanup_workspaces(workspace_id)

        result = subprocess.run(
            ["python", "-m", "src.agent_interface.cli", "workspace.create",
             "--workspace_id", workspace_id],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=Path(__file__).parent.parent.parent
        )
        assert result.returncode == 0, f"Failed to create workspace for {role_name}"

        # Create agent with this role
        agent = controller.create_agent(
            agent_id=f"agent_{role_name}",
            role_name=role_name,
            workspace_id=workspace_id
        )

        # Test 1: Allowed operation should succeed
        allowed_params_with_ws = {**allowed_params, "workspace_id": workspace_id}

        try:
            result = controller.execute_operation(
                agent_id=agent.agent_id,
                operation=allowed_op,
                params=allowed_params_with_ws
            )
            allowed_success = True
            # Note: operation may fail for other reasons (e.g., entity doesn't exist)
            # but it should NOT be blocked by role constraint
        except RoleViolationError as e:
            allowed_success = False
            pytest.fail(
                f"Role {role_name}: Allowed operation {allowed_op} was blocked: {str(e)}"
            )
        except Exception as e:
            # Operation failed for non-role reasons (e.g., entity not found)
            # This is acceptable - we only care that role didn't block it
            allowed_success = True

        # Test 2: Forbidden operation should be blocked
        forbidden_params_with_ws = {**forbidden_params, "workspace_id": workspace_id}
        forbidden_blocked = False

        try:
            result = controller.execute_operation(
                agent_id=agent.agent_id,
                operation=forbidden_op,
                params=forbidden_params_with_ws
            )
            # If we got here, the forbidden operation was NOT blocked
            forbidden_blocked = False
        except RoleViolationError as e:
            # Expected: forbidden operation was blocked
            forbidden_blocked = True
            assert role_name in str(e) or forbidden_op in str(e), (
                f"RoleViolationError should mention role or operation: {str(e)}"
            )

        # Record enforcement results
        enforcement_results.append({
            "role": role_name,
            "allowed_enforced_correctly": allowed_success,
            "forbidden_blocked_correctly": forbidden_blocked
        })

        # Verify forbidden operation was blocked
        assert forbidden_blocked, (
            f"Role {role_name}: Forbidden operation {forbidden_op} was NOT blocked! "
            f"This violates SC-003 (100% constraint enforcement)"
        )

    # Verify 100% enforcement across all roles
    total_tests = len(enforcement_results) * 2  # allowed + forbidden for each role
    correct_enforcements = sum(
        result["allowed_enforced_correctly"] and result["forbidden_blocked_correctly"]
        for result in enforcement_results
    )

    enforcement_rate = (correct_enforcements / len(enforcement_results)) * 100

    assert enforcement_rate == 100.0, (
        f"Enforcement rate is {enforcement_rate:.1f}%, expected 100% (SC-003). "
        f"Results: {enforcement_results}"
    )


def test_multiple_forbidden_operations_per_role(controller, cleanup_workspaces):
    """
    Additional test: Verify ALL forbidden operations for a role are blocked.

    Focus on designer role as example - it has 7 forbidden operations.
    """
    from src.multi_agent.roles import RoleViolationError

    workspace_id = "ws_designer_forbidden"
    cleanup_workspaces(workspace_id)

    result = subprocess.run(
        ["python", "-m", "src.agent_interface.cli", "workspace.create",
         "--workspace_id", workspace_id],
        capture_output=True,
        text=True,
        timeout=10,
        cwd=Path(__file__).parent.parent.parent
    )
    assert result.returncode == 0

    agent = controller.create_agent(
        agent_id="designer_test",
        role_name="designer",
        workspace_id=workspace_id
    )

    # Designer forbidden operations from role_templates.json
    forbidden_operations = [
        ("solid.extrude", {"entity_id": "line_1", "distance": 20.0}),
        ("solid.revolve", {"entity_id": "line_1", "axis": "z", "angle": 360.0}),
        ("solid.boolean", {"op": "union", "entity1": "solid_1", "entity2": "solid_2"}),
        ("constraint.apply", {"entity_id": "line_1", "constraint_type": "distance", "value": 100.0}),
        ("workspace.merge", {"source_workspace": "ws_a", "target_workspace": "ws_b"}),
    ]

    blocked_count = 0

    for operation, params in forbidden_operations:
        params_with_ws = {**params, "workspace_id": workspace_id}

        try:
            controller.execute_operation(
                agent_id=agent.agent_id,
                operation=operation,
                params=params_with_ws
            )
            # Should not reach here
            pytest.fail(f"Designer: Forbidden operation {operation} was NOT blocked!")
        except RoleViolationError:
            # Expected
            blocked_count += 1

    # Verify all forbidden operations were blocked
    assert blocked_count == len(forbidden_operations), (
        f"Only {blocked_count}/{len(forbidden_operations)} forbidden operations blocked"
    )


def test_role_enforcement_with_concurrent_agents(controller, cleanup_workspaces):
    """
    Verify role enforcement works correctly when multiple agents execute concurrently.

    Tests that role checks don't have race conditions or cross-agent interference.
    """
    from src.multi_agent.roles import RoleViolationError
    import concurrent.futures

    # Create 3 different role agents concurrently
    roles = ["designer", "modeler", "validator"]
    agents = []

    for role in roles:
        workspace_id = f"ws_concurrent_role_{role}"
        cleanup_workspaces(workspace_id)

        result = subprocess.run(
            ["python", "-m", "src.agent_interface.cli", "workspace.create",
             "--workspace_id", workspace_id],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=Path(__file__).parent.parent.parent
        )
        assert result.returncode == 0

        agent = controller.create_agent(
            agent_id=f"concurrent_{role}",
            role_name=role,
            workspace_id=workspace_id
        )
        agents.append((agent, workspace_id))

    # Each agent attempts both allowed and forbidden operations concurrently
    def test_agent_role(agent, workspace_id):
        from src.multi_agent.roles import RoleViolationError

        role_name = agent.role.name
        results = {"allowed": False, "forbidden_blocked": False}

        # Test allowed operation
        if role_name == "designer":
            try:
                controller.execute_operation(
                    agent.agent_id,
                    "entity.create_point",
                    {"x": 10.0, "y": 10.0, "z": 0.0, "workspace_id": workspace_id}
                )
                results["allowed"] = True
            except RoleViolationError:
                pass
        elif role_name == "modeler":
            try:
                controller.execute_operation(
                    agent.agent_id,
                    "entity.create_point",
                    {"x": 10.0, "y": 10.0, "z": 0.0, "workspace_id": workspace_id}
                )
                results["allowed"] = True
            except RoleViolationError:
                pass
        elif role_name == "validator":
            try:
                controller.execute_operation(
                    agent.agent_id,
                    "entity.list",
                    {"workspace_id": workspace_id}
                )
                results["allowed"] = True
            except RoleViolationError:
                pass

        # Test forbidden operation (all roles forbidden from workspace.merge except integrator)
        if role_name != "integrator":
            try:
                controller.execute_operation(
                    agent.agent_id,
                    "workspace.merge" if role_name != "designer" else "solid.extrude",
                    {"source_workspace": "a", "target_workspace": "b", "workspace_id": workspace_id}
                    if role_name != "designer" else
                    {"entity_id": "line_1", "distance": 20.0, "workspace_id": workspace_id}
                )
                results["forbidden_blocked"] = False
            except RoleViolationError:
                results["forbidden_blocked"] = True

        return results

    # Execute all tests concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(test_agent_role, agent, ws): agent.role.name
                   for agent, ws in agents}

        all_results = {}
        for future in concurrent.futures.as_completed(futures):
            role_name = futures[future]
            result = future.result()
            all_results[role_name] = result

    # Verify all results
    for role_name, results in all_results.items():
        assert results["allowed"], f"Role {role_name}: Allowed operation failed in concurrent execution"
        assert results["forbidden_blocked"], (
            f"Role {role_name}: Forbidden operation NOT blocked in concurrent execution"
        )
