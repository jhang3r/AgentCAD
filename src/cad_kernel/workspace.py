"""Workspace management with isolation and branching support."""
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class Workspace:
    """Isolated workspace for agent operations.

    Attributes:
        workspace_id: Unique identifier
        workspace_name: Human-readable name
        workspace_type: Type ('main' or 'agent_branch')
        base_workspace_id: Parent workspace for branches
        owning_agent_id: Agent that owns this workspace
        created_at: Creation timestamp
        entity_count: Number of entities in workspace
        operation_count: Number of operations performed
        branch_status: Status ('clean', 'modified', 'conflicted', 'merged')
        divergence_point: Operation ID where branch diverged from base
    """

    workspace_id: str
    workspace_name: str
    workspace_type: str
    created_at: str
    entity_count: int = 0
    operation_count: int = 0
    branch_status: str = "clean"
    base_workspace_id: Optional[str] = None
    owning_agent_id: Optional[str] = None
    divergence_point: Optional[str] = None

    def is_main(self) -> bool:
        """Check if this is the main workspace.

        Returns:
            True if main workspace
        """
        return self.workspace_type == "main"

    def is_branch(self) -> bool:
        """Check if this is an agent branch workspace.

        Returns:
            True if branch workspace
        """
        return self.workspace_type == "agent_branch"

    def can_merge(self) -> bool:
        """Check if workspace can be merged.

        Returns:
            True if workspace is in a mergeable state
        """
        return self.branch_status in ("clean", "modified")

    def to_dict(self) -> dict[str, Any]:
        """Convert workspace to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "workspace_id": self.workspace_id,
            "workspace_name": self.workspace_name,
            "workspace_type": self.workspace_type,
            "base_workspace_id": self.base_workspace_id,
            "owning_agent_id": self.owning_agent_id,
            "created_at": self.created_at,
            "entity_count": self.entity_count,
            "operation_count": self.operation_count,
            "branch_status": self.branch_status,
            "divergence_point": self.divergence_point
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Workspace":
        """Create workspace from dictionary.

        Args:
            data: Dictionary with workspace fields

        Returns:
            Workspace instance
        """
        return cls(
            workspace_id=data["workspace_id"],
            workspace_name=data["workspace_name"],
            workspace_type=data["workspace_type"],
            base_workspace_id=data.get("base_workspace_id"),
            owning_agent_id=data.get("owning_agent_id"),
            created_at=data["created_at"],
            entity_count=data.get("entity_count", 0),
            operation_count=data.get("operation_count", 0),
            branch_status=data.get("branch_status", "clean"),
            divergence_point=data.get("divergence_point")
        )


class WorkspaceManager:
    """Manage workspace lifecycle and operations."""

    def __init__(self, workspace_store):
        """Initialize workspace manager.

        Args:
            workspace_store: WorkspaceStore instance for persistence
        """
        self.workspace_store = workspace_store
        self._active_workspace: Optional[Workspace] = None

    def create_workspace(
        self,
        workspace_name: str,
        workspace_type: str,
        base_workspace_id: Optional[str] = None,
        owning_agent_id: Optional[str] = None
    ) -> Workspace:
        """Create new workspace.

        Args:
            workspace_name: Human-readable name
            workspace_type: 'main' or 'agent_branch'
            base_workspace_id: Parent workspace for branches
            owning_agent_id: Agent that owns this workspace

        Returns:
            Created Workspace instance
        """
        from datetime import datetime, timezone

        # Generate workspace ID
        if workspace_type == "main":
            workspace_id = "main"
        else:
            workspace_id = f"{owning_agent_id}:{workspace_name}"

        now = datetime.now(timezone.utc).isoformat()

        workspace = Workspace(
            workspace_id=workspace_id,
            workspace_name=workspace_name,
            workspace_type=workspace_type,
            base_workspace_id=base_workspace_id,
            owning_agent_id=owning_agent_id,
            created_at=now,
            branch_status="clean"
        )

        # Persist to database
        self.workspace_store.create_workspace(
            workspace_id=workspace.workspace_id,
            workspace_name=workspace.workspace_name,
            workspace_type=workspace.workspace_type,
            base_workspace_id=workspace.base_workspace_id,
            owning_agent_id=workspace.owning_agent_id,
            branch_status=workspace.branch_status
        )

        return workspace

    def get_workspace(self, workspace_id: str) -> Optional[Workspace]:
        """Retrieve workspace by ID.

        Args:
            workspace_id: Workspace identifier

        Returns:
            Workspace instance or None if not found
        """
        data = self.workspace_store.get_workspace(workspace_id)
        if data is None:
            return None
        return Workspace.from_dict(data)

    def list_workspaces(self) -> list[Workspace]:
        """List all workspaces.

        Returns:
            List of Workspace instances
        """
        workspaces_data = self.workspace_store.list_workspaces()
        return [Workspace.from_dict(data) for data in workspaces_data]

    def get_active_workspace(self) -> Optional[Workspace]:
        """Get currently active workspace.

        Returns:
            Active Workspace or None
        """
        return self._active_workspace

    def set_active_workspace(self, workspace_id: str) -> Workspace:
        """Set active workspace by ID.

        Args:
            workspace_id: Workspace to activate

        Returns:
            Activated Workspace instance

        Raises:
            ValueError: If workspace not found
        """
        workspace = self.get_workspace(workspace_id)
        if workspace is None:
            raise ValueError(f"Workspace '{workspace_id}' not found")

        self._active_workspace = workspace
        return workspace

    def update_branch_status(self, workspace_id: str, status: str) -> None:
        """Update workspace branch status.

        Args:
            workspace_id: Workspace to update
            status: New status ('clean', 'modified', 'conflicted', 'merged')
        """
        self.workspace_store.update_workspace(
            workspace_id=workspace_id,
            branch_status=status
        )

        # Update cached active workspace if it matches
        if self._active_workspace and self._active_workspace.workspace_id == workspace_id:
            self._active_workspace.branch_status = status
