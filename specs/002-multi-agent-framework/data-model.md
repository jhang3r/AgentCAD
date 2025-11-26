# Data Model: Multi-Agent CAD Collaboration Framework

**Feature**: 002-multi-agent-framework
**Date**: 2025-11-25
**Phase**: Phase 1 - Design & Contracts

## Overview

The multi-agent framework manages AI agents collaborating on CAD design tasks through role-based specialization, workspace isolation, and message-based communication. All CAD operations are executed via JSON-RPC CLI subprocess calls to the existing CAD environment.

## Core Entities

### Agent

Represents an AI agent instance with a specific role and isolated workspace.

**Fields**:
- `agent_id` (str): Unique identifier (e.g., "agent_001", "designer_a")
- `role` (RoleTemplate): Assigned role defining capabilities and constraints
- `workspace_id` (str): Isolated workspace identifier for CAD operations
- `operation_count` (int): Total number of operations attempted
- `success_count` (int): Number of successful operations
- `error_count` (int): Number of failed operations
- `created_entities` (List[str]): Entity IDs created by this agent
- `error_log` (List[str]): Recent error messages
- `status` (str): Current agent status - "idle", "working", "error", "terminated"
- `created_at` (float): Timestamp when agent was created
- `last_active` (float): Timestamp of last operation

**Relationships**:
- Agent belongs to one RoleTemplate (many-to-one)
- Agent has one workspace (one-to-one with CAD environment workspace)
- Agent sends/receives AgentMessages (one-to-many)
- Agent assigned to TaskAssignments (one-to-many)

**Validation Rules**:
- `agent_id` must be unique across all agents in controller
- `workspace_id` must exist in CAD environment before agent creation
- `role` must be a valid RoleTemplate instance
- `success_count` + `error_count` <= `operation_count`
- `status` must be one of: "idle", "working", "error", "terminated"

**State Transitions**:
```
Created → idle
idle → working (when operation starts)
working → idle (operation succeeds)
working → error (operation fails)
error → idle (error cleared/retry)
any → terminated (agent shutdown)
```

### RoleTemplate

Defines a specialized agent role with permitted capabilities and constraints.

**Fields**:
- `name` (str): Role name (e.g., "designer", "modeler", "validator")
- `description` (str): Human-readable role purpose
- `allowed_operations` (List[str]): JSON-RPC method names agent can execute (e.g., ["entity.create_point", "entity.create_line"])
- `forbidden_operations` (List[str]): Explicitly prohibited operations (e.g., ["solid.extrude", "file.delete"])
- `example_tasks` (List[str]): Sample tasks demonstrating role purpose

**Relationships**:
- RoleTemplate defines capabilities for many Agents (one-to-many)

**Validation Rules**:
- `name` must be unique across all role templates
- `allowed_operations` and `forbidden_operations` must not overlap
- All operation names must match existing JSON-RPC CLI methods
- At least one `allowed_operations` must be specified
- `description` and `example_tasks` required for documentation

**Predefined Roles**:
1. **designer**: 2D geometry creation (points, lines, circles, arcs)
2. **modeler**: 3D solid modeling (extrude, revolve, boolean operations)
3. **constraint_solver**: Apply geometric constraints (distance, angle, parallel)
4. **validator**: Read-only verification (query entities, check properties)
5. **optimizer**: Design improvement (simplify, reduce entities, optimize topology)
6. **integrator**: Workspace management (merge workspaces, resolve conflicts)

### Controller

Orchestrates multiple agents, manages task assignment, and coordinates workflows.

**Fields**:
- `controller_id` (str): Unique controller identifier
- `agents` (Dict[str, Agent]): Map of agent_id → Agent instances
- `role_templates` (Dict[str, RoleTemplate]): Map of role_name → RoleTemplate
- `message_queues` (Dict[str, queue.Queue]): Map of agent_id → message queue
- `thread_pool` (ThreadPoolExecutor): Executor for concurrent agent operations
- `active_workflows` (Dict[str, WorkflowExecution]): Map of workflow_id → active workflows
- `max_concurrent_agents` (int): Maximum agents executing simultaneously (default: 10)

**Relationships**:
- Controller manages many Agents (one-to-many)
- Controller defines many RoleTemplates (one-to-many)
- Controller executes many WorkflowExecutions (one-to-many)

**Operations**:
- `create_agent(agent_id, role_name, workspace_id)` → Agent
- `execute_operation(agent_id, operation, params)` → result
- `send_message(from_agent_id, to_agent_id, message_type, content)` → None
- `get_messages(agent_id)` → List[AgentMessage]
- `decompose_task(goal_description)` → List[TaskAssignment]
- `assign_task(agent_id, task)` → None
- `execute_workflow(scenario_name, agents)` → WorkflowExecution
- `get_agent_metrics(agent_id)` → dict
- `shutdown_agent(agent_id)` → None

