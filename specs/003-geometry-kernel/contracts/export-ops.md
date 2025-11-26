# Contract: Export Operations API

**Version**: 1.0.0
**Date**: 2025-11-26
**Purpose**: Define CLI contracts for geometry export (STL)

---

## Overview

Export operations convert 3D solids to external file formats. The primary operation is STL export with real tessellation (replacing placeholder code). All exports validate geometry, generate mesh, and write to file.

---

## file.export (STL)

**Purpose**: Export 3D solid(s) to STL file with real geometry

**Method**: `file.export`

**Parameters**:
```json
{
    "file_path": "output.stl",
    "format": "stl",
    "entity_ids": ["ws:solid_1", "ws:solid_2"],  // Optional, default: all solids
    "workspace_id": "workspace_id",
    "tessellation_quality": "standard",  // Optional: preview, standard, high_quality
    "ascii": false  // Optional, default: false (binary STL)
}
```

**Parameter Constraints**:
- `file_path`: Valid file path, must end with .stl
- `format`: Must be "stl" (other formats reserved for future)
- `entity_ids`: If provided, must reference existing solids; if omitted, exports all solids in workspace
- `tessellation_quality`: One of "preview", "standard", "high_quality"
- `ascii`: true for ASCII STL, false for binary STL (smaller files)

**Tessellation Quality Presets**:

| Quality | Linear Deflection | Angular Deflection | Use Case |
|---------|------------------|-------------------|----------|
| preview | 1.0mm | 1.0 rad | Quick visualization |
| standard | 0.1mm | 0.5 rad | General use (default) |
| high_quality | 0.01mm | 0.1 rad | Manufacturing, detailed views |

**Example Request**:
```bash
py -m src.agent_interface.cli file.export --params '{
    "file_path": "cylinder.stl",
    "format": "stl",
    "entity_ids": ["ws:cylinder_123"],
    "workspace_id": "my_workspace",
    "tessellation_quality": "standard"
}'
```

**Success Response**:
```json
{
    "jsonrpc": "2.0",
    "id": 1,
    "result": {
        "status": "success",
        "data": {
            "file_path": "cylinder.stl",
            "format": "stl",
            "entity_count": 1,
            "triangle_count": 6126,
            "file_size": 306383,
            "tessellation_config": {
                "linear_deflection": 0.1,
                "angular_deflection": 0.5,
                "quality": "standard"
            }
        },
        "metadata": {
            "operation_type": "file.export",
            "execution_time_ms": 1247
        }
    }
}
```

**Response Fields**:
- `file_path`: Absolute path to created file
- `entity_count`: Number of solids exported
- `triangle_count`: Total triangles in mesh
- `file_size`: File size in bytes
- `tessellation_config`: Quality settings used
- `execution_time_ms`: Time to tessellate and write

**Possible Errors**:
- `-32602`: Invalid parameters (bad file path, entity not found, invalid quality)
- `-32603`: Export failed (tessellation error, file write error, invalid geometry)

---

## Tessellation Process

### Steps

1. **Validate Solids**: Check all input solids with BRepCheck_Analyzer
2. **Mesh Generation**: Use BRepMesh_IncrementalMesh with quality parameters
3. **Triangle Extraction**: Extract triangle data from meshed shape
4. **STL Write**: Write triangles to STL file (binary or ASCII)
5. **Validation**: Verify file was written and has correct size

### Quality vs Performance

```
Triangle Count vs Quality (for standard cylinder: r=15mm, h=50mm):

Preview:     ~100 triangles, <0.5s
Standard:  ~1,000 triangles, 1-2s
High Quality: ~10,000 triangles, 2-5s
```

**Recommendation**: Use "standard" for general purposes (meets SC-004: smooth appearance)

---

## file.export (Multi-Solid)

**Behavior**: When multiple entity_ids provided or no IDs specified (export all):

1. Each solid is tessellated individually
2. All triangles written to single STL file
3. STL format supports multiple disconnected components
4. Total triangle count is sum of all solids

**Example** (export all solids in workspace):
```bash
py -m src.agent_interface.cli file.export --params '{
    "file_path": "assembly.stl",
    "format": "stl",
    "workspace_id": "my_workspace"
}'
```

**Response** (multiple solids):
```json
{
    "result": {
        "data": {
            "file_path": "assembly.stl",
            "entity_count": 3,
            "triangle_count": 18432,
            "entities": [
                {"entity_id": "ws:solid_1", "triangle_count": 6126},
                {"entity_id": "ws:solid_2", "triangle_count": 8200},
                {"entity_id": "ws:solid_3", "triangle_count": 4106}
            ]
        }
    }
}
```

