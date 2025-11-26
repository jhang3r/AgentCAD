# Data Model: 3D Geometry Kernel

**Date**: 2025-11-26
**Feature**: 3D Geometry Kernel
**Purpose**: Define data structures for geometry entities and operations

---

## Overview

This feature extends the existing CAD entity model with real 3D geometry capabilities. The data model maintains the existing entity/workspace structure while adding Open CASCADE shape storage and geometric property tracking.

---

## Core Entities

### GeometryShape

**Purpose**: Wrapper for Open CASCADE TopoDS_Shape with serialization

**Fields**:
- `shape_id`: str - Unique identifier (UUID)
- `shape_type`: str - Type (SOLID, SHELL, FACE, WIRE, EDGE, VERTEX, COMPOUND)
- `brep_data`: str - Serialized BRep string for shape reconstruction
- `is_valid`: bool - Result of BRepCheck_Analyzer validation
- `created_at`: datetime - Creation timestamp
- `workspace_id`: str - Owning workspace

**Methods**:
- `to_shape()`: TopoDS_Shape - Deserialize BRep to Open CASCADE shape
- `from_shape(shape)`: GeometryShape - Create from TopoDS_Shape
- `validate()`: bool - Run BRepCheck_Analyzer

**Relationships**:
- One-to-one with CAD Entity (solid type)

**Validation Rules**:
- brep_data must be valid BRep format
- Deserialize check: Must successfully reconstruct shape
- is_valid must match BRepCheck_Analyzer result

---

### SolidProperties

**Purpose**: Cached geometric properties for 3D solids

**Fields**:
- `entity_id`: str - Reference to CAD entity (foreign key)
- `volume`: float - Volume in cubic units
- `surface_area`: float - Total surface area in square units
- `center_of_mass_x`: float - COM X coordinate
- `center_of_mass_y`: float - COM Y coordinate
- `center_of_mass_z`: float - COM Z coordinate
- `bounding_box_min_x`: float
- `bounding_box_min_y`: float
- `bounding_box_min_z`: float
- `bounding_box_max_x`: float
- `bounding_box_max_y`: float
- `bounding_box_max_z`: float
- `face_count`: int - Number of faces in topology
- `edge_count`: int - Number of edges in topology
- `vertex_count`: int - Number of vertices in topology
- `is_closed`: bool - Whether solid is closed (manifold)
- `is_manifold`: bool - Whether solid is manifold
- `computed_at`: datetime - When properties were calculated

**Methods**:
- `compute_from_shape(shape)`: void - Calculate all properties from TopoDS_Shape
- `matches_tolerance(expected, tolerance)`: bool - Validate against expected values

**Relationships**:
- One-to-one with CAD Entity (solid type)
- Referenced by GeometryShape

**Validation Rules**:
- volume > 0 for valid solids
- surface_area > 0
- face_count >= 4 (minimum for closed solid: tetrahedron)
- is_closed must be True for solids
- Bounding box: min coordinates <= max coordinates

---

## Operation Entities

### CreationOperation

**Purpose**: Record of geometry creation operation execution

**Fields**:
- `operation_id`: str - Unique identifier
- `operation_type`: str - Type (EXTRUDE, REVOLVE, LOFT, SWEEP, PRIMITIVE, PATTERN, MIRROR)
- `input_entity_ids`: list[str] - Input entities (2D profiles, solids)
- `output_entity_id`: str - Resulting solid entity ID
- `parameters`: dict - Operation-specific parameters (JSON)
- `workspace_id`: str - Workspace where operation executed
- `agent_id`: str - Agent that executed operation
- `executed_at`: datetime
- `execution_time_ms`: int - Operation duration
- `success`: bool - Whether operation succeeded
- `error_message`: str | None - Error details if failed

**Parameter Schemas by Type**:

**EXTRUDE**:
```python
{
    "base_entity_id": str,  # 2D profile (circle, rectangle, wire)
    "direction": [x, y, z],  # Extrusion direction (normalized)
    "distance": float  # Extrusion distance
}
```

**REVOLVE**:
```python
{
    "profile_entity_id": str,
    "axis_point": [x, y, z],
    "axis_direction": [x, y, z],
    "angle_degrees": float  # Rotation angle
}
```

**LOFT**:
```python
{
    "profile_entity_ids": [str, str, ...],  # Ordered list of profiles
    "is_solid": bool,  # True for solid, False for shell
    "is_ruled": bool  # True for ruled, False for smooth
}
```

**SWEEP**:
```python
{
    "profile_entity_id": str,
    "path_entity_id": str  # Wire or edge defining path
}
```

**PRIMITIVE**:
```python
{
    "primitive_type": str,  # BOX, CYLINDER, SPHERE, CONE
    "dimensions": dict  # Type-specific dimensions
}
```

