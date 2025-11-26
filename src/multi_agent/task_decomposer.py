"""
Task decomposition and coordination for multi-agent workflows.

Decomposes high-level design goals into specific tasks, assigns them to agents
based on role matching, and coordinates execution with dependency handling.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
import time


@dataclass
class TaskAssignment:
    """
    Associates a specific task with an agent.

    Fields:
        task_id: Unique task identifier
        agent_id: Assigned agent ID (None if not yet assigned)
        description: Human-readable task description
        required_operations: JSON-RPC operations needed for task
        dependencies: Task IDs that must complete first
        success_criteria: Measurable completion condition
        status: "pending", "in_progress", "completed", "failed", "blocked"
        assigned_at: Timestamp when task assigned
        completed_at: Timestamp when task completed/failed
        result: Task execution result or error details

    Validation Rules:
        - required_operations must all be in assigned agent's role allowed_operations
        - Cannot set status to "completed" unless success_criteria met
        - dependencies must reference valid task_ids
        - completed_at only set when status is "completed" or "failed"

    State Transitions:
        Created → pending
        pending → in_progress (agent starts work)
        in_progress → completed (success criteria met)
        in_progress → failed (error occurred)
        pending → blocked (dependency not met)
        blocked → pending (dependency resolved)
    """
    task_id: str
    description: str
    required_operations: List[str]
    success_criteria: str
    agent_id: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    status: str = "pending"
    assigned_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Optional[dict] = None

    def __post_init__(self):
        """Validate task assignment fields."""
        if not self.task_id:
            raise ValueError("Task ID cannot be empty")

        if not self.description:
            raise ValueError("Task description cannot be empty")

        if not self.required_operations:
            raise ValueError("Task must have at least one required operation")

        valid_statuses = ["pending", "in_progress", "completed", "failed", "blocked"]
        if self.status not in valid_statuses:
            raise ValueError(
                f"Invalid status {self.status}, must be one of: {valid_statuses}"
            )

        if self.completed_at is not None and self.status not in ["completed", "failed"]:
            raise ValueError(
                f"completed_at can only be set when status is completed or failed, not {self.status}"
            )


def decompose_goal(goal_description: str, context: Optional[Dict] = None) -> List[TaskAssignment]:
    """
    Decompose a high-level design goal into specific tasks.

    Uses rule-based logic to identify common patterns (box assembly, bracket creation,
    cylinder) and generate appropriate task sequences.

    Args:
        goal_description: High-level design goal (e.g., "create a box assembly with lid")
        context: Additional context (dimensions, constraints, etc.)

    Returns:
        List of TaskAssignment instances representing the decomposed tasks

    Examples:
        >>> tasks = decompose_goal("create a box assembly with lid")
        >>> len(tasks)
        3
        >>> tasks[0].description
        'Create box base'
    """
    if context is None:
        context = {}

    goal_lower = goal_description.lower()
    tasks = []

    # Pattern 1: Box assembly with lid
    if "box" in goal_lower and "lid" in goal_lower:
        tasks = _decompose_box_assembly(context)

    # Pattern 2: Mechanical bracket
    elif "bracket" in goal_lower:
        tasks = _decompose_bracket(context)

    # Pattern 3: Cylinder or shaft
    elif "cylinder" in goal_lower or "shaft" in goal_lower:
        tasks = _decompose_cylinder(context)

    # Pattern 4: Generic assembly (fallback)
    elif "assembly" in goal_lower or "create" in goal_lower:
        tasks = _decompose_generic_assembly(goal_description, context)

    else:
        # Unknown pattern - create a single generic task
        tasks = [
            TaskAssignment(
                task_id="task_001",
                description=f"Execute: {goal_description}",
                required_operations=["entity.create_point", "entity.create_line"],
                success_criteria="Design goal achieved"
            )
        ]

    return tasks


def _decompose_box_assembly(context: Dict) -> List[TaskAssignment]:
    """Decompose box assembly with lid into specific tasks."""
    # Extract dimensions from context or use defaults
    length = context.get("box_dimensions", {}).get("length", 100)
    width = context.get("box_dimensions", {}).get("width", 80)
    height = context.get("box_dimensions", {}).get("height", 50)
    lid_height = context.get("lid_height", 10)

    tasks = [
        TaskAssignment(
            task_id="box_task_001",
            description=f"Create box base ({length}x{width}x{height}mm)",
            required_operations=["entity.create_line", "solid.extrude"],
            success_criteria=f"Box base entity exists with volume ~{length*width*height}mm³",
            dependencies=[]
        ),
        TaskAssignment(
            task_id="box_task_002",
            description=f"Create lid ({length}x{width}x{lid_height}mm)",
            required_operations=["entity.create_line", "solid.extrude"],
            success_criteria=f"Lid entity exists with correct dimensions",
            dependencies=[]  # Can be created in parallel with base
        ),
        TaskAssignment(
            task_id="box_task_003",
            description="Integrate base and lid into assembly",
            required_operations=["workspace.merge"],
            success_criteria="Both base and lid present in final assembly with no conflicts",
            dependencies=["box_task_001", "box_task_002"]  # Requires both components
        )
    ]

    return tasks


def _decompose_bracket(context: Dict) -> List[TaskAssignment]:
    """Decompose mechanical bracket creation into specific tasks."""
    tasks = [
        TaskAssignment(
            task_id="bracket_task_001",
            description="Create bracket base profile",
            required_operations=["entity.create_line", "entity.create_arc"],
            success_criteria="Closed 2D profile for bracket base created",
            dependencies=[]
        ),
        TaskAssignment(
            task_id="bracket_task_002",
            description="Add mounting holes to bracket",
            required_operations=["entity.create_circle", "solid.boolean"],
            success_criteria="Mounting holes created in correct positions",
            dependencies=["bracket_task_001"]
        ),
        TaskAssignment(
            task_id="bracket_task_003",
            description="Extrude bracket to 3D",
            required_operations=["solid.extrude"],
            success_criteria="3D bracket solid created",
            dependencies=["bracket_task_001"]
        )
    ]

    return tasks


def _decompose_cylinder(context: Dict) -> List[TaskAssignment]:
    """Decompose cylinder/shaft creation into specific tasks."""
    radius = context.get("radius", 25.0)
    height = context.get("height", 100.0)

    tasks = [
        TaskAssignment(
            task_id="cylinder_task_001",
            description=f"Create circular profile (radius {radius}mm)",
            required_operations=["entity.create_circle"],
            success_criteria=f"Circle with radius {radius}mm created",
            dependencies=[]
        ),
        TaskAssignment(
            task_id="cylinder_task_002",
            description=f"Extrude circle to create cylinder (height {height}mm)",
            required_operations=["solid.extrude"],
            success_criteria=f"Cylinder with height {height}mm and radius {radius}mm created",
            dependencies=["cylinder_task_001"]
        )
    ]

    return tasks


def _decompose_generic_assembly(goal: str, context: Dict) -> List[TaskAssignment]:
    """Decompose generic assembly into basic tasks."""
    tasks = [
        TaskAssignment(
            task_id="generic_task_001",
            description="Create primary component",
            required_operations=["entity.create_line", "solid.extrude"],
            success_criteria="Primary component created",
            dependencies=[]
        ),
        TaskAssignment(
            task_id="generic_task_002",
            description="Create secondary component",
            required_operations=["entity.create_line", "solid.extrude"],
            success_criteria="Secondary component created",
            dependencies=[]
        ),
        TaskAssignment(
            task_id="generic_task_003",
            description="Integrate components",
            required_operations=["workspace.merge"],
            success_criteria="All components integrated successfully",
            dependencies=["generic_task_001", "generic_task_002"]
        )
    ]

    return tasks


def resolve_dependencies(tasks: List[TaskAssignment]) -> List[List[TaskAssignment]]:
    """
    Resolve task dependencies and return execution order.

    Groups tasks into execution phases where tasks in each phase can run in parallel,
    and each phase depends on completion of all previous phases.

    Args:
        tasks: List of TaskAssignment instances

    Returns:
        List of task lists, where each inner list represents tasks that can execute in parallel

    Example:
        >>> tasks = [
        ...     TaskAssignment("t1", "Task 1", ["op1"], "criteria", dependencies=[]),
        ...     TaskAssignment("t2", "Task 2", ["op2"], "criteria", dependencies=[]),
        ...     TaskAssignment("t3", "Task 3", ["op3"], "criteria", dependencies=["t1", "t2"])
        ... ]
        >>> phases = resolve_dependencies(tasks)
        >>> len(phases)
        2
        >>> len(phases[0])  # t1 and t2 can run in parallel
        2
        >>> len(phases[1])  # t3 depends on t1 and t2
        1
    """
    # Build task lookup
    task_map = {task.task_id: task for task in tasks}

    # Track completed tasks
    completed = set()
    phases = []

    while len(completed) < len(tasks):
        # Find tasks ready to execute (all dependencies met)
        ready_tasks = []
        for task in tasks:
            if task.task_id in completed:
                continue

            # Check if all dependencies are completed
            if all(dep_id in completed for dep_id in task.dependencies):
                ready_tasks.append(task)

        if not ready_tasks:
            # No tasks ready but not all completed - circular dependency or missing task
            remaining = [t for t in tasks if t.task_id not in completed]
            raise ValueError(
                f"Circular dependency or missing task detected. Remaining tasks: {[t.task_id for t in remaining]}"
            )

        # Add this phase
        phases.append(ready_tasks)

        # Mark as completed
        for task in ready_tasks:
            completed.add(task.task_id)

    return phases