**Validation Rules**:
- Cannot create agent with duplicate `agent_id`
- Cannot execute operation if agent's role forbids it
- `max_concurrent_agents` must be between 1 and 50
- Cannot send message to non-existent agent

### TaskAssignment

Associates a specific task with an agent for execution.

**Fields**:
- `task_id` (str): Unique task identifier
- `agent_id` (str): Assigned agent ID
- `description` (str): Human-readable task description
- `required_operations` (List[str]): JSON-RPC operations needed for task
- `dependencies` (List[str]): Task IDs that must complete first
- `success_criteria` (str): Measurable completion condition
- `status` (str): "pending", "in_progress", "completed", "failed", "blocked"
- `assigned_at` (float): Timestamp when task assigned
- `completed_at` (Optional[float]): Timestamp when task completed/failed
- `result` (Optional[dict]): Task execution result or error details

**Relationships**:
- TaskAssignment assigned to one Agent (many-to-one)
- TaskAssignment part of one WorkflowExecution (many-to-one)
- TaskAssignment may depend on other TaskAssignments (many-to-many via dependencies)

**Validation Rules**:
- `required_operations` must all be in assigned agent's role `allowed_operations`
- Cannot set status to "completed" unless `success_criteria` met
- `dependencies` must reference valid task_ids
- `completed_at` only set when status is "completed" or "failed"

**State Transitions**:
```
Created → pending
pending → in_progress (agent starts work)
in_progress → completed (success criteria met)
in_progress → failed (error occurred)
pending → blocked (dependency not met)
blocked → pending (dependency resolved)
```

### AgentMessage

Direct communication between agents for coordination and feedback.

**Fields**:
- `message_id` (str): Unique message identifier
- `from_agent_id` (str): Sender agent ID
- `to_agent_id` (str): Receiver agent ID (or "broadcast" for all)
- `message_type` (str): "request", "response", "broadcast", "error"
- `content` (dict): Message payload (structure depends on message_type)
- `timestamp` (float): When message was sent
- `read` (bool): Whether receiver has retrieved message

**Relationships**:
- AgentMessage sent by one Agent (many-to-one from_agent)
- AgentMessage received by one Agent or broadcast (many-to-one to_agent)

**Validation Rules**:
- `from_agent_id` and `to_agent_id` must reference existing agents (or "broadcast")
- `message_type` must be one of: "request", "response", "broadcast", "error"
- `content` must be JSON-serializable dict
- `timestamp` must be <= current time

**Message Type Structures**:

```python
# Request message
{
    "message_type": "request",
    "content": {
        "request_type": "validate_component",
        "component_id": "entity_123",
        "validation_criteria": ["check_dimensions", "check_constraints"]
    }
}

# Response message
{
    "message_type": "response",
    "content": {
        "request_id": "msg_456",
        "status": "success",
        "validation_results": {"dimensions": "pass", "constraints": "fail"}
    }
}

# Broadcast message
{
    "message_type": "broadcast",
    "content": {
        "announcement": "workspace_merge_complete",
        "merged_workspace": "main",
        "source_workspaces": ["ws_a", "ws_b"]
    }
}

# Error message
{
    "message_type": "error",
    "content": {
        "error_code": "ROLE_VIOLATION",
        "error_message": "Cannot execute solid.extrude - designer role constraint"
    }
}
```

### CollaborativeScenario

Defines a reusable multi-agent workflow template for testing and demonstration.

**Fields**:
- `scenario_name` (str): Unique scenario identifier (e.g., "assembly_design", "design_review_loop")
- `description` (str): Scenario purpose and expected outcome
- `agent_assignments` (List[dict]): Agent role assignments - [{"agent_id": "...", "role_name": "...", "workspace_id": "..."}]
- `workflow_pattern` (str): "parallel", "sequential", "mixed"
- `task_sequence` (List[dict]): Ordered tasks with dependencies
- `success_criteria` (str): How to measure scenario completion
- `estimated_duration` (float): Expected execution time in seconds

**Relationships**:
- CollaborativeScenario executed as WorkflowExecution instances (one-to-many)

**Validation Rules**:
- `scenario_name` must be unique
- All `agent_assignments` roles must reference valid RoleTemplates
- `workflow_pattern` must be "parallel", "sequential", or "mixed"
- `task_sequence` tasks must form valid dependency graph (no cycles)

**Example Scenarios**:

