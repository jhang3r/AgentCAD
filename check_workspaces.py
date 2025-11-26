"""
Check what entities are in each workspace.
"""

import sqlite3
from pathlib import Path

workspace_dir = Path("data/workspaces/demo_build").absolute()
db_path = workspace_dir / "database.db"

print(f"\nChecking database: {db_path}\n")

if not db_path.exists():
    print(f"Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# List all workspaces
print("="*80)
print("WORKSPACES:")
print("="*80)
cursor.execute("SELECT workspace_id, created_at FROM workspaces")
workspaces = cursor.fetchall()
for ws_id, created_at in workspaces:
    print(f"  - {ws_id} (created: {created_at})")

# List all entities by workspace
print("\n" + "="*80)
print("ENTITIES BY WORKSPACE:")
print("="*80)

for ws_id, _ in workspaces:
    cursor.execute("""
        SELECT entity_id, entity_type, properties
        FROM entities
        WHERE workspace_id = ?
    """, (ws_id,))
    entities = cursor.fetchall()

    print(f"\n{ws_id}: {len(entities)} entities")
    for entity_id, entity_type, properties in entities:
        print(f"  - {entity_type}: {entity_id}")

conn.close()

print("\n" + "="*80)
