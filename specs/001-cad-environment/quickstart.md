# Quickstart Guide: AI Agent CAD Environment

**Feature**: `001-cad-environment`
**Date**: 2025-11-24
**Audience**: AI Agents and Human Developers

## Overview

This guide provides a practical introduction to the CAD environment for AI agents. It covers installation, basic operations, constraint solving, solid modeling, workspace management, and file I/O.

---

## Prerequisites

**System Requirements**:
- Python 3.11+
- 16GB+ RAM
- SSD storage
- Windows/Linux/macOS

**Dependencies**:
- OpenCascade Technology (OCCT) 7.8+
- build123d (Python bindings)
- ezdxf (DXF support)
- SQLite 3.x (operation history)

---

## Installation

```bash
# Create virtual environment
python -m venv cad_env
source cad_env/bin/activate  # Windows: cad_env\Scripts\activate

# Install dependencies
pip install build123d ezdxf

# Install CAD CLI tool
pip install -e .

# Verify installation
cad_cli --version
```

---

## Basic Usage Pattern

### 1. Start CLI Session

```bash
# Standard mode (interactive for humans)
cad_cli

# Agent mode (JSON-RPC over stdin/stdout)
echo '{"jsonrpc":"2.0","method":"entity.create.point","params":{"coordinates":[0,0,0]},"id":1}' | cad_cli --agent-mode
```

### 2. Request/Response Flow

**Agent sends** (stdin):
```json
{"jsonrpc":"2.0","method":"entity.create.point","params":{"coordinates":[0,0,0]},"id":1}\n
```

**CLI responds** (stdout):
```json
{"jsonrpc":"2.0","id":1,"result":{"status":"success","data":{"entity_id":"main:point_abc123","coordinates":[0,0,0]}}}\n
```

---

## Tutorial: First CAD Operations

### Step 1: Create Basic Geometry

**Create a Point**:
```json
{"jsonrpc":"2.0","method":"entity.create.point","params":{"coordinates":[0,0,0]},"id":1}
```

**Expected Response**:
```json
{"jsonrpc":"2.0","id":1,"result":{"status":"success","data":{"entity_id":"main:point_001","entity_type":"point","coordinates":[0,0,0]}}}
```

**Create a Line**:
```json
{"jsonrpc":"2.0","method":"entity.create.line","params":{"start":[0,0,0],"end":[10,0,0]},"id":2}
```

**Expected Response**:
```json
{"jsonrpc":"2.0","id":2,"result":{"status":"success","data":{"entity_id":"main:line_002","length":10.0,"direction_vector":[1,0,0]}}}
```

**Create a Circle**:
```json
{"jsonrpc":"2.0","method":"entity.create.circle","params":{"center":[0,0,0],"radius":5},"id":3}
```

**Expected Response**:
```json
{"jsonrpc":"2.0","id":3,"result":{"status":"success","data":{"entity_id":"main:circle_003","area":78.5398,"circumference":31.4159}}}
```

### Step 2: Query Entities

**List All Entities**:
```json
{"jsonrpc":"2.0","method":"entity.list","params":{},"id":4}
```

**Query Specific Entity**:
```json
{"jsonrpc":"2.0","method":"entity.query","params":{"entity_id":"main:circle_003","properties":["all"]},"id":5}
```

**Expected Response**:
```json
{
  "jsonrpc":"2.0",
  "id":5,
  "result":{
    "status":"success",
    "data":{
      "entity_id":"main:circle_003",
      "entity_type":"circle",
      "created_at":"2025-11-24T10:30:00Z",
      "properties":{"center":[0,0,0],"radius":5,"area":78.5398}
    }
  }
}
```

---

## Tutorial: Constraint Solving

### Step 3: Apply Constraints

**Create Two Lines**:
```json
{"jsonrpc":"2.0","method":"entity.create.line","params":{"start":[0,0,0],"end":[10,0,0]},"id":6}
{"jsonrpc":"2.0","method":"entity.create.line","params":{"start":[10,0,0],"end":[10,10,0]},"id":7}
```

