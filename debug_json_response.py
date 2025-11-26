"""
Debug script to see the exact JSON response structure from entity.list
"""

import subprocess
import json
import sys
from pathlib import Path

repo_root = Path(__file__).parent

print("=" * 60)
print("DEBUG: JSON Response Structure")
print("=" * 60)

# Create a workspace
workspace_id = "debug_json"
result = subprocess.run(
    [sys.executable, "-m", "src.agent_interface.cli", "workspace.create",
     "--workspace_id", workspace_id],
    capture_output=True,
    text=True,
    timeout=10,
    cwd=repo_root
)
print(f"\n1. Created workspace: {result.returncode == 0}")

# Create an entity
result = subprocess.run(
    [sys.executable, "-m", "src.agent_interface.cli", "entity.create_point",
     "--params", json.dumps({"x": 10.0, "y": 20.0, "z": 0.0, "workspace_id": workspace_id})],
    capture_output=True,
    text=True,
    timeout=10,
    cwd=repo_root
)
print(f"2. Created entity: {result.returncode == 0}")
if result.returncode == 0:
    print(f"   Response: {result.stdout[:200]}...")

# List entities
result = subprocess.run(
    [sys.executable, "-m", "src.agent_interface.cli", "entity.list",
     "--workspace_id", workspace_id],
    capture_output=True,
    text=True,
    timeout=10,
    cwd=repo_root
)

print(f"\n3. List entities - Return code: {result.returncode}")
print(f"\n4. Raw stdout:")
print(result.stdout)
print("\n5. Parsed JSON:")
response = json.loads(result.stdout)
print(json.dumps(response, indent=2))

print("\n6. Accessing entities:")
print(f"   response.keys() = {list(response.keys())}")
print(f"   response.get('entities') = {response.get('entities')}")
print(f"   response.get('result') = {response.get('result', {}).keys() if response.get('result') else None}")
if response.get('result'):
    print(f"   response['result'].keys() = {list(response['result'].keys())}")
    if response['result'].get('data'):
        print(f"   response['result']['data'].keys() = {list(response['result']['data'].keys())}")
        print(f"   response['result']['data']['entities'] length = {len(response['result']['data'].get('entities', []))}")

# Cleanup
subprocess.run(
    [sys.executable, "-m", "src.agent_interface.cli", "workspace.delete",
     "--workspace_id", workspace_id],
    capture_output=True,
    text=True,
    timeout=10,
    cwd=repo_root
)

print("\n" + "=" * 60)
