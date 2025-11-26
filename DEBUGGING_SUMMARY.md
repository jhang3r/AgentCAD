# Integration Test Debugging Summary

**Date**: 2025-11-26
**Issue**: Integration tests showing 0 entities when 5 expected

## Bugs Found and Fixed

### 1. JSON Parsing - Tests Not Handling Multiple Output Lines
**File**: `tests/multi_agent_integration/test_concurrent_agents.py:184-194`
**Problem**: CLI outputs both logging lines AND JSON response, but tests only used `json.loads(result.stdout)` which would fail on multi-line output.
**Fix**: Updated to find the JSON line starting with `{`:
```python
response_line = None
for line in result.stdout.strip().split('\n'):
    if line.startswith('{'):
        response_line = line
        break
response = json.loads(response_line)
```
**Status**: ✅ FIXED

### 2. JSON-RPC Response Parsing - Wrong Line Selected
**File**: `src/agent_interface/cli.py:1843-1846`
**Problem**: CLI's `main()` function never read the `MULTI_AGENT_WORKSPACE_DIR` environment variable, always using default "data/workspaces/main".
**Fix**: Added environment variable reading:
```python
workspace_dir = os.environ.get("MULTI_AGENT_WORKSPACE_DIR", "data/workspaces/main")
cli = CLI(workspace_dir=workspace_dir)
```
**Status**: ✅ FIXED

### 3. Controller Parsing Wrong stdout Line
**File**: `src/multi_agent/controller.py:223-235`
**Problem**: Controller took the FIRST line of stdout, but that's often a logging line, not the JSON response.
**Fix**: Updated to find the JSON-RPC response line:
```python
response_line = None
for line in stdout.strip().split('\n'):
    if line.startswith('{'):
        response_line = line
        break
if response_line is None:
    raise ValueError("No JSON response found in CLI output")
response = json.loads(response_line)
```
**Status**: ✅ FIXED

### 4. Workspace Name Resolution
**File**: `src/agent_interface/cli.py:655-660` and `401-406`
**Problem**: CLI's `get_workspace()` only does exact ID lookups, failing when short names like "ws_test" are used instead of full IDs like "default_agent:ws_test".
**Fix**: Added fallback resolution for short names:
```python
ws = self.workspace_manager.get_workspace(workspace_id)
if ws:
    workspace_id = ws.workspace_id
elif ":" not in workspace_id:
    # Try with default_agent prefix
    full_id = f"default_agent:{workspace_id}"
    ws = self.workspace_manager.get_workspace(full_id)
    if ws:
        workspace_id = ws.workspace_id
```
**Status**: ✅ FIXED (in _handle_entity_list and _handle_create_point)

### 5. Integration Test Files Using Relative Paths
**Files**: `tests/multi_agent_integration/test_*.py`
**Problem**: Tests used relative paths for workspace_dir which could cause resolution issues.
**Fix**: Changed to absolute paths:
```python
workspace_dir = (Path(__file__).parent.parent.parent / "data/workspaces/test_concurrent").absolute()
```
**Status**: ✅ FIXED (test_concurrent_agents.py, test_workspace_merge_workflow.py, test_merge_conflicts.py)

## Test Results After Fixes

### ✅ Pure CLI Test - PASSING
When both create and list are done via CLI command-line args:
- Create workspace: ✅ OK
- Create entity: ✅ OK
- List entities: ✅ OK (1 entity found)

**Conclusion**: CLI itself works correctly.

### ❌ Controller + CLI Test - FAILING
When controller creates entities (JSON-RPC stdin) and test lists them (command-line args):
- Create workspace: ✅ OK
- Create entity via controller: ✅ OK
- List entities via CLI: ❌ FAIL (0 entities found)

**Status**: Still failing despite all fixes

## Analysis

The entity IS in the database (verified via direct SQL query), but CLI's entity.list returns 0 entities. This suggests:

1. **Database Isolation Issue**: Each CLI invocation might be reading from a different database instance
2. **Transaction/Commit Issue**: Entities created but not properly committed
3. **Workspace Filtering Issue**: Query logic has a bug

## Verification Done

- ✅ Database file exists and contains entity
- ✅ Workspace exists with correct ID
- ✅ Entity has correct workspace_id in database
- ✅ Pure CLI operations work end-to-end
- ✅ All JSON parsing fixed
- ✅ Workspace resolution fixed
- ❌ Controller + CLI interaction still broken

## Next Steps Required

1. **Investigate Database Connection Handling**: Check if multiple CLI processes share database state properly
2. **Add Debug Logging**: Add logging to entity_manager.list_entities() to see actual SQL query and results
3. **Check Transaction Handling**: Verify entity writes are committed before CLI reads
4. **Review Architecture**: May need architectural changes to how CLI and controller interact

## Files Modified

1. `src/agent_interface/cli.py` - Lines 655-660, 401-406, 1844-1846
2. `src/multi_agent/controller.py` - Lines 223-235
3. `tests/multi_agent_integration/test_concurrent_agents.py` - Lines 29, 184-194
4. `tests/multi_agent_integration/test_workspace_merge_workflow.py` - Line 27
5. `tests/multi_agent_integration/test_merge_conflicts.py` - Line 28

## Test Artifacts Created

- `debug_entity_creation.py` - Verified entity creation works
- `debug_json_response.py` - Verified JSON structure
- `debug_workspace_id.py` - Verified workspace ID handling
- `test_pure_cli.py` - Verified pure CLI works (SUCCESS)
- `test_cli_fix.py` - Verified controller + CLI (FAILS)
- `check_database.py` - Direct database inspection

---

**Summary**: Found and fixed 5 bugs in JSON parsing, environment handling, and workspace resolution. Pure CLI works, but controller-CLI interaction still has an unresolved issue preventing integration tests from passing. Further investigation needed into database connection handling and transaction management.
