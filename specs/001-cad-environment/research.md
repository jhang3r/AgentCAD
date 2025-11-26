# Research: AI Agent CAD Environment

**Feature**: `001-cad-environment`
**Date**: 2025-11-24
**Phase**: Phase 0 - Technical Research

## Overview

This document consolidates research findings for building a CAD practice environment where AI agents can create geometry, apply constraints, perform solid modeling, and receive real-time feedback through a text-based CLI interface.

---

## 1. Geometry Kernel Selection

### Decision: OpenCascade Technology (OCCT) as Foundation

**Selected Approach**: Build on OCCT v7.x+ as the geometry kernel with Python bindings (build123d or pythonOCC).

### Rationale

1. **Constitutional Alignment**: Using OCCT aligns with Principle VIII (Owned 3D CAD System):
   - LGPL 2.1 license permits commercial use without fees
   - Full source code access for inspection and modification
   - Ownership of application layer, workflows, and agent integration
   - Building a robust B-rep kernel from scratch requires ~10 years of expert development time

2. **Comprehensive Feature Coverage**:
   - 2D/3D primitives (points, lines, arcs, circles, splines, planes, spheres, cylinders, etc.)
   - Solid modeling (extrude, revolve, boolean operations, fillet, chamfer)
   - Native STEP, STL support; DXF via add-on or ezdxf
   - Boundary representation with NURBS curves/surfaces
   - Built-in topology validation (BRepCheck_Analyzer)

3. **Performance Characteristics**:
   - Simple operations: <<100ms (typically 5-15ms)
   - Complex operations: <1s for models under 1000 faces
   - Production-proven in FreeCAD, KiCad, SALOME

4. **Active Development**:
   - Professionally maintained by Open Cascade SAS
   - Latest commits as of November 2025
   - Large ecosystem (~30 open-source projects)

5. **Python Integration**:
   - **build123d**: Modern, clean Pythonic API on OCCT
   - **pythonOCC-core**: Direct OCCT bindings for low-level access
   - Enables rapid CLI development for agent interface

### Alternatives Considered

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **CGAL** | Strong computational geometry algorithms, header-only | Not a CAD kernel, no native solid modeling, no STEP support | Insufficient for CAD workflows |
| **libfive** | Innovative f-rep approach, GPU rendering | No explicit topology (no entity IDs), incompatible with STEP, no constraint solver | Too different from traditional CAD |
| **SolveSpace** | Integrated constraint solver, lightweight | Limited NURBS, no STEP import, GPL 3.0 license | Too limited for comprehensive environment |
| **Build from Scratch** | Complete control | 10+ year timeline, requires deep expertise, high risk | Impractical for project goals |

### Implementation Recommendation

**Hybrid Python Approach**:
- **Primary**: build123d for high-level geometric operations and CLI
- **Secondary**: pythonOCC-core for low-level OCCT access when needed
- **Performance**: Profile and rewrite bottlenecks in C++ if necessary

---

## 2. Constraint Solver Architecture

### Decision: Newton-Raphson Method with Decomposition

**Selected Approach**: Implement custom constraint solver layer on top of OCCT using Newton-Raphson with graph-based decomposition.

### Rationale

1. **OCCT Limitation**: OCCT does not include parametric constraint solver (focuses on geometry kernel only)
2. **Industry Standard**: Newton-Raphson used in Pro/Engineer, SolidWorks, and other commercial CAD systems
3. **Fast Convergence**: Newton-Raphson provides quadratic convergence near solutions

### Constraint Solving Strategy

**Core Algorithm**:
1. Represent constraints as systems of nonlinear equations
2. Use sparse matrix techniques for large constraint systems (hundreds of unknowns)
3. Implement rank-revealing LU or QR factorizations (as used in SolveSpace)
4. Decompose constraint graphs into solvable subsystems
5. Combine Newton-Raphson (fast) with Homotopy methods (better convergence from poor initial guesses)

**Degrees of Freedom Analysis**:
- Use Jacobian matrix rank analysis to detect under/over-constrained systems
- Report specific DOFs (which entities can move, in what directions)

**Reference Implementation**: SolveSpace's constraint solver (libslvs) available as standalone library and could be integrated with OCCT.

