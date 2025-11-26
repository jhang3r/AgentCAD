# Quickstart: Multi-Agent CAD Collaboration Framework

**Feature**: 002-multi-agent-framework
**Date**: 2025-11-25

## Prerequisites

- Python 3.11+ installed
- CAD environment from 001-cad-environment fully functional (all 122/123 tests passing)
- JSON-RPC CLI accessible at `src/agent_interface/cli.py`

## Installation

```bash
# No additional dependencies needed - uses Python stdlib only
# Ensure CAD environment is working
python src/agent_interface/cli.py workspace.list
```

## Basic Usage

### Example 1: Create a Single Agent

```python
from multi_agent_controller import MultiAgentController

# Initialize controller
controller = MultiAgentController(max_concurrent_agents=10)

# Create a designer agent with isolated workspace
agent = controller.create_agent(
    agent_id="designer_001",
    role_name="designer",
    workspace_id="ws_designer_001"
)

# Execute operations via the agent
result = controller.execute_operation(
    agent_id="designer_001",
    operation="entity.create_point",
    params={"x": 10.0, "y": 20.0, "z": 0.0}
)

print(f"Operation success: {result['success']}")
print(f"Created entity: {result['result']['entity_id']}")

# Check agent metrics
metrics = controller.get_agent_metrics("designer_001")
print(f"Success rate: {metrics['success_rate']:.2%}")
```

### Example 2: Role Constraint Enforcement

```python
# Create designer agent (2D geometry only)
designer = controller.create_agent(
    agent_id="designer_002",
    role_name="designer",
    workspace_id="ws_designer_002"
)

# This succeeds - designer can create lines
result = controller.execute_operation(
    agent_id="designer_002",
    operation="entity.create_line",
    params={"start": {"x": 0, "y": 0}, "end": {"x": 100, "y": 0}}
)
assert result['success'] == True

# This fails - designer cannot extrude (role violation)
try:
    result = controller.execute_operation(
        agent_id="designer_002",
        operation="solid.extrude",
        params={"entity_id": "line_1", "distance": 20.0}
    )
except RoleViolationError as e:
    print(f"Role violation: {e}")
    # Output: "Agent designer_002 with role designer cannot execute solid.extrude"
```

### Example 3: Agent-to-Agent Messaging

```python
# Create two agents
designer = controller.create_agent("designer_a", "designer", "ws_designer_a")
validator = controller.create_agent("validator_a", "validator", "ws_validator_a")

# Designer creates a component
controller.execute_operation(
    "designer_a",
    "entity.create_circle",
    {"center": {"x": 50, "y": 50}, "radius": 25.0}
)

# Designer requests validation from validator
controller.send_message(
    from_agent_id="designer_a",
    to_agent_id="validator_a",
    message_type="request",
    content={
        "request_type": "validate_component",
        "component_id": "circle_1",
        "validation_criteria": ["check_dimensions"]
    }
)

# Validator retrieves message and responds
messages = controller.get_messages("validator_a")
request = messages[0]

# Validator checks the component (read-only query)
component_result = controller.execute_operation(
    "validator_a",
    "entity.query",
    {"entity_id": "circle_1"}
)

# Validator sends response
controller.send_message(
    from_agent_id="validator_a",
    to_agent_id="designer_a",
    message_type="response",
    content={
        "request_id": request['message_id'],
        "status": "success",
        "validation_results": {"check_dimensions": "pass"}
    }
)

# Designer retrieves validation response
response_messages = controller.get_messages("designer_a")
print(f"Validation status: {response_messages[0]['content']['status']}")
```

### Example 4: Concurrent Agents (Parallel Work)

```python
# Create 3 modeler agents with separate workspaces
agents = []
for i in range(3):
    agent = controller.create_agent(
        agent_id=f"modeler_{i}",
        role_name="modeler",
        workspace_id=f"ws_modeler_{i}"
    )
    agents.append(agent)

# All 3 agents work in parallel creating different components
import concurrent.futures

def create_component(agent_id, workspace_id):
    # Create 2D sketch
    controller.execute_operation(
        agent_id,
        "entity.create_circle",
        {"center": {"x": 0, "y": 0}, "radius": 50.0, "workspace_id": workspace_id}
    )
    # Extrude to 3D
    result = controller.execute_operation(
        agent_id,
        "solid.extrude",
        {"entity_id": "circle_1", "distance": 20.0, "workspace_id": workspace_id}
    )
    return result

# Execute in parallel
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
    futures = []
    for i, agent in enumerate(agents):
        future = executor.submit(create_component, agent.agent_id, agent.workspace_id)
        futures.append(future)

    # Wait for all to complete
    for future in concurrent.futures.as_completed(futures):
        result = future.result()
        print(f"Component created: {result['success']}")

# All 3 components created simultaneously without interference
```

