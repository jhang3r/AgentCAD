# CLI API Contract: AI Agent CAD Environment

**Version**: 1.0.0
**Protocol**: JSON-RPC 2.0 over NDJSON (stdin/stdout)
**Date**: 2025-11-24

## Overview

This document defines the complete CLI API contract for AI agents interacting with the CAD environment. All commands follow JSON-RPC 2.0 specification with newline-delimited JSON (NDJSON) transport.

---

## Transport Protocol

### Request Format (stdin)

```json
{"jsonrpc":"2.0","method":"<resource>.<action>","params":{...},"id":<number>}\n
```

### Response Format (stdout)

**Success**:
```json
{"jsonrpc":"2.0","id":<number>,"result":{...}}\n
```

**Error**:
```json
{"jsonrpc":"2.0","id":<number>,"error":{"code":"<CODE>","message":"<msg>","data":{...}}}\n
```

**Progress** (for long-running operations):
```json
{"jsonrpc":"2.0","id":<number>,"result":{"status":"progress","percent":<0-100>,"stage":"<stage_name>"}}\n
```

---

## Entity Operations

### entity.create.point

**Description**: Create a point entity in 2D or 3D space (FR-002, FR-003)

**Request**:
```json
{
  "jsonrpc": "2.0",
  "method": "entity.create.point",
  "params": {
    "coordinates": [0.0, 0.0, 0.0]
  },
  "id": 1
}
```

**Parameters**:
| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `coordinates` | `array<float>` | Yes | Length: 2 or 3, finite values, range: [-1e6, 1e6] | Point coordinates in mm |

**Response**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "status": "success",
    "operation": {
      "type": "entity.create.point",
      "execution_time_ms": 5
    },
    "data": {
      "entity_id": "main:point_a1b2c3",
      "entity_type": "point",
      "coordinates": [0.0, 0.0, 0.0]
    }
  }
}
```

**Errors**:
- `INVALID_PARAMETER`: Coordinate out of range or non-finite
- `MISSING_PARAMETER`: Required field missing

---

### entity.create.line

**Description**: Create a line segment (FR-002, FR-003)

**Request**:
```json
{
  "jsonrpc": "2.0",
  "method": "entity.create.line",
  "params": {
    "start": [0.0, 0.0, 0.0],
    "end": [10.0, 0.0, 0.0]
  },
  "id": 2
}
```

**Parameters**:
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `start` | `array<float>` | Yes | Length: 2 or 3, finite values |
| `end` | `array<float>` | Yes | Length: 2 or 3, finite values |

**Response**:
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "status": "success",
    "operation": {
      "type": "entity.create.line",
      "execution_time_ms": 8
    },
    "data": {
      "entity_id": "main:line_d4e5f6",
      "entity_type": "line",
      "start": [0.0, 0.0, 0.0],
      "end": [10.0, 0.0, 0.0],
      "length": 10.0,
      "direction_vector": [1.0, 0.0, 0.0]
    }
  }
}
```

**Errors**:
- `INVALID_GEOMETRY`: Start and end points are coincident (degenerate line)

---

### entity.create.circle

**Description**: Create a circle or arc (FR-002, FR-003)

**Request**:
```json
{
  "jsonrpc": "2.0",
  "method": "entity.create.circle",
  "params": {
    "center": [0.0, 0.0, 0.0],
    "radius": 5.0,
    "normal": [0.0, 0.0, 1.0],
    "start_angle": 0.0,
    "end_angle": 6.2832
  },
  "id": 3
}
```

**Parameters**:
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `center` | `array<float>` | Yes | Length: 2 or 3 |
| `radius` | `float` | Yes | Range: (1e-6, 1e6] |
| `normal` | `array<float>` | No (default: [0,0,1]) | Length: 3, unit vector |
| `start_angle` | `float` | No (default: 0) | Radians |
| `end_angle` | `float` | No (default: 2π) | Radians |

