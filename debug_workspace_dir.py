"""
Debug workspace directory path resolution
"""

import os
import subprocess
import json
import sys
from pathlib import Path

repo_root = Path(__file__).parent
test_dir = repo_root / "tests" / "multi_agent_integration"

# Simulate test setup
workspace_dir_relative = Path("data/workspaces/test_debug")
workspace_dir_absolute = (repo_root / workspace_dir_relative).absolute()

print("=" * 60)
print("Workspace Directory Path Resolution")
print("=" * 60)

print(f"\nRepo root: {repo_root.absolute()}")
print(f"Relative workspace_dir: {workspace_dir_relative}")
print(f"Absolute workspace_dir: {workspace_dir_absolute}")

# Create the directory
workspace_dir_absolute.mkdir(parents=True, exist_ok=True)

# Test 1: Controller with relative path
print(f"\n1. Testing with relative path in env var...")
env = os.environ.copy()
env["MULTI_AGENT_WORKSPACE_DIR"] = str(workspace_dir_relative)

result = subprocess.run(
    [sys.executable, "-m", "src.agent_interface.cli", "workspace.create",
     "--workspace_id", "test1"],
    capture_output=True,
    text=True,
    timeout=10,
    cwd=repo_root,  # Controller runs from repo root
    env=env
)
print(f"   Create from repo root: {result.returncode == 0}")

# Now try to list from test directory (different cwd)
result = subprocess.run(
    [sys.executable, "-m", "src.agent_interface.cli", "entity.list",
     "--workspace_id", "test1"],
    capture_output=True,
    text=True,
    timeout=10,
    cwd=test_dir,  # Test runs from different directory!
    env=env
)
print(f"   List from test dir: {result.returncode == 0}")
if result.returncode != 0:
    print(f"   Error: {result.stderr[:200]}")

# Test 2: Controller with absolute path
print(f"\n2. Testing with absolute path in env var...")
env["MULTI_AGENT_WORKSPACE_DIR"] = str(workspace_dir_absolute)

result = subprocess.run(
    [sys.executable, "-m", "src.agent_interface.cli", "workspace.create",
     "--workspace_id", "test2"],
    capture_output=True,
    text=True,
    timeout=10,
    cwd=repo_root,
    env=env
)
print(f"   Create from repo root: {result.returncode == 0}")

result = subprocess.run(
    [sys.executable, "-m", "src.agent_interface.cli", "entity.list",
     "--workspace_id", "test2"],
    capture_output=True,
    text=True,
    timeout=10,
    cwd=test_dir,  # Different cwd
    env=env
)
print(f"   List from test dir: {result.returncode == 0}")

# Cleanup
for ws_id in ["test1", "test2"]:
    subprocess.run(
        [sys.executable, "-m", "src.agent_interface.cli", "workspace.delete",
         "--workspace_id", ws_id],
        capture_output=True,
        timeout=10,
        cwd=repo_root,
        env=env
    )

print("\n" + "=" * 60)
print("CONCLUSION: Use absolute paths for workspace_dir!")
print("=" * 60)
