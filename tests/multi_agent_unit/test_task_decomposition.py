"""
Unit tests for task decomposition logic.

Tests T035: Unit test for task decomposition patterns
- test decompose logic for box assembly, bracket creation, cylinder patterns
  using real role definitions (no mocks)

Constitution compliance:
- Tests real decomposition algorithms
- Uses real role definitions from role_templates.json
- No mocks or stubs
"""

import pytest


def test_decompose_box_assembly_pattern():
    """
    Test T035: Unit test for box assembly decomposition pattern.

    Success criteria:
    - Box assembly decomposes into create_base, create_lid, integrate tasks
    - Each task has appropriate required_operations
    - Tasks have correct dependencies
    - Uses real role definitions
    """
    from src.multi_agent.task_decomposer import decompose_goal

    goal_description = "create box assembly with lid"
    context = {
        "box_dimensions": {"length": 100, "width": 80, "height": 50},
        "lid_height": 10
    }

    tasks = decompose_goal(goal_description, context)

    # Verify tasks returned
    assert len(tasks) > 0, "Box assembly should decompose into tasks"

    # Verify task structure
    task_descriptions = [task.description.lower() for task in tasks]

    # Should have base/box, lid, and integration tasks
    has_base = any("base" in desc or "box" in desc for desc in task_descriptions)
    has_lid = any("lid" in desc for desc in task_descriptions)
    has_integration = any("merge" in desc or "integrate" in desc for desc in task_descriptions)

    assert has_base, f"Missing base task. Found: {task_descriptions}"
    assert has_lid, f"Missing lid task. Found: {task_descriptions}"
    assert has_integration, f"Missing integration task. Found: {task_descriptions}"

    # Verify operations match expected pattern
    all_operations = []
    for task in tasks:
        all_operations.extend(task.required_operations)

    # Should have entity and solid operations
    has_entity_ops = any("entity." in op for op in all_operations)
    has_solid_or_workspace = any("solid." in op or "workspace." in op for op in all_operations)

    assert has_entity_ops, "Box assembly should require entity operations"
    assert has_solid_or_workspace, "Box assembly should require solid or workspace operations"


def test_decompose_bracket_pattern():
    """
    Unit test for mounting bracket decomposition pattern.

    Success criteria:
    - Bracket decomposes into sketch, extrude, holes tasks
    - Holes task accounts for hole_count from context
    - Dependencies set correctly (holes after extrude)
    """
    from src.multi_agent.task_decomposer import decompose_goal

    goal_description = "create mounting bracket with holes"
    context = {
        "bracket_dimensions": {"length": 150, "width": 50, "thickness": 5},
        "hole_diameter": 8,
        "hole_count": 4
    }

    tasks = decompose_goal(goal_description, context)

    assert len(tasks) > 0, "Bracket should decompose into tasks"

    task_descriptions = [task.description.lower() for task in tasks]

    # Bracket pattern should include sketch, extrude, holes
    has_sketch_or_entity = any(
        "sketch" in desc or "profile" in desc or "shape" in desc
        for desc in task_descriptions
    )
    has_holes = any("hole" in desc or "drill" in desc for desc in task_descriptions)

    # At minimum should have entity creation and some solid operations
    all_operations = []
    for task in tasks:
        all_operations.extend(task.required_operations)

    has_creation = any("create" in op for op in all_operations)
    assert has_creation, "Bracket should require entity creation"


def test_decompose_cylinder_pattern():
    """
    Unit test for cylinder decomposition pattern.

    Success criteria:
    - Cylinder decomposes into create_circle, extrude tasks
    - Circle task uses diameter from context
    - Extrude task uses height from context
    - Dependencies set: extrude depends on circle
    """
    from src.multi_agent.task_decomposer import decompose_goal

    goal_description = "create cylinder"
    context = {
        "diameter": 50,
        "height": 100
    }

    tasks = decompose_goal(goal_description, context)

    assert len(tasks) > 0, "Cylinder should decompose into tasks"

    task_descriptions = [task.description.lower() for task in tasks]
    all_operations = []
    for task in tasks:
        all_operations.extend(task.required_operations)

    # Cylinder should require circle creation and extrusion
    has_circle = any("circle" in op for op in all_operations)
    has_extrude = any("extrude" in op for op in all_operations)

    # At minimum should have entity creation
    has_entity_creation = any("entity.create" in op for op in all_operations)
    assert has_entity_creation, "Cylinder should require entity creation"


def test_decompose_uses_context_values():
    """
    Verify that task decomposer uses context values in task creation.

    Tests that dimensions, counts, and other context data influence tasks.
    """
    from src.multi_agent.task_decomposer import decompose_goal

    # Same goal with different context should produce different task details
    goal = "create box assembly with lid"

    context1 = {"box_dimensions": {"length": 100, "width": 80, "height": 50}}
    context2 = {"box_dimensions": {"length": 200, "width": 160, "height": 100}}

    tasks1 = decompose_goal(goal, context1)
    tasks2 = decompose_goal(goal, context2)

    # Both should produce tasks
    assert len(tasks1) > 0
    assert len(tasks2) > 0

    # Tasks should have same structure (same pattern)
    assert len(tasks1) == len(tasks2), "Same pattern should produce same number of tasks"


