"""Contract test for entity.query JSON-RPC interface.

Tests verify the JSON-RPC contract for querying entity details,
ensuring correct request/response format and error handling.

TDD: These tests should FAIL until implementation is complete.
"""
import json
import subprocess
import sys
from pathlib import Path


def call_cli(request: dict) -> dict:
    """Helper to call CLI with JSON-RPC request."""
    input_data = json.dumps(request) + "\n"
    result = subprocess.run(
        [sys.executable, "-m", "src.agent_interface.cli"],
        input=input_data,
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent
    )

    if result.returncode != 0:
        raise RuntimeError(f"CLI failed: {result.stderr}")

    return json.loads(result.stdout.strip())


def test_query_point_success():
    """Test querying a point entity."""
    # First create a point
    create_request = {
        "jsonrpc": "2.0",
        "method": "entity.create.point",
        "params": {
            "coordinates": [10.0, 20.0, 30.0]
        },
        "id": 1
    }

    create_response = call_cli(create_request)
    entity_id = create_response["result"]["data"]["entity_id"]

    # Now query it
    query_request = {
        "jsonrpc": "2.0",
        "method": "entity.query",
        "params": {
            "entity_id": entity_id
        },
        "id": 2
    }

    response = call_cli(query_request)

    # Verify JSON-RPC response structure
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 2
    assert "result" in response

    result = response["result"]
    assert result["status"] == "success"
    assert "data" in result

    # Verify entity data
    data = result["data"]
    assert data["entity_id"] == entity_id
    assert data["entity_type"] == "point"
    assert data["coordinates"] == [10.0, 20.0, 30.0]
    assert "workspace_id" in data
    assert "created_at" in data


def test_query_line_success():
    """Test querying a line entity."""
    # First create a line
    create_request = {
        "jsonrpc": "2.0",
        "method": "entity.create.line",
        "params": {
            "start": [0.0, 0.0],
            "end": [10.0, 10.0]
        },
        "id": 1
    }

    create_response = call_cli(create_request)
    entity_id = create_response["result"]["data"]["entity_id"]

    # Now query it
    query_request = {
        "jsonrpc": "2.0",
        "method": "entity.query",
        "params": {
            "entity_id": entity_id
        },
        "id": 2
    }

    response = call_cli(query_request)

    result = response["result"]
    data = result["data"]
    assert data["entity_id"] == entity_id
    assert data["entity_type"] == "line"
    assert "length" in data
    assert "direction_vector" in data


def test_query_circle_success():
    """Test querying a circle entity."""
    # First create a circle
    create_request = {
        "jsonrpc": "2.0",
        "method": "entity.create.circle",
        "params": {
            "center": [5.0, 5.0],
            "radius": 3.0
        },
        "id": 1
    }

    create_response = call_cli(create_request)
    entity_id = create_response["result"]["data"]["entity_id"]

    # Now query it
    query_request = {
        "jsonrpc": "2.0",
        "method": "entity.query",
        "params": {
            "entity_id": entity_id
        },
        "id": 2
    }

    response = call_cli(query_request)

    result = response["result"]
    data = result["data"]
    assert data["entity_id"] == entity_id
    assert data["entity_type"] == "circle"
    assert "area" in data
    assert "circumference" in data


def test_query_entity_not_found():
    """Test querying non-existent entity."""
    query_request = {
        "jsonrpc": "2.0",
        "method": "entity.query",
        "params": {
            "entity_id": "main:nonexistent_12345"
        },
        "id": 1
    }

    response = call_cli(query_request)

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 1
    assert "error" in response

    error = response["error"]
    assert error["code"] == -32001  # ENTITY_NOT_FOUND
    assert "not found" in error["message"].lower()


def test_query_missing_entity_id():
    """Test query without entity_id parameter."""
    query_request = {
        "jsonrpc": "2.0",
        "method": "entity.query",
        "params": {},
        "id": 1
    }

    response = call_cli(query_request)

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 1
    assert "error" in response

    error = response["error"]
    assert error["code"] == -32602  # INVALID_PARAMETER
    assert "entity_id" in error["message"].lower()


def test_query_invalid_entity_id_format():
    """Test query with malformed entity_id."""
    query_request = {
        "jsonrpc": "2.0",
        "method": "entity.query",
        "params": {
            "entity_id": "invalid_format"
        },
        "id": 1
    }

    response = call_cli(query_request)

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 1
    assert "error" in response

    error = response["error"]
    # Could be INVALID_PARAMETER or ENTITY_NOT_FOUND
    assert error["code"] in (-32602, -32001)
