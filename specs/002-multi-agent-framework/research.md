# Research: Multi-Agent CAD Collaboration Framework

**Feature**: 002-multi-agent-framework
**Date**: 2025-11-25
**Phase**: Phase 0 - Research & Unknowns Resolution

## Research Questions

From Technical Context unknowns and dependencies:

1. **Message Queue Library Selection**: Which message queue implementation for agent-to-agent communication?
2. **Python Subprocess Patterns**: Best practices for managing subprocess lifecycle and communication
3. **Python Multiprocessing Patterns**: Concurrent agent execution approaches
4. **pytest Real CLI Integration**: Fixture patterns for integration tests with subprocess CLI calls
5. **Role-Based Access Control**: Pythonic patterns for enforcing role constraints

## Research Findings

### 1. Message Queue Library Selection

**Decision**: `queue.Queue` (Python standard library)

**Rationale**:
- All agents run in the same Python process (controller spawns subprocess CLI calls, but message queue is in-process)
- `queue.Queue` is thread-safe and sufficient for in-process, multi-threaded scenarios
- No external dependencies required (stdlib only)
- Performance: supports 100+ messages/second easily for in-process queues
- Simple API: `put()`, `get()`, `task_done()`

**Alternatives considered**:
- `asyncio.Queue`: Requires async/await throughout codebase - unnecessary complexity for subprocess-based agent model
- `multiprocessing.Queue`: For inter-process communication - not needed since controller is single-process with subprocess CLI invocations (not long-running agent processes)
- External message brokers (Redis, RabbitMQ): Over-engineered for local-only, in-process communication

**Implementation approach**:
- Controller maintains per-agent `queue.Queue` instances indexed by agent_id
- Agents query their message queue via controller API (not direct access)
- Thread-safe access pattern ensures concurrent reads/writes

### 2. Python Subprocess Patterns

**Decision**: Use `subprocess.run()` with `capture_output=True` and `text=True` for synchronous CLI invocations

**Rationale**:
- Each agent operation is a single JSON-RPC CLI invocation (fire and response pattern)
- `subprocess.run()` is simpler than `Popen` for request-response pattern
- `capture_output=True` captures stdout/stderr for result parsing and error reporting
- `text=True` returns strings instead of bytes (easier JSON parsing)
- Timeout support via `timeout` parameter prevents hung processes

**Best practices from Python docs**:
- Always specify `timeout` to prevent indefinite hangs
- Check `returncode` for non-zero values (errors)
- Parse stderr for error messages when returncode != 0
- Use `shlex.quote()` for any user-provided values in CLI arguments

**Error handling pattern**:
```python
import subprocess
result = subprocess.run(
    ["python", "src/agent_interface/cli.py", "entity.create", "--type", "point", ...],
    capture_output=True,
    text=True,
    timeout=10
)
if result.returncode != 0:
    # Parse stderr for error details
    raise AgentOperationError(result.stderr)
response = json.loads(result.stdout)
```

**Alternatives considered**:
- `subprocess.Popen`: More control but unnecessary complexity for simple request-response
- `asyncio.create_subprocess_exec`: Async not needed since each operation is synchronous
- Long-running agent processes with IPC: Over-engineered; subprocess per operation is simpler

### 3. Python Multiprocessing Patterns

**Decision**: Use `concurrent.futures.ThreadPoolExecutor` for concurrent agent operations

**Rationale**:
- Agents execute CLI subprocesses (I/O-bound, not CPU-bound) - threads sufficient
- ThreadPoolExecutor provides simple API: `submit()`, `as_completed()`, `wait()`
- Shared state (message queues, agent registry) easier with threads than separate processes
- No pickling required (unlike multiprocessing.Pool)
- Performance: 10+ concurrent threads executing subprocess calls is well-supported

**Best practices**:
- Create executor with `max_workers` matching desired concurrency (e.g., 10-15 agents)
- Use `submit()` to dispatch operations, `Future` objects to track completion
- Catch exceptions in futures: `future.exception()` for error handling
- Shutdown executor gracefully: `executor.shutdown(wait=True)`

**Implementation pattern**:
```python
from concurrent.futures import ThreadPoolExecutor, as_completed

executor = ThreadPoolExecutor(max_workers=10)
futures = []
for agent in agents:
    future = executor.submit(agent.execute_task, task)
    futures.append((agent.id, future))

for agent_id, future in as_completed([f for _, f in futures]):
    try:
        result = future.result()
    except Exception as e:
        # Handle agent error
```

