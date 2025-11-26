"""Contract test for entity.list JSON-RPC interface.

Tests verify the JSON-RPC contract for listing entities,
ensuring correct request/response format, filtering, and pagination.

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


def test_list_entities_empty():
    """Test listing entities when workspace is empty."""
    request = {
        "jsonrpc": "2.0",
        "method": "entity.list",
        "params": {},
        "id": 1
    }

    response = call_cli(request)

    # Verify JSON-RPC response structure
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 1
    assert "result" in response

    result = response["result"]
    assert result["status"] == "success"
    assert "data" in result

    # Verify list structure
    data = result["data"]
    assert "entities" in data
    assert isinstance(data["entities"], list)
    assert "total_count" in data
    assert data["total_count"] >= 0


def test_list_entities_after_creation():
    """Test listing entities after creating some."""
    # Create multiple entities
    entities_to_create = [
        {
            "jsonrpc": "2.0",
            "method": "entity.create.point",
            "params": {"coordinates": [0.0, 0.0]},
            "id": 1
        },
        {
            "jsonrpc": "2.0",
            "method": "entity.create.line",
            "params": {"start": [0.0, 0.0], "end": [10.0, 10.0]},
            "id": 2
        },
        {
            "jsonrpc": "2.0",
            "method": "entity.create.circle",
            "params": {"center": [5.0, 5.0], "radius": 3.0},
            "id": 3
        }
    ]

    created_ids = []
    for create_request in entities_to_create:
        create_response = call_cli(create_request)
        created_ids.append(create_response["result"]["data"]["entity_id"])

    # List all entities
    list_request = {
        "jsonrpc": "2.0",
        "method": "entity.list",
        "params": {},
        "id": 4
    }

    response = call_cli(list_request)

    result = response["result"]
    data = result["data"]

    assert data["total_count"] >= 3
    assert len(data["entities"]) >= 3

    # Verify created entities are in list
    listed_ids = [e["entity_id"] for e in data["entities"]]
    for created_id in created_ids:
        assert created_id in listed_ids


def test_list_entities_filter_by_type():
    """Test filtering entities by type."""
    # Create entities of different types
    call_cli({
        "jsonrpc": "2.0",
        "method": "entity.create.point",
        "params": {"coordinates": [0.0, 0.0]},
        "id": 1
    })
    call_cli({
        "jsonrpc": "2.0",
        "method": "entity.create.line",
        "params": {"start": [0.0, 0.0], "end": [10.0, 10.0]},
        "id": 2
    })

    # List only point entities
    list_request = {
        "jsonrpc": "2.0",
        "method": "entity.list",
        "params": {
            "entity_type": "point"
        },
        "id": 3
    }

    response = call_cli(list_request)
    result = response["result"]
    data = result["data"]

    # All returned entities should be points
    for entity in data["entities"]:
        assert entity["entity_type"] == "point"


def test_list_entities_pagination():
    """Test entity list pagination."""
    # Create several entities
    for i in range(5):
        call_cli({
            "jsonrpc": "2.0",
            "method": "entity.create.point",
            "params": {"coordinates": [float(i), float(i)]},
            "id": i + 1
        })

    # Request with limit
    list_request = {
        "jsonrpc": "2.0",
        "method": "entity.list",
        "params": {
            "limit": 2,
            "offset": 0
        },
        "id": 100
    }

    response = call_cli(list_request)
    result = response["result"]
    data = result["data"]

    assert len(data["entities"]) <= 2
    assert data["total_count"] >= 5

    # Verify pagination metadata
    assert "limit" in data
    assert "offset" in data


def test_list_entities_invalid_filter():
    """Test listing with invalid filter parameters."""
    list_request = {
        "jsonrpc": "2.0",
        "method": "entity.list",
        "params": {
            "entity_type": "invalid_type"
        },
        "id": 1
    }

    response = call_cli(list_request)

    # Should succeed but return empty list
    # OR return error depending on implementation choice
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 1
    # Accept either empty result or error
    assert "result" in response or "error" in response


def test_list_entities_include_metadata():
    """Test that listed entities include basic metadata."""
    # Create an entity
    create_response = call_cli({
        "jsonrpc": "2.0",
        "method": "entity.create.point",
        "params": {"coordinates": [1.0, 2.0, 3.0]},
        "id": 1
    })

    entity_id = create_response["result"]["data"]["entity_id"]

    # List entities
    list_response = call_cli({
        "jsonrpc": "2.0",
        "method": "entity.list",
        "params": {},
        "id": 2
    })

    entities = list_response["result"]["data"]["entities"]

    # Find our entity
    our_entity = next(e for e in entities if e["entity_id"] == entity_id)

    # Verify metadata is included
    assert "entity_type" in our_entity
    assert "workspace_id" in our_entity
    assert "created_at" in our_entity
