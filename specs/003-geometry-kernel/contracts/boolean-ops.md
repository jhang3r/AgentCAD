# Contract: Boolean Operations API

**Version**: 1.0.0
**Date**: 2025-11-26
**Purpose**: Define CLI contracts for boolean operations on 3D solids

---

## Overview

Boolean operations combine or modify solids through union, subtraction, and intersection. All operations validate inputs, execute Open CASCADE boolean operations, and return the resulting solid with properties.

---

## Common Response Format

```json
{
    "jsonrpc": "2.0",
    "id": 1,
    "result": {
        "status": "success",
        "data": {
            "entity_id": "workspace:solid_result_uuid",
            "shape_id": "shape_uuid",
            "operation_type": "union",
            "operand1_id": "ws:solid_a",
            "operand2_id": "ws:solid_b",
            "volume": 45000.0,
            "surface_area": 8000.0,
            "center_of_mass": [25.0, 30.0, 15.0],
            "topology": {
                "face_count": 12,
                "edge_count": 24,
                "vertex_count": 16,
                "is_closed": true,
                "is_manifold": true
            }
        },
        "metadata": {
            "operation_type": "solid.boolean.union",
            "execution_time_ms": 342
        }
    }
}
```

---

## solid.boolean.union

**Purpose**: Combine two solids into one (A ∪ B)

**Method**: `solid.boolean.union`

**Parameters**:
```json
{
    "solid1_entity_id": "ws:solid_a_uuid",
    "solid2_entity_id": "ws:solid_b_uuid",
    "workspace_id": "workspace_id",
    "agent_id": "agent_001"  // Optional
}
```

**Parameter Constraints**:
- Both entity IDs must reference existing 3D solids
- Solids must be valid (is_closed=true, is_manifold=true)
- Solids should have some overlap or contact for meaningful result

**Example Request**:
```bash
py -m src.agent_interface.cli solid.boolean.union --params '{
    "solid1_entity_id": "ws:cylinder_1",
    "solid2_entity_id": "ws:cylinder_2",
    "workspace_id": "my_workspace"
}'
```

**Behavior**:
- Creates new solid representing combined volume of both inputs
- Original solids remain unchanged
- Result volume approximately equals solid1.volume + solid2.volume - overlap_volume
- Result is automatically refined for cleaner edges

**Possible Errors**:
- `-32602`: Invalid parameters (entity not found, not a solid, invalid geometry)
- `-32603`: Boolean operation failed (Open CASCADE error, incompatible geometry)

---

## solid.boolean.subtract

**Purpose**: Remove one solid from another (A - B)

**Method**: `solid.boolean.subtract`

**Parameters**:
```json
{
    "base_entity_id": "ws:solid_a_uuid",
    "tool_entity_id": "ws:solid_b_uuid",
    "workspace_id": "workspace_id",
    "agent_id": "agent_001"
}
```

**Parameter Constraints**:
- Both entity IDs must reference existing 3D solids
- Solids must be valid
- Tool should overlap with base for meaningful result

**Example Request**:
```bash
py -m src.agent_interface.cli solid.boolean.subtract --params '{
    "base_entity_id": "ws:block_main",
    "tool_entity_id": "ws:cylinder_hole",
    "workspace_id": "my_workspace"
}'
```

**Behavior**:
- Removes tool solid's volume from base solid
- Original solids remain unchanged
- Result volume = base.volume - overlap_volume
- If tool doesn't intersect base, returns base unchanged (warning logged)

**Possible Errors**:
- `-32602`: Invalid parameters
- `-32603`: Boolean operation failed
- **Warning** (not error): Tool doesn't intersect base (returns base unchanged)

---

## solid.boolean.intersect

**Purpose**: Create solid from overlapping volume (A ∩ B)

**Method**: `solid.boolean.intersect`

**Parameters**:
```json
{
    "solid1_entity_id": "ws:solid_a_uuid",
    "solid2_entity_id": "ws:solid_b_uuid",
    "workspace_id": "workspace_id",
    "agent_id": "agent_001"
}
```

