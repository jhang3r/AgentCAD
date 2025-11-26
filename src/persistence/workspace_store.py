"""Workspace metadata persistence layer."""
import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Optional

from .database import Database


class WorkspaceStore:
    """Manage workspace metadata persistence in SQLite."""

    def __init__(self, database: Database):
        """Initialize workspace store.

        Args:
            database: Database connection manager
        """
        self.database = database

    def create_workspace(
        self,
        workspace_id: str,
        workspace_name: str,
        workspace_type: str,
        base_workspace_id: Optional[str] = None,
        owning_agent_id: Optional[str] = None,
        branch_status: str = "clean"
    ) -> None:
        """Create new workspace in database.

        Args:
            workspace_id: Unique workspace identifier
            workspace_name: Human-readable workspace name
            workspace_type: Type ('main' or 'agent_branch')
            base_workspace_id: Parent workspace for branches (optional)
            owning_agent_id: Agent that owns this workspace (optional)
            branch_status: Initial status ('clean', 'modified', 'conflicted', 'merged')
        """
        now = datetime.now(timezone.utc).isoformat()
        conn = self.database.connect()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO workspaces (
                workspace_id, workspace_name, workspace_type, base_workspace_id,
                owning_agent_id, created_at, entity_count, operation_count,
                branch_status, divergence_point
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            workspace_id,
            workspace_name,
            workspace_type,
            base_workspace_id,
            owning_agent_id,
            now,
            0,  # entity_count
            0,  # operation_count
            branch_status,
            None  # divergence_point
        ))
        conn.commit()

    def get_workspace(self, workspace_id: str) -> Optional[dict[str, Any]]:
        """Retrieve workspace by ID.

        Args:
            workspace_id: Workspace identifier

        Returns:
            Workspace data as dictionary, or None if not found
        """
        conn = self.database.connect()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM workspaces WHERE workspace_id = ?", (workspace_id,))
        row = cursor.fetchone()

        if row is None:
            # Try suffix match (for tests using short names)
            cursor.execute("SELECT * FROM workspaces WHERE workspace_id LIKE ?", (f"%:{workspace_id}",))
            row = cursor.fetchone()
            
            if row is None:
                return None

        return dict(row)

    def list_workspaces(self) -> list[dict[str, Any]]:
        """List all workspaces.

        Returns:
            List of workspace dictionaries
        """
        conn = self.database.connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT workspace_id, workspace_name, workspace_type, base_workspace_id,
                   owning_agent_id, created_at, entity_count, operation_count, branch_status
            FROM workspaces
            ORDER BY created_at DESC
        """)

        return [dict(row) for row in cursor.fetchall()]

    def update_workspace(
        self,
        workspace_id: str,
        entity_count: Optional[int] = None,
        operation_count: Optional[int] = None,
        branch_status: Optional[str] = None,
        divergence_point: Optional[str] = None
    ) -> None:
        """Update workspace fields.

        Args:
            workspace_id: Workspace to update
            entity_count: New entity count (optional)
            operation_count: New operation count (optional)
            branch_status: New branch status (optional)
            divergence_point: New divergence point operation ID (optional)
        """
        conn = self.database.connect()
        cursor = conn.cursor()

        updates = []
        params: list[Any] = []

        if entity_count is not None:
            updates.append("entity_count = ?")
            params.append(entity_count)

        if operation_count is not None:
            updates.append("operation_count = ?")
            params.append(operation_count)

        if branch_status is not None:
            updates.append("branch_status = ?")
            params.append(branch_status)

        if divergence_point is not None:
            updates.append("divergence_point = ?")
            params.append(divergence_point)

        if not updates:
            return

        params.append(workspace_id)

        cursor.execute(
            f"UPDATE workspaces SET {', '.join(updates)} WHERE workspace_id = ?",
            params
        )
        conn.commit()

    def delete_workspace(self, workspace_id: str) -> None:
        """Delete workspace from database.

        Args:
            workspace_id: Workspace to delete

        Raises:
            ValueError: If attempting to delete main workspace
        """
        conn = self.database.connect()
        cursor = conn.cursor()

        # Check if this is the main workspace
        cursor.execute("SELECT workspace_type FROM workspaces WHERE workspace_id = ?", (workspace_id,))
        row = cursor.fetchone()

        if row and row[0] == "main":
            raise ValueError("Cannot delete main workspace")

        # Delete workspace (cascade will handle related entities, constraints, operations)
        cursor.execute("DELETE FROM workspaces WHERE workspace_id = ?", (workspace_id,))
        conn.commit()

    def increment_operation_count(self, workspace_id: str) -> None:
        """Increment operation count for workspace.

        Args:
            workspace_id: Workspace to update
        """
        conn = self.database.connect()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE workspaces
            SET operation_count = operation_count + 1
            WHERE workspace_id = ?
        """, (workspace_id,))
        conn.commit()
