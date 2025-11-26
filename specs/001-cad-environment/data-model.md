# Data Model: AI Agent CAD Environment

**Feature**: `001-cad-environment`
**Date**: 2025-11-24
**Phase**: Phase 1 - Design

## Overview

This document defines the core data entities, their relationships, validation rules, and state transitions for the AI Agent CAD Environment. All entities support persistence, workspace isolation, and operation history tracking.

---

## Entity Hierarchy

```
GeometricEntity (abstract base)
├── Primitive2D
│   ├── Point2D
│   ├── Line2D
│   ├── Arc2D
│   ├── Circle2D
│   └── Spline2D
├── Primitive3D
│   ├── Point3D
│   ├── Line3D
│   ├── Plane
│   ├── Sphere
│   ├── Cylinder
│   ├── Cone
│   └── Torus
└── SolidBody
    ├── ExtrudedBody
    ├── RevolvedBody
    └── BooleanBody

Constraint
├── GeometricConstraint
│   ├── CoincidentConstraint
│   ├── ParallelConstraint
│   ├── PerpendicularConstraint
│   └── TangentConstraint
└── DimensionalConstraint
    ├── DistanceConstraint
    ├── AngleConstraint
    └── RadiusConstraint

Workspace
├── MainWorkspace
└── AgentWorkspace (branch)

Operation
└── OperationRecord

ValidationResult
├── TopologyValidation
├── GeometryValidation
└── ConstraintValidation
```

---

## Core Entities

### 1. GeometricEntity (Abstract Base)

**Description**: Base class for all CAD geometry objects. Provides common properties and lifecycle management.

**Attributes**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `entity_id` | `string` | Unique, immutable, format: `{workspace}:{type}_{uuid}` | Unique identifier across all workspaces |
| `entity_type` | `enum` | Required, values: `point`, `line`, `arc`, `circle`, `spline`, `plane`, `sphere`, `cylinder`, `cone`, `torus`, `solid` | Geometric type classification |
| `workspace_id` | `string` | Required, foreign key to `Workspace.workspace_id` | Owning workspace |
| `created_at` | `timestamp` | Required, ISO 8601 format | Entity creation time |
| `modified_at` | `timestamp` | Required, ISO 8601 format | Last modification time |
| `created_by_agent` | `string` | Required | Agent ID that created this entity |
| `parent_entities` | `array<string>` | Optional, entity IDs | Entities this was derived from (e.g., extrude from sketch) |
| `child_entities` | `array<string>` | Optional, entity IDs | Entities derived from this |
| `properties` | `object` | Required, type-specific | Geometric properties (coordinates, dimensions, etc.) |
| `bounding_box` | `BoundingBox` | Required | Axis-aligned bounding box |
| `is_valid` | `boolean` | Required, default: `true` | Topology/geometry validity status |
| `validation_errors` | `array<string>` | Optional | List of validation error codes if `is_valid` is `false` |

**Relationships**:
- **Workspace**: Many-to-one (many entities belong to one workspace)
- **Constraints**: Many-to-many (entities can be constrained to each other)
- **Operations**: One-to-many (entity created/modified by operations)

**Validation Rules**:
- `entity_id` must be unique across all workspaces
- `entity_type` must match the concrete class type
- `created_at` ≤ `modified_at`
- `bounding_box` must contain all entity geometry
- If `is_valid` is `false`, `validation_errors` must not be empty

**State Transitions**:
```
[Created] → [Modified] → [Deleted]
                ↓
           [Invalidated] ← (topology/geometry errors detected)
                ↓
           [Repaired] → [Modified]
```

---

### 2. Point2D / Point3D

**Description**: Point primitive in 2D or 3D space.

**Attributes** (extends `GeometricEntity`):

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `coordinates` | `array<float>` | Required, length: 2 (2D) or 3 (3D) | Point coordinates in workspace units (mm) |

**Validation Rules**:
- All coordinate values must be finite (no NaN, no Infinity)
- Coordinate values must be within workspace bounds: -1e6 to 1e6 mm