**Alternatives considered**:
- `multiprocessing.Pool`: Separate processes for each agent - unnecessary overhead and complexity
- `asyncio` with async/await: Requires rewriting entire stack; threads simpler for subprocess-based model
- Sequential execution: No concurrency, violates performance requirements

### 4. pytest Real CLI Integration

**Decision**: Use pytest fixtures with real subprocess CLI invocations and shared test database

**Rationale**:
- Constitution principle: no mocks - tests must use real CLI subprocess calls
- Fixtures provide setup/teardown for test database and workspace cleanup
- Can reuse actual CLI implementation from `src/agent_interface/cli.py`

**Fixture pattern from pytest docs**:
```python
import pytest
import subprocess
import tempfile
import shutil

@pytest.fixture
def test_workspace():
    """Create isolated test workspace via real CLI."""
    result = subprocess.run(
        ["python", "src/agent_interface/cli.py", "workspace.create", "--workspace_id", "test_ws"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    yield "test_ws"
    # Cleanup: delete workspace
    subprocess.run(
        ["python", "src/agent_interface/cli.py", "workspace.delete", "--workspace_id", "test_ws"],
        capture_output=True
    )

def test_agent_creates_entity(test_workspace):
    # Test uses real CLI calls
    result = subprocess.run(
        ["python", "src/agent_interface/cli.py", "entity.create", "--type", "point", "--workspace_id", test_workspace, ...],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    response = json.loads(result.stdout)
    assert response["success"] is True
```

**Best practices**:
- Use `scope="function"` for per-test isolation (default)
- Use `scope="module"` for shared resources across test file
- Implement proper cleanup in fixture teardown (after yield)
- Use real database file for integration tests (not in-memory)

**Alternatives considered**:
- Mock subprocess calls: Violates constitution - forbidden
- Direct Python imports instead of CLI: Doesn't test real integration path agents use
- In-memory database: Doesn't match production SQLite file usage

### 5. Role-Based Access Control Patterns

**Decision**: Role templates as dataclasses with explicit `allowed_operations` and `forbidden_operations` lists

**Rationale**:
- Explicit is better than implicit (Zen of Python)
- Dataclasses provide structure with minimal boilerplate
- Allow-list approach (check if operation in `allowed_operations`) ensures security by default
- Easy to serialize role templates to JSON for documentation/configuration

**Implementation pattern**:
```python
from dataclasses import dataclass
from typing import List

@dataclass
class RoleTemplate:
    name: str
    description: str
    allowed_operations: List[str]  # e.g., ["entity.create_point", "entity.create_line"]
    forbidden_operations: List[str]  # e.g., ["solid.extrude", "solid.boolean"]
    example_tasks: List[str]

# Role enforcement
def enforce_role(agent, operation):
    if operation not in agent.role.allowed_operations:
        raise RoleViolationError(f"Agent {agent.id} with role {agent.role.name} cannot execute {operation}")
    if operation in agent.role.forbidden_operations:
        raise RoleViolationError(f"Operation {operation} explicitly forbidden for role {agent.role.name}")
```

**Best practices from Python patterns**:
- Use `dataclass` for structured data (not plain dicts)
- Explicit checks in controller before dispatching to subprocess
- Log all role violations for audit trail
- Return clear error messages citing specific role constraint

**Alternatives considered**:
- Decorator-based permissions: Requires modifying underlying CAD system (violates separation of concerns)
- Dynamic role checking at CLI level: Requires passing role in every CLI call (added complexity)
- Capability-based security: Over-engineered for simple role model

## Technology Decisions Summary

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Message Queue | `queue.Queue` (stdlib) | In-process, thread-safe, simple API, no dependencies |
| Subprocess Management | `subprocess.run()` with `capture_output=True` | Request-response pattern, timeout support, stderr capture |
| Concurrency | `concurrent.futures.ThreadPoolExecutor` | I/O-bound subprocess calls, shared state, simple API |
| Testing | pytest fixtures with real CLI subprocess calls | Real integration, proper setup/teardown, no mocks |
| Role Enforcement | Dataclasses with explicit allow/forbid lists | Explicit, serializable, security by default |

## Resolved Technical Context Unknowns

**Original**: NEEDS CLARIFICATION (message queue library: queue.Queue, asyncio.Queue, or other)
**Resolved**: `queue.Queue` - thread-safe in-process queue for agent-to-agent messages

All technology choices documented with rationale and alternatives considered. Ready for Phase 1 design.
