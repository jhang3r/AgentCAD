# Contract: Creation Operations API

**Version**: 1.0.0
**Date**: 2025-11-26
**Purpose**: Define CLI contracts for 3D solid creation operations

---

## Overview

Creation operations transform 2D profiles into 3D solids or create primitive solids from parameters. All operations follow the pattern:
1. Validate input entities exist and are correct type
2. Execute Open CASCADE operation
3. Store resulting solid with properties
4. Return operation result

---

## Common Response Format

All operations return JSON-RPC 2.0 responses:

```json
{
    "jsonrpc": "2.0",
    "id": 1,
    "result": {
        "status": "success",
        "data": {
            "entity_id": "workspace:solid_uuid",
            "shape_id": "shape_uuid",
            "volume": 35342.917,
            "surface_area": 6126.106,
            "center_of_mass": [50.0, 40.0, 25.0],
            "topology": {
                "face_count": 3,
                "edge_count": 2,
                "vertex_count": 0,
                "is_closed": true,
                "is_manifold": true
            }
        },
        "metadata": {
            "operation_type": "solid.extrude",
            "execution_time_ms": 127
        }
    }
}
```

**Error Response**:
```json
{
    "jsonrpc": "2.0",
    "id": 1,
    "error": {
        "code": -32602,
        "message": "Invalid parameters",
        "data": {
            "parameter": "base_entity_id",
            "reason": "Entity not found in workspace"
        }
    }
}
```

---

## solid.extrude

**Purpose**: Extrude 2D profile into 3D solid

**Method**: `solid.extrude`

**Parameters**:
```json
{
    "base_entity_id": "workspace:circle_uuid",
    "distance": 50.0,
    "direction": [0, 0, 1],  // Optional, default: [0, 0, 1]
    "workspace_id": "workspace_id",
    "agent_id": "agent_001"  // Optional
}
```

**Parameter Constraints**:
- `base_entity_id`: Must reference existing 2D entity (circle, wire, face)
- `distance`: Must be > 0
- `direction`: 3D vector, will be normalized
- `workspace_id`: Required

**Example Request**:
```bash
py -m src.agent_interface.cli solid.extrude --params '{
    "base_entity_id": "ws:circle_123",
    "distance": 50.0,
    "workspace_id": "my_workspace"
}'
```

**Success Response**: See common format above

**Possible Errors**:
- `-32602`: Invalid parameters (entity not found, distance <= 0)
- `-32603`: Internal error (Open CASCADE operation failed)

---

## solid.revolve

**Purpose**: Revolve 2D profile around axis

**Method**: `solid.revolve`

**Parameters**:
```json
{
    "profile_entity_id": "workspace:wire_uuid",
    "axis_point": [0, 0, 0],
    "axis_direction": [0, 0, 1],
    "angle_degrees": 360.0,
    "workspace_id": "workspace_id",
    "agent_id": "agent_001"
}
```

**Parameter Constraints**:
- `profile_entity_id`: Must reference existing 2D entity
- `axis_point`: 3D point defining axis location
- `axis_direction`: 3D vector (normalized), axis direction
- `angle_degrees`: 0 < angle <= 360
- Profile must not intersect axis

**Example Request**:
```bash
py -m src.agent_interface.cli solid.revolve --params '{
    "profile_entity_id": "ws:profile_456",
    "axis_point": [0, 0, 0],
    "axis_direction": [0, 0, 1],
    "angle_degrees": 360.0,
    "workspace_id": "my_workspace"
}'
```

---

## solid.loft

**Purpose**: Blend between multiple 2D profiles

**Method**: `solid.loft`

**Parameters**:
```json
{
    "profile_entity_ids": ["ws:profile_1", "ws:profile_2", "ws:profile_3"],
    "is_solid": true,
    "is_ruled": false,
    "workspace_id": "workspace_id",
    "agent_id": "agent_001"
}
```

**Parameter Constraints**:
- `profile_entity_ids`: Array of 2+ profile IDs, ordered
- `is_solid`: true for solid, false for shell
- `is_ruled`: false for smooth blend, true for ruled surfaces
- Profiles should be topologically compatible

**Example Request**:
```bash
py -m src.agent_interface.cli solid.loft --params '{
    "profile_entity_ids": ["ws:p1", "ws:p2", "ws:p3"],
    "is_solid": true,
    "is_ruled": false,
    "workspace_id": "my_workspace"
}'
```

**Possible Errors**:
- `-32602`: Less than 2 profiles provided
- `-32603`: Profiles incompatible for loft

---

## solid.sweep

**Purpose**: Sweep profile along path

**Method**: `solid.sweep`

**Parameters**:
```json
{
    "profile_entity_id": "ws:profile_uuid",
    "path_entity_id": "ws:wire_uuid",
    "workspace_id": "workspace_id",
    "agent_id": "agent_001"
}
```

**Parameter Constraints**:
- `profile_entity_id`: Must reference 2D profile (wire or face)
- `path_entity_id`: Must reference wire or edge
- Path must have G1 continuity (smooth)