**Example**:
```json
{
  "entity_id": "main:point_a1b2c3",
  "entity_type": "point",
  "workspace_id": "main",
  "created_at": "2025-11-24T10:30:00Z",
  "modified_at": "2025-11-24T10:30:00Z",
  "created_by_agent": "agent_alpha",
  "parent_entities": [],
  "child_entities": [],
  "properties": {
    "coordinates": [0.0, 0.0, 0.0]
  },
  "bounding_box": {
    "min": [0.0, 0.0, 0.0],
    "max": [0.0, 0.0, 0.0]
  },
  "is_valid": true,
  "validation_errors": []
}
```

---

### 3. Line2D / Line3D

**Description**: Line segment defined by start and end points.

**Attributes** (extends `GeometricEntity`):

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `start_point` | `array<float>` | Required, length: 2 or 3 | Line start coordinates |
| `end_point` | `array<float>` | Required, length: 2 or 3 | Line end coordinates |
| `length` | `float` | Computed, > 0 | Euclidean distance between start and end |
| `direction_vector` | `array<float>` | Computed, normalized | Unit vector from start to end |

**Validation Rules**:
- `start_point` ≠ `end_point` (no degenerate lines with zero length)
- `length` must be ≥ 1e-6 mm (numerical tolerance threshold)
- All coordinates must be finite

**Derived Properties**:
- `length` = sqrt((end.x - start.x)² + (end.y - start.y)² + (end.z - start.z)²)
- `direction_vector` = (end - start) / length

---

### 4. Circle2D / Arc2D

**Description**: Circular curve in 2D plane.

**Attributes** (extends `GeometricEntity`):

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `center` | `array<float>` | Required, length: 2 or 3 | Circle center coordinates |
| `radius` | `float` | Required, > 0 | Circle radius in mm |
| `normal` | `array<float>` | Required for 3D, length: 3, normalized | Plane normal vector |
| `start_angle` | `float` | Optional (arc only), radians | Arc start angle (default: 0) |
| `end_angle` | `float` | Optional (arc only), radians | Arc end angle (default: 2π) |
| `area` | `float` | Computed (circle only) | Circle area = π × radius² |
| `arc_length` | `float` | Computed | Arc length or circumference |

**Validation Rules**:
- `radius` must be > 1e-6 mm (no degenerate circles)
- `radius` must be < 1e6 mm (workspace limit)
- For arcs: `start_angle` ≠ `end_angle`
- `normal` must be unit vector (length = 1.0)

**Derived Properties**:
- `area` = π × radius² (circle only)
- `arc_length` = radius × (end_angle - start_angle)
- `circumference` = 2π × radius (circle only)

---

### 5. SolidBody

**Description**: 3D solid with boundary representation (B-rep) topology.

**Attributes** (extends `GeometricEntity`):

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `volume` | `float` | Required, > 0 | Solid volume in mm³ |
| `surface_area` | `float` | Required, > 0 | Total surface area in mm² |
| `center_of_mass` | `array<float>` | Required, length: 3 | Centroid coordinates |
| `topology` | `Topology` | Required | B-rep topology structure |
| `material_properties` | `object` | Optional | Material density, properties |

**Topology** (nested object):

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `face_count` | `integer` | Required, ≥ 4 | Number of faces (min: tetrahedron) |
| `edge_count` | `integer` | Required, ≥ 6 | Number of edges |
| `vertex_count` | `integer` | Required, ≥ 4 | Number of vertices |
| `shell_count` | `integer` | Required, ≥ 1 | Number of shells (1 for simple solids) |
| `is_closed` | `boolean` | Required | True if all shells are closed |
| `is_manifold` | `boolean` | Required | True if no non-manifold edges/vertices |
| `euler_characteristic` | `integer` | Computed | V - E + F (should be 2 for simple solids) |

