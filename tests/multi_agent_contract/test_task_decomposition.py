"""
Contract tests for task decomposition functionality.

Tests T031-T033: Contract tests for decompose_task(), assign_task(), and task dependencies

Constitution compliance:
- Tests real controller API
- No mocks or stubs
"""

import pytest


@pytest.fixture
def controller():
    """Create controller instance for testing."""
    from src.multi_agent.controller import Controller

    controller = Controller(controller_id="test_controller_task_decomp", max_concurrent_agents=10)
    yield controller

    agent_ids = list(controller.agents.keys())
    for agent_id in agent_ids:
        try:
            controller.shutdown_agent(agent_id)
        except:
            pass


def test_decompose_task_returns_task_assignments(controller):
    """
    Test T031: Contract test for decompose_task().

    Pass "create box assembly with lid", verify returns TaskAssignment list
    with create_base, create_lid, integrate tasks.

    Success criteria:
    - Returns List[TaskAssignment]
    - Contains expected tasks for box assembly pattern
    - Each task has required_operations matching pattern
    """
    from src.multi_agent.task_decomposer import TaskAssignment

    goal_description = "create box assembly with lid"
    context = {
        "box_dimensions": {"length": 100, "width": 80, "height": 50},
        "lid_height": 10
    }

    # Decompose goal into tasks
    tasks = controller.decompose_task(goal_description, context)

    # Verify return type
    assert isinstance(tasks, list), "decompose_task should return a list"
    assert len(tasks) > 0, "decompose_task should return at least one task"

    # Verify all items are TaskAssignment instances
    for task in tasks:
        assert isinstance(task, TaskAssignment), f"Expected TaskAssignment, got {type(task)}"

    # Verify box assembly pattern tasks are present
    task_descriptions = [task.description.lower() for task in tasks]

    # Should have tasks for creating base, creating lid, and integrating
    has_base_task = any("base" in desc or "box" in desc for desc in task_descriptions)
    has_lid_task = any("lid" in desc for desc in task_descriptions)
    has_integrate_task = any("merge" in desc or "integrate" in desc for desc in task_descriptions)

    assert has_base_task, f"Should have base/box task, found descriptions: {task_descriptions}"
    assert has_lid_task, f"Should have lid task, found descriptions: {task_descriptions}"
    assert has_integrate_task, f"Should have integrate/merge task, found descriptions: {task_descriptions}"

    # Verify each task has required_operations
    for task in tasks:
        assert hasattr(task, "required_operations"), "Task should have required_operations"
        assert isinstance(task.required_operations, list), "required_operations should be a list"
        assert len(task.required_operations) > 0, f"Task {task.task_id} has no required_operations"


def test_decompose_task_assigns_correct_operations(controller):
    """
    Verify that decomposed tasks have appropriate operation requirements.

    Box assembly should include:
    - 2D geometry operations (for designer)
    - 3D solid operations (for modeler)
    - Workspace merge operations (for integrator)
    """
    goal_description = "create box assembly with lid"
    context = {"box_dimensions": {"length": 100, "width": 80, "height": 50}}

    tasks = controller.decompose_task(goal_description, context)

    # Collect all required operations across tasks
    all_operations = []
    for task in tasks:
        all_operations.extend(task.required_operations)

    # Verify appropriate operation types are present
    # Should have entity creation for geometry
    has_entity_ops = any("entity.create" in op for op in all_operations)
    assert has_entity_ops, "Should have entity creation operations"

    # Should have solid modeling or workspace operations
    has_solid_or_workspace_ops = any(
        "solid." in op or "workspace." in op for op in all_operations
    )
    assert has_solid_or_workspace_ops, "Should have solid or workspace operations"