### Example 5: Workspace Merge (Integration)

```python
# After parallel work, create integrator to merge workspaces
integrator = controller.create_agent(
    agent_id="integrator_001",
    role_name="integrator",
    workspace_id="ws_main"
)

# Integrator merges all 3 component workspaces
merge_result = controller.execute_operation(
    "integrator_001",
    "workspace.merge",
    {
        "source_workspace": "ws_modeler_0",
        "target_workspace": "ws_main"
    }
)

merge_result = controller.execute_operation(
    "integrator_001",
    "workspace.merge",
    {
        "source_workspace": "ws_modeler_1",
        "target_workspace": "ws_main"
    }
)

merge_result = controller.execute_operation(
    "integrator_001",
    "workspace.merge",
    {
        "source_workspace": "ws_modeler_2",
        "target_workspace": "ws_main"
    }
)

# Broadcast merge completion to all agents
controller.send_message(
    from_agent_id="integrator_001",
    to_agent_id="broadcast",
    message_type="broadcast",
    content={
        "announcement": "workspace_merge_complete",
        "merged_workspace": "ws_main",
        "source_workspaces": ["ws_modeler_0", "ws_modeler_1", "ws_modeler_2"]
    }
)
```

### Example 6: Collaborative Scenario Execution

```python
# Execute predefined assembly design scenario
workflow = controller.execute_workflow(
    scenario_name="assembly_design",
    agent_overrides=None  # Use default agent assignments
)

print(f"Workflow ID: {workflow.workflow_id}")
print(f"Tasks: {len(workflow.task_assignments)}")

# Monitor workflow progress
import time
while workflow.execution_state == "running":
    status = controller.get_workflow_status(workflow.workflow_id)
    print(f"Progress: {status.completion_percentage:.1f}%")
    time.sleep(1)

# Check final status
final_status = controller.get_workflow_status(workflow.workflow_id)
print(f"Final state: {final_status.execution_state}")
print(f"Total operations: {final_status.metrics['total_operations']}")
print(f"Duration: {final_status.metrics['total_duration']:.2f}s")

if final_status.agent_failures:
    print("Failures:")
    for failure in final_status.agent_failures:
        print(f"  - Agent {failure['agent_id']}: {failure['error']}")
```

### Example 7: Task Decomposition

```python
# Controller decomposes high-level goal into specific tasks
tasks = controller.decompose_task(
    goal_description="Create a box assembly with lid and mounting holes",
    context={
        "box_dimensions": {"length": 100, "width": 80, "height": 50},
        "lid_height": 10,
        "hole_diameter": 5,
        "hole_count": 4
    }
)

print(f"Decomposed into {len(tasks)} tasks:")
for task in tasks:
    print(f"  - {task.description} (requires {task.required_operations})")

# Assign tasks to appropriate agents
for task in tasks:
    # Find agent with matching role
    suitable_agent = None
    for agent_id, agent in controller.agents.items():
        if all(op in agent.role.allowed_operations for op in task.required_operations):
            suitable_agent = agent_id
            break

    if suitable_agent:
        controller.assign_task(task.task_id, suitable_agent)
        print(f"Assigned {task.task_id} to {suitable_agent}")
```

### Example 8: Agent Performance Tracking

```python
# Create agent and execute multiple operations
agent = controller.create_agent("test_agent", "modeler", "ws_test")

# Execute 20 operations (mix of success and failure)
for i in range(20):
    try:
        result = controller.execute_operation(
            "test_agent",
            "entity.create_point",
            {"x": i*10, "y": i*10, "z": 0}
        )
    except Exception as e:
        pass  # Some may fail

# Get comprehensive metrics
metrics = controller.get_agent_metrics("test_agent")

print(f"Agent: {metrics['agent_id']}")
print(f"Operations: {metrics['operation_count']}")
print(f"Success rate: {metrics['success_rate']:.2%}")
print(f"Error rate trend: {metrics['error_rate_trend']}")
print(f"Avg operation time: {metrics['average_operation_time']:.3f}s")
print(f"Learning status: {metrics['learning_status']}")
```

## CLI Usage

The multi-agent framework also provides a CLI interface:

```bash
# Create controller
python -m src.multi_agent.cli controller.create --controller_id main_controller

# Create agent
python -m src.multi_agent.cli agent.create \
  --agent_id designer_001 \
  --role_name designer \
  --workspace_id ws_designer_001

# Execute operation
python -m src.multi_agent.cli agent.execute \
  --agent_id designer_001 \
  --operation entity.create_point \
  --params '{"x": 10.0, "y": 20.0, "z": 0.0}'

# Get metrics
python -m src.multi_agent.cli agent.metrics --agent_id designer_001

# Execute workflow
python -m src.multi_agent.cli workflow.execute --scenario_name assembly_design
```

