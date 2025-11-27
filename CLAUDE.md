# multi-agent Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-11-26

**CRITICAL**: All development MUST comply with `.specify/memory/constitution.md`. This document provides runtime guidance; the constitution defines non-negotiable principles.

## Active Technologies
- Python 3.11+ + pythonOCC-core 7.9.0 (Open CASCADE Python bindings) (001-cad-environment, 003-geometry-kernel)
- File-based (workspace persistence, operation history logs, CAD file I/O: STEP, STL) (001-cad-environment, 003-geometry-kernel)
- Python 3.11+ + subprocess (JSON-RPC CLI invocation) + concurrent.futures.ThreadPoolExecutor (concurrent agents) + queue.Queue (agent-to-agent messaging) (002-multi-agent-framework)
- pytest (contract tests, integration tests with real CAD CLI, unit tests) (002-multi-agent-framework)
- Python 3.11+ + pythonOCC-core 7.9.0 + numpy (geometry calculations and tessellation) (003-geometry-kernel)
- SQLite database with geometry tables (entities, workspaces, geometry_shapes, solid_properties, creation_operations, boolean_operations, tessellation_configs, mesh_data) (003-geometry-kernel)

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
- 003-geometry-kernel Phase 5 COMPLETE: Boolean operations (union, subtract, intersect) fully implemented!
  - Boolean ops module (src/cad_kernel/boolean_ops.py) with BRepAlgoAPI_Fuse/Cut/Common
  - Edge refinement (RefineEdges, FuseEdges) for cleaner geometry
  - Pre/post validation with BRepCheck_Analyzer
  - Three CLI handlers: solid.boolean.union, solid.boolean.subtract, solid.boolean.intersect
  - BooleanOperation records logged to database with execution tracking
  - ✅ Ready for testing: Create overlapping solids, perform boolean operations
- 003-geometry-kernel Phase 3 COMPLETE: STEP + STL export fully functional with real geometry!
  - STEP export: STEPControl_Writer with AP203/AP214/AP242 schema support (preserves exact BRep)
  - STL export: Real tessellation using BRepMesh_IncrementalMesh with 3 quality presets
  - Export manager coordinates both formats, retrieves geometry from database
  - CLI handler updated to support both formats via file.export
  - ✅ Verified: 20×30×40mm box exports to 15KB STEP file + 684 byte STL (12 triangles)
- 003-geometry-kernel Phase 2 COMPLETE: Database migration with 6 new geometry tables, GeometryShape class (BRep serialization), SolidProperties class (OCCT property computation)
- 003-geometry-kernel: Confirmed pythonOCC-core 7.9.0 via conda, BRep serialization tested and working
- 002-multi-agent-framework: Added Python 3.11+ + subprocess + concurrent.futures.ThreadPoolExecutor + queue.Queue for multi-agent CAD collaboration
- 002-multi-agent-framework: Added pytest integration tests with real CLI subprocess calls (no mocks)

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
