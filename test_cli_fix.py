"""
Simple test to verify CLI workspace_dir fix
"""

import os
import subprocess
import json
import sys
from pathlib import Path
from src.multi_agent.controller import Controller

repo_root = Path(__file__).parent
workspace_dir = (repo_root / "data/workspaces/test_cli_fix").absolute()
workspace_dir.mkdir(parents=True, exist_ok=True)

os.environ["MULTI_AGENT_WORKSPACE_DIR"] = str(workspace_dir)

print("Testing CLI workspace_dir fix...")
print(f"workspace_dir: {workspace_dir}")

# Create controller
controller = Controller(
    controller_id="test_fix",
    max_concurrent_agents=5,
    workspace_dir=str(workspace_dir)
)

# Create workspace via CLI
workspace_id = "ws_fix"
result = subprocess.run(
    [sys.executable, "-m", "src.agent_interface.cli", "workspace.create",
     "--workspace_id", workspace_id],
    capture_output=True,
    text=True,
    timeout=10,
    cwd=repo_root,
    env=os.environ
)
print(f"1. Create workspace: {'OK' if result.returncode == 0 else 'FAIL'}")

# Create agent
agent = controller.create_agent(
    agent_id="agent_fix",
    role_name="modeler",
    workspace_id=workspace_id
)

# Create entity via controller
result = controller.execute_operation(
    agent_id=agent.agent_id,
    operation="entity.create_point",
    params={"x": 10.0, "y": 20.0, "z": 0.0, "workspace_id": workspace_id}
)
print(f"2. Create entity: {'OK' if result.get('success') else 'FAIL'}")

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
print(f"3. List entities via CLI: {'OK' if result.returncode == 0 else 'FAIL'}")

if result.returncode == 0:
    response = json.loads(result.stdout)
    result_data = response.get("result", {}).get("data", {})
    entities = result_data.get("entities", [])
    print(f"4. Entities found: {len(entities)}")
    if len(entities) == 1:
        print("✓ SUCCESS! CLI is now reading from the correct database!")
    else:
        print("✗ FAIL! Still getting 0 entities")
else:
    print(f"✗ ERROR: {result.stderr}")

# Cleanup
del os.environ["MULTI_AGENT_WORKSPACE_DIR"]