**Example Request**:
```bash
py -m src.agent_interface.cli solid.sweep --params '{
    "profile_entity_id": "ws:prof_789",
    "path_entity_id": "ws:path_012",
    "workspace_id": "my_workspace"
}'
```

---

## solid.primitive

**Purpose**: Create primitive solid (box, cylinder, sphere, cone)

**Method**: `solid.primitive`

**Parameters** (Box):
```json
{
    "primitive_type": "box",
    "width": 100.0,
    "depth": 80.0,
    "height": 50.0,
    "position": [0, 0, 0],  // Optional, default origin
    "workspace_id": "workspace_id"
}
```

**Parameters** (Cylinder):
```json
{
    "primitive_type": "cylinder",
    "radius": 15.0,
    "height": 50.0,
    "axis_point": [0, 0, 0],  // Optional
    "axis_direction": [0, 0, 1],  // Optional
    "workspace_id": "workspace_id"
}
```

**Parameters** (Sphere):
```json
{
    "primitive_type": "sphere",
    "radius": 50.0,
    "center": [0, 0, 0],  // Optional
    "workspace_id": "workspace_id"
}
```

**Parameters** (Cone):
```json
{
    "primitive_type": "cone",
    "radius1": 20.0,  // Bottom radius
    "radius2": 10.0,  // Top radius
    "height": 50.0,
    "axis_point": [0, 0, 0],  // Optional
    "axis_direction": [0, 0, 1],  // Optional
    "workspace_id": "workspace_id"
}
```

**Parameter Constraints**:
- All dimensions must be > 0
- For cone: radius1 or radius2 can be 0 (pointed)

**Example Request**:
```bash
py -m src.agent_interface.cli solid.primitive --params '{
    "primitive_type": "cylinder",
    "radius": 15.0,
    "height": 50.0,
    "workspace_id": "my_workspace"
}'
```

---

## solid.pattern.linear

**Purpose**: Create linear array of solid copies

**Method**: `solid.pattern.linear`

**Parameters**:
```json
{
    "base_entity_id": "ws:solid_uuid",
    "direction": [1, 0, 0],
    "spacing": 10.0,
    "count": 5,
    "workspace_id": "workspace_id"
}
```

**Parameter Constraints**:
- `base_entity_id`: Must reference existing solid
- `direction`: 3D vector (normalized)
- `spacing`: Distance between copies, must be > 0
- `count`: Number of copies, 2 <= count <= 100

**Returns**: Array of entity IDs for created copies

```json
{
    "result": {
        "status": "success",
        "data": {
            "base_entity_id": "ws:solid_123",
            "copy_entity_ids": ["ws:copy_1", "ws:copy_2", "ws:copy_3", "ws:copy_4"],
            "count": 4
        }
    }
}
```

---

## solid.pattern.circular

**Purpose**: Create circular array of solid copies

**Method**: `solid.pattern.circular`

**Parameters**:
```json
{
    "base_entity_id": "ws:solid_uuid",
    "axis_point": [0, 0, 0],
    "axis_direction": [0, 0, 1],
    "count": 8,
    "angle_degrees": 360.0,  // Optional, default: 360
    "workspace_id": "workspace_id"
}
```

**Parameter Constraints**:
- `base_entity_id`: Must reference existing solid
- `axis_point`: 3D point for rotation center
- `axis_direction`: 3D vector (normalized)
- `count`: Number of copies, 2 <= count <= 100
- `angle_degrees`: Total angle to distribute copies, 0 < angle <= 360

**Returns**: Array of entity IDs for created copies

---

## solid.mirror

**Purpose**: Create mirrored copy of solid

**Method**: `solid.mirror`

**Parameters**:
```json
{
    "base_entity_id": "ws:solid_uuid",
    "mirror_plane_point": [0, 0, 0],
    "mirror_plane_normal": [1, 0, 0],
    "workspace_id": "workspace_id"
}
```

**Parameter Constraints**:
- `base_entity_id`: Must reference existing solid
- `mirror_plane_point`: Point on mirror plane
- `mirror_plane_normal`: Plane normal vector (normalized)

**Returns**: Single mirrored entity

```json
{
    "result": {
        "status": "success",
        "data": {
            "base_entity_id": "ws:solid_123",
            "mirrored_entity_id": "ws:mirrored_456"
        }
    }
}
```

---

## Contract Tests

All operations must pass these contract tests:

1. **Valid Input → Success**: Proper parameters return success with valid entity
2. **Invalid Entity → Error**: Non-existent base_entity_id returns -32602
3. **Invalid Parameters → Error**: Out-of-range values return -32602
4. **Operation Failure → Error**: Open CASCADE errors return -32603
5. **Properties Calculated**: Response includes volume, surface_area, center_of_mass
6. **Topology Valid**: is_closed=true, is_manifold=true for all results
7. **Performance**: Operations complete in <5s for standard shapes
8. **Idempotent**: Same inputs produce geometrically equivalent outputs

---

## Backward Compatibility

- New operations (solid.*) do not affect existing entity.* operations
- Existing 2D entity creation unchanged
- STL export updated to use real tessellation but maintains same CLI signature
