"""
Contract tests for the messaging module.

Verifies:
- AgentMessage dataclass structure and validation
- Message content validation against schemas
- Helper functions for message creation
- Error handling for invalid messages
"""

import pytest
import time
from src.multi_agent.messaging import (
    AgentMessage,
    validate_message_content,
    create_request_message,
    create_response_message,
    create_broadcast_message,
    create_error_message
)

class TestAgentMessage:
    """Tests for AgentMessage dataclass."""

    def test_agent_message_creation(self):
        """Verify AgentMessage can be created with valid data."""
        msg = AgentMessage(
            message_id="msg_001",
            from_agent_id="agent_a",
            to_agent_id="agent_b",
            message_type="request",
            content={"request_type": "validate_component"},
            timestamp=time.time()
        )
        
        assert msg.message_id == "msg_001"
        assert msg.from_agent_id == "agent_a"
        assert msg.to_agent_id == "agent_b"
        assert msg.message_type == "request"
        assert msg.content == {"request_type": "validate_component"}
        assert not msg.read

    def test_invalid_message_type(self):
        """Verify ValueError raised for invalid message type."""
        with pytest.raises(ValueError, match="Invalid message_type"):
            AgentMessage(
                message_id="msg_001",
                from_agent_id="agent_a",
                to_agent_id="agent_b",
                message_type="invalid_type",
                content={}
            )

    def test_invalid_content_type(self):
        """Verify ValueError raised if content is not a dict."""
        with pytest.raises(ValueError, match="Message content must be a dictionary"):
            AgentMessage(
                message_id="msg_001",
                from_agent_id="agent_a",
                to_agent_id="agent_b",
                message_type="request",
                content="not a dict"
            )

    def test_future_timestamp(self):
        """Verify ValueError raised for future timestamp."""
        future_time = time.time() + 100  # > 60s in future
        with pytest.raises(ValueError, match="is in the future"):
            AgentMessage(
                message_id="msg_001",
                from_agent_id="agent_a",
                to_agent_id="agent_b",
                message_type="request",
                content={"request_type": "test"},
                timestamp=future_time
            )

    def test_serialization(self):
        """Verify to_dict and from_dict work correctly."""
        original_msg = AgentMessage(
            message_id="msg_001",
            from_agent_id="agent_a",
            to_agent_id="agent_b",
            message_type="request",
            content={"request_type": "test"},
            timestamp=time.time()
        )
        
        data = original_msg.to_dict()
        reconstructed_msg = AgentMessage.from_dict(data)
        
        assert reconstructed_msg.message_id == original_msg.message_id
        assert reconstructed_msg.from_agent_id == original_msg.from_agent_id
        assert reconstructed_msg.content == original_msg.content
        assert reconstructed_msg.timestamp == original_msg.timestamp


class TestMessageValidation:
    """Tests for validate_message_content function."""

    def test_validate_request_valid(self):
        """Verify valid request content passes validation."""
        content = {
            "request_type": "validate_component",
            "component_id": "entity_123",
            "validation_criteria": ["check_dimensions"]
        }
        assert validate_message_content("request", content) is True

    def test_validate_request_missing_field(self):
        """Verify missing required field raises ValueError."""
        content = {"component_id": "entity_123"}  # Missing request_type
        with pytest.raises(ValueError, match="missing required field"):
            validate_message_content("request", content)

    def test_validate_response_valid(self):
        """Verify valid response content passes validation."""
        content = {
            "request_id": "msg_001",
            "status": "success",
            "validation_results": {"check": "pass"}
        }
        assert validate_message_content("response", content) is True

    def test_validate_broadcast_valid(self):
        """Verify valid broadcast content passes validation."""
        content = {
            "announcement": "workspace_merge_complete",
            "merged_workspace": "ws_main"
        }
        assert validate_message_content("broadcast", content) is True

    def test_validate_error_valid(self):
        """Verify valid error content passes validation."""
        content = {
            "error_code": "OPERATION_FAILED",
            "error_message": "Something went wrong"
        }
        assert validate_message_content("error", content) is True


class TestMessageHelpers:
    """Tests for message creation helper functions."""

    def test_create_request_message(self):
        """Verify create_request_message creates valid AgentMessage."""
        msg = create_request_message(
            message_id="msg_req_1",
            from_agent_id="agent_a",
            to_agent_id="agent_b",
            request_type="validate_component",
            component_id="entity_1"
        )
        
        assert isinstance(msg, AgentMessage)
        assert msg.message_type == "request"
        assert msg.content["request_type"] == "validate_component"
        assert msg.content["component_id"] == "entity_1"

    def test_create_response_message(self):
        """Verify create_response_message creates valid AgentMessage."""
        msg = create_response_message(
            message_id="msg_resp_1",
            from_agent_id="agent_b",
            to_agent_id="agent_a",
            request_id="msg_req_1",
            status="success"
        )
        
        assert isinstance(msg, AgentMessage)
        assert msg.message_type == "response"
        assert msg.content["request_id"] == "msg_req_1"
        assert msg.content["status"] == "success"

    def test_create_broadcast_message(self):
        """Verify create_broadcast_message creates valid AgentMessage."""
        msg = create_broadcast_message(
            message_id="msg_broad_1",
            from_agent_id="agent_a",
            announcement="task_completed",
            task_id="task_1"
        )
        
        assert isinstance(msg, AgentMessage)
        assert msg.message_type == "broadcast"
        assert msg.to_agent_id == "broadcast"
        assert msg.content["announcement"] == "task_completed"
        assert msg.content["task_id"] == "task_1"

    def test_create_error_message(self):
        """Verify create_error_message creates valid AgentMessage."""
        msg = create_error_message(
            message_id="msg_err_1",
            from_agent_id="agent_b",
            to_agent_id="agent_a",
            error_code="INVALID_PARAMETERS",
            error_message="Bad input"
        )
        
        assert isinstance(msg, AgentMessage)
        assert msg.message_type == "error"
        assert msg.content["error_code"] == "INVALID_PARAMETERS"
        assert msg.content["error_message"] == "Bad input"
