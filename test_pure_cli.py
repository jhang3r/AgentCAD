"""
Test pure CLI operations (no controller)
"""

import os
import subprocess
import json
import sys
from pathlib import Path

repo_root = Path(__file__).parent
workspace_dir = (repo_root / "data/workspaces/test_pure_cli").absolute()
workspace_dir.mkdir(parents=True, exist_ok=True)

os.environ["MULTI_AGENT_WORKSPACE_DIR"] = str(workspace_dir)

print("Pure CLI Test (no controller)")
print(f"workspace_dir: {workspace_dir}")

# Create workspace
result = subprocess.run(
    [sys.executable, "-m", "src.agent_interface.cli", "workspace.create",
     "--workspace_id", "ws_pure"],
    capture_output=True,
    text=True,
    timeout=10,
    cwd=repo_root,
    env=os.environ
)
print(f"1. Create workspace: {'OK' if result.returncode == 0 else 'FAIL'}")

# Create entity
result = subprocess.run(
    [sys.executable, "-m", "src.agent_interface.cli", "entity.create_point",
     "--params", json.dumps({"x": 10.0, "y": 20.0, "z": 0.0, "workspace_id": "ws_pure"})],
    capture_output=True,
    text=True,
    timeout=10,
    cwd=repo_root,
    env=os.environ
)
print(f"2. Create entity: {'OK' if result.returncode == 0 else 'FAIL'}")
if result.returncode == 0:
    # Find JSON line
    for line in result.stdout.split('\n'):
        if line.startswith('{'):
            response = json.loads(line)
            print(f"   Entity: {response['result']['data']['entity_id']}")
            break

# List entities
result = subprocess.run(
    [sys.executable, "-m", "src.agent_interface.cli", "entity.list",
     "--workspace_id", "ws_pure"],
    capture_output=True,
    text=True,
    timeout=10,
    cwd=repo_root,
    env=os.environ
)
print(f"3. List entities: {'OK' if result.returncode == 0 else 'FAIL'}")
if result.returncode == 0:
    for line in result.stdout.split('\n'):
        if line.startswith('{'):
            response = json.loads(line)
            entities = response['result']['data']['entities']
            print(f"   Entities found: {len(entities)}")
            if len(entities) > 0:
                print("   SUCCESS! Pure CLI works!")
            else:
                print("   FAIL! Pure CLI also returns 0 entities")
            break

del os.environ["MULTI_AGENT_WORKSPACE_DIR"]