**PATTERN_LINEAR**:
```python
{
    "base_entity_id": str,
    "direction": [x, y, z],
    "spacing": float,
    "count": int
}
```

**PATTERN_CIRCULAR**:
```python
{
    "base_entity_id": str,
    "axis_point": [x, y, z],
    "axis_direction": [x, y, z],
    "count": int,
    "angle_degrees": float  # Total angle to distribute copies
}
```

**MIRROR**:
```python
{
    "base_entity_id": str,
    "mirror_plane_point": [x, y, z],
    "mirror_plane_normal": [x, y, z]
}
```

**Methods**:
- `validate_parameters()`: bool - Check parameter completeness
- `execute()`: str - Execute operation, return output entity ID

**Validation Rules**:
- input_entity_ids must reference existing entities
- parameters must match schema for operation_type
- execution_time_ms > 0 if success=True

---

### BooleanOperation

**Purpose**: Record of boolean operation execution

**Fields**:
- `operation_id`: str - Unique identifier
- `operation_type`: str - Type (UNION, SUBTRACT, INTERSECT)
- `operand1_entity_id`: str - First solid
- `operand2_entity_id`: str - Second solid
- `output_entity_id`: str - Resulting solid
- `workspace_id`: str
- `agent_id`: str
- `executed_at`: datetime
- `execution_time_ms`: int
- `success`: bool
- `error_message`: str | None

**Methods**:
- `validate_operands()`: bool - Check operands are valid solids
- `execute()`: str - Execute boolean operation

**Validation Rules**:
- operand1_entity_id and operand2_entity_id must reference existing solids
- For SUBTRACT: operand1 volume >= operand2 volume (optional warning)
- execution_time_ms > 0 if success=True

---

## Export Entities

### TessellationConfig

**Purpose**: Mesh quality configuration for STL export

**Fields**:
- `config_id`: str - Unique identifier
- `linear_deflection`: float - Max distance from surface (mm)
- `angular_deflection`: float - Max angular deviation (radians)
- `relative`: bool - Whether deflection is relative to shape size
- `is_default`: bool - Whether this is the default config

**Presets**:
- **preview**: linear=1.0mm, angular=1.0rad
- **standard**: linear=0.1mm, angular=0.5rad (default)
- **high_quality**: linear=0.01mm, angular=0.1rad

**Validation Rules**:
- linear_deflection > 0
- angular_deflection > 0
- Only one config can have is_default=True

---

### MeshData

**Purpose**: Tessellated mesh data for export

**Fields**:
- `mesh_id`: str - Unique identifier
- `entity_id`: str - Source solid entity
- `triangle_count`: int - Number of triangles
- `vertex_count`: int - Number of unique vertices
- `tessellation_config_id`: str - Config used for tessellation
- `mesh_size_bytes`: int - Approximate memory size
- `generated_at`: datetime

**Methods**:
- `to_stl(filepath)`: void - Export to STL file
- `validate_mesh()`: bool - Check mesh validity (closed, manifold)

**Relationships**:
- Many-to-one with CAD Entity (solid)
- Many-to-one with TessellationConfig

**Validation Rules**:
- triangle_count > 0
- vertex_count >= 3
- mesh_size_bytes > 0

---

## Database Schema Updates

### New Tables

**geometry_shapes**:
```sql
CREATE TABLE geometry_shapes (
    shape_id TEXT PRIMARY KEY,
    shape_type TEXT NOT NULL,
    brep_data TEXT NOT NULL,
    is_valid BOOLEAN NOT NULL,
    created_at TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(workspace_id)
);
```

**solid_properties**:
```sql
CREATE TABLE solid_properties (
    entity_id TEXT PRIMARY KEY,
    volume REAL NOT NULL,
    surface_area REAL NOT NULL,
    center_of_mass_x REAL NOT NULL,
    center_of_mass_y REAL NOT NULL,
    center_of_mass_z REAL NOT NULL,
    bounding_box_min_x REAL NOT NULL,
    bounding_box_min_y REAL NOT NULL,
    bounding_box_min_z REAL NOT NULL,
    bounding_box_max_x REAL NOT NULL,
    bounding_box_max_y REAL NOT NULL,
    bounding_box_max_z REAL NOT NULL,
    face_count INTEGER NOT NULL,
    edge_count INTEGER NOT NULL,
    vertex_count INTEGER NOT NULL,
    is_closed BOOLEAN NOT NULL,
    is_manifold BOOLEAN NOT NULL,
    computed_at TEXT NOT NULL,
    FOREIGN KEY (entity_id) REFERENCES entities(entity_id)
);
```

