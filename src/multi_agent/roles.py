"""
Role templates and role-based access control for multi-agent system.

Defines agent roles with specific capabilities and constraints. Each role specifies
allowed and forbidden operations to enforce separation of concerns.
"""

from dataclasses import dataclass, field
from typing import List
import json
from pathlib import Path


@dataclass
class RoleTemplate:
    """
    Defines a specialized agent role with permitted capabilities and constraints.

    Fields:
        name: Role name (e.g., "designer", "modeler", "validator")
        description: Human-readable role purpose
        allowed_operations: JSON-RPC method names agent can execute
        forbidden_operations: Explicitly prohibited operations
        example_tasks: Sample tasks demonstrating role purpose

    Validation rules:
        - name must be unique across all role templates
        - allowed_operations and forbidden_operations must not overlap
        - All operation names must match existing JSON-RPC CLI methods
        - At least one allowed_operations must be specified
    """
    name: str
    description: str
    allowed_operations: List[str]
    forbidden_operations: List[str]
    example_tasks: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate role template fields."""
        if not self.name:
            raise ValueError("Role name cannot be empty")

        if not self.allowed_operations:
            raise ValueError(f"Role {self.name} must have at least one allowed operation")

        # Check for overlap between allowed and forbidden
        overlap = set(self.allowed_operations) & set(self.forbidden_operations)
        if overlap:
            raise ValueError(
                f"Role {self.name} has overlapping allowed and forbidden operations: {overlap}"
            )

    def can_execute(self, operation: str) -> bool:
        """
        Check if this role can execute the specified operation.

        Args:
            operation: JSON-RPC method name (e.g., "entity.create_point")

        Returns:
            True if operation is allowed and not forbidden, False otherwise
        """
        if operation in self.forbidden_operations:
            return False
        return operation in self.allowed_operations


class RoleViolationError(Exception):
    """
    Raised when an agent attempts an operation outside its role's capabilities.

    Attributes:
        agent_id: ID of the agent that attempted the operation
        role_name: Name of the agent's role
        operation: Operation that was attempted
        message: Detailed error message
    """
    def __init__(self, agent_id: str, role_name: str, operation: str):
        self.agent_id = agent_id
        self.role_name = role_name
        self.operation = operation
        self.message = (
            f"Agent {agent_id} with role {role_name} cannot execute {operation} - "
            f"operation not permitted by role constraints"
        )
        super().__init__(self.message)


# Predefined role templates will be loaded from contracts/role_templates.json
# Placeholder - will be populated by load_predefined_roles()
PREDEFINED_ROLES: dict[str, RoleTemplate] = {}


def load_predefined_roles(roles_file_path: str = None) -> dict[str, RoleTemplate]:
    """
    Load predefined role templates from contracts/role_templates.json.

    Args:
        roles_file_path: Path to role templates JSON file. If None, uses default
                        location: specs/002-multi-agent-framework/contracts/role_templates.json

    Returns:
        Dictionary mapping role name to RoleTemplate instance

    Raises:
        FileNotFoundError: If role templates file doesn't exist
        json.JSONDecodeError: If file contains invalid JSON
    """
    if roles_file_path is None:
        # Default location relative to repository root
        repo_root = Path(__file__).parent.parent.parent
        roles_file_path = repo_root / "specs" / "002-multi-agent-framework" / "contracts" / "role_templates.json"

    roles_path = Path(roles_file_path)
    if not roles_path.exists():
        raise FileNotFoundError(f"Role templates file not found: {roles_path}")

    with open(roles_path, 'r') as f:
        data = json.load(f)

    roles = {}
    for role_data in data.get("role_templates", []):
        role = RoleTemplate(
            name=role_data["name"],
            description=role_data["description"],
            allowed_operations=role_data["allowed_operations"],
            forbidden_operations=role_data["forbidden_operations"],
            example_tasks=role_data.get("example_tasks", [])
        )
        roles[role.name] = role

    return roles


# Load predefined roles on module import
try:
    PREDEFINED_ROLES = load_predefined_roles()
except (FileNotFoundError, json.JSONDecodeError):
    # Roles will be loaded later when contracts file is available
    pass
