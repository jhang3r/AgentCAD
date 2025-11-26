"""
Debug script that mimics the exact test scenario
"""

import os
import subprocess
import json
import sys
from pathlib import Path
from src.multi_agent.controller import Controller

repo_root = Path(__file__).parent

print("=" * 60)
print("Mimicking Test Scenario")
print("=" * 60)

# Step 1: Setup like the test fixture
workspace_dir = Path("data/workspaces/test_mimic")
if workspace_dir.exists():
    import shutil
    shutil.rmtree(workspace_dir)
workspace_dir.mkdir(parents=True, exist_ok=True)

print(f"\n1. Workspace directory: {workspace_dir}")
print(f"   Absolute: {workspace_dir.absolute()}")

# Create controller with RELATIVE path (like test)
controller = Controller(
    controller_id="test_mimic",
    max_concurrent_agents=10,
    workspace_dir=str(workspace_dir)  # RELATIVE path as string
)

# Set env var for subprocess calls (like test)
os.environ["MULTI_AGENT_WORKSPACE_DIR"] = str(workspace_dir)

print(f"\n2. Controller workspace_dir: {controller.workspace_dir}")
print(f"   Env var set: {os.environ.get('MULTI_AGENT_WORKSPACE_DIR')}")

# Step 2: Create workspace via subprocess CLI (like test line 105-114)
workspace_id = "ws_test"
result = subprocess.run(
    ["python", "-m", "src.agent_interface.cli", "workspace.create",
     "--workspace_id", workspace_id],
    capture_output=True,
    text=True,
    timeout=10,
    cwd=repo_root,  # Same as test
    env=os.environ
)

print(f"\n3. Create workspace via CLI")
print(f"   Return code: {result.returncode}")
print(f"   CWD: {repo_root}")
if result.returncode != 0:
    print(f"   ERROR: {result.stderr}")
else:
    response = json.loads(result.stdout)
    print(f"   Created: {response['result']['data']['workspace_id']}")

# Step 3: Create agent via controller (like test line 117-121)
agent = controller.create_agent(
    agent_id="agent_test",
    role_name="modeler",
    workspace_id=workspace_id
)

print(f"\n4. Create agent")
print(f"   Agent ID: {agent.agent_id}")
print(f"   Agent workspace: {agent.workspace_id}")

# Step 4: Create entity via controller (like test line 130-139)
result = controller.execute_operation(
    agent_id=agent.agent_id,
    operation="entity.create_point",
    params={
        "x": 10.0,
        "y": 20.0,
        "z": 0.0,
        "workspace_id": agent.workspace_id
    }
)

print(f"\n5. Create entity via controller.execute_operation")
print(f"   Success: {result.get('success')}")
print(f"   Entity ID: {result.get('entity_id', 'N/A')}")

# Step 5: List entities via subprocess CLI (like test line 173-181)
result = subprocess.run(
    ["python", "-m", "src.agent_interface.cli", "entity.list",
     "--workspace_id", agent.workspace_id],
    capture_output=True,
    text=True,
    timeout=10,
    cwd=repo_root,
    env=os.environ
)

print(f"\n6. List entities via CLI")
print(f"   Return code: {result.returncode}")
print(f"   CWD: {repo_root}")
print(f"   workspace_id param: {agent.workspace_id}")

if result.returncode == 0:
    response = json.loads(result.stdout)
    # Use the FIXED parsing
    result_data = response.get("result", {}).get("data", {})
    entities = result_data.get("entities", [])
    print(f"   Entities found: {len(entities)}")
    for entity in entities:
        print(f"     - {entity['entity_id']}")
else:
    print(f"   ERROR: {result.stderr}")

# Cleanup
del os.environ["MULTI_AGENT_WORKSPACE_DIR"]
subprocess.run(
    ["python", "-m", "src.agent_interface.cli", "workspace.delete",
     "--workspace_id", workspace_id],
    capture_output=True,
    timeout=10,
    cwd=repo_root
)

print("\n" + "=" * 60)