### Supported Constraints (from spec FR-008)

- Coincident
- Parallel
- Perpendicular
- Tangent
- Distance (point-point, point-line, point-plane)
- Angle (line-line)
- Radius (circle, arc)

---

## 3. CLI Interface Design

### Decision: NDJSON JSON-RPC with Noun-Verb Commands

**Selected Approach**: Newline-delimited JSON (NDJSON) transport with JSON-RPC 2.0 protocol over stdin/stdout.

### Command Structure

**Pattern**: `<resource> <action> [--param value] [--json '{}']`

**Examples**:
```bash
entity create point --x 0 --y 0 --z 0
entity create circle --center-x 0 --center-y 0 --radius 5
entity query circle_123 --properties all
constraint apply perpendicular --entities line_1,line_2
solid extrude sketch_45 --distance 10
workspace create --name agent_practice_01
workspace merge --source agent_practice_01 --target main
file import step --path model.step --validate
file export stl --entities solid_123 --path output.stl
history undo
history redo
```

### Rationale

1. **Noun-Verb Pattern**:
   - REST-like semantics familiar to AI agents
   - Groups related operations (`entity create`, `entity query`)
   - Extensible without affecting existing commands

2. **GNU-Style Long Options**:
   - Self-documenting for agent log analysis
   - No parameter order dependencies
   - Supports JSON parameter injection: `--json '{"center":[0,0],"radius":5}'`

3. **NDJSON + JSON-RPC**:
   - Line-oriented: agents can `readline()` and parse incrementally
   - No buffering required (unlike traditional JSON)
   - Standard protocol with request/response correlation via `id` field
   - Streaming-native for progress updates
   - Grep-friendly logs

### Response Schema

**Success Response**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "status": "success",
    "operation": {
      "type": "entity.create.circle",
      "execution_time_ms": 12
    },
    "data": {
      "entity_id": "circle_789",
      "type": "circle",
      "properties": {
        "center": [0, 0, 0],
        "radius": 5,
        "area": 78.54
      }
    }
  }
}
```

**Error Response**:
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "error": {
    "code": "INVALID_PARAMETER",
    "message": "Radius must be greater than zero",
    "data": {
      "field": "radius",
      "provided_value": -5,
      "constraints": {"min": 0.001, "max": 1000000},
      "suggestion": "Specify --radius with a positive value",
      "recoverable": true
    }
  }
}
```

