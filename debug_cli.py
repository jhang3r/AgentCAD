
import subprocess
import json
import sys
import os

def run_cli(args):
    cmd = [sys.executable, "-m", "src.agent_interface.cli"] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result

# 1. Create workspace
print("Creating workspace...")
res = run_cli(["workspace.create", "--workspace_name", "debug_ws"])
print(f"Create WS: {res.returncode}")
print(res.stdout)

# 2. Create point
print("\nCreating point...")
res = run_cli(["entity.create.point", "--x", "10", "--y", "20", "--workspace_id", "debug_ws"])
print(f"Create Point: {res.returncode}")
print(res.stdout)

# 3. List entities
print("\nListing entities...")
res = run_cli(["entity.list", "--workspace_id", "debug_ws"])
print(f"List Entities: {res.returncode}")
print(res.stdout)