**Validation Rules**:
- `volume` > 1e-9 mm³ (no degenerate solids)
- `surface_area` > 1e-6 mm² (no degenerate surfaces)
- `topology.is_closed` must be `true` for valid solids
- `topology.is_manifold` must be `true` for valid solids
- `topology.face_count` ≤ 10,000 (workspace limit per spec)
- Euler characteristic: V - E + F = 2 (for simple solids without holes)

**State Transitions**:
```
[Sketch] → [Extruded] → [Modified (boolean)] → [Finalized (fillet/chamfer)]
```

---

### 6. Constraint

**Description**: Represents geometric or dimensional relationships between entities.

**Attributes**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `constraint_id` | `string` | Unique, immutable | Format: `{workspace}:constraint_{uuid}` |
| `constraint_type` | `enum` | Required | Values: `coincident`, `parallel`, `perpendicular`, `tangent`, `distance`, `angle`, `radius` |
| `workspace_id` | `string` | Required, foreign key | Owning workspace |
| `constrained_entities` | `array<string>` | Required, length: 1-2 | Entity IDs being constrained |
| `parameters` | `object` | Optional | Type-specific parameters (distance value, angle value, etc.) |
| `satisfaction_status` | `enum` | Required | Values: `satisfied`, `violated`, `redundant` |
| `degrees_of_freedom_removed` | `integer` | Required, ≥ 0 | DOF removed by this constraint |
| `created_at` | `timestamp` | Required | Constraint creation time |
| `created_by_agent` | `string` | Required | Agent that applied constraint |

**Constraint-Specific Parameters**:

**DistanceConstraint**:
```json
{
  "parameters": {
    "distance": 10.0,
    "unit": "mm",
    "tolerance": 0.01
  }
}
```

**AngleConstraint**:
```json
{
  "parameters": {
    "angle": 1.5708,
    "unit": "radians",
    "tolerance": 0.001
  }
}
```

**Validation Rules**:
- `constrained_entities` must reference existing, valid entities
- For `distance` constraints: `parameters.distance` ≥ 0
- For `angle` constraints: `parameters.angle` in range [0, 2π]
- For `radius` constraints: `parameters.radius` > 0
- `degrees_of_freedom_removed` ≤ 6 (max DOF for 3D object)
- Constraint must not create circular dependency graph

**State Transitions**:
```
[Created] → [Satisfied] → [Modified] → [Violated]
                ↓              ↓
           [Redundant]    [Re-Satisfied]
```

---

### 7. Workspace

**Description**: Isolated environment for agent operations with branching support.

**Attributes**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `workspace_id` | `string` | Unique, immutable | Format: `main` or `{agent_id}_{name}` |
| `workspace_name` | `string` | Required, unique | Human-readable name |
| `workspace_type` | `enum` | Required | Values: `main`, `agent_branch` |
| `base_workspace_id` | `string` | Optional, foreign key | Parent workspace (for branches) |
| `owning_agent_id` | `string` | Optional | Agent that owns this workspace (for branches) |
| `created_at` | `timestamp` | Required | Workspace creation time |
| `entity_count` | `integer` | Computed, ≥ 0 | Number of entities in workspace |
| `operation_count` | `integer` | Computed, ≥ 0 | Number of operations performed |
| `branch_status` | `enum` | Required | Values: `clean`, `modified`, `conflicted`, `merged` |
| `divergence_point` | `string` | Optional, operation ID | Last operation before branch diverged from base |

**Validation Rules**:
- `workspace_id` must be unique across all workspaces
- `main` workspace has no `base_workspace_id`
- Agent branches must have `owning_agent_id`
- `entity_count` ≤ 10,000 (workspace limit per spec)
- Cannot delete `main` workspace
- Cannot modify workspace with `branch_status` = `conflicted` until resolved

**State Transitions**:
```
[Created (clean)] → [Modified] → [Merged] → [Archived]
         ↓                ↓
    [Modified]    [Conflicted] → [Resolved] → [Merged]
```

---

### 8. Operation