**Apply Perpendicular Constraint**:
```json
{"jsonrpc":"2.0","method":"constraint.apply","params":{"constraint_type":"perpendicular","entities":["main:line_006","main:line_007"]},"id":8}
```

**Expected Response**:
```json
{
  "jsonrpc":"2.0",
  "id":8,
  "result":{
    "status":"success",
    "data":{
      "constraint_id":"main:constraint_008",
      "satisfaction_status":"satisfied",
      "degrees_of_freedom_removed":1
    }
  }
}
```

**Check Constraint Status**:
```json
{"jsonrpc":"2.0","method":"constraint.status","params":{"scope":"all"},"id":9}
```

---

## Tutorial: Solid Modeling

### Step 4: Create 3D Solid

**Create a Rectangular Sketch** (sequence of lines forming closed loop):
```json
{"jsonrpc":"2.0","method":"entity.create.line","params":{"start":[0,0,0],"end":[10,0,0]},"id":10}
{"jsonrpc":"2.0","method":"entity.create.line","params":{"start":[10,0,0],"end":[10,5,0]},"id":11}
{"jsonrpc":"2.0","method":"entity.create.line","params":{"start":[10,5,0],"end":[0,5,0]},"id":12}
{"jsonrpc":"2.0","method":"entity.create.line","params":{"start":[0,5,0],"end":[0,0,0]},"id":13}
```

**Create Sketch Entity from Lines**:
```json
{"jsonrpc":"2.0","method":"entity.create.sketch","params":{"entities":["main:line_010","main:line_011","main:line_012","main:line_013"]},"id":14}
```

**Extrude Sketch**:
```json
{"jsonrpc":"2.0","method":"solid.extrude","params":{"sketch_id":"main:sketch_014","distance":10},"id":15}
```

**Expected Response** (with progress streaming):
```json
{"jsonrpc":"2.0","id":15,"result":{"status":"progress","percent":30,"stage":"validating_sketch"}}
{"jsonrpc":"2.0","id":15,"result":{"status":"progress","percent":70,"stage":"generating_faces"}}
{"jsonrpc":"2.0","id":15,"result":{"status":"success","data":{"entity_id":"main:solid_015","volume":500.0,"surface_area":340.0,"face_count":6}}}
```

### Step 5: Boolean Operations

**Create Second Solid** (cylinder):
```json
{"jsonrpc":"2.0","method":"entity.create.circle","params":{"center":[5,2.5,5],"radius":2},"id":16}
{"jsonrpc":"2.0","method":"entity.create.sketch","params":{"entities":["main:circle_016"]},"id":17}
{"jsonrpc":"2.0","method":"solid.extrude","params":{"sketch_id":"main:sketch_017","distance":15},"id":18}
```

**Boolean Subtract** (create hole):
```json
{"jsonrpc":"2.0","method":"solid.boolean","params":{"operation":"subtract","bodies":["main:solid_015","main:solid_018"]},"id":19}
```

**Expected Response**:
```json
{
  "jsonrpc":"2.0",
  "id":19,
  "result":{
    "status":"success",
    "data":{
      "entity_id":"main:solid_019",
      "volume":312.8,
      "surface_area":402.1,
      "operation_result":"success"
    }
  }
}
```

---

## Tutorial: Workspace Management

### Step 6: Create Agent Workspace

**Create Isolated Workspace**:
```json
{"jsonrpc":"2.0","method":"workspace.create","params":{"name":"practice_session_01","base":"main"},"id":20}
```

**Expected Response**:
```json
{
  "jsonrpc":"2.0",
  "id":20,
  "result":{
    "status":"success",
    "data":{
      "workspace_id":"agent_alpha:practice_session_01",
      "branch_status":"clean",
      "created_at":"2025-11-24T10:40:00Z"
    }
  }
}
```

**Switch to Workspace**:
```json
{"jsonrpc":"2.0","method":"workspace.switch","params":{"workspace_id":"agent_alpha:practice_session_01"},"id":21}
```

**Work in Isolated Workspace** (all operations now affect this workspace):
```json
{"jsonrpc":"2.0","method":"entity.create.point","params":{"coordinates":[100,100,100]},"id":22}
```

