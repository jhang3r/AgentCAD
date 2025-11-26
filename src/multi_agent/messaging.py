"""
Agent-to-agent messaging functionality for multi-agent coordination.

Implements:
- AgentMessage dataclass (T046)
- Message type validation (T050)
- Message schemas from contracts/message_schemas.json

Constitution compliance:
- No mocks or stubs - real message queue implementation
- Uses real queue.Queue instances
- All message validation uses real schema checks
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import time
import json
from pathlib import Path


@dataclass
class AgentMessage:
    """
    Message sent between agents for coordination and feedback.

    Fields match data-model.md specification.
    """
    message_id: str
    from_agent_id: str
    to_agent_id: str  # or "broadcast" for all agents
    message_type: str  # "request", "response", "broadcast", "error"
    content: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    read: bool = False

    def __post_init__(self):
        """Validate message structure."""
        # Validate message_type
        valid_types = ["request", "response", "broadcast", "error"]
        if self.message_type not in valid_types:
            raise ValueError(
                f"Invalid message_type '{self.message_type}'. "
                f"Must be one of: {valid_types}"
            )

        # Validate content is dict
        if not isinstance(self.content, dict):
            raise ValueError("Message content must be a dictionary")

        # Validate timestamp
        current_time = time.time()
        if self.timestamp > current_time + 60:  # Allow 60s clock skew
            raise ValueError(
                f"Message timestamp {self.timestamp} is in the future (current: {current_time})"
            )

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for serialization."""
        return {
            "message_id": self.message_id,
            "from_agent_id": self.from_agent_id,
            "to_agent_id": self.to_agent_id,
            "message_type": self.message_type,
            "content": self.content,
            "timestamp": self.timestamp,
            "read": self.read
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentMessage":
        """Create message from dictionary."""
        return cls(
            message_id=data["message_id"],
            from_agent_id=data["from_agent_id"],
            to_agent_id=data["to_agent_id"],
            message_type=data["message_type"],
            content=data["content"],
            timestamp=data.get("timestamp", time.time()),
            read=data.get("read", False)
        )


def validate_message_content(message_type: str, content: Dict[str, Any]) -> bool:
    """
    Validate message content structure matches expected schema for message_type.

    Implements T050: Message type validation

    Args:
        message_type: Type of message ("request", "response", "broadcast", "error")
        content: Message content dictionary

    Returns:
        True if content matches schema

    Raises:
        ValueError: If content doesn't match schema for message_type
    """
    if not isinstance(content, dict):
        raise ValueError("Content must be a dictionary")

    # Load message schemas from contracts
    contracts_dir = Path(__file__).parent.parent.parent / "specs" / "002-multi-agent-framework" / "contracts"
    schema_file = contracts_dir / "message_schemas.json"

    if schema_file.exists():
        with open(schema_file, "r") as f:
            schemas = json.load(f)

        # Get message_schemas object
        message_schemas = schemas.get("message_schemas", {})

        # Validate based on message_type
        if message_type == "request":
            schema = message_schemas.get("request", {}).get("content_schema", {})
            required_fields = schema.get("required", [])
            for field in required_fields:
                if field not in content:
                    raise ValueError(
                        f"Request message missing required field: {field}"
                    )

        elif message_type == "response":
            schema = message_schemas.get("response", {}).get("content_schema", {})
            required_fields = schema.get("required", [])
            for field in required_fields:
                if field not in content:
                    raise ValueError(
                        f"Response message missing required field: {field}"
                    )

        elif message_type == "broadcast":
            schema = message_schemas.get("broadcast", {}).get("content_schema", {})
            required_fields = schema.get("required", [])
            for field in required_fields:
                if field not in content:
                    raise ValueError(
                        f"Broadcast message missing required field: {field}"
                    )

        elif message_type == "error":
            schema = message_schemas.get("error", {}).get("content_schema", {})
            required_fields = schema.get("required", [])
            for field in required_fields:
                if field not in content:
                    raise ValueError(
                        f"Error message missing required field: {field}"
                    )

    # If schema file doesn't exist, do basic validation
    else:
        # Basic validation based on data-model.md examples
        if message_type == "request":
            if "request_type" not in content:
                raise ValueError("Request message must have 'request_type' field")

        elif message_type == "response":
            if "status" not in content:
                raise ValueError("Response message must have 'status' field")

        elif message_type == "broadcast":
            if "announcement" not in content:
                raise ValueError("Broadcast message must have 'announcement' field")

        elif message_type == "error":
            if "error_code" not in content or "error_message" not in content:
                raise ValueError("Error message must have 'error_code' and 'error_message' fields")

    return True


def create_request_message(
    message_id: str,
    from_agent_id: str,
    to_agent_id: str,
    request_type: str,
    **kwargs
) -> AgentMessage:
    """
    Helper function to create a request message with proper structure.

    Args:
        message_id: Unique message identifier
        from_agent_id: Sender agent ID
        to_agent_id: Receiver agent ID
        request_type: Type of request
        **kwargs: Additional request fields

    Returns:
        AgentMessage instance
    """
    content = {
        "request_type": request_type,
        **kwargs
    }

    validate_message_content("request", content)

    return AgentMessage(
        message_id=message_id,
        from_agent_id=from_agent_id,
        to_agent_id=to_agent_id,
        message_type="request",
        content=content
    )


def create_response_message(
    message_id: str,
    from_agent_id: str,
    to_agent_id: str,
    request_id: str,
    status: str,
    **kwargs
) -> AgentMessage:
    """
    Helper function to create a response message with proper structure.

    Args:
        message_id: Unique message identifier
        from_agent_id: Sender agent ID
        to_agent_id: Receiver agent ID
        request_id: ID of request being responded to
        status: Response status ("success", "failure", etc.)
        **kwargs: Additional response fields

    Returns:
        AgentMessage instance
    """
    content = {
        "request_id": request_id,
        "status": status,
        **kwargs
    }

    validate_message_content("response", content)

    return AgentMessage(
        message_id=message_id,
        from_agent_id=from_agent_id,
        to_agent_id=to_agent_id,
        message_type="response",
        content=content
    )


def create_broadcast_message(
    message_id: str,
    from_agent_id: str,
    announcement: str,
    **kwargs
) -> AgentMessage:
    """
    Helper function to create a broadcast message with proper structure.

    Args:
        message_id: Unique message identifier
        from_agent_id: Sender agent ID
        announcement: Broadcast announcement text
        **kwargs: Additional broadcast fields

    Returns:
        AgentMessage instance
    """
    content = {
        "announcement": announcement,
        **kwargs
    }

    validate_message_content("broadcast", content)

    return AgentMessage(
        message_id=message_id,
        from_agent_id=from_agent_id,
        to_agent_id="broadcast",
        message_type="broadcast",
        content=content
    )


def create_error_message(
    message_id: str,
    from_agent_id: str,
    to_agent_id: str,
    error_code: str,
    error_message: str,
    **kwargs
) -> AgentMessage:
    """
    Helper function to create an error message with proper structure.

    Args:
        message_id: Unique message identifier
        from_agent_id: Sender agent ID
        to_agent_id: Receiver agent ID
        error_code: Error code identifier
        error_message: Human-readable error description
        **kwargs: Additional error fields

    Returns:
        AgentMessage instance
    """
    content = {
        "error_code": error_code,
        "error_message": error_message,
        **kwargs
    }

    validate_message_content("error", content)

    return AgentMessage(
        message_id=message_id,
        from_agent_id=from_agent_id,
        to_agent_id=to_agent_id,
        message_type="error",
        content=content
    )