---

## Error Scenarios

### Invalid Solid Geometry

**Scenario**: Solid fails validation before tessellation

```json
{
    "error": {
        "code": -32603,
        "message": "Cannot export invalid geometry",
        "data": {
            "entity_id": "ws:solid_broken",
            "reason": "Solid is not manifold",
            "validation": {
                "is_closed": true,
                "is_manifold": false
            }
        }
    }
}
```

### Tessellation Failure

**Scenario**: Mesh generation fails (extreme geometry, very small features)

```json
{
    "error": {
        "code": -32603,
        "message": "Tessellation failed",
        "data": {
            "entity_id": "ws:solid_complex",
            "reason": "Mesh generation did not complete",
            "suggestion": "Try lower quality setting or check geometry for degeneracies"
        }
    }
}
```

### File Write Error

**Scenario**: Cannot write to file (permissions, disk full)

```json
{
    "error": {
        "code": -32603,
        "message": "File write failed",
        "data": {
            "file_path": "/protected/output.stl",
            "reason": "Permission denied"
        }
    }
}
```

---

## Contract Tests

All export operations must pass:

1. **Valid Solid → STL File**: Solid exports to valid STL file
2. **File Contains Geometry**: STL file has non-zero triangle data (not all zeros)
3. **File Opens Externally**: STL opens in MeshLab, FreeCAD, online viewers
4. **Triangle Count Correct**: Reported count matches file content
5. **Performance**: Export completes in <5s for standard solids
6. **Quality Appropriate**: Standard quality produces smooth surfaces (no visible faceting)
7. **Binary vs ASCII**: Both formats produce valid, equivalent geometry
8. **Multiple Solids**: Multiple solids export to single file correctly

### Specific Test Cases

**Simple Cylinder**:
- Input: Cylinder (r=15mm, h=50mm)
- Standard quality
- Expected: ~1,000 triangles, smooth curved surface, file size ~50KB

**Complex Solid**:
- Input: Boolean union of multiple primitives
- High quality
- Expected: ~10,000 triangles, all features preserved, file size ~500KB

**Empty Workspace**:
- Input: No solids in workspace
- Expected: Error -32602 "No solids to export"

**Invalid Quality**:
- Input: tessellation_quality="ultra"
- Expected: Error -32602 "Invalid quality setting"

---

## Success Criteria Mapping

| Success Criterion | Contract Validation |
|-------------------|---------------------|
| SC-001: Viewable in 5s | Export + open in viewer completes quickly |
| SC-003: Create/export in 2min | End-to-end test: create + export |
| SC-004: Smooth tessellation | Visual inspection of standard quality output |
| SC-006: 10k faces in 5s | Performance test with complex solid |
| SC-007: 95% viewer compatibility | Test with 3+ different STL viewers |

---

## Backward Compatibility

**Breaking Change**: This operation REPLACES the placeholder implementation in `src/file_io/stl_handler.py`.

**Migration**:
- Old behavior: Generated empty/dummy triangles (all zeros)
- New behavior: Generates real geometry from Open CASCADE mesh
- **No API changes**: CLI signature remains identical
- **Breaking**: Files generated before this change were invalid; no migration needed

**Impact**:
- Existing CLI scripts work without changes
- Previously generated STL files were unusable anyway (all zeros)
- Tests expecting dummy triangles must be updated

---

## Performance Targets

| Operation | Target | Notes |
|-----------|--------|-------|
| Single solid export | <2s | Standard quality, typical geometry |
| Complex solid export | <5s | Up to 10,000 faces |
| Multi-solid export (3-5 solids) | <5s | Combined tessellation time |
| High quality export | <5s | Even with fine mesh |

**Logging**: Operations exceeding targets should log performance warning.

---

## File Format Details

**Binary STL Format**:
```
Header: 80 bytes (ASCII text, ignored by readers)
Triangle count: 4 bytes (unsigned int, little-endian)
For each triangle (50 bytes):
  - Normal vector: 12 bytes (3 floats)
  - Vertex 1: 12 bytes (3 floats)
  - Vertex 2: 12 bytes (3 floats)
  - Vertex 3: 12 bytes (3 floats)
  - Attribute: 2 bytes (usually 0)
```

**Validation**: Export implementation must write exact binary STL format matching specification.