**Progress Response** (for operations >1s):
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "status": "progress",
    "percent": 45,
    "stage": "computing_intersections",
    "estimated_time_remaining_ms": 850
  }
}
```

---

## 4. Workspace Isolation & Branching

### Decision: Git-Inspired Branching with Copy-on-Write

**Selected Approach**: Isolated workspaces per agent using copy-on-write geometry storage with three-way merge for conflict detection.

### Architecture

```
Main Workspace (Shared Reference Geometry)
├── Agent A Workspace (Branch)
├── Agent B Workspace (Branch)
└── Agent C Workspace (Branch)
```

### Key Mechanisms

1. **Process-Level Isolation**: Each agent runs separate CLI process with its own workspace
2. **Entity ID Namespacing**: `main:circle_123`, `agent_a:circle_124`
3. **Copy-on-Write**: Agents share read-only references; modifications create workspace-local copies
4. **Lock-Free Concurrency**: No global locks; conflicts detected only during merge

### Workspace Commands

```bash
workspace create --name agent_a_practice --base main
workspace switch --name agent_a_practice
workspace list --show-status
workspace status
workspace merge --source agent_a_practice --target main --strategy auto
```

### Merge Conflict Detection

**Three-Way Merge**: Compare entity versions across base, source, and target workspaces.

**Conflict Response**:
```json
{
  "status": "error",
  "error": {
    "code": "MERGE_CONFLICT",
    "conflicts": [
      {
        "entity_id": "circle_123",
        "base_version": {"radius": 5},
        "source_version": {"radius": 7},
        "target_version": {"radius": 10},
        "resolution_options": ["keep_source", "keep_target", "manual_merge"]
      }
    ]
  }
}
```

### Performance Optimizations

- **Lazy Loading**: Load geometry only when accessed
- **Differential Storage**: Store only changes relative to base workspace
- **Parallel Processing**: Operations in separate workspaces use separate CPU cores
- **Shared Geometry Cache**: Read-only geometry shared via memory-mapped files

**Target**: 10 concurrent agents without performance degradation

---

## 5. File Interoperability

### 5.1 STEP Import/Export

**Decision**: Use OCCT's STEPControl_Reader and STEPControl_Writer

**Supported Application Protocols**:
- AP203 (Configuration controlled 3D designs)
- AP214 (Automotive design)
- AP242 (Managed model-based 3D engineering)

**Validation Strategy**:
1. **File Format Validation**: STEP Part 21 structure compliance
2. **Entity Reconstruction**: Parse and convert to OCCT BRep
3. **Topology Validation**: BRepCheck_Analyzer (manifold, orientation, closed shells)
4. **Geometry Validation**: Check NURBS validity, degenerate entities
5. **Semantic Validation**: Compare validation properties (volume, center of gravity)

**Key Classes**:
- `STEPControl_Reader`: STEP parsing
- `BRepCheck_Analyzer`: Topology validation
- `ShapeFix_Shape`: Automated repair toolkit
- `BRepGProp`: Geometric properties calculation

### 5.2 STL Export

**Decision**: Use OCCT's StlAPI_Writer with configurable tessellation

**Tessellation Parameters**:
```python
tessellation_config = {
    "linear_deflection": 0.1,    # Max distance between mesh and surface (mm)
    "angular_deflection": 0.5,   # Max angle between adjacent normals (radians)
    "relative_mode": True,       # Scale deflection by object size
    "binary": True               # Binary STL (smaller) vs ASCII
}
```

**Validation & Reporting**:
- Triangle count
- Volume/surface area comparison with original solid
- Approximation error percentage
- Manifold mesh verification
- Data loss warnings (exact geometry → mesh approximation)

### 5.3 DXF Import/Export

**Decision**: Use ezdxf (MIT license) for Python-native DXF handling

**Rationale**:
- Pure Python (no compilation dependencies)
- Comprehensive version support (R12 through R2018)
- Read & write capability
- Excellent documentation

**Fallback**: OCCT DXF Import-Export SDK for complex 3D conversions

**Validation**:
1. Format validation (DXF version detection)
2. Layer inventory
3. Entity type support checking
4. Coordinate bounds validation
5. Unit system detection
6. Degenerate geometry detection

### 5.4 Data Loss Detection

**Conversion Impact**:

| Conversion | Loss Type | Detectable | Reversible |
|------------|-----------|------------|------------|
| STEP → STL | Exact → Mesh approximation | Yes (volume/area comparison) | No (lossy) |
| STEP → DXF (2D) | 3D solid → 2D projection | Yes (dimension reduction) | No |
| DXF → STEP | 2D → 3D interpretation ambiguity | Yes (missing Z-axis) | Requires clarification |

**Detection Strategies**:
1. **Validation Properties Comparison**: Compare volume, surface area, center of gravity before/after
2. **Entity Type Analysis**: Track entity type mappings (surfaces → triangles)
3. **Capability Matrix Warnings**: Pre-conversion warnings based on format capabilities
4. **Round-Trip Testing**: Export then re-import to detect approximation errors

---

## 6. Real-Time Feedback Mechanisms

### Performance Targets

| Operation Type | Target | Typical |
|----------------|--------|---------|
| Simple (create point/line) | <100ms | 5-15ms |
| Complex (boolean, constraint) | <1000ms | 200-600ms |
| File import (<10MB STEP) | <5000ms | ~3000ms |

### Streaming Progress Protocol

**For operations >1s**: Stream NDJSON progress updates

```bash
# Agent sends request
echo '{"jsonrpc":"2.0","method":"solid.boolean.union","params":{"body1":"solid_123","body2":"solid_456"},"id":42}' | cad_cli