```python
# Assembly Design Scenario
{
    "scenario_name": "assembly_design",
    "description": "4 agents create housing, lid, supports, and integrate",
    "agent_assignments": [
        {"agent_id": "housing_designer", "role_name": "modeler", "workspace_id": "ws_housing"},
        {"agent_id": "lid_designer", "role_name": "modeler", "workspace_id": "ws_lid"},
        {"agent_id": "support_designer", "role_name": "modeler", "workspace_id": "ws_supports"},
        {"agent_id": "integrator", "role_name": "integrator", "workspace_id": "ws_main"}
    ],
    "workflow_pattern": "mixed",  # parallel design, sequential integration
    "task_sequence": [
        {"task_id": "t1", "agent_id": "housing_designer", "description": "Create housing", "dependencies": []},
        {"task_id": "t2", "agent_id": "lid_designer", "description": "Create lid", "dependencies": []},
        {"task_id": "t3", "agent_id": "support_designer", "description": "Create supports", "dependencies": []},
        {"task_id": "t4", "agent_id": "integrator", "description": "Merge all workspaces", "dependencies": ["t1", "t2", "t3"]}
    ],
    "success_criteria": "All components merged, 0 conflicts, final assembly exportable"
}
```

### WorkflowExecution

Tracks the runtime state of a collaborative scenario execution.

**Fields**:
- `workflow_id` (str): Unique execution identifier
- `scenario_name` (str): Reference to CollaborativeScenario being executed
- `task_assignments` (List[TaskAssignment]): Active task instances
- `execution_state` (str): "initializing", "running", "completed", "failed", "partial_failure"
- `completion_percentage` (float): 0.0 to 100.0
- `agent_failures` (List[dict]): [{"agent_id": "...", "task_id": "...", "error": "..."}]
- `started_at` (float): Timestamp when workflow started
- `completed_at` (Optional[float]): Timestamp when workflow finished
- `metrics` (dict): Performance metrics - {"total_operations": N, "total_duration": seconds, "agents_used": N}

**Relationships**:
- WorkflowExecution contains many TaskAssignments (one-to-many)
- WorkflowExecution managed by one Controller (many-to-one)
- WorkflowExecution based on one CollaborativeScenario (many-to-one)

**Validation Rules**:
- `completion_percentage` must be 0-100
- `execution_state` must be one of: "initializing", "running", "completed", "failed", "partial_failure"
- Cannot set `completed_at` unless state is "completed", "failed", or "partial_failure"
- `agent_failures` only populated when errors occur

**State Transitions**:
```
Created → initializing
initializing → running (all agents/workspaces created)
running → completed (all tasks successful)
running → failed (critical failure, cannot continue)
running → partial_failure (some tasks failed, others succeeded)
```

## Persistence and Storage

**In-Memory Only** (no database persistence beyond CAD environment):
- All entities (Agent, RoleTemplate, TaskAssignment, etc.) exist only in controller process memory
- Controller does not persist state to disk
- CAD data persists via existing SQLite database (001-cad-environment)
- On controller restart, all agent state lost (ephemeral sessions)

**Rationale**: Simplicity for initial version. Agent metrics and workflow history can be added later if needed.

## Data Flow

1. **Agent Creation**: Controller → creates workspace via CLI → creates Agent object
2. **Operation Execution**: Agent → Controller validates role → subprocess CLI call → parse result → update agent metrics
3. **Messaging**: Agent A → Controller.send_message() → queue.Queue → Agent B polls → Controller.get_messages()
4. **Task Assignment**: Controller.decompose_task() → create TaskAssignments → assign to agents → track execution
5. **Workspace Merge**: Integrator agent → Controller validates role → CLI workspace.merge → handle conflicts

## Example Data Instances

### Example: Designer Agent

```python
agent = Agent(
    agent_id="designer_001",
    role=designer_role,  # RoleTemplate instance
    workspace_id="ws_designer_001",
    operation_count=15,
    success_count=14,
    error_count=1,
    created_entities=["point_1", "line_2", "circle_3"],
    error_log=["entity.create_line: Invalid parameter 'length'"],
    status="idle",
    created_at=1732567890.123,
    last_active=1732567920.456
)
```

### Example: Role Template (Validator)

```python
validator_role = RoleTemplate(
    name="validator",
    description="Read-only verification agent - queries entities and validates designs without modifications",
    allowed_operations=[
        "entity.list",
        "entity.query",
        "workspace.list",
        "agent.metrics"
    ],
    forbidden_operations=[
        "entity.create_point",
        "entity.create_line",
        "solid.extrude",
        "solid.boolean",
        "workspace.merge",
        "file.export"
    ],
    example_tasks=[
        "Verify all entities have valid IDs",
        "Check that assembly has required components",
        "Validate geometric constraints are satisfied"
    ]
)
```

### Example: Task Assignment

```python
task = TaskAssignment(
    task_id="task_housing_001",
    agent_id="modeler_a",
    description="Create rectangular housing base 100x80x20mm",
    required_operations=["entity.create_line", "solid.extrude"],
    dependencies=[],
    success_criteria="Housing entity exists with correct dimensions",
    status="in_progress",
    assigned_at=1732567900.0,
    completed_at=None,
    result=None
)
```

## API Contract References

See `contracts/controller_api.yaml` for full Controller REST/Python API specification.
See `contracts/role_templates.json` for all predefined RoleTemplate definitions.
See `contracts/message_schemas.json` for AgentMessage content structures by type.
