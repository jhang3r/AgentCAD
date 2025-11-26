"""Error handling and structured error responses."""
from enum import Enum
from typing import Any, Optional


class ErrorCode(int, Enum):
    """Enumeration of all error codes (JSON-RPC 2.0 numeric codes)."""

    # Request/parsing errors (standard JSON-RPC codes)
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    INVALID_COMMAND = -32601

    # Parameter validation errors
    INVALID_PARAMETER = -32602
    MISSING_PARAMETER = -32602

    # Entity errors (custom codes starting at -32001)
    ENTITY_NOT_FOUND = -32001
    INVALID_GEOMETRY = -32603

    # Constraint errors
    CONSTRAINT_CONFLICT = -32002
    CIRCULAR_DEPENDENCY = -32003
    INVALID_CONSTRAINT = -32004

    # Operation errors
    OPERATION_INVALID = -32005
    TOPOLOGY_ERROR = -32006

    # Workspace errors
    WORKSPACE_CONFLICT = -32007

    # File errors
    FILE_NOT_FOUND = -32008
    UNSUPPORTED_FORMAT = -32009
    IMPORT_FAILED = -32010

    # System errors
    GEOMETRY_ENGINE_ERROR = -32603
    INSUFFICIENT_MEMORY = -32011
    TIMEOUT = -32012


class ErrorHandler:
    """Handle errors and generate structured error responses."""

    def __init__(self):
        """Initialize error handler with suggestion mappings."""
        self.suggestions = {
            ErrorCode.INVALID_PARAMETER: "Check parameter type and value constraints",
            ErrorCode.MISSING_PARAMETER: "Provide all required parameters",
            ErrorCode.ENTITY_NOT_FOUND: "Use entity.list to see available entities",
            ErrorCode.INVALID_GEOMETRY: "Ensure coordinates are finite and within bounds [-1e6, 1e6]",
            ErrorCode.CONSTRAINT_CONFLICT: "Remove conflicting constraint first using constraint.remove",
            ErrorCode.WORKSPACE_CONFLICT: "Use workspace.resolve_conflict to resolve merge conflicts",
            ErrorCode.FILE_NOT_FOUND: "Check file path exists and is accessible",
            ErrorCode.UNSUPPORTED_FORMAT: "Supported formats: STEP, STL, DXF"
        }

    def create_error_data(
        self,
        error_code: ErrorCode,
        field: Optional[str] = None,
        provided_value: Any = None,
        constraints: Optional[dict[str, Any]] = None,
        suggestion: Optional[str] = None,
        recoverable: bool = True,
        **extra_data
    ) -> dict[str, Any]:
        """Create structured error data dictionary.

        Args:
            error_code: Error code enum
            field: Field that caused the error
            provided_value: Value that was provided
            constraints: Valid constraints for the field
            suggestion: Suggested fix (auto-generated if not provided)
            recoverable: Whether error is recoverable
            **extra_data: Additional error-specific data

        Returns:
            Structured error data dictionary
        """
        data: dict[str, Any] = {"recoverable": recoverable}

        if field:
            data["field"] = field

        if provided_value is not None:
            data["provided_value"] = provided_value

        if constraints:
            data["constraints"] = constraints

        # Use provided suggestion or get default
        if suggestion:
            data["suggestion"] = suggestion
        elif error_code in self.suggestions:
            data["suggestion"] = self.suggestions[error_code]

        # Add any extra data
        data.update(extra_data)

        return data

    def invalid_parameter(
        self,
        field: str,
        provided_value: Any,
        constraints: Optional[dict[str, Any]] = None,
        reason: Optional[str] = None
    ) -> tuple[str, dict[str, Any]]:
        """Generate INVALID_PARAMETER error.

        Args:
            field: Parameter name
            provided_value: Invalid value provided
            constraints: Valid constraints
            reason: Specific reason for invalidity

        Returns:
            Tuple of (error_message, error_data)
        """
        message = f"Invalid value for parameter '{field}'"
        if reason:
            message += f": {reason}"

        data = self.create_error_data(
            ErrorCode.INVALID_PARAMETER,
            field=field,
            provided_value=provided_value,
            constraints=constraints
        )

        return message, data

    def missing_parameter(self, field: str) -> tuple[str, dict[str, Any]]:
        """Generate MISSING_PARAMETER error.

        Args:
            field: Required parameter name

        Returns:
            Tuple of (error_message, error_data)
        """
        message = f"Missing required parameter: '{field}'"
        data = self.create_error_data(
            ErrorCode.MISSING_PARAMETER,
            field=field
        )

        return message, data

    def entity_not_found(self, entity_id: str, workspace_id: str) -> tuple[str, dict[str, Any]]:
        """Generate ENTITY_NOT_FOUND error.

        Args:
            entity_id: Entity that was not found
            workspace_id: Workspace that was searched

        Returns:
            Tuple of (error_message, error_data)
        """
        message = f"Entity '{entity_id}' does not exist"
        data = self.create_error_data(
            ErrorCode.ENTITY_NOT_FOUND,
            entity_id=entity_id,
            workspace_id=workspace_id
        )

        return message, data

    def invalid_geometry(self, reason: str, field: Optional[str] = None) -> tuple[str, dict[str, Any]]:
        """Generate INVALID_GEOMETRY error.

        Args:
            reason: Reason for geometry invalidity
            field: Field with invalid geometry

        Returns:
            Tuple of (error_message, error_data)
        """
        message = f"Invalid geometry: {reason}"
        data = self.create_error_data(
            ErrorCode.INVALID_GEOMETRY,
            field=field
        )

        return message, data

    def constraint_conflict(
        self,
        conflicting_constraint_id: str,
        conflicting_constraint_type: str,
        reason: str
    ) -> tuple[str, dict[str, Any]]:
        """Generate CONSTRAINT_CONFLICT error.

        Args:
            conflicting_constraint_id: ID of conflicting constraint
            conflicting_constraint_type: Type of conflicting constraint
            reason: Reason for conflict

        Returns:
            Tuple of (error_message, error_data)
        """
        message = f"Constraint conflicts with existing {conflicting_constraint_type} constraint: {reason}"
        data = self.create_error_data(
            ErrorCode.CONSTRAINT_CONFLICT,
            conflicting_constraint_id=conflicting_constraint_id,
            conflicting_constraint_type=conflicting_constraint_type
        )

        return message, data

    def operation_invalid(self, reason: str) -> tuple[str, dict[str, Any]]:
        """Generate OPERATION_INVALID error.

        Args:
            reason: Reason operation cannot be performed

        Returns:
            Tuple of (error_message, error_data)
        """
        message = f"Operation cannot be performed: {reason}"
        data = self.create_error_data(
            ErrorCode.OPERATION_INVALID,
            recoverable=True
        )

        return message, data
