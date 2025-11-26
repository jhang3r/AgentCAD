"""Operation history persistence layer."""
import json
from datetime import datetime, timezone
from typing import Any, Optional

from .database import Database


class OperationLog:
    """Manage operation history persistence in SQLite."""

    def __init__(self, database: Database):
        """Initialize operation log.

        Args:
            database: Database connection manager
        """
        self.database = database

    def log_operation(
        self,
        operation_id: str,
        operation_type: str,
        workspace_id: str,
        agent_id: str,
        input_parameters: dict[str, Any],
        execution_time_ms: int,
        result_status: str,
        input_entities: Optional[list[str]] = None,
        output_entities: Optional[list[str]] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        undo_data: Optional[dict[str, Any]] = None
    ) -> None:
        """Log an operation to the database.

        Args:
            operation_id: Unique operation identifier
            operation_type: Type of operation performed
            workspace_id: Workspace where operation occurred
            agent_id: Agent that performed the operation
            input_parameters: Operation-specific parameters
            execution_time_ms: Operation execution time in milliseconds
            result_status: 'success', 'error', or 'warning'
            input_entities: List of input entity IDs (optional)
            output_entities: List of output entity IDs (optional)
            error_code: Error code if failed (optional)
            error_message: Error message if failed (optional)
            undo_data: Data needed to undo this operation (optional)
        """
        now = datetime.now(timezone.utc).isoformat()
        conn = self.database.connect()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO operations (
                operation_id, operation_type, workspace_id, agent_id, timestamp,
                input_parameters, input_entities, output_entities, result_status,
                error_code, error_message, execution_time_ms, undo_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            operation_id,
            operation_type,
            workspace_id,
            agent_id,
            now,
            json.dumps(input_parameters),
            json.dumps(input_entities or []),
            json.dumps(output_entities or []),
            result_status,
            error_code,
            error_message,
            execution_time_ms,
            json.dumps(undo_data or {})
        ))
        conn.commit()

        # Update workspace operation count
        cursor.execute("""
            UPDATE workspaces
            SET operation_count = operation_count + 1
            WHERE workspace_id = ?
        """, (workspace_id,))
        conn.commit()

    def get_operation(self, operation_id: str) -> Optional[dict[str, Any]]:
        """Retrieve operation by ID.

        Args:
            operation_id: Operation identifier

        Returns:
            Operation data as dictionary, or None if not found
        """
        conn = self.database.connect()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM operations WHERE operation_id = ?", (operation_id,))
        row = cursor.fetchone()

        if row is None:
            return None

        # Convert Row to dict and parse JSON fields
        operation = dict(row)
        operation["input_parameters"] = json.loads(operation["input_parameters"])
        operation["input_entities"] = json.loads(operation["input_entities"])
        operation["output_entities"] = json.loads(operation["output_entities"])
        operation["undo_data"] = json.loads(operation["undo_data"])

        return operation

    def list_operations(
        self,
        workspace_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> tuple[list[dict[str, Any]], int]:
        """List operations in workspace with pagination.

        Args:
            workspace_id: Workspace to query
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            Tuple of (operations list, total count)
        """
        conn = self.database.connect()
        cursor = conn.cursor()

        # Get total count
        cursor.execute(
            "SELECT COUNT(*) FROM operations WHERE workspace_id = ?",
            (workspace_id,)
        )
        total_count = cursor.fetchone()[0]

        # Get paginated results (most recent first)
        cursor.execute("""
            SELECT operation_id, operation_type, agent_id, timestamp,
                   result_status, execution_time_ms
            FROM operations
            WHERE workspace_id = ?
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        """, (workspace_id, limit, offset))

        operations = [dict(row) for row in cursor.fetchall()]

        return operations, total_count

    def get_history_for_undo(
        self,
        workspace_id: str,
        limit: int = 100
    ) -> list[dict[str, Any]]:
        """Get operation history for undo/redo functionality.

        Args:
            workspace_id: Workspace to query
            limit: Maximum number of operations to retrieve

        Returns:
            List of operations in chronological order (oldest first)
        """
        conn = self.database.connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT operation_id, operation_type, timestamp, undo_data,
                   input_entities, output_entities
            FROM operations
            WHERE workspace_id = ? AND result_status = 'success'
            ORDER BY timestamp ASC
            LIMIT ?
        """, (workspace_id, limit))

        operations = []
        for row in cursor.fetchall():
            op = dict(row)
            op["undo_data"] = json.loads(op["undo_data"])
            op["input_entities"] = json.loads(op["input_entities"])
            op["output_entities"] = json.loads(op["output_entities"])
            operations.append(op)

        return operations

    def get_agent_metrics(self, agent_id: str, workspace_id: Optional[str] = None) -> dict[str, Any]:
        """Calculate agent performance metrics.

        Args:
            agent_id: Agent to analyze
            workspace_id: Optional workspace filter

        Returns:
            Dictionary with agent metrics (total_operations, success_rate, etc.)
        """
        conn = self.database.connect()
        cursor = conn.cursor()

        where_clause = "agent_id = ?"
        params: list[Any] = [agent_id]

        if workspace_id:
            where_clause += " AND workspace_id = ?"
            params.append(workspace_id)

        # Total operations
        cursor.execute(f"SELECT COUNT(*) FROM operations WHERE {where_clause}", params)
        total_operations = cursor.fetchone()[0]

        if total_operations == 0:
            return {
                "total_operations": 0,
                "success_rate": 0.0,
                "error_rate_first_10": 0.0,
                "error_rate_last_10": 0.0,
                "improvement_percent": 0.0,
                "avg_execution_time_ms": 0
            }

        # Success count
        cursor.execute(
            f"SELECT COUNT(*) FROM operations WHERE {where_clause} AND result_status = 'success'",
            params
        )
        success_count = cursor.fetchone()[0]

        # Error rate for first 10 operations
        cursor.execute(f"""
            SELECT COUNT(*) FROM (
                SELECT result_status FROM operations
                WHERE {where_clause}
                ORDER BY timestamp ASC
                LIMIT 10
            ) WHERE result_status = 'error'
        """, params)
        errors_first_10 = cursor.fetchone()[0]

        # Error rate for last 10 operations
        cursor.execute(f"""
            SELECT COUNT(*) FROM (
                SELECT result_status FROM operations
                WHERE {where_clause}
                ORDER BY timestamp DESC
                LIMIT 10
            ) WHERE result_status = 'error'
        """, params)
        errors_last_10 = cursor.fetchone()[0]

        # Average execution time
        cursor.execute(
            f"SELECT AVG(execution_time_ms) FROM operations WHERE {where_clause}",
            params
        )
        avg_execution_time = cursor.fetchone()[0] or 0

        first_10_count = min(total_operations, 10)
        last_10_count = min(total_operations, 10)

        error_rate_first = errors_first_10 / first_10_count if first_10_count > 0 else 0
        error_rate_last = errors_last_10 / last_10_count if last_10_count > 0 else 0

        # Calculate improvement percentage
        if error_rate_first > 0:
            improvement = ((error_rate_first - error_rate_last) / error_rate_first) * 100
        else:
            improvement = 0.0 if error_rate_last == 0 else -100.0

        return {
            "total_operations": total_operations,
            "success_rate": success_count / total_operations,
            "error_rate_first_10": error_rate_first,
            "error_rate_last_10": error_rate_last,
            "improvement_percent": improvement,
            "avg_execution_time_ms": int(avg_execution_time)
        }
