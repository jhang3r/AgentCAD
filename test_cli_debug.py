"""
Debug workspace resolution in CLI
"""

import os
import subprocess
import json
import sys
from pathlib import Path

repo_root = Path(__file__).parent
workspace_dir = (repo_root / "data/workspaces/test_cli_debug").absolute()
workspace_dir.mkdir(parents=True, exist_ok=True)

os.environ["MULTI_AGENT_WORKSPACE_DIR"] = str(workspace_dir)

print("Testing workspace resolution...")

# Test 1: Create workspace and check its ID
result = subprocess.run(
    [sys.executable, "-m", "src.agent_interface.cli", "workspace.create",
     "--workspace_id", "ws_test"],
    capture_output=True,
    text=True,
    timeout=10,
    cwd=repo_root,
    env=os.environ
)

if result.returncode == 0:
    response = json.loads(result.stdout)
    created_ws_id = response['result']['data']['workspace_id']
    print(f"1. Created workspace ID: {created_ws_id}")
else:
    print(f"ERROR creating workspace: {result.stderr}")
    sys.exit(1)

# Test 2: Create entity with SHORT workspace_id
result = subprocess.run(
    [sys.executable, "-m", "src.agent_interface.cli", "entity.create_point",
     "--params", json.dumps({"x": 10.0, "y": 20.0, "z": 0.0, "workspace_id": "ws_test"})],
    capture_output=True,
    text=True,
    timeout=10,
    cwd=repo_root,
    env=os.environ
)

if result.returncode == 0:
    response = json.loads(result.stdout)
    entity_id = response['result']['data']['entity_id']
    entity_ws = response['result']['data']['workspace_id']
    print(f"2. Created entity: {entity_id}")
    print(f"   Entity workspace_id: {entity_ws}")
else:
    print(f"ERROR creating entity: {result.stderr}")

# Test 3: List entities with SHORT workspace_id
print(f"3. Listing entities with workspace_id='ws_test'...")
result = subprocess.run(
    [sys.executable, "-m", "src.agent_interface.cli", "entity.list",
     "--workspace_id", "ws_test"],
    capture_output=True,
    text=True,
    timeout=10,
    cwd=repo_root,
    env=os.environ
)

if result.returncode == 0:
    response = json.loads(result.stdout)
    result_data = response.get("result", {}).get("data", {})
    entities = result_data.get("entities", [])
    print(f"   Entities found: {len(entities)}")
    if entities:
        for ent in entities:
            print(f"   - {ent['entity_id']}")
else:
    print(f"   ERROR: {result.stderr}")

# Test 4: List entities with FULL workspace_id
print(f"4. Listing entities with workspace_id='{created_ws_id}'...")
result = subprocess.run(
    [sys.executable, "-m", "src.agent_interface.cli", "entity.list",
     "--workspace_id", created_ws_id],
    capture_output=True,
    text=True,
    timeout=10,
    cwd=repo_root,
    env=os.environ
)

if result.returncode == 0:
    response = json.loads(result.stdout)
    result_data = response.get("result", {}).get("data", {})
    entities = result_data.get("entities", [])
    print(f"   Entities found: {len(entities)}")
    if entities:
        for ent in entities:
            print(f"   - {ent['entity_id']}")
else:
    print(f"   ERROR: {result.stderr}")

del os.environ["MULTI_AGENT_WORKSPACE_DIR"]