**Check Workspace Status**:
```json
{"jsonrpc":"2.0","method":"workspace.status","params":{},"id":23}
```

**Expected Response**:
```json
{
  "jsonrpc":"2.0",
  "id":23,
  "result":{
    "status":"success",
    "data":{
      "workspace_id":"agent_alpha:practice_session_01",
      "branch_status":"modified",
      "entity_count":1,
      "operation_count":1,
      "can_merge":true
    }
  }
}
```

### Step 7: Merge Workspace

**Merge Back to Main**:
```json
{"jsonrpc":"2.0","method":"workspace.merge","params":{"source":"agent_alpha:practice_session_01","target":"main","strategy":"auto"},"id":24}
```

**Expected Response (success)**:
```json
{
  "jsonrpc":"2.0",
  "id":24,
  "result":{
    "status":"success",
    "data":{
      "merge_status":"completed",
      "entities_added":1,
      "conflicts":[]
    }
  }
}
```

**Handling Merge Conflicts**:
```json
{
  "jsonrpc":"2.0",
  "id":24,
  "error":{
    "code":"WORKSPACE_CONFLICT",
    "message":"Merge conflicts detected",
    "data":{
      "conflicts":[
        {
          "entity_id":"main:circle_003",
          "conflict_type":"both_modified",
          "resolution_options":["keep_source","keep_target","manual_merge"]
        }
      ]
    }
  }
}
```

**Resolve Conflict**:
```json
{"jsonrpc":"2.0","method":"workspace.resolve_conflict","params":{"entity_id":"main:circle_003","resolution":"keep_source"},"id":25}
```

---

## Tutorial: File Import/Export

### Step 8: Import STEP File

**Import CAD Model**:
```json
{"jsonrpc":"2.0","method":"file.import","params":{"format":"step","path":"/data/models/bracket.step","validate":true},"id":26}
```

**Expected Response**:
```json
{
  "jsonrpc":"2.0",
  "id":26,
  "result":{
    "status":"success",
    "data":{
      "import_status":"completed_with_warnings",
      "entities_imported":127,
      "entity_types":{"solid":5,"face":48},
      "total_volume":1250.5,
      "validation":{
        "topology_errors":0,
        "geometry_warnings":2
      }
    }
  }
}
```

### Step 9: Export to STL

**Export for 3D Printing**:
```json
{
  "jsonrpc":"2.0",
  "method":"file.export",
  "params":{
    "format":"stl",
    "entities":["main:solid_019"],
    "path":"/output/part.stl",
    "options":{
      "binary":true,
      "linear_deflection":0.1,
      "angular_deflection":0.5
    }
  },
  "id":27
}
```

**Expected Response**:
```json
{
  "jsonrpc":"2.0",
  "id":27,
  "result":{
    "status":"success",
    "data":{
      "export_status":"completed",
      "triangle_count":10240,
      "file_size_bytes":524288,
      "data_loss_warning":{
        "severity":"expected",
        "message":"Exact geometry approximated as mesh",
        "volume_error_percent":0.16
      }
    }
  }
}
```

---

## Tutorial: Operation History & Undo/Redo

### Step 10: Manage History

**List Recent Operations**:
```json
{"jsonrpc":"2.0","method":"history.list","params":{"limit":5},"id":28}
```

**Undo Last Operation**:
```json
{"jsonrpc":"2.0","method":"history.undo","params":{},"id":29}
```

**Expected Response**:
```json
{
  "jsonrpc":"2.0",
  "id":29,
  "result":{
    "status":"success",
    "data":{
      "undone_operation":{
        "operation_id":"op_1732450500_xyz789",
        "operation_type":"entity.create.point"
      },
      "current_position":27,
      "can_undo":true,
      "can_redo":true
    }
  }
}
```

**Redo Operation**:
```json
{"jsonrpc":"2.0","method":"history.redo","params":{},"id":30}
```

---

## Error Handling Patterns

### Pattern 1: Parameter Validation Error

**Invalid Request** (negative radius):
```json
{"jsonrpc":"2.0","method":"entity.create.circle","params":{"center":[0,0,0],"radius":-5},"id":31}
```

