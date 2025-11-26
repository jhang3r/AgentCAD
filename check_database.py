import sqlite3

conn = sqlite3.connect('data/workspaces/test_cli_fix/database.db')
cursor = conn.cursor()

# Check entities table
cursor.execute('SELECT entity_id, entity_type, workspace_id FROM entities')
rows = cursor.fetchall()

print(f"Entities in database: {len(rows)}")
for row in rows:
    print(f"  - {row[0]} | {row[1]} | {row[2]}")

# Check workspaces table
cursor.execute('SELECT workspace_id, workspace_name FROM workspaces')
workspaces = cursor.fetchall()
print(f"\nWorkspaces in database: {len(workspaces)}")
for ws in workspaces:
    print(f"  - {ws[0]} | {ws[1]}")

conn.close()
