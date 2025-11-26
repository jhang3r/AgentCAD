"""
Debug workspace resolution in CLI
"""

import os
import json
import sys
from pathlib import Path

# Directly test the CLI workspace resolution
from src.agent_interface.cli import CLI

repo_root = Path(__file__).parent
workspace_dir = Path("data/workspaces/test_resolution")
workspace_dir.mkdir(parents=True, exist_ok=True)

os.environ["MULTI_AGENT_WORKSPACE_DIR"] = str(workspace_dir)

print("=" * 60)
print("Workspace Resolution Debug")
print("=" * 60)

# Create CLI instance
cli = CLI(workspace_dir=str(workspace_dir))

# Create workspace with short name
workspace_id_short = "ws_test"
print(f"\n1. Creating workspace with ID='{workspace_id_short}'")

# Build JSON-RPC request for workspace.create
request_json = {
    "jsonrpc": "2.0",
    "method": "workspace.create",
    "params": {"workspace_id": workspace_id_short},
    "id": 1
}

response = cli.handle_request(request_json)
print(f"   Created: {response.get('result', {}).get('data', {}).get('workspace_id', 'N/A')}")
created_ws_id = response['result']['data']['workspace_id']

# Now check if get_workspace can find it
print(f"\n2. Testing workspace_manager.get_workspace('{workspace_id_short}')")
ws = cli.workspace_manager.get_workspace(workspace_id_short)
if ws:
    print(f"   Found: {ws.workspace_id}")
else:
    print(f"   NOT FOUND!")

# Create entity with short workspace_id
print(f"\n3. Creating entity with workspace_id='{workspace_id_short}'")
request_json = {
    "jsonrpc": "2.0",
    "method": "entity.create_point",
    "params": {"x": 10.0, "y": 20.0, "z": 0.0, "workspace_id": workspace_id_short},
    "id": 2
}

response = cli.handle_request(request_json)
if 'result' in response:
    entity_id = response['result']['data']['entity_id']
    print(f"   Created: {entity_id}")
    # Check which workspace_id was used
    print(f"   Entity workspace_id: {response['result']['data'].get('workspace_id', 'N/A')}")
else:
    print(f"   ERROR: {response.get('error', 'Unknown')}")

# List entities with short workspace_id
print(f"\n4. Listing entities with workspace_id='{workspace_id_short}'")
request_json = {
    "jsonrpc": "2.0",
    "method": "entity.list",
    "params": {"workspace_id": workspace_id_short},
    "id": 3
}

response = cli.handle_request(request_json)
if 'result' in response:
    entities = response['result']['data']['entities']
    print(f"   Entities found: {len(entities)}")
    if entities:
        for ent in entities:
            print(f"     - {ent['entity_id']} (workspace: {ent.get('workspace_id', 'N/A')})")
else:
    print(f"   ERROR: {response.get('error', 'Unknown')}")

# Try listing with full workspace_id
print(f"\n5. Listing entities with workspace_id='{created_ws_id}'")
request_json = {
    "jsonrpc": "2.0",
    "method": "entity.list",
    "params": {"workspace_id": created_ws_id},
    "id": 4
}

response = cli.handle_request(request_json)
if 'result' in response:
    entities = response['result']['data']['entities']
    print(f"   Entities found: {len(entities)}")
    if entities:
        for ent in entities:
            print(f"     - {ent['entity_id']}")
else:
    print(f"   ERROR: {response.get('error', 'Unknown')}")

del os.environ["MULTI_AGENT_WORKSPACE_DIR"]

print("\n" + "=" * 60)