# CLI streams responses
{"jsonrpc":"2.0","id":42,"result":{"status":"progress","percent":20,"stage":"face_intersection"}}
{"jsonrpc":"2.0","id":42,"result":{"status":"progress","percent":50,"stage":"topology_validation"}}
{"jsonrpc":"2.0","id":42,"result":{"status":"success","data":{"entity_id":"solid_789","volume":1234.5}}}
```

### Operation Logging

**All operations logged with**:
- Operation ID
- Agent ID
- Workspace
- Timestamp
- Operation type
- Inputs/outputs
- Status (success/error)
- Execution time

**Purpose**: Enable agent learning analysis and success pattern recognition

### Undo/Redo History

**Command Pattern Implementation**:
- Maintain operation stack per workspace (100+ operations per spec SC-008)
- Store lightweight command representation (not full geometry state)
- Support replay from clean state for undo/redo
- Enable history export as reusable scripts

**Commands**:
```bash
history list --limit 10
history undo
history redo
history goto --command-id cmd_1234
history diff --command-id cmd_1230
```

---

## 7. Error Handling & Agent Learning

### Error Classification

**Client Errors**:
- `INVALID_COMMAND`: Unrecognized command
- `INVALID_PARAMETER`: Parameter validation failed
- `MISSING_PARAMETER`: Required parameter not provided
- `ENTITY_NOT_FOUND`: Referenced entity doesn't exist
- `CONSTRAINT_CONFLICT`: Constraint violates existing constraints

**Server Errors**:
- `GEOMETRY_ENGINE_ERROR`: CAD kernel internal error
- `INSUFFICIENT_MEMORY`: Out of memory
- `TIMEOUT`: Operation exceeded time limit
- `TOPOLOGY_ERROR`: Generated invalid topology

**Logical Errors**:
- `OPERATION_INVALID`: Operation logically impossible
- `WORKSPACE_CONFLICT`: Merge conflict detected
- `CIRCULAR_DEPENDENCY`: Constraint circular reference

### Error Recovery Pattern

**All errors include**:
- `code`: Machine-readable error code
- `message`: Human-readable description
- `field`: Which parameter caused the error
- `provided_value`: What the agent sent
- `constraints`: Valid parameter range
- `suggestion`: Concrete correction suggestion
- `recoverable`: Boolean indicating if retry is viable

**Agent Self-Correction** (per spec SC-006):
- Agents should correct 90%+ of invalid operations on next attempt using error suggestions
- Agents should reduce error rate by 50%+ after 100 operations (SC-011)
- System provides feedback enabling self-correction within 3 attempts for 80%+ of failures (SC-013)

---

## 8. Technology Stack Summary

| Component | Technology | Version | License |
|-----------|-----------|---------|---------|
| **Geometry Kernel** | OpenCascade Technology (OCCT) | 7.8+ | LGPL 2.1 |
| **Python Bindings** | build123d | Latest | Apache 2.0 |
| **Low-Level Access** | pythonOCC-core | 7.8+ | LGPL 2.1 |
| **STEP Import/Export** | OCCT STEPControl | Native | LGPL 2.1 |
| **STL Export** | OCCT StlAPI | Native | LGPL 2.1 |
| **DXF Import/Export** | ezdxf | 1.3+ | MIT |
| **CLI Framework** | Python argparse/Click | Native/Latest | PSF/BSD |
| **JSON Handling** | Python json | Native | PSF |
| **Constraint Solver** | Custom (Newton-Raphson) | N/A | Custom |

---

## 9. Development Phases

### Phase 0: Proof of Concept (1-2 weeks)
- Install build123d and pythonOCC
- Implement basic CLI for 5-10 primitive operations
- Validate performance targets (<100ms simple ops)
- Test STEP/STL import/export

### Phase 1: Core Geometry Engine (4-6 weeks)
- Complete 2D/3D primitive operations
- Entity management with persistent IDs
- Geometric property calculations
- Workspace isolation and basic branching
- Operation logging and history

### Phase 2: Constraint Solver (6-8 weeks)
- Newton-Raphson constraint solver implementation
- Constraint graph analysis and decomposition
- Degrees of freedom detection
- Constraint conflict reporting
- OCCT geometry update integration

### Phase 3: Solid Modeling Operations (4-6 weeks)
- Extrude and revolve operations
- Boolean operations with validation
- Fillet and chamfer
- Topology checking and healing
- Mass properties calculation

### Phase 4: Multi-Agent Support (3-4 weeks)
- Concurrent workspace management
- Workspace merge and conflict detection
- Shared reference geometry
- Optimization for 10+ concurrent agents

### Phase 5: Agent Feedback & Learning (3-4 weeks)
- Structured error reporting with suggestions
- Operation success tracking and metrics
- Test scenario validation system
- Performance profiling for agent self-assessment

**Total Estimated Timeline**: 20-30 weeks for MVP

---

## 10. Constitution Compliance Verification

### Principle I: Multi-Agent Architecture
✅ **COMPLIANT**: Feature designed for multiple agents (planning, implementation, testing) coordinating through workspace system.

### Principle II: No Mocks/Stubs
✅ **COMPLIANT**: All implementations will use real OCCT geometry kernel, real file I/O, real databases for operation history. No mocks in tests.

### Principle III: Verifiable Task Completion
✅ **COMPLIANT**: All tasks will be verified against success criteria (operations succeed, tests pass, agents achieve learning metrics).

### Principle IV: Test Reality
✅ **COMPLIANT**: Tests will focus on:
- Contract tests (CLI command/response schemas)
- Integration tests (geometry operations with real OCCT kernel)
- Agent journey tests (multi-operation workflows)

### Principle V: Documentation-Driven Development
✅ **COMPLIANT**: Research phase complete with extensive documentation review. All OCCT APIs, file format specs, and constraint solving papers referenced.

### Principle VI: Live Error Reporting
✅ **COMPLIANT**: All errors streamed via stdout/stderr in structured JSON. Agents receive errors immediately without asking.

### Principle VII: Library-First Architecture
✅ **COMPLIANT**: CAD environment structured as standalone library with:
- Clear purpose (agent CAD practice environment)
- Self-contained implementation (OCCT + custom constraint solver)
- CLI interface for standalone execution
- Independent test suite

### Principle VIII: Owned 3D CAD System
✅ **COMPLIANT**: Using OCCT as foundation but owning:
- Application layer (CLI, agent interface)
- Constraint solver implementation
- Workspace management and branching
- Operation history and learning systems
- File validation and error reporting logic

**Justification**: Building B-rep kernel from scratch requires 10+ years. OCCT provides geometry primitives while we own all agent-facing functionality, workflows, and learning systems. This balances practical delivery with ownership principle.

---

## References

### Geometry Kernels
- [Open CASCADE Technology Portal](https://dev.opencascade.org/)
- [CGAL: The Computational Geometry Algorithms Library](https://www.cgal.org/)
- [libfive: Infrastructure for solid modeling](https://libfive.com/)
- [SolveSpace - Technology](https://solvespace.github.io/solvespace-web/tech.html)

### Constraint Solving
- [Geometric constraint solving - Wikipedia](https://en.wikipedia.org/wiki/Geometric_constraint_solving)
- [A review on geometric constraint solving (arXiv)](https://arxiv.org/abs/2202.13795)

### CLI Design & Protocols
- [Command Line Interface Guidelines](https://clig.dev/)
- [JSON-RPC 2.0 Specification](https://www.jsonrpc.org/specification)
- [NDJSON - Newline Delimited JSON](http://ndjson.org/)

### CAD File Formats
- [STEPcode Documentation](https://stepcode.github.io/docs/home/)
- [ezdxf Documentation](https://ezdxf.readthedocs.io/)
- [Open CASCADE STEP Translator](https://dev.opencascade.org/doc/overview/html/occt_user_guides__step.html)

### Workspace Management
- [Git-Style Version Control for CAD](https://www.onshape.com/en/blog/git-style-version-control-cad-data-management)
- [11 Ways CAD Teams Can Leverage Branching and Merging](https://www.onshape.com/en/blog/use-cases-branching-merging)

### Python CAD Libraries
- [build123d GitHub Repository](https://github.com/gumyr/build123d)
- [CadQuery Documentation](https://cadquery.readthedocs.io/en/latest/)
- [pythonOCC GitHub Repository](https://github.com/tpaviot/pythonocc-core)

---

**Conclusion**: All technical unknowns from plan template resolved. Ready to proceed to Phase 1 (Design & Contracts).