**Parameter Constraints**:
- Both entity IDs must reference existing 3D solids
- Solids must be valid
- Solids must overlap to produce valid result

**Example Request**:
```bash
py -m src.agent_interface.cli solid.boolean.intersect --params '{
    "solid1_entity_id": "ws:sphere_1",
    "solid2_entity_id": "ws:sphere_2",
    "workspace_id": "my_workspace"
}'
```

**Behavior**:
- Creates new solid from only the overlapping volume
- Original solids remain unchanged
- Result volume = overlap_volume only
- If no overlap, operation fails with error

**Possible Errors**:
- `-32602`: Invalid parameters
- `-32603`: Boolean operation failed (no overlap, incompatible geometry)

---

## Operation-Specific Behavior

### Edge Refinement

All boolean operations automatically apply:
- `RefineEdges()`: Merges collinear edges
- `FuseEdges()`: Fuses coincident edges

This ensures cleaner geometry and better mesh generation.

### Validation Steps

1. **Pre-validation**: Check both inputs with BRepCheck_Analyzer
2. **Operation**: Execute Open CASCADE boolean operation
3. **Post-validation**: Verify result is valid solid
4. **Property Calculation**: Compute volume, surface area, topology

### Performance Characteristics

| Input Complexity | Expected Time | Notes |
|------------------|---------------|-------|
| Simple (< 100 faces each) | < 0.5s | Primitives, basic shapes |
| Medium (100-1000 faces) | 0.5-2s | Moderately complex geometry |
| Complex (1000-10,000 faces) | 2-5s | Detailed models, many features |

Operations exceeding 5s should log performance warning.

---

## Error Handling

### Invalid Geometry Errors

**Scenario**: Input solids fail validation
```json
{
    "error": {
        "code": -32602,
        "message": "Invalid solid geometry",
        "data": {
            "entity_id": "ws:solid_a",
            "reason": "Solid is not closed",
            "validation": {
                "is_closed": false,
                "is_manifold": true
            }
        }
    }
}
```

### Operation Failure Errors

**Scenario**: Open CASCADE boolean operation fails
```json
{
    "error": {
        "code": -32603,
        "message": "Boolean operation failed",
        "data": {
            "operation": "union",
            "reason": "Result geometry is invalid",
            "error_status": "GeomAbs_C0"
        }
    }
}
```

### No Intersection Warning

**Scenario**: Intersect operation on non-overlapping solids
```json
{
    "error": {
        "code": -32603,
        "message": "Boolean intersect failed",
        "data": {
            "reason": "Solids do not overlap",
            "suggestion": "Check solid positions and try union or subtract instead"
        }
    }
}
```

---

## Contract Tests

All boolean operations must pass:

1. **Valid Solids → Success**: Two valid solids produce valid result
2. **Invalid Input → Error**: Non-solid or invalid geometry returns -32602
3. **Operation Failure → Error**: Incompatible geometry returns -32603
4. **Properties Correct**: Result properties match geometric expectations
5. **Topology Valid**: Result is closed, manifold solid
6. **Performance**: Operations complete in <5s for solids up to 10k faces
7. **Edge Refinement**: Result has refined edges (no unnecessary vertices)
8. **Idempotent**: Same inputs produce geometrically equivalent results

### Specific Test Cases

**Union**:
- Two overlapping cylinders → single merged solid
- Volume(result) ≈ Volume(A) + Volume(B) - Volume(overlap)

**Subtract**:
- Cylinder with sphere subtracted → hollow cylinder
- Volume(result) = Volume(base) - Volume(overlap)

**Intersect**:
- Two overlapping spheres → lens-shaped solid
- Volume(result) = Volume(overlap only)

---

## Success Criteria Mapping

| Success Criterion | Contract Validation |
|-------------------|---------------------|
| SC-005: Boolean ops 100% success | All contract tests pass |
| SC-006: 10k faces in 5s | Performance test with complex solids |
| SC-002: Properties within 0.1% | Volume calculations validated |

---

## Backward Compatibility

- Boolean operations are new functionality
- Existing solid creation operations unchanged
- No breaking changes to existing API