**Description**: Record of a geometric operation performed by an agent.

**Attributes**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `operation_id` | `string` | Unique, immutable | Format: `op_{timestamp}_{uuid}` |
| `operation_type` | `enum` | Required | Values: `create`, `modify`, `delete`, `extrude`, `revolve`, `boolean`, `constrain`, etc. |
| `workspace_id` | `string` | Required, foreign key | Workspace where operation occurred |
| `agent_id` | `string` | Required | Agent that performed operation |
| `timestamp` | `timestamp` | Required, ISO 8601 | Operation execution time |
| `input_parameters` | `object` | Required | Operation-specific parameters |
| `input_entities` | `array<string>` | Optional | Entity IDs used as inputs |
| `output_entities` | `array<string>` | Optional | Entity IDs created/modified |
| `result_status` | `enum` | Required | Values: `success`, `error`, `warning` |
| `error_code` | `string` | Optional | Machine-readable error code if failed |
| `error_message` | `string` | Optional | Human-readable error message |
| `execution_time_ms` | `integer` | Required, ≥ 0 | Operation execution time in milliseconds |
| `undo_data` | `object` | Optional | Data needed to undo this operation |

**Validation Rules**:
- `operation_id` must be unique across all workspaces
- `timestamp` must be ≥ previous operation timestamp in workspace
- If `result_status` = `error`, `error_code` and `error_message` must be present
- `execution_time_ms` < 600,000 (10 minute timeout)
- `undo_data` must be present for undoable operations

**Example**:
```json
{
  "operation_id": "op_1732450200_a1b2c3",
  "operation_type": "create_circle",
  "workspace_id": "agent_alpha_practice",
  "agent_id": "agent_alpha",
  "timestamp": "2025-11-24T10:30:00Z",
  "input_parameters": {
    "center": [0, 0, 0],
    "radius": 5.0
  },
  "input_entities": [],
  "output_entities": ["agent_alpha_practice:circle_d4e5f6"],
  "result_status": "success",
  "error_code": null,
  "error_message": null,
  "execution_time_ms": 12,
  "undo_data": {
    "operation": "delete_entity",
    "entity_id": "agent_alpha_practice:circle_d4e5f6"
  }
}
```

---

### 9. ValidationResult

**Description**: Outcome of a validation check on geometry or constraints.

**Attributes**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `validation_id` | `string` | Unique | Format: `val_{timestamp}_{uuid}` |
| `validation_type` | `enum` | Required | Values: `topology`, `geometry`, `constraints` |
| `checked_entities` | `array<string>` | Required | Entity IDs that were validated |
| `timestamp` | `timestamp` | Required | Validation execution time |
| `overall_status` | `enum` | Required | Values: `pass`, `fail`, `warning` |
| `issues` | `array<Issue>` | Required | List of validation issues found |

**Issue** (nested object):

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `issue_code` | `string` | Required | Machine-readable code (e.g., `TOPO-001`) |
| `severity` | `enum` | Required | Values: `error`, `warning`, `info` |
| `entity_id` | `string` | Required | Affected entity |
| `description` | `string` | Required | Human-readable description |
| `suggested_fix` | `string` | Optional | Recommended correction |
| `auto_repairable` | `boolean` | Required | Can system automatically fix this? |

**Validation Issue Codes**:

| Code | Severity | Description |
|------|----------|-------------|
| `TOPO-001` | error | Non-manifold edge detected |
| `TOPO-002` | error | Non-manifold vertex detected |
| `TOPO-003` | warning | Open shell (not closed solid) |
| `TOPO-004` | error | Incorrect face orientation |
| `GEOM-001` | error | Degenerate edge (zero length) |
| `GEOM-002` | error | Degenerate face (zero area) |
| `GEOM-003` | warning | Self-intersection detected |
| `GEOM-004` | error | Invalid NURBS parameters |
| `CONST-001` | error | Over-constrained sketch |
| `CONST-002` | warning | Under-constrained sketch |
| `CONST-003` | error | Circular constraint dependency |
| `CONST-004` | error | Conflicting constraints |

