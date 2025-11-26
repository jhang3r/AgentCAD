"""
Debug script to test entity creation via controller.

This script will:
1. Create a workspace via CLI
2. Create an agent with that workspace
3. Create entities via controller.execute_operation
4. List entities via CLI
5. Compare results
"""

import subprocess
import json
import sys
from pathlib import Path
from src.multi_agent.controller import Controller

# Setup
workspace_id = "debug_workspace"
repo_root = Path(__file__).parent

print("=" * 60)
print("DEBUG: Entity Creation Test")
print("=" * 60)

# Step 1: Create workspace via CLI
print(f"\n1. Creating workspace '{workspace_id}' via CLI...")
result = subprocess.run(
    [sys.executable, "-m", "src.agent_interface.cli", "workspace.create",
     "--workspace_id", workspace_id],
    capture_output=True,
    text=True,
    timeout=10,
    cwd=repo_root
)

print(f"   Return code: {result.returncode}")
print(f"   Stdout: {result.stdout}")
if result.stderr:
    print(f"   Stderr: {result.stderr}")

if result.returncode != 0:
    print("   ERROR: Failed to create workspace!")
    sys.exit(1)

# Step 2: Create controller and agent
print(f"\n2. Creating controller and agent...")
controller = Controller(controller_id="debug_controller", max_concurrent_agents=5)
agent = controller.create_agent(
    agent_id="debug_agent",
    role_name="modeler",
    workspace_id=workspace_id
)
print(f"   Agent created: {agent.agent_id}")
print(f"   Agent workspace: {agent.workspace_id}")
print(f"   Agent role: {agent.role.name}")

# Step 3: Create entities via controller
print(f"\n3. Creating 3 entities via controller.execute_operation...")
for i in range(3):
    params = {
        "x": float(i * 10),
        "y": float(i * 10),
        "z": 0.0,
        "workspace_id": workspace_id
    }
    print(f"\n   Creating point {i} at ({params['x']}, {params['y']}, {params['z']})...")
    print(f"   Params: {params}")

    try:
        result = controller.execute_operation(
            agent_id=agent.agent_id,
            operation="entity.create_point",
            params=params
        )
        print(f"   Result: {result}")
        print(f"   Success: {result.get('success')}")
        if "entity_id" in result:
            print(f"   Entity ID: {result['entity_id']}")
    except Exception as e:
        print(f"   ERROR: {e}")
        import traceback
        traceback.print_exc()

# Step 4: Check agent metrics
print(f"\n4. Agent metrics:")
print(f"   Operation count: {agent.operation_count}")
print(f"   Success count: {agent.success_count}")
print(f"   Error count: {agent.error_count}")
print(f"   Created entities: {agent.created_entities}")

# Step 5: List entities via CLI
print(f"\n5. Listing entities via CLI...")
result = subprocess.run(
    [sys.executable, "-m", "src.agent_interface.cli", "entity.list",
     "--workspace_id", workspace_id],
    capture_output=True,
    text=True,
    timeout=10,
    cwd=repo_root
)

print(f"   Return code: {result.returncode}")
print(f"   Stdout: {result.stdout}")
if result.stderr:
    print(f"   Stderr: {result.stderr}")

if result.returncode == 0:
    response = json.loads(result.stdout)
    entities = response.get("entities", [])
    print(f"   Entity count: {len(entities)}")
    for entity in entities:
        print(f"   - {entity.get('entity_id')}: {entity.get('type')}")
else:
    print("   ERROR: Failed to list entities!")

# Step 6: Cleanup
print(f"\n6. Cleanup...")
result = subprocess.run(
    [sys.executable, "-m", "src.agent_interface.cli", "workspace.delete",
     "--workspace_id", workspace_id],
    capture_output=True,
    text=True,
    timeout=10,
    cwd=repo_root
)
print(f"   Workspace deleted: {result.returncode == 0}")

print("\n" + "=" * 60)
print("DEBUG: Test Complete")
print("=" * 60)