## Common Patterns

### Pattern 1: Sequential Design Chain

Designer → Constraint Solver → Modeler → Validator

```python
# Designer creates 2D sketch
designer = controller.create_agent("designer", "designer", "ws_design")
controller.execute_operation("designer", "entity.create_line", {...})

# Constraint solver applies constraints
solver = controller.create_agent("solver", "constraint_solver", "ws_design")
controller.execute_operation("solver", "constraint.apply", {...})

# Modeler extrudes to 3D
modeler = controller.create_agent("modeler", "modeler", "ws_design")
controller.execute_operation("modeler", "solid.extrude", {...})

# Validator checks final result
validator = controller.create_agent("validator", "validator", "ws_design")
controller.execute_operation("validator", "entity.query", {...})
```

### Pattern 2: Parallel Component Creation

Multiple modelers work simultaneously, integrator combines results

```python
# 4 modelers create different parts in parallel
modelers = [
    controller.create_agent(f"modeler_{i}", "modeler", f"ws_{i}")
    for i in range(4)
]

# Parallel execution (shown in Example 4 above)
# ...

# Integrator merges all workspaces
integrator = controller.create_agent("integrator", "integrator", "ws_main")
for i in range(4):
    controller.execute_operation("integrator", "workspace.merge", {
        "source_workspace": f"ws_{i}",
        "target_workspace": "ws_main"
    })
```

### Pattern 3: Iterative Refinement Loop

Modeler → Validator → Optimizer → Validator

```python
# Modeler creates initial design
modeler = controller.create_agent("modeler", "modeler", "ws_refine")
controller.execute_operation("modeler", "solid.extrude", {...})

# Validator checks
validator = controller.create_agent("validator", "validator", "ws_refine")
result = controller.execute_operation("validator", "entity.query", {...})

# If validation fails, optimizer improves design
if result['validation_status'] != "pass":
    optimizer = controller.create_agent("optimizer", "optimizer", "ws_refine")
    controller.execute_operation("optimizer", "solid.boolean", {...})

    # Re-validate
    result = controller.execute_operation("validator", "entity.query", {...})
```

## Testing Your Multi-Agent System

```bash
# Run contract tests (controller API)
pytest tests/multi_agent_contract/

# Run integration tests (real CLI subprocess calls)
pytest tests/multi_agent_integration/

# Run unit tests (task decomposition)
pytest tests/multi_agent_unit/

# Run all multi-agent tests
pytest tests/multi_agent_*/
```

## Troubleshooting

### Role Violation Errors

```python
# Check agent role before operation
agent = controller.agents["designer_001"]
if "solid.extrude" not in agent.role.allowed_operations:
    print(f"Cannot execute - agent role {agent.role.name} does not permit solid.extrude")
    # Assign to different agent or create new agent with modeler role
```

### Workspace Merge Conflicts

```python
# Handle merge conflicts explicitly
try:
    result = controller.execute_operation("integrator", "workspace.merge", {...})
except WorkspaceMergeConflictError as e:
    print(f"Conflict detected: {e.conflict_type}")
    # Resolve manually
    controller.execute_operation("integrator", "workspace.resolve_conflict", {
        "conflict_id": e.conflict_id,
        "strategy": "keep_source"  # or "keep_target", "manual_merge"
    })
```

### Agent Subprocess Timeout

```python
# For long-running operations, increase timeout in controller config
controller = MultiAgentController(
    max_concurrent_agents=10,
    subprocess_timeout=30  # seconds
)
```

## Next Steps

- Review `contracts/controller_api.yaml` for complete API reference
- Review `contracts/role_templates.json` for all role definitions
- Review `data-model.md` for entity relationships and validation rules
- Implement your own collaborative scenarios in `src/multi_agent/scenarios.py`
- Extend role templates for domain-specific agent types

## Performance Benchmarks (Success Criteria Reference)

From spec.md success criteria:

- ✅ SC-001: 4+ agents work simultaneously without interference
- ✅ SC-003: Role constraints enforced 100% of the time
- ✅ SC-004: Workspace merge <5 seconds for 100 entities
- ✅ SC-006: 10 agents in parallel, operations remain <100ms
- ✅ SC-010: Agent messaging <100ms latency
- ✅ SC-011: Individual agent failures preserve other agents' work

Test these benchmarks with the integration test suite.