**creation_operations**:
```sql
CREATE TABLE creation_operations (
    operation_id TEXT PRIMARY KEY,
    operation_type TEXT NOT NULL,
    input_entity_ids TEXT NOT NULL,  -- JSON array
    output_entity_id TEXT NOT NULL,
    parameters TEXT NOT NULL,  -- JSON
    workspace_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    executed_at TEXT NOT NULL,
    execution_time_ms INTEGER NOT NULL,
    success BOOLEAN NOT NULL,
    error_message TEXT,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(workspace_id),
    FOREIGN KEY (output_entity_id) REFERENCES entities(entity_id)
);
```

**boolean_operations**:
```sql
CREATE TABLE boolean_operations (
    operation_id TEXT PRIMARY KEY,
    operation_type TEXT NOT NULL,
    operand1_entity_id TEXT NOT NULL,
    operand2_entity_id TEXT NOT NULL,
    output_entity_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    executed_at TEXT NOT NULL,
    execution_time_ms INTEGER NOT NULL,
    success BOOLEAN NOT NULL,
    error_message TEXT,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(workspace_id),
    FOREIGN KEY (operand1_entity_id) REFERENCES entities(entity_id),
    FOREIGN KEY (operand2_entity_id) REFERENCES entities(entity_id),
    FOREIGN KEY (output_entity_id) REFERENCES entities(entity_id)
);
```

**tessellation_configs**:
```sql
CREATE TABLE tessellation_configs (
    config_id TEXT PRIMARY KEY,
    linear_deflection REAL NOT NULL,
    angular_deflection REAL NOT NULL,
    relative BOOLEAN NOT NULL,
    is_default BOOLEAN NOT NULL
);
```

**mesh_data**:
```sql
CREATE TABLE mesh_data (
    mesh_id TEXT PRIMARY KEY,
    entity_id TEXT NOT NULL,
    triangle_count INTEGER NOT NULL,
    vertex_count INTEGER NOT NULL,
    tessellation_config_id TEXT NOT NULL,
    mesh_size_bytes INTEGER NOT NULL,
    generated_at TEXT NOT NULL,
    FOREIGN KEY (entity_id) REFERENCES entities(entity_id),
    FOREIGN KEY (tessellation_config_id) REFERENCES tessellation_configs(config_id)
);
```

### Existing Table Updates

**entities table** - Add column:
```sql
ALTER TABLE entities ADD COLUMN shape_id TEXT REFERENCES geometry_shapes(shape_id);
```

---

## State Transitions

### Solid Entity Lifecycle

```
┌─────────────────┐
│   2D Profile    │ (existing entity: circle, wire, etc.)
└────────┬────────┘
         │ Creation Operation (extrude, revolve, etc.)
         ▼
┌─────────────────┐
│  Solid Created  │ entity_type='solid', shape_id assigned
└────────┬────────┘
         │ Compute Properties
         ▼
┌─────────────────┐
│Properties Stored│ solid_properties record created
└────────┬────────┘
         │ Tessellate
         ▼
┌─────────────────┐
│  Mesh Generated │ mesh_data record created
└────────┬────────┘
         │ Export
         ▼
┌─────────────────┐
│   STL File      │ file system (*.stl)
└─────────────────┘
```

### Boolean Operation Flow

```
┌──────────┐     ┌──────────┐
│ Solid A  │     │ Solid B  │
└─────┬────┘     └────┬─────┘
      │               │
      └───────┬───────┘
              │ Boolean Operation (union/subtract/intersect)
              ▼
      ┌──────────────┐
      │  Result Solid │
      └──────────────┘
```

---

## Migration Strategy

1. **Phase 1**: Add new tables (geometry_shapes, solid_properties, operations)
2. **Phase 2**: Add shape_id column to entities table
3. **Phase 3**: Populate tessellation_configs with presets
4. **Phase 4**: No migration of existing data needed (no real 3D solids yet)

---

## Validation Summary

**Entity Validation**:
- All geometric properties must be positive for valid solids
- BRep data must successfully deserialize to TopoDS_Shape
- Solid must pass BRepCheck_Analyzer validation

**Operation Validation**:
- Input entities must exist in workspace
- Operation parameters must match schema
- Result must be valid solid (BRepCheck_Analyzer)

**Performance Validation**:
- Operations complete in <5s for solids up to 10,000 faces
- Property calculation completes in <1s
- Tessellation completes in <5s

---

## Success Criteria Mapping

| Success Criterion | Data Model Support |
|-------------------|-------------------|
| SC-001: STL viewable in 5s | mesh_data + export operations |
| SC-002: Properties within 0.1% | solid_properties validation |
| SC-003: Create/export in 2min | operation tracking + timing |
| SC-004: Smooth tessellation | tessellation_configs presets |
| SC-005: Boolean ops 100% success | boolean_operations error tracking |
| SC-006: 10k faces in 5s | operation execution_time_ms |
| SC-008: Dimensions within 0.01mm | solid_properties validation |
| SC-009: Revolve symmetry | Creation operation parameters |
| SC-010: Exact pattern count | Pattern operation validation |