def test_assign_task_validates_role_match(controller):
    """
    Test T032: Contract test for assign_task().

    Assign task to agent, verify agent role matches task.required_operations.

    Success criteria:
    - assign_task succeeds when agent role allows required operations
    - Task assignment recorded correctly
    - Agent ID set on task
    """
    from src.multi_agent.task_decomposer import TaskAssignment
    import subprocess
    from pathlib import Path

    # Create workspace for test agent
    workspace_id = "ws_assign_test"

    result = subprocess.run(
        ["python", "-m", "src.agent_interface.cli", "workspace.create",
         "--workspace_id", workspace_id],
        capture_output=True,
        text=True,
        timeout=10,
        cwd=Path(__file__).parent.parent.parent
    )
    assert result.returncode == 0

    try:
        # Create a modeler agent
        agent = controller.create_agent(
            agent_id="modeler_assign_test",
            role_name="modeler",
            workspace_id=workspace_id
        )

        # Create a task that requires modeler operations
        task = TaskAssignment(
            task_id="task_test_001",
            agent_id=None,  # Not assigned yet
            description="Extrude circle into cylinder",
            required_operations=["entity.create_circle", "solid.extrude"],
            dependencies=[],
            success_criteria="Cylinder entity exists",
            status="pending",
            assigned_at=None,
            completed_at=None,
            result=None
        )

        # Assign task to agent (pass task object since it's not in a workflow)
        controller.assign_task(task.task_id, agent.agent_id, task=task)

        # Verify task assignment succeeded
        assert task.agent_id == agent.agent_id, "Task should be assigned to agent"
        assert task.status == "pending", "Task status should be pending after assignment"
        assert task.assigned_at is not None, "Task should have assigned_at timestamp"

    finally:
        # Cleanup workspace
        subprocess.run(
            ["python", "-m", "src.agent_interface.cli", "workspace.delete",
             "--workspace_id", workspace_id],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=Path(__file__).parent.parent.parent
        )


def test_task_dependencies_execution_order(controller):
    """
    Test T033: Contract test for task dependencies.

    Verify tasks execute in correct order respecting dependencies.

    Success criteria:
    - Tasks with dependencies wait for prerequisite tasks
    - Dependency resolution respects task.dependencies list
    - Execution order follows dependency graph
    """
    from src.multi_agent.task_decomposer import TaskAssignment

    # Create tasks with dependencies
    tasks = [
        TaskAssignment(
            task_id="task_a",
            agent_id=None,
            description="Create base component",
            required_operations=["entity.create_point"],
            dependencies=[],  # No dependencies
            success_criteria="Base created",
            status="pending",
            assigned_at=None,
            completed_at=None,
            result=None
        ),
        TaskAssignment(
            task_id="task_b",
            agent_id=None,
            description="Create lid component",
            required_operations=["entity.create_point"],
            dependencies=[],  # No dependencies
            success_criteria="Lid created",
            status="pending",
            assigned_at=None,
            completed_at=None,
            result=None
        ),
        TaskAssignment(
            task_id="task_c",
            agent_id=None,
            description="Merge base and lid",
            required_operations=["workspace.merge"],
            dependencies=["task_a", "task_b"],  # Depends on both A and B
            success_criteria="Components merged",
            status="pending",
            assigned_at=None,
            completed_at=None,
            result=None
        ),
    ]

    # Test dependency resolution
    from src.multi_agent.task_decomposer import resolve_dependencies

    execution_order = resolve_dependencies(tasks)
    
    # Flatten phases into a single list
    flat_order = []
    for phase in execution_order:
        flat_order.extend(phase)
    execution_order = flat_order

    # Verify execution order
    assert len(execution_order) == len(tasks), "All tasks should be in execution order"

    # Find positions of tasks in execution order
    task_positions = {task.task_id: idx for idx, task in enumerate(execution_order)}

    # Verify task_c comes after both task_a and task_b
    assert task_positions["task_c"] > task_positions["task_a"], (
        "Task C should execute after Task A (dependency)"
    )
    assert task_positions["task_c"] > task_positions["task_b"], (
        "Task C should execute after Task B (dependency)"
    )

    # task_a and task_b can be in any order relative to each other (no dependency)


def test_decompose_complex_pattern(controller):
    """
    Additional test: Decompose different patterns to verify decomposer handles variety.

    Tests bracket creation pattern.
    """
    goal_description = "create mounting bracket with holes"
    context = {
        "bracket_dimensions": {"length": 150, "width": 50, "thickness": 5},
        "hole_diameter": 8,
        "hole_count": 4
    }

    tasks = controller.decompose_task(goal_description, context)

    # Verify tasks returned
    assert len(tasks) > 0, "Bracket pattern should decompose into tasks"

    # Verify tasks have different operation requirements
    operation_types = set()
    for task in tasks:
        for op in task.required_operations:
            operation_types.add(op.split(".")[0])  # Get operation category (entity, solid, etc.)

    # Bracket should require multiple operation categories
    assert len(operation_types) >= 2, (
        f"Bracket should require multiple operation types, found: {operation_types}"
    )
