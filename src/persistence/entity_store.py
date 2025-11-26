"""Entity metadata persistence layer."""
import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Optional

from .database import Database


class EntityStore:
    """Manage entity metadata persistence in SQLite."""

    def __init__(self, database: Database):
        """Initialize entity store.

        Args:
            database: Database connection manager
        """
        self.database = database

    def create_entity(
        self,
        entity_id: str,
        entity_type: str,
        workspace_id: str,
        created_by_agent: str,
        properties: dict[str, Any],
        bounding_box: dict[str, list[float]],
        parent_entities: Optional[list[str]] = None,
        is_valid: bool = True,
        validation_errors: Optional[list[str]] = None
    ) -> None:
        """Create new entity in database.

        Args:
            entity_id: Unique entity identifier
            entity_type: Type of entity (point, line, circle, etc.)
            workspace_id: Workspace this entity belongs to
            created_by_agent: Agent ID that created this entity
            properties: Entity-specific properties (coordinates, dimensions, etc.)
            bounding_box: Axis-aligned bounding box {min: [x,y,z], max: [x,y,z]}
            parent_entities: List of parent entity IDs (optional)
            is_valid: Topology/geometry validity status
            validation_errors: List of error codes if invalid (optional)
        """
        now = datetime.now(timezone.utc).isoformat()
        conn = self.database.connect()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO entities (
                entity_id, entity_type, workspace_id, created_at, modified_at,
                created_by_agent, parent_entities, child_entities, properties,
                bounding_box, is_valid, validation_errors
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entity_id,
            entity_type,
            workspace_id,
            now,
            now,
            created_by_agent,
            json.dumps(parent_entities or []),
            json.dumps([]),  # Empty child_entities initially
            json.dumps(properties),
            json.dumps(bounding_box),
            1 if is_valid else 0,
            json.dumps(validation_errors or [])
        ))
        conn.commit()

        # Update workspace entity count
        cursor.execute("""
            UPDATE workspaces
            SET entity_count = entity_count + 1
            WHERE workspace_id = ?
        """, (workspace_id,))
        conn.commit()

    def get_entity(self, entity_id: str) -> Optional[dict[str, Any]]:
        """Retrieve entity by ID.

        Args:
            entity_id: Entity identifier

        Returns:
            Entity data as dictionary, or None if not found
        """
        conn = self.database.connect()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM entities WHERE entity_id = ?", (entity_id,))
        row = cursor.fetchone()

        if row is None:
            return None

        # Convert Row to dict and parse JSON fields
        entity = dict(row)
        entity["parent_entities"] = json.loads(entity["parent_entities"]) if entity["parent_entities"] else []
        entity["child_entities"] = json.loads(entity["child_entities"]) if entity["child_entities"] else []
        entity["properties"] = json.loads(entity["properties"]) if entity["properties"] else {}
        entity["bounding_box"] = json.loads(entity["bounding_box"]) if entity["bounding_box"] else {}
        entity["validation_errors"] = json.loads(entity["validation_errors"]) if entity["validation_errors"] else []
        entity["is_valid"] = bool(entity["is_valid"])

        return entity

    def list_entities(
        self,
        workspace_id: str,
        entity_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> tuple[list[dict[str, Any]], int]:
        """List entities in workspace with pagination.

        Args:
            workspace_id: Workspace to query
            entity_type: Filter by entity type (optional)
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            Tuple of (entities list, total count)
        """
        conn = self.database.connect()
        cursor = conn.cursor()

        # Build query with optional type filter
        where_clause = "workspace_id = ?"
        params: list[Any] = [workspace_id]

        if entity_type:
            where_clause += " AND entity_type = ?"
            params.append(entity_type)

        # Get total count
        cursor.execute(f"SELECT COUNT(*) FROM entities WHERE {where_clause}", params)
        total_count = cursor.fetchone()[0]

        # Get paginated results
        query = f"""
            SELECT entity_id, entity_type, workspace_id, created_at, modified_at
            FROM entities
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        cursor.execute(query, params)

        entities = [dict(row) for row in cursor.fetchall()]

        return entities, total_count

    def update_entity(
        self,
        entity_id: str,
        properties: Optional[dict[str, Any]] = None,
        bounding_box: Optional[dict[str, list[float]]] = None,
        is_valid: Optional[bool] = None,
        validation_errors: Optional[list[str]] = None,
        child_entities: Optional[list[str]] = None
    ) -> None:
        """Update entity fields.

        Args:
            entity_id: Entity to update
            properties: New properties (optional)
            bounding_box: New bounding box (optional)
            is_valid: New validity status (optional)
            validation_errors: New error list (optional)
            child_entities: New child entity list (optional)
        """
        now = datetime.now(timezone.utc).isoformat()
        conn = self.database.connect()
        cursor = conn.cursor()

        updates = ["modified_at = ?"]
        params: list[Any] = [now]

        if properties is not None:
            updates.append("properties = ?")
            params.append(json.dumps(properties))

        if bounding_box is not None:
            updates.append("bounding_box = ?")
            params.append(json.dumps(bounding_box))

        if is_valid is not None:
            updates.append("is_valid = ?")
            params.append(1 if is_valid else 0)

        if validation_errors is not None:
            updates.append("validation_errors = ?")
            params.append(json.dumps(validation_errors))

        if child_entities is not None:
            updates.append("child_entities = ?")
            params.append(json.dumps(child_entities))

        params.append(entity_id)

        cursor.execute(
            f"UPDATE entities SET {', '.join(updates)} WHERE entity_id = ?",
            params
        )
        conn.commit()

    def delete_entity(self, entity_id: str) -> None:
        """Delete entity from database.

        Args:
            entity_id: Entity to delete
        """
        conn = self.database.connect()
        cursor = conn.cursor()

        # Get workspace_id before deleting
        cursor.execute("SELECT workspace_id FROM entities WHERE entity_id = ?", (entity_id,))
        row = cursor.fetchone()

        if row:
            workspace_id = row[0]

            # Delete entity (cascade will handle entity_constraints)
            cursor.execute("DELETE FROM entities WHERE entity_id = ?", (entity_id,))

            # Update workspace entity count
            cursor.execute("""
                UPDATE workspaces
                SET entity_count = entity_count - 1
                WHERE workspace_id = ?
            """, (workspace_id,))

            conn.commit()
