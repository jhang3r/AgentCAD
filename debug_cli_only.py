"""
Test entity creation and listing purely via CLI (no controller)
"""

import os
import subprocess
import json
import sys
from pathlib import Path

repo_root = Path(__file__).parent
workspace_dir = Path("data/workspaces/test_cli_only")
workspace_dir.mkdir(parents=True, exist_ok=True)

print("=" * 60)
print("CLI-Only Test")
print("=" * 60)

# Set env var
os.environ["MULTI_AGENT_WORKSPACE_DIR"] = str(workspace_dir)

# Create workspace
workspace_id = "ws_cli_only"
result = subprocess.run(
    [sys.executable, "-m", "src.agent_interface.cli", "workspace.create",
     "--workspace_id", workspace_id],
    capture_output=True,
    text=True,
    timeout=10,
    cwd=repo_root,
    env=os.environ
)
print(f"\n1. Create workspace: {result.returncode == 0}")

# Create entity via CLI
result = subprocess.run(
    [sys.executable, "-m", "src.agent_interface.cli", "entity.create_point",
     "--params", json.dumps({"x": 10.0, "y": 20.0, "z": 0.0, "workspace_id": workspace_id})],
    capture_output=True,
    text=True,
    timeout=10,
    cwd=repo_root,
    env=os.environ
)
print(f"2. Create entity via CLI: {result.returncode == 0}")
if result.returncode == 0:
    response = json.loads(result.stdout)
    entity_id = response['result']['data']['entity_id']
    print(f"   Entity ID: {entity_id}")

# List entities via CLI
result = subprocess.run(
    [sys.executable, "-m", "src.agent_interface.cli", "entity.list",
     "--workspace_id", workspace_id],
    capture_output=True,
    text=True,
    timeout=10,
    cwd=repo_root,
    env=os.environ
)
print(f"3. List entities via CLI: {result.returncode == 0}")
if result.returncode == 0:
    response = json.loads(result.stdout)
    result_data = response.get("result", {}).get("data", {})
    entities = result_data.get("entities", [])
    print(f"   Entities found: {len(entities)}")
else:
    print(f"   ERROR: {result.stderr}")

# Cleanup
del os.environ["MULTI_AGENT_WORKSPACE_DIR"]
subprocess.run(
    [sys.executable, "-m", "src.agent_interface.cli", "workspace.delete",
     "--workspace_id", workspace_id],
    capture_output=True,
    timeout=10,
    cwd=repo_root
)

print("\n" + "=" * 60)