**Response**:
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "status": "success",
    "data": {
      "entity_id": "main:circle_g7h8i9",
      "entity_type": "circle",
      "center": [0.0, 0.0, 0.0],
      "radius": 5.0,
      "area": 78.5398,
      "circumference": 31.4159
    }
  }
}
```

**Errors**:
- `INVALID_RADIUS`: Radius ≤ 0 or > 1e6

---

### entity.query

**Description**: Query entity properties (FR-006, FR-007)

**Request**:
```json
{
  "jsonrpc": "2.0",
  "method": "entity.query",
  "params": {
    "entity_id": "main:circle_g7h8i9",
    "properties": ["all"]
  },
  "id": 4
}
```

**Parameters**:
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `entity_id` | `string` | Yes | Must exist in workspace |
| `properties` | `array<string>` | No (default: ["all"]) | Options: "all", "coordinates", "dimensions", "type", "relationships" |

**Response**:
```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "result": {
    "status": "success",
    "data": {
      "entity_id": "main:circle_g7h8i9",
      "entity_type": "circle",
      "workspace_id": "main",
      "created_at": "2025-11-24T10:30:00Z",
      "modified_at": "2025-11-24T10:30:00Z",
      "created_by_agent": "agent_alpha",
      "properties": {
        "center": [0.0, 0.0, 0.0],
        "radius": 5.0,
        "area": 78.5398,
        "circumference": 31.4159
      },
      "parent_entities": [],
      "child_entities": []
    }
  }
}
```

**Errors**:
- `ENTITY_NOT_FOUND`: Entity ID does not exist

---

### entity.list

**Description**: List all entities in workspace (FR-006)

**Request**:
```json
{
  "jsonrpc": "2.0",
  "method": "entity.list",
  "params": {
    "filter_type": "circle",
    "limit": 100,
    "offset": 0
  },
  "id": 5
}
```

**Parameters**:
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `filter_type` | `string` | No | Entity type filter |
| `limit` | `integer` | No (default: 100) | Max results to return |
| `offset` | `integer` | No (default: 0) | Pagination offset |

**Response**:
```json
{
  "jsonrpc": "2.0",
  "id": 5,
  "result": {
    "status": "success",
    "data": {
      "entities": [
        {
          "entity_id": "main:point_a1b2c3",
          "entity_type": "point",
          "created_at": "2025-11-24T10:30:00Z"
        },
        {
          "entity_id": "main:circle_g7h8i9",
          "entity_type": "circle",
          "created_at": "2025-11-24T10:31:00Z"
        }
      ],
      "total_count": 2,
      "limit": 100,
      "offset": 0
    }
  }
}
```

---

## Constraint Operations

### constraint.apply

**Description**: Apply geometric constraint to entities (FR-008)

**Request**:
```json
{
  "jsonrpc": "2.0",
  "method": "constraint.apply",
  "params": {
    "constraint_type": "perpendicular",
    "entities": ["main:line_1", "main:line_2"]
  },
  "id": 6
}
```

**Parameters**:
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `constraint_type` | `string` | Yes | Values: "coincident", "parallel", "perpendicular", "tangent", "distance", "angle", "radius" |
| `entities` | `array<string>` | Yes | 1-2 entity IDs |
| `parameters` | `object` | Conditional | Required for distance/angle/radius constraints |

**Parameters for Distance Constraint**:
```json
{
  "constraint_type": "distance",
  "entities": ["main:point_1", "main:point_2"],
  "parameters": {
    "distance": 10.0,
    "tolerance": 0.01
  }
}
```

**Response**:
```json
{
  "jsonrpc": "2.0",
  "id": 6,
  "result": {
    "status": "success",
    "operation": {
      "type": "constraint.apply",
      "execution_time_ms": 200
    },
    "data": {
      "constraint_id": "main:constraint_j1k2l3",
      "constraint_type": "perpendicular",
      "satisfaction_status": "satisfied",
      "degrees_of_freedom_removed": 1,
      "affected_entities": ["main:line_1", "main:line_2"]
    }
  }
}
```

**Errors**:
- `CONSTRAINT_CONFLICT`: Constraint conflicts with existing constraints (FR-009)
- `ENTITY_NOT_FOUND`: Referenced entity doesn't exist
- `INVALID_CONSTRAINT`: Constraint type incompatible with entity types

---

### constraint.status

**Description**: Query constraint satisfaction status (FR-012)

**Request**:
```json
{
  "jsonrpc": "2.0",
  "method": "constraint.status",
  "params": {
    "scope": "sketch",
    "entity_id": "main:sketch_1"
  },
  "id": 7
}
```

**Response**:
```json
{
  "jsonrpc": "2.0",
  "id": 7,
  "result": {
    "status": "success",
    "data": {
      "constraint_count": 5,
      "satisfied_count": 4,
      "violated_count": 1,
      "redundant_count": 0,
      "degrees_of_freedom": 2,
      "constraints": [
        {
          "constraint_id": "main:constraint_j1k2l3",
          "constraint_type": "perpendicular",
          "satisfaction_status": "satisfied"
        },
        {
          "constraint_id": "main:constraint_m4n5o6",
          "constraint_type": "distance",
          "satisfaction_status": "violated",
          "expected_value": 10.0,
          "actual_value": 10.5,
          "tolerance": 0.01
        }
      ]
    }
  }
}
```

---

## Solid Modeling Operations

### solid.extrude

**Description**: Extrude 2D sketch into 3D solid (FR-013)

**Request**:
```json
{
  "jsonrpc": "2.0",
  "method": "solid.extrude",
  "params": {
    "sketch_id": "main:sketch_1",
    "distance": 10.0,
    "taper_angle": 0.0,
    "direction": [0.0, 0.0, 1.0]
  },
  "id": 8
}
```

**Parameters**:
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `sketch_id` | `string` | Yes | Must be closed 2D sketch |
| `distance` | `float` | Yes | > 0 |
| `taper_angle` | `float` | No (default: 0) | Radians, range: [-π/4, π/4] |
| `direction` | `array<float>` | No (default: sketch normal) | Unit vector |

**Response** (with progress streaming):
```json
{"jsonrpc":"2.0","id":8,"result":{"status":"progress","percent":30,"stage":"validating_sketch"}}\n
{"jsonrpc":"2.0","id":8,"result":{"status":"progress","percent":70,"stage":"generating_faces"}}\n
{"jsonrpc":"2.0","id":8,"result":{"status":"success","data":{"entity_id":"main:solid_p7q8r9","entity_type":"solid","volume":500.0,"surface_area":340.0,"face_count":6}}}\n
```

**Errors**:
- `INVALID_SKETCH`: Sketch is not closed or contains self-intersections
- `INVALID_DISTANCE`: Distance ≤ 0

---

### solid.boolean

**Description**: Boolean operation on solid bodies (FR-015)

**Request**:
```json
{
  "jsonrpc": "2.0",
  "method": "solid.boolean",
  "params": {
    "operation": "union",
    "bodies": ["main:solid_1", "main:solid_2"]
  },
  "id": 9
}
```

**Parameters**:
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `operation` | `string` | Yes | Values: "union", "subtract", "intersect" |
| `bodies` | `array<string>` | Yes | 2 solid entity IDs |

**Response**:
```json
{
  "jsonrpc": "2.0",
  "id": 9,
  "result": {
    "status": "success",
    "operation": {
      "type": "solid.boolean.union",
      "execution_time_ms": 650
    },
    "data": {
      "entity_id": "main:solid_s0t1u2",
      "entity_type": "solid",
      "volume": 1250.5,
      "surface_area": 850.3,
      "operation_result": "success",
      "input_volumes": [500.0, 800.0],
      "volume_change": -49.5
    }
  }
}
```

**Errors**:
- `OPERATION_INVALID`: Boolean subtract with no intersection (FR-017)
- `TOPOLOGY_ERROR`: Result has invalid topology

---

## Workspace Operations

### workspace.create

**Description**: Create isolated workspace for agent practice (FR-025)

**Request**:
```json
{
  "jsonrpc": "2.0",
  "method": "workspace.create",
  "params": {
    "name": "practice_session_01",
    "base": "main"
  },
  "id": 10
}
```

**Response**:
```json
{
  "jsonrpc": "2.0",
  "id": 10,
  "result": {
    "status": "success",
    "data": {
      "workspace_id": "agent_alpha:practice_session_01",
      "workspace_name": "practice_session_01",
      "base_workspace_id": "main",
      "branch_status": "clean",
      "created_at": "2025-11-24T10:35:00Z"
    }
  }
}
```

---

### workspace.status

**Description**: Get workspace status and divergence info (FR-032)

**Request**:
```json
{
  "jsonrpc": "2.0",
  "method": "workspace.status",
  "params": {},
  "id": 11
}
```

**Response**:
```json
{
  "jsonrpc": "2.0",
  "id": 11,
  "result": {
    "status": "success",
    "data": {
      "workspace_id": "agent_alpha:practice_session_01",
      "branch_status": "modified",
      "entity_count": 15,
      "operation_count": 23,
      "divergence_point": "op_1732450000_abc123",
      "can_merge": true
    }
  }
}
```

---

### workspace.merge

**Description**: Merge workspace into target (FR-031)

**Request**:
```json
{
  "jsonrpc": "2.0",
  "method": "workspace.merge",
  "params": {
    "source": "agent_alpha:practice_session_01",
    "target": "main",
    "strategy": "auto"
  },
  "id": 12
}
```

**Response (success)**:
```json
{
  "jsonrpc": "2.0",
  "id": 12,
  "result": {
    "status": "success",
    "data": {
      "merge_status": "completed",
      "entities_added": 10,
      "entities_modified": 3,
      "entities_deleted": 1,
      "conflicts": []
    }
  }
}
```

**Response (conflict)**:
```json
{
  "jsonrpc": "2.0",
  "id": 12,
  "error": {
    "code": "WORKSPACE_CONFLICT",
    "message": "Merge conflicts detected",
    "data": {
      "conflicts": [
        {
          "entity_id": "main:circle_123",
          "conflict_type": "both_modified",
          "base_version": {"radius": 5.0},
          "source_version": {"radius": 7.0},
          "target_version": {"radius": 10.0},
          "resolution_options": ["keep_source", "keep_target", "manual_merge"]
        }
      ]
    }
  }
}
```

---

## File Operations

### file.import

**Description**: Import CAD file (STEP, DXF) (FR-034, FR-036)

**Request**:
```json
{
  "jsonrpc": "2.0",
  "method": "file.import",
  "params": {
    "format": "step",
    "path": "/path/to/model.step",
    "validate": true
  },
  "id": 13
}
```

**Response** (with validation):
```json
{
  "jsonrpc": "2.0",
  "id": 13,
  "result": {
    "status": "success",
    "data": {
      "import_status": "completed_with_warnings",
      "entities_imported": 127,
      "entity_types": {
        "solid": 5,
        "face": 48,
        "edge": 92,
        "vertex": 64
      },
      "total_volume": 1250.5,
      "validation": {
        "topology_errors": 0,
        "geometry_warnings": 2,
        "warnings": [
          {
            "code": "GEOM-003",
            "severity": "warning",
            "description": "Degenerate edge detected (auto-repaired)",
            "entity_id": "main:edge_156"
          }
        ]
      }
    }
  }
}
```

**Errors**:
- `FILE_NOT_FOUND`: Path does not exist
- `UNSUPPORTED_FORMAT`: Format not supported
- `IMPORT_FAILED`: Import failed with topology errors (FR-038)

---

### file.export

**Description**: Export geometry to file (STL, STEP, DXF) (FR-035, FR-036, FR-037)

**Request**:
```json
{
  "jsonrpc": "2.0",
  "method": "file.export",
  "params": {
    "format": "stl",
    "entities": ["main:solid_1"],
    "path": "/path/to/output.stl",
    "options": {
      "binary": true,
      "linear_deflection": 0.1,
      "angular_deflection": 0.5
    }
  },
  "id": 14
}
```

**Response**:
```json
{
  "jsonrpc": "2.0",
  "id": 14,
  "result": {
    "status": "success",
    "data": {
      "export_status": "completed",
      "format": "stl",
      "file_path": "/path/to/output.stl",
      "file_size_bytes": 524288,
      "triangle_count": 10240,
      "data_loss_warning": {
        "severity": "expected",
        "message": "STEP to STL conversion: exact geometry approximated as mesh",
        "original_volume": 500.0,
        "mesh_volume": 499.2,
        "volume_error_percent": 0.16
      }
    }
  }
}
```

---

## History Operations

### history.list

**Description**: List operation history (FR-023)

**Request**:
```json
{
  "jsonrpc": "2.0",
  "method": "history.list",
  "params": {
    "limit": 10,
    "offset": 0
  },
  "id": 15
}
```

**Response**:
```json
{
  "jsonrpc": "2.0",
  "id": 15,
  "result": {
    "status": "success",
    "data": {
      "operations": [
        {
          "operation_id": "op_1732450200_a1b2c3",
          "operation_type": "entity.create.circle",
          "timestamp": "2025-11-24T10:30:00Z",
          "result_status": "success",
          "execution_time_ms": 12
        }
      ],
      "total_count": 23,
      "current_position": 23,
      "can_undo": true,
      "can_redo": false
    }
  }
}
```

---

### history.undo

**Description**: Undo last operation (FR-023)

**Request**:
```json
{
  "jsonrpc": "2.0",
  "method": "history.undo",
  "params": {},
  "id": 16
}
```

**Response**:
```json
{
  "jsonrpc": "2.0",
  "id": 16,
  "result": {
    "status": "success",
    "data": {
      "undone_operation": {
        "operation_id": "op_1732450200_a1b2c3",
        "operation_type": "entity.create.circle",
        "affected_entities": ["main:circle_g7h8i9"]
      },
      "current_position": 22,
      "can_undo": true,
      "can_redo": true
    }
  }
}
```

---

## Error Codes

| Code | Severity | Description | Recoverable |
|------|----------|-------------|-------------|
| `INVALID_COMMAND` | error | Unrecognized method | No |
| `INVALID_PARAMETER` | error | Parameter validation failed | Yes |
| `MISSING_PARAMETER` | error | Required parameter missing | Yes |
| `ENTITY_NOT_FOUND` | error | Referenced entity doesn't exist | Yes |
| `CONSTRAINT_CONFLICT` | error | Constraint conflicts with existing | Yes |
| `INVALID_GEOMETRY` | error | Geometric validation failed | Yes |
| `OPERATION_INVALID` | error | Operation logically impossible | Yes |
| `WORKSPACE_CONFLICT` | error | Merge conflict detected | Yes |
| `TOPOLOGY_ERROR` | error | Invalid topology generated | No |
| `GEOMETRY_ENGINE_ERROR` | error | CAD kernel internal error | No |
| `FILE_NOT_FOUND` | error | Import file doesn't exist | Yes |
| `IMPORT_FAILED` | error | Import failed with errors | Partial |
| `INSUFFICIENT_MEMORY` | error | Out of memory | No |
| `TIMEOUT` | error | Operation exceeded time limit | No |

---

## Performance Contracts

| Operation Type | Target Response Time | Typical Response Time |
|----------------|---------------------|----------------------|
| entity.create.point | <100ms | ~5ms |
| entity.create.line | <100ms | ~8ms |
| entity.create.circle | <100ms | ~15ms |
| entity.query | <100ms | ~6ms |
| constraint.apply | <1000ms | ~200ms |
| solid.extrude | <1000ms | ~150ms |
| solid.boolean | <1000ms | ~600ms |
| file.import (10MB STEP) | <5000ms | ~3000ms |
| workspace.merge | <1000ms | ~400ms |

**Progress Streaming**: Operations exceeding 1000ms must stream progress updates every 500ms.

---

## Compliance Mapping

| Functional Requirement | API Method |
|------------------------|------------|
| FR-001 | All methods (JSON-RPC over stdin/stdout) |
| FR-002, FR-003 | entity.create.* |
| FR-004 | All methods (validation before execution) |
| FR-005 | All entity.* methods (persistent IDs) |
| FR-006, FR-007 | entity.query, entity.list |
| FR-008 | constraint.apply |
| FR-009, FR-010 | constraint.status |
| FR-013, FR-014 | solid.extrude, solid.revolve |
| FR-015, FR-016 | solid.boolean, solid.fillet |
| FR-019, FR-020 | Performance contracts |
| FR-022 | Error response schema |
| FR-023 | history.* methods |
| FR-025, FR-026 | workspace.create, workspace.reset |
| FR-030, FR-031 | workspace.* methods |
| FR-034, FR-035, FR-036 | file.import, file.export |

---

**Conclusion**: Complete CLI API contract covering all functional requirements (FR-001 through FR-038). Ready for implementation.
