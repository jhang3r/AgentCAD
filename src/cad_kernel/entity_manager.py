"""Entity management and base classes for geometric entities."""
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass
class GeometricEntity:
    """Base class for all CAD geometric entities.

    Attributes:
        entity_id: Unique identifier (format: workspace:type_uuid)
        entity_type: Type classification (point, line, circle, solid, etc.)
        workspace_id: Owning workspace identifier
        created_at: Entity creation timestamp (ISO 8601)
        modified_at: Last modification timestamp (ISO 8601)
        created_by_agent: Agent ID that created this entity
        parent_entities: List of parent entity IDs (entities this was derived from)
        child_entities: List of child entity IDs (entities derived from this)
        properties: Type-specific geometric properties
        bounding_box: Axis-aligned bounding box {min: [x,y,z], max: [x,y,z]}
        is_valid: Topology/geometry validity status
        validation_errors: List of validation error codes if invalid
    """

    entity_id: str
    entity_type: str
    workspace_id: str
    created_at: str
    modified_at: str
    created_by_agent: str
    properties: dict[str, Any]
    bounding_box: dict[str, list[float]]
    parent_entities: list[str] = field(default_factory=list)
    child_entities: list[str] = field(default_factory=list)
    is_valid: bool = True
    validation_errors: list[str] = field(default_factory=list)

    @classmethod
    def generate_entity_id(cls, workspace_id: str, entity_type: str) -> str:
        """Generate unique entity ID.

        Args:
            workspace_id: Workspace identifier
            entity_type: Type of entity

        Returns:
            Formatted entity ID (workspace:type_uuid)
        """
        unique_id = uuid.uuid4().hex[:8]
        return f"{workspace_id}:{entity_type}_{unique_id}"

    @classmethod
    def get_current_timestamp(cls) -> str:
        """Get current timestamp in ISO 8601 format with UTC timezone.

        Returns:
            ISO 8601 timestamp string
        """
        return datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Convert entity to dictionary representation.

        Returns:
            Dictionary with all entity fields
        """
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "workspace_id": self.workspace_id,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "created_by_agent": self.created_by_agent,
            "parent_entities": self.parent_entities,
            "child_entities": self.child_entities,
            "properties": self.properties,
            "bounding_box": self.bounding_box,
            "is_valid": self.is_valid,
            "validation_errors": self.validation_errors
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GeometricEntity":
        """Create entity from dictionary representation.

        Args:
            data: Dictionary with entity fields

        Returns:
            GeometricEntity instance
        """
        return cls(
            entity_id=data["entity_id"],
            entity_type=data["entity_type"],
            workspace_id=data["workspace_id"],
            created_at=data["created_at"],
            modified_at=data["modified_at"],
            created_by_agent=data["created_by_agent"],
            parent_entities=data.get("parent_entities", []),
            child_entities=data.get("child_entities", []),
            properties=data["properties"],
            bounding_box=data["bounding_box"],
            is_valid=data.get("is_valid", True),
            validation_errors=data.get("validation_errors", [])
        )


class EntityManager:
    """Manage entity lifecycle and validation."""

    def __init__(self, entity_store):
        """Initialize entity manager.

        Args:
            entity_store: EntityStore instance for persistence
        """
        self.entity_store = entity_store

    def create_entity(
        self,
        entity_type: str,
        workspace_id: str,
        agent_id: str,
        properties: dict[str, Any],
        bounding_box: dict[str, list[float]],
        parent_entities: Optional[list[str]] = None
    ) -> GeometricEntity:
        """Create and persist a new geometric entity.

        Args:
            entity_type: Type of entity to create
            workspace_id: Workspace identifier
            agent_id: Agent creating this entity
            properties: Entity-specific properties
            bounding_box: Axis-aligned bounding box
            parent_entities: List of parent entity IDs (optional)

        Returns:
            Created GeometricEntity instance
        """
        now = GeometricEntity.get_current_timestamp()
        entity_id = GeometricEntity.generate_entity_id(workspace_id, entity_type)

        entity = GeometricEntity(
            entity_id=entity_id,
            entity_type=entity_type,
            workspace_id=workspace_id,
            created_at=now,
            modified_at=now,
            created_by_agent=agent_id,
            parent_entities=parent_entities or [],
            child_entities=[],
            properties=properties,
            bounding_box=bounding_box,
            is_valid=True,
            validation_errors=[]
        )

        # Persist to database
        self.entity_store.create_entity(
            entity_id=entity.entity_id,
            entity_type=entity.entity_type,
            workspace_id=entity.workspace_id,
            created_by_agent=entity.created_by_agent,
            properties=entity.properties,
            bounding_box=entity.bounding_box,
            parent_entities=entity.parent_entities,
            is_valid=entity.is_valid,
            validation_errors=entity.validation_errors
        )

        return entity

    def get_entity(self, entity_id: str) -> Optional[GeometricEntity]:
        """Retrieve entity by ID.

        Args:
            entity_id: Entity identifier

        Returns:
            GeometricEntity instance or None if not found
        """
        data = self.entity_store.get_entity(entity_id)
        if data is None:
            return None
        return GeometricEntity.from_dict(data)

    def list_entities(
        self,
        workspace_id: str,
        entity_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> tuple[list[dict[str, Any]], int]:
        """List entities in workspace.

        Args:
            workspace_id: Workspace to query
            entity_type: Optional type filter
            limit: Maximum results
            offset: Pagination offset

        Returns:
            Tuple of (entity list, total count)
        """
        return self.entity_store.list_entities(
            workspace_id=workspace_id,
            entity_type=entity_type,
            limit=limit,
            offset=offset
        )

    def validate_coordinates(self, coordinates: list[float]) -> bool:
        """Validate coordinate values are finite and within bounds.

        Args:
            coordinates: List of coordinate values

        Returns:
            True if valid, False otherwise
        """
        import math

        for coord in coordinates:
            # Check if finite (no NaN, no Infinity)
            if not math.isfinite(coord):
                return False
            # Check if within workspace bounds [-1e6, 1e6]
            if abs(coord) > 1e6:
                return False

        return True
