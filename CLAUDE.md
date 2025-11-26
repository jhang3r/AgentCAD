# multi-agent Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-11-25

**CRITICAL**: All development MUST comply with `.specify/memory/constitution.md`. This document provides runtime guidance; the constitution defines non-negotiable principles.

## Active Technologies
- Python 3.11+ + NEEDS CLARIFICATION (geometry kernel options: pythonOCC/Open CASCADE, CadQuery, Build3D, trimesh, or custom implementation) (001-cad-environment)
- File-based (workspace persistence, operation history logs, CAD file I/O) (001-cad-environment)
- Python 3.11+ + subprocess (JSON-RPC CLI invocation) + concurrent.futures.ThreadPoolExecutor (concurrent agents) + queue.Queue (agent-to-agent messaging) (002-multi-agent-framework)
- pytest (contract tests, integration tests with real CAD CLI, unit tests) (002-multi-agent-framework)
- Python 3.11+ (existing project standard) + pythonOCC-core (Open CASCADE Python bindings), numpy (geometry calculations) (003-geometry-kernel)
- Existing SQLite database (entities table, workspaces) (003-geometry-kernel)

## Project Structure

```text
src/
├── agent_interface/          # JSON-RPC CLI for CAD operations
├── cad_kernel/              # Core CAD functionality
├── constraint_solver/       # Constraint solving
├── file_io/                 # File I/O handlers
├── operations/              # CAD operations
├── multi_agent/             # Multi-agent framework (002-multi-agent-framework)
│   ├── controller.py
│   ├── roles.py
│   ├── messaging.py
│   ├── task_decomposer.py
│   └── cli.py
└── ...

tests/
├── contract/                # CAD API contract tests
├── integration/             # CAD integration tests
├── multi_agent_contract/    # Controller API contract tests (002-multi-agent-framework)
├── multi_agent_integration/ # Multi-agent integration tests (002-multi-agent-framework)
└── multi_agent_unit/        # Task decomposition unit tests (002-multi-agent-framework)
```

## Commands

```bash
# Run all tests
pytest

# Run CAD environment tests
pytest tests/contract/ tests/integration/

# Run multi-agent framework tests
pytest tests/multi_agent_*/

# Linting
cd src && ruff check .
```

## Code Style

Python 3.11+: Follow PEP 8 conventions, use dataclasses for structured data, type hints required

## Recent Changes
- 003-geometry-kernel: Added Python 3.11+ (existing project standard) + pythonOCC-core (Open CASCADE Python bindings), numpy (geometry calculations)
- 002-multi-agent-framework: Added Python 3.11+ + subprocess + concurrent.futures.ThreadPoolExecutor + queue.Queue for multi-agent CAD collaboration
- 002-multi-agent-framework: Added pytest integration tests with real CLI subprocess calls (no mocks)

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
