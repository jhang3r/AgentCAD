"""
Debug workspace ID handling
"""

import subprocess
import json
import sys
from pathlib import Path

repo_root = Path(__file__).parent

print("Testing workspace ID handling...")

# Create workspace with short ID
workspace_id_short = "test_ws"
result = subprocess.run(
    [sys.executable, "-m", "src.agent_interface.cli", "workspace.create",
     "--workspace_id", workspace_id_short],
    capture_output=True,
    text=True,
    timeout=10,
    cwd=repo_root
)

print(f"\n1. Create workspace with ID='{workspace_id_short}'")
print(f"   Return code: {result.returncode}")
if result.returncode == 0:
    response = json.loads(result.stdout)
    actual_ws_id = response['result']['data']['workspace_id']
    print(f"   Actual workspace_id returned: '{actual_ws_id}'")

# Try to create entity with SHORT workspace ID
print(f"\n2. Create entity with workspace_id='{workspace_id_short}'")
result = subprocess.run(
    [sys.executable, "-m", "src.agent_interface.cli", "entity.create_point",
     "--params", json.dumps({"x": 10.0, "y": 20.0, "z": 0.0, "workspace_id": workspace_id_short})],
    capture_output=True,
    text=True,
    timeout=10,
    cwd=repo_root
)
print(f"   Return code: {result.returncode}")
if result.returncode == 0:
    response = json.loads(result.stdout)
    print(f"   Entity created: {response['result']['data']['entity_id']}")
else:
    print(f"   ERROR: {result.stderr}")

# Try to list entities with SHORT workspace ID
print(f"\n3. List entities with workspace_id='{workspace_id_short}'")
result = subprocess.run(
    [sys.executable, "-m", "src.agent_interface.cli", "entity.list",
     "--workspace_id", workspace_id_short],
    capture_output=True,
    text=True,
    timeout=10,
    cwd=repo_root
)
print(f"   Return code: {result.returncode}")
if result.returncode == 0:
    response = json.loads(result.stdout)
    entities = response['result']['data']['entities']
    print(f"   Entities found: {len(entities)}")
else:
    print(f"   ERROR: {result.stderr}")

# Cleanup
subprocess.run(
    [sys.executable, "-m", "src.agent_interface.cli", "workspace.delete",
     "--workspace_id", workspace_id_short],
    capture_output=True,
    timeout=10,
    cwd=repo_root
)