**Error Response**:
```json
{
  "jsonrpc":"2.0",
  "id":31,
  "error":{
    "code":"INVALID_PARAMETER",
    "message":"Radius must be greater than zero",
    "data":{
      "field":"radius",
      "provided_value":-5,
      "constraints":{"min":0.001,"max":1000000},
      "suggestion":"Specify --radius with a positive value",
      "recoverable":true
    }
  }
}
```

**Agent Self-Correction**:
```json
{"jsonrpc":"2.0","method":"entity.create.circle","params":{"center":[0,0,0],"radius":5},"id":32}
```

### Pattern 2: Entity Not Found

**Invalid Entity Reference**:
```json
{"jsonrpc":"2.0","method":"entity.query","params":{"entity_id":"main:nonexistent_999"},"id":33}
```

**Error Response**:
```json
{
  "jsonrpc":"2.0",
  "id":33,
  "error":{
    "code":"ENTITY_NOT_FOUND",
    "message":"Entity 'main:nonexistent_999' does not exist",
    "data":{
      "entity_id":"main:nonexistent_999",
      "workspace_id":"main",
      "suggestion":"Use entity.list to see available entities",
      "recoverable":true
    }
  }
}
```

**Agent Recovery**:
```json
{"jsonrpc":"2.0","method":"entity.list","params":{},"id":34}
```

### Pattern 3: Constraint Conflict

**Conflicting Constraints**:
```json
{"jsonrpc":"2.0","method":"constraint.apply","params":{"constraint_type":"parallel","entities":["main:line_006","main:line_007"]},"id":35}
```

**Error Response** (lines already constrained perpendicular):
```json
{
  "jsonrpc":"2.0",
  "id":35,
  "error":{
    "code":"CONSTRAINT_CONFLICT",
    "message":"Constraint conflicts with existing perpendicular constraint",
    "data":{
      "conflicting_constraint_id":"main:constraint_008",
      "conflicting_constraint_type":"perpendicular",
      "suggestion":"Remove conflicting constraint first using constraint.remove",
      "recoverable":true
    }
  }
}
```

---

## Agent Learning Strategy

### Success Metrics Tracking

**After 100 Operations** (SC-011):
- Track operation success rate
- Measure error rate reduction (target: 50%+ improvement)
- Analyze common error patterns

**Self-Assessment Query**:
```json
{"jsonrpc":"2.0","method":"agent.metrics","params":{"agent_id":"agent_alpha"},"id":36}
```

**Expected Response**:
```json
{
  "jsonrpc":"2.0",
  "id":36,
  "result":{
    "status":"success",
    "data":{
      "total_operations":150,
      "success_rate":0.93,
      "error_rate_first_10":0.40,
      "error_rate_last_10":0.05,
      "improvement_percent":87.5,
      "most_common_errors":["INVALID_PARAMETER"],
      "avg_correction_attempts":1.2
    }
  }
}
```

### Test Scenarios

**Built-in Test Scenarios** (FR-028):
```json
{"jsonrpc":"2.0","method":"scenario.run","params":{"scenario_id":"basic_2d_sketch"},"id":37}
```

**Expected Response**:
```json
{
  "jsonrpc":"2.0",
  "id":37,
  "result":{
    "status":"success",
    "data":{
      "scenario_id":"basic_2d_sketch",
      "test_result":"pass",
      "expected_entities":5,
      "actual_entities":5,
      "expected_constraints":3,
      "actual_constraints":3,
      "all_constraints_satisfied":true
    }
  }
}
```

---

## Performance Benchmarks

**Expected Performance** (from SC-001, SC-002, SC-003):

| Operation | Target Time | Typical Time |
|-----------|-------------|--------------|
| Create point/line/circle | <100ms | 5-15ms |
| Apply constraint | <500ms | ~200ms |
| Extrude solid | <1s | ~150ms |
| Boolean operation | <1s | ~600ms |
| Import 10MB STEP | <5s | ~3s |

**Agent Optimization**:
- Batch independent operations when possible
- Minimize workspace switches
- Cache frequently queried entities
- Use validation only when necessary

---

## Common Workflows

### Workflow 1: Create Parametric Bracket

