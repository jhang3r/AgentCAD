"""
Check database immediately after controller creates entity
"""

import os
import sqlite3
import sys
from pathlib import Path
from src.multi_agent.controller import Controller

repo_root = Path(__file__).parent
workspace_dir = (repo_root / "data/workspaces/test_immediate").absolute()

# Clean up if exists
if workspace_dir.exists():
    import shutil
    shutil.rmtree(workspace_dir)

workspace_dir.mkdir(parents=True, exist_ok=True)
os.environ["MULTI_AGENT_WORKSPACE_DIR"] = str(workspace_dir)

print(f"workspace_dir: {workspace_dir}")
print(f"DB path: {workspace_dir / 'database.db'}")

# Create controller
controller = Controller(
    controller_id="test_immediate",
    max_concurrent_agents=5,
    workspace_dir=str(workspace_dir)
)

# Create workspace via CLI
import subprocess
result = subprocess.run(
    [sys.executable, "-m", "src.agent_interface.cli", "workspace.create",
     "--workspace_id", "ws_test"],
    capture_output=True,
    text=True,
    timeout=10,
    cwd=repo_root,
    env=os.environ
)
print(f"1. Create workspace: {'OK' if result.returncode == 0 else 'FAIL'}")

# Create agent
agent = controller.create_agent(
    agent_id="agent_test",
    role_name="modeler",
    workspace_id="ws_test"
)
print(f"2. Created agent: {agent.agent_id}")

# Create entity via controller
print(f"3. Creating entity via controller...")
result = controller.execute_operation(
    agent_id=agent.agent_id,
    operation="entity.create_point",
    params={"x": 10.0, "y": 20.0, "z": 0.0, "workspace_id": "ws_test"}
)
print(f"   Success: {result.get('success')}")
print(f"   Entity ID: {result.get('entity_id', 'N/A')}")

# Immediately check database
print(f"\n4. Checking database IMMEDIATELY after creation:")
db_path = workspace_dir / "database.db"
print(f"   DB exists: {db_path.exists()}")

if db_path.exists():
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Check entities
    cursor.execute("SELECT entity_id, workspace_id FROM entities")
    entities = cursor.fetchall()
    print(f"   Entities in DB: {len(entities)}")
    for ent in entities:
        print(f"     - {ent[0]} | {ent[1]}")

    # Check workspaces
    cursor.execute("SELECT workspace_id FROM workspaces")
    workspaces = cursor.fetchall()
    print(f"   Workspaces in DB: {len(workspaces)}")
    for ws in workspaces:
        print(f"     - {ws[0]}")

    conn.close()

del os.environ["MULTI_AGENT_WORKSPACE_DIR"]