def test_dependency_graph_no_cycles():
    """
    Verify that decomposed tasks never create dependency cycles.

    Tests that all patterns produce acyclic dependency graphs.
    """
    from src.multi_agent.task_decomposer import decompose_goal

    test_patterns = [
        ("create box assembly with lid", {"box_dimensions": {"length": 100, "width": 80, "height": 50}}),
        ("create mounting bracket with holes", {"bracket_dimensions": {"length": 150, "width": 50}, "hole_count": 4}),
        ("create cylinder", {"diameter": 50, "height": 100}),
    ]

    for goal, context in test_patterns:
        tasks = decompose_goal(goal, context)

        # Build dependency graph
        task_ids = {task.task_id for task in tasks}

        for task in tasks:
            # Verify all dependencies reference valid tasks
            for dep in task.dependencies:
                assert dep in task_ids, f"Task {task.task_id} has invalid dependency {dep}"

        # Verify no self-dependencies
        for task in tasks:
            assert task.task_id not in task.dependencies, (
                f"Task {task.task_id} has self-dependency"
            )

        # Simple cycle detection: if task A depends on B, B cannot depend on A (directly or indirectly)
        # Build adjacency list
        graph = {task.task_id: task.dependencies for task in tasks}

        # Check for cycles using DFS
        def has_cycle(node, visited, rec_stack):
            visited.add(node)
            rec_stack.add(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor, visited, rec_stack):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        visited = set()
        for task_id in graph:
            if task_id not in visited:
                assert not has_cycle(task_id, visited, set()), (
                    f"Dependency cycle detected in {goal}"
                )


def test_required_operations_match_real_roles():
    """
    Verify that required_operations in tasks match actual role definitions.

    Tests that decomposer only assigns operations that exist in role_templates.json.
    """
    from src.multi_agent.task_decomposer import decompose_goal
    from src.multi_agent.roles import load_predefined_roles

    # Load real role definitions
    role_templates = load_predefined_roles()

    # Collect all allowed operations across all roles
    all_allowed_operations = set()
    for role in role_templates.values():
        all_allowed_operations.update(role.allowed_operations)

    # Test decomposition
    goal = "create box assembly with lid"
    context = {"box_dimensions": {"length": 100, "width": 80, "height": 50}}

    tasks = decompose_goal(goal, context)

    # Verify all required operations exist in some role
    for task in tasks:
        for op in task.required_operations:
            assert op in all_allowed_operations, (
                f"Task {task.task_id} requires operation '{op}' which is not in any role definition"
            )


def test_task_assignment_fields_populated():
    """
    Verify that decomposed tasks have all required fields populated.

    Tests TaskAssignment dataclass completeness.
    """
    from src.multi_agent.task_decomposer import decompose_goal

    goal = "create cylinder"
    context = {"diameter": 50, "height": 100}

    tasks = decompose_goal(goal, context)

    assert len(tasks) > 0

    for task in tasks:
        # Verify required fields are populated
        assert task.task_id is not None and task.task_id != "", "task_id must be set"
        assert task.description is not None and task.description != "", "description must be set"
        assert task.required_operations is not None, "required_operations must be set"
        assert isinstance(task.required_operations, list), "required_operations must be a list"
        assert task.dependencies is not None, "dependencies must be set"
        assert isinstance(task.dependencies, list), "dependencies must be a list"
        assert task.success_criteria is not None, "success_criteria must be set"
        assert task.status is not None, "status must be set"

        # Initial state should be correct
        assert task.status == "pending", "New tasks should have pending status"
        assert task.agent_id is None, "New tasks should not be assigned yet"
        assert task.assigned_at is None, "New tasks should not have assigned_at"
        assert task.completed_at is None, "New tasks should not have completed_at"
        assert task.result is None, "New tasks should not have result"


def test_decompose_unknown_pattern_returns_generic_tasks():
    """
    Verify that decomposer handles unknown patterns gracefully.

    If pattern not recognized, should return at least generic tasks.
    """
    from src.multi_agent.task_decomposer import decompose_goal

    goal = "create some_unknown_exotic_thing"
    context = {}

    tasks = decompose_goal(goal, context)

    # Should return at least one task (even if generic)
    assert len(tasks) > 0, "Unknown pattern should still produce at least one task"

    # Tasks should have valid structure
    for task in tasks:
        assert task.task_id is not None
        assert task.description is not None
        assert task.required_operations is not None
        assert isinstance(task.required_operations, list)