```json
// 1. Create base sketch
{"jsonrpc":"2.0","method":"entity.create.line","params":{"start":[0,0,0],"end":[50,0,0]},"id":1}
{"jsonrpc":"2.0","method":"entity.create.line","params":{"start":[50,0,0],"end":[50,30,0]},"id":2}
{"jsonrpc":"2.0","method":"entity.create.line","params":{"start":[50,30,0],"end":[0,30,0]},"id":3}
{"jsonrpc":"2.0","method":"entity.create.line","params":{"start":[0,30,0],"end":[0,0,0]},"id":4}

// 2. Apply constraints
{"jsonrpc":"2.0","method":"constraint.apply","params":{"constraint_type":"distance","entities":["line_1","line_3"],"parameters":{"distance":50}},"id":5}

// 3. Extrude to 3D
{"jsonrpc":"2.0","method":"entity.create.sketch","params":{"entities":["line_1","line_2","line_3","line_4"]},"id":6}
{"jsonrpc":"2.0","method":"solid.extrude","params":{"sketch_id":"sketch_6","distance":10},"id":7}

// 4. Add mounting hole
{"jsonrpc":"2.0","method":"entity.create.circle","params":{"center":[25,15,0],"radius":5},"id":8}
{"jsonrpc":"2.0","method":"entity.create.sketch","params":{"entities":["circle_8"]},"id":9}
{"jsonrpc":"2.0","method":"solid.extrude","params":{"sketch_id":"sketch_9","distance":10},"id":10}
{"jsonrpc":"2.0","method":"solid.boolean","params":{"operation":"subtract","bodies":["solid_7","solid_10"]},"id":11}
```

### Workflow 2: Multi-Agent Collaboration

**Agent A** (creates base part):
```json
{"jsonrpc":"2.0","method":"workspace.create","params":{"name":"agent_a_part","base":"main"},"id":1}
// ... create geometry ...
{"jsonrpc":"2.0","method":"workspace.merge","params":{"source":"agent_a_part","target":"main"},"id":N}
```

**Agent B** (creates complementary part):
```json
{"jsonrpc":"2.0","method":"workspace.create","params":{"name":"agent_b_part","base":"main"},"id":1}
// ... create geometry ...
{"jsonrpc":"2.0","method":"workspace.merge","params":{"source":"agent_b_part","target":"main"},"id":M}
```

**Conflict Resolution** (if both modified same entity):
```json
{"jsonrpc":"2.0","method":"workspace.resolve_conflict","params":{"entity_id":"main:solid_001","resolution":"keep_source"},"id":1}
```

---

## Troubleshooting

### Issue: Command Not Recognized

**Symptom**: `INVALID_COMMAND` error

**Solution**: Check method name spelling and verify against CLI API contract

### Issue: Topology Error After Boolean Operation

**Symptom**: `TOPOLOGY_ERROR` with invalid manifold

**Solution**:
1. Validate input solids before boolean: `entity.query` with validation
2. Check for coincident faces or edges
3. Try simplifying geometry or adjusting tolerances

### Issue: Workspace Merge Conflicts

**Symptom**: `WORKSPACE_CONFLICT` error

**Solution**:
1. Query conflict details from error response
2. Use `workspace.resolve_conflict` with appropriate resolution strategy
3. For complex conflicts, manually merge entities

---

## Next Steps

1. **Practice Basic Operations**: Complete all tutorials in order
2. **Experiment with Constraints**: Apply different constraint types
3. **Build Complex Models**: Combine multiple operations
4. **Test Workspace Collaboration**: Create multiple branches and merge
5. **Analyze Performance Metrics**: Use `agent.metrics` to track improvement
6. **Run Test Scenarios**: Validate skills with built-in scenarios

---

## Reference

**Full API Documentation**: See `contracts/cli-api.md`
**Data Model**: See `data-model.md`
**Research Background**: See `research.md`
**Implementation Plan**: See `plan.md`

---

**Conclusion**: This quickstart guide covers all essential workflows for AI agents to practice CAD operations, manage workspaces, and learn from feedback. Agents should achieve 90%+ success rate after completing these tutorials (per SC-005).
