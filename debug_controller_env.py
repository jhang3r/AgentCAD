"""
Debug controller environment variable handling
"""

import os
import subprocess
import json
import sys
from pathlib import Path

# Temporarily patch controller to log subprocess calls
original_popen = subprocess.Popen

def logged_popen(*args, **kwargs):
    print(f"\n>>> subprocess.Popen called:")
    print(f"    cmd: {args[0] if args else kwargs.get('args', 'N/A')}")
    print(f"    cwd: {kwargs.get('cwd', 'not set')}")
    if 'env' in kwargs and kwargs['env']:
        workspace_dir_env = kwargs['env'].get('MULTI_AGENT_WORKSPACE_DIR', 'NOT SET')
        print(f"    MULTI_AGENT_WORKSPACE_DIR: {workspace_dir_env}")
    print(f"    stdin: {kwargs.get('stdin', 'not set')}")
    return original_popen(*args, **kwargs)

subprocess.Popen = logged_popen

# Now run the test scenario
from src.multi_agent.controller import Controller

repo_root = Path(__file__).parent
workspace_dir = Path("data/workspaces/test_env_debug")
workspace_dir.mkdir(parents=True, exist_ok=True)

print("=" * 60)
print("Controller Environment Debug")
print("=" * 60)

# Set env var like test does
os.environ["MULTI_AGENT_WORKSPACE_DIR"] = str(workspace_dir)
print(f"\n1. Test sets env var: {os.environ['MULTI_AGENT_WORKSPACE_DIR']}")

# Create controller
controller = Controller(
    controller_id="test_env",
    max_concurrent_agents=5,
    workspace_dir=str(workspace_dir)
)
print(f"2. Controller workspace_dir: {controller.workspace_dir}")

# Create workspace via direct CLI (like test does)
print(f"\n3. Test creates workspace via direct CLI call:")
workspace_id = "ws_env"
result = subprocess.run(
    [sys.executable, "-m", "src.agent_interface.cli", "workspace.create",
     "--workspace_id", workspace_id],
    capture_output=True,
    text=True,
    timeout=10,
    cwd=repo_root,
    env=os.environ
)
print(f"   Result: {result.returncode == 0}")

# Create agent
agent = controller.create_agent(
    agent_id="agent_env",
    role_name="modeler",
    workspace_id=workspace_id
)

# Create entity via controller
print(f"\n4. Test creates entity via controller.execute_operation:")
result = controller.execute_operation(
    agent_id=agent.agent_id,
    operation="entity.create_point",
    params={"x": 10.0, "y": 20.0, "z": 0.0, "workspace_id": workspace_id}
)
print(f"   Result: {result.get('success')}")

# List entities via direct CLI (like test does)
print(f"\n5. Test lists entities via direct CLI call:")
result = subprocess.run(
    [sys.executable, "-m", "src.agent_interface.cli", "entity.list",
     "--workspace_id", workspace_id],
    capture_output=True,
    text=True,
    timeout=10,
    cwd=repo_root,
    env=os.environ
)
print(f"   Result: {result.returncode == 0}")
if result.returncode == 0:
    response = json.loads(result.stdout)
    result_data = response.get("result", {}).get("data", {})
    entities = result_data.get("entities", [])
    print(f"   Entities: {len(entities)}")

# Cleanup
subprocess.Popen = original_popen  # Restore
del os.environ["MULTI_AGENT_WORKSPACE_DIR"]

print("\n" + "=" * 60)
