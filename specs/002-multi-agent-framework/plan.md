# Implementation Plan: Multi-Agent CAD Collaboration Framework

**Branch**: `002-multi-agent-framework` | **Date**: 2025-11-25 | **Spec**: specs/002-multi-agent-framework/spec.md
**Input**: Feature specification from `/specs/002-multi-agent-framework/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Multi-agent CAD collaboration framework enabling multiple AI agents to work simultaneously on CAD design tasks with role-based specialization (designer, modeler, validator, optimizer, integrator, constraint_solver). The framework provides agent orchestration, workspace isolation, role constraint enforcement, task decomposition, agent-to-agent messaging, and performance tracking. Built on top of existing CAD environment (001-cad-environment) using JSON-RPC CLI for all CAD operations.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: subprocess (JSON-RPC CLI invocation), concurrent.futures.ThreadPoolExecutor (concurrent agents), queue.Queue (agent-to-agent messaging)
**Storage**: File-based (shares existing SQLite database from CAD environment via JSON-RPC CLI), in-memory queue.Queue instances for agent communication
**Testing**: pytest (contract tests for controller API, integration tests with real CAD CLI, unit tests for task decomposition logic)
**Target Platform**: Local machine (Windows/Linux/macOS), single-process controller with subprocess agent invocations
**Project Type**: Single library project with CLI interface
**Performance Goals**: <100ms latency for simple CAD operations via JSON-RPC, <5 seconds for workspace merge with 100 entities, support 10+ concurrent agents, <2 seconds for task decomposition
**Constraints**: All agents local (not distributed), JSON-RPC subprocess communication overhead, SQLite WAL mode concurrency limits, <15% controller overhead vs single-agent operation
**Scale/Scope**: 10+ concurrent agents, 6 role templates, 3+ collaborative scenarios, 100+ entities per workspace merge, 100 messages/second agent-to-agent throughput

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with `.specify/memory/constitution.md` principles:

- [x] **Multi-Agent Architecture**: This feature IS the multi-agent architecture itself - enables coordination across agents for CAD design tasks
- [x] **No Mocks/Stubs**: All agent operations use real JSON-RPC CLI subprocess calls to actual CAD environment, real SQLite database, real file I/O, real in-memory message queues
- [x] **Verifiable Completion**: Tasks will have binary criteria - controller API works with real CLI invocations, role constraints block unauthorized operations, workspace merges preserve all entities, performance metrics match actual measurements
- [x] **Test Reality**: Test strategy prioritizes (1) contract tests for controller API and role templates, (2) integration tests with real CAD CLI subprocess calls and real database, (3) unit tests only for task decomposition algorithms using real role definitions
- [x] **Documentation-Driven**: Tools requiring documentation review: Python subprocess module (process management patterns), Python multiprocessing (concurrent agent patterns), message queue library selection (queue.Queue vs asyncio.Queue vs alternatives), pytest (test fixtures for real CLI integration)
- [x] **Live Error Reporting**: Development environment will use pytest with real-time output, subprocess stderr/stdout capture for CLI errors, Python exception handling with immediate logging
- [x] **Library-First**: Controller designed as standalone library (`multi_agent_controller.py`) with CLI interface for orchestration commands, importable by other systems
- [x] **3D CAD Ownership**: Uses existing owned CAD system (001-cad-environment) via JSON-RPC CLI - no third-party CAD dependencies

**Justification for Any Violations**: No violations. All principles satisfied.

---

**POST-DESIGN RE-EVALUATION** (after Phase 1 completion):

- [x] **Multi-Agent Architecture**: ✅ CONFIRMED - Design includes controller, agents, roles, messaging - full multi-agent coordination
- [x] **No Mocks/Stubs**: ✅ CONFIRMED - data-model.md, contracts, and quickstart all specify real subprocess.run() calls to CLI, real queue.Queue instances, real database via JSON-RPC
- [x] **Verifiable Completion**: ✅ CONFIRMED - Tasks will verify: real CLI invocations work, role constraints block operations, workspace merges succeed, metrics match actual counts
- [x] **Test Reality**: ✅ CONFIRMED - Test structure defines contract tests (controller API), integration tests (real subprocess CLI calls), unit tests (task decomposition with real role definitions)
- [x] **Documentation-Driven**: ✅ CONFIRMED - research.md documents subprocess, concurrent.futures, queue.Queue, pytest - all with rationale from documentation
- [x] **Live Error Reporting**: ✅ CONFIRMED - Design includes subprocess stderr/stdout capture, pytest real-time output, exception logging
- [x] **Library-First**: ✅ CONFIRMED - Project structure shows src/multi_agent/ module with controller.py, roles.py, messaging.py, task_decomposer.py, cli.py
- [x] **3D CAD Ownership**: ✅ CONFIRMED - All CAD operations via JSON-RPC CLI to owned CAD system (001-cad-environment)

**Design Phase Conclusion**: No new violations introduced. All principles remain satisfied after completing Phase 0 research and Phase 1 design. Ready for Phase 2 (task generation via /speckit.tasks).

## Project Structure

### Documentation (this feature)

```text
specs/002-multi-agent-framework/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
# Multi-agent framework modules (new for this feature)
multi_agent_controller.py      # Main controller orchestrating agents
agent_templates.py             # Role template definitions (designer, modeler, etc.)

src/
├── agent_interface/          # Existing: JSON-RPC CLI for CAD operations
│   ├── cli.py               # Existing: CLI entry point used by agents
│   ├── agent_metrics.py     # Existing: Performance tracking
│   └── ...
├── cad_kernel/              # Existing: Core CAD functionality
│   ├── workspace.py         # Existing: Workspace isolation/merge
│   └── ...
├── multi_agent/             # NEW: Multi-agent framework library
│   ├── __init__.py
│   ├── controller.py        # Agent lifecycle, task assignment
│   ├── roles.py             # Role constraint enforcement
│   ├── messaging.py         # Agent-to-agent communication
│   ├── task_decomposer.py   # High-level goal → subtasks
│   └── cli.py               # Multi-agent CLI interface
└── ...

tests/
├── contract/                # Existing: API contract tests
│   └── ...
├── integration/             # Existing: Integration tests with real DB
│   └── ...
├── multi_agent_contract/    # NEW: Controller API contract tests
│   ├── test_agent_create.py
│   ├── test_role_enforcement.py
│   ├── test_task_assignment.py
│   └── test_messaging.py
├── multi_agent_integration/ # NEW: Multi-agent integration tests
│   ├── test_concurrent_agents.py
│   ├── test_workspace_merge_workflow.py
│   ├── test_collaborative_scenarios.py
│   └── test_real_cli_invocation.py
└── multi_agent_unit/        # NEW: Unit tests for task decomposition
    └── test_task_decomposition.py
```

**Structure Decision**: Single project structure with new `src/multi_agent/` module for framework code. The multi-agent framework is a library that orchestrates agents via subprocess invocations of the existing JSON-RPC CLI (`src/agent_interface/cli.py`). Top-level files (`multi_agent_controller.py`, `agent_templates.py`) provide convenience entry points and will be refactored into `src/multi_agent/` module during implementation.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