---

## Relationships

### Entity-Constraint (Many-to-Many)

```
GeometricEntity ←→ Constraint
```

- A single entity can have multiple constraints applied to it
- A constraint can involve 1-2 entities (e.g., distance between two points)
- Junction table: `EntityConstraint`

### Entity-Operation (Many-to-Many)

```
GeometricEntity ←→ Operation
```

- Entities are created/modified by operations
- Operations can affect multiple entities
- Operations maintain input/output entity lists

### Workspace-Entity (One-to-Many)

```
Workspace 1→∞ GeometricEntity
```

- Each workspace contains many entities
- Each entity belongs to exactly one workspace
- Foreign key: `GeometricEntity.workspace_id`

### Workspace-Operation (One-to-Many)

```
Workspace 1→∞ Operation
```

- Each workspace has operation history
- Operations are workspace-scoped
- Foreign key: `Operation.workspace_id`

### Workspace Hierarchy (Tree Structure)

```
MainWorkspace
├── AgentWorkspace_A (branch)
├── AgentWorkspace_B (branch)
└── AgentWorkspace_C (branch)
```

- Main workspace is root
- Agent workspaces are branches
- Foreign key: `Workspace.base_workspace_id`

---

## Persistence Strategy

### Database Schema (SQLite for MVP)

**Tables**:
- `entities` (all geometric entities)
- `constraints` (constraint records)
- `entity_constraints` (junction table)
- `workspaces` (workspace metadata)
- `operations` (operation history)
- `validation_results` (validation records)

### File Storage

**Geometry Data**:
- OCCT BREP files (`.brep`) for each solid body
- Stored in: `{workspace_dir}/geometry/{entity_id}.brep`

**Workspace Structure**:
```
workspaces/
├── main/
│   ├── database.db
│   ├── geometry/
│   │   ├── solid_abc123.brep
│   │   └── solid_def456.brep
│   └── history/
│       └── operations.json
└── agent_alpha_practice/
    ├── database.db
    ├── geometry/
    └── history/
```

---

## Performance Considerations

### Indexing Strategy

**Primary Indexes**:
- `entities.entity_id` (unique, primary key)
- `entities.workspace_id` (foreign key index)
- `constraints.constraint_id` (unique, primary key)
- `operations.operation_id` (unique, primary key)
- `operations.workspace_id` + `operations.timestamp` (composite index for history queries)

**Secondary Indexes**:
- `entities.entity_type` (for type filtering)
- `entities.created_by_agent` (for agent tracking)
- `constraints.satisfaction_status` (for conflict detection)

### Caching Strategy

**Entity Property Cache**:
- Cache computed properties (volume, area, length) in memory
- Invalidate cache on entity modification
- TTL: Until entity modified or deleted

**Workspace Entity List Cache**:
- Cache entity IDs per workspace
- Invalidate on entity create/delete
- Reduces database queries for `workspace status` command

---

## Success Criteria Mapping

| Success Criteria | Data Model Support |
|------------------|-------------------|
| SC-001: Agents create 2D geometry | `Point2D`, `Line2D`, `Arc2D`, `Circle2D` entities |
| SC-002: Constraint satisfaction | `Constraint.satisfaction_status`, `ValidationResult` |
| SC-003: Solid modeling | `SolidBody.volume`, `SolidBody.topology` |
| SC-004: 10 concurrent agents | `Workspace` isolation, copy-on-write |
| SC-008: 100+ undo/redo | `Operation.undo_data`, operation history stack |
| SC-009: 100% conflict detection | `Workspace.branch_status`, merge conflict detection |
| SC-010: Agent learning | `Operation` logging with timestamps, status, execution time |

---

**Conclusion**: Data model supports all functional requirements (FR-001 through FR-038) and success criteria (SC-001 through SC-016). Ready to proceed with API contract generation.
