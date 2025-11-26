"""Operation history and undo/redo functionality.

Maintains an operation stack per workspace to support undo/redo operations.
Critical for agent learning - allows experimentation and backtracking.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass
class HistoryEntry:
    """Represents a single operation in history.

    Attributes:
        operation_id: Unique identifier for this operation
        operation_type: Type of operation (e.g., "entity.create.point")
        workspace_id: Workspace where operation occurred
        timestamp: When the operation was executed
        params: Parameters used for the operation
        result: Result data from the operation
        inverse_operation: Operation type needed to undo this
        inverse_params: Parameters for undo operation
    """
    operation_id: str
    operation_type: str
    workspace_id: str
    timestamp: str
    params: dict[str, Any]
    result: dict[str, Any]
    inverse_operation: Optional[str] = None
    inverse_params: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "operation_id": self.operation_id,
            "operation_type": self.operation_type,
            "workspace_id": self.workspace_id,
            "timestamp": self.timestamp,
            "params": self.params,
            "result": self.result,
            "inverse_operation": self.inverse_operation,
            "inverse_params": self.inverse_params
        }


class OperationHistory:
    """Manages undo/redo stack for a workspace.

    Maintains operation history and supports undo/redo operations.
    Each workspace has its own independent history.
    """

    def __init__(self, workspace_id: str, max_history: int = 100):
        """Initialize operation history.

        Args:
            workspace_id: Workspace identifier
            max_history: Maximum operations to keep in history
        """
        self.workspace_id = workspace_id
        self.max_history = max_history
        self.operations: list[HistoryEntry] = []
        self.current_position = -1  # -1 means no operations yet

    def add_operation(self, entry: HistoryEntry) -> None:
        """Add operation to history.

        Args:
            entry: History entry to add
        """
        # If we're not at the end, truncate future operations
        if self.current_position < len(self.operations) - 1:
            self.operations = self.operations[:self.current_position + 1]

        # Add new operation
        self.operations.append(entry)
        self.current_position += 1

        # Trim history if exceeded max
        if len(self.operations) > self.max_history:
            self.operations = self.operations[-self.max_history:]
            self.current_position = len(self.operations) - 1

    def can_undo(self) -> bool:
        """Check if undo is possible.

        Returns:
            True if there are operations to undo
        """
        return self.current_position >= 0

    def can_redo(self) -> bool:
        """Check if redo is possible.

        Returns:
            True if there are operations to redo
        """
        return self.current_position < len(self.operations) - 1

    def get_undo_operation(self) -> Optional[HistoryEntry]:
        """Get operation to undo.

        Returns:
            History entry for current operation, or None if can't undo
        """
        if not self.can_undo():
            return None
        return self.operations[self.current_position]

    def get_redo_operation(self) -> Optional[HistoryEntry]:
        """Get operation to redo.

        Returns:
            History entry for next operation, or None if can't redo
        """
        if not self.can_redo():
            return None
        return self.operations[self.current_position + 1]

    def mark_undo_complete(self) -> None:
        """Mark current operation as undone."""
        if self.can_undo():
            self.current_position -= 1

    def mark_redo_complete(self) -> None:
        """Mark next operation as redone."""
        if self.can_redo():
            self.current_position += 1

    def list_operations(
        self,
        limit: int = 10,
        offset: int = 0,
        include_future: bool = False
    ) -> list[dict[str, Any]]:
        """List operations in history.

        Args:
            limit: Maximum operations to return
            offset: Number of operations to skip
            include_future: If True, include operations after current position

        Returns:
            List of operation dictionaries
        """
        if include_future:
            ops = self.operations
        else:
            ops = self.operations[:self.current_position + 1]

        # Reverse so most recent is first
        ops = list(reversed(ops))

        # Apply pagination
        start = offset
        end = offset + limit
        return [op.to_dict() for op in ops[start:end]]

    def get_current_position(self) -> int:
        """Get current position in history.

        Returns:
            Current position index (-1 if no operations)
        """
        return self.current_position

    def get_total_count(self) -> int:
        """Get total operation count.

        Returns:
            Total number of operations in history
        """
        return len(self.operations)

    def clear(self) -> None:
        """Clear all history."""
        self.operations = []
        self.current_position = -1


class HistoryManager:
    """Manages operation history for all workspaces."""

    def __init__(self):
        """Initialize history manager."""
        self.histories: dict[str, OperationHistory] = {}

    def get_history(self, workspace_id: str) -> OperationHistory:
        """Get or create history for workspace.

        Args:
            workspace_id: Workspace identifier

        Returns:
            OperationHistory instance for the workspace
        """
        if workspace_id not in self.histories:
            self.histories[workspace_id] = OperationHistory(workspace_id)
        return self.histories[workspace_id]

    def clear_workspace_history(self, workspace_id: str) -> None:
        """Clear history for specific workspace.

        Args:
            workspace_id: Workspace to clear history for
        """
        if workspace_id in self.histories:
            self.histories[workspace_id].clear()
