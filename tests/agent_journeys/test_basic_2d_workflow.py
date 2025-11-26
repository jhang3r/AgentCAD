"""Agent journey test for basic 2D geometry workflow.

This test simulates an AI agent's journey through creating and querying
2D geometric entities, verifying the complete workflow end-to-end.

Tests follow TDD principles and use real OCCT (no mocks).
"""
import json
import subprocess
import sys
from pathlib import Path


def call_cli(request: dict) -> dict:
    """Helper to call CLI with JSON-RPC request.

    Args:
        request: JSON-RPC request dict

    Returns:
        JSON-RPC response dict
    """
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


def test_basic_2d_workflow():
    """Test complete agent workflow: create entities → query → verify.

    Simulates an AI agent learning to work with 2D geometry:
    1. Create a point
    2. Query the point to verify properties
    3. Create a line
    4. Create a circle
    5. List all entities
    6. Verify all entities are accessible
    """
    # Step 1: Agent creates a point
    point_request = {
        "jsonrpc": "2.0",
        "method": "entity.create.point",
        "params": {
            "coordinates": [10.0, 20.0]
        },
        "id": 1
    }

    point_response = call_cli(point_request)

    # Verify point creation succeeded
    assert point_response["jsonrpc"] == "2.0"
    assert point_response["id"] == 1
    assert "result" in point_response
    assert point_response["result"]["status"] == "success"

    point_data = point_response["result"]["data"]
    point_id = point_data["entity_id"]
    assert point_id.startswith("main:point_")
    assert point_data["coordinates"] == [10.0, 20.0, 0.0]

    # Step 2: Agent queries the point to verify it was created
    query_request = {
        "jsonrpc": "2.0",
        "method": "entity.query",
        "params": {
            "entity_id": point_id
        },
        "id": 2
    }

    query_response = call_cli(query_request)

    # Verify query succeeded and data matches
    assert query_response["result"]["status"] == "success"
    queried_data = query_response["result"]["data"]
    assert queried_data["entity_id"] == point_id
    assert queried_data["entity_type"] == "point"
    assert queried_data["coordinates"] == [10.0, 20.0, 0.0]

    # Step 3: Agent creates a line
    line_request = {
        "jsonrpc": "2.0",
        "method": "entity.create.line",
        "params": {
            "start": [0.0, 0.0],
            "end": [30.0, 40.0]
        },
        "id": 3
    }

    line_response = call_cli(line_request)

    # Verify line creation
    assert line_response["result"]["status"] == "success"
    line_data = line_response["result"]["data"]
    line_id = line_data["entity_id"]
    assert line_id.startswith("main:line_")
    assert "length" in line_data
    assert line_data["length"] == 50.0  # 3-4-5 triangle scaled by 10
    assert "direction_vector" in line_data

    # Step 4: Agent creates a circle
    circle_request = {
        "jsonrpc": "2.0",
        "method": "entity.create.circle",
        "params": {
            "center": [50.0, 50.0],
            "radius": 15.0
        },
        "id": 4
    }

    circle_response = call_cli(circle_request)

    # Verify circle creation
    assert circle_response["result"]["status"] == "success"
    circle_data = circle_response["result"]["data"]
    circle_id = circle_data["entity_id"]
    assert circle_id.startswith("main:circle_")
    assert circle_data["radius"] == 15.0
    assert "area" in circle_data
    assert "circumference" in circle_data

    # Step 5: Agent lists all entities to see what it created
    list_request = {
        "jsonrpc": "2.0",
        "method": "entity.list",
        "params": {},
        "id": 5
    }

    list_response = call_cli(list_request)

    # Verify list contains all created entities
    assert list_response["result"]["status"] == "success"
    list_data = list_response["result"]["data"]
    assert "entities" in list_data
    assert "total_count" in list_data
    assert list_data["total_count"] >= 3

    # Verify our entities are in the list
    entity_ids = [e["entity_id"] for e in list_data["entities"]]
    assert point_id in entity_ids
    assert line_id in entity_ids
    assert circle_id in entity_ids

    # Step 6: Verify each entity has required metadata
    for entity in list_data["entities"]:
        assert "entity_id" in entity
        assert "entity_type" in entity
        # Note: Other tests may have created solids, so don't restrict entity types
        assert "workspace_id" in entity
        assert "created_at" in entity


def test_agent_learns_from_error():
    """Test agent receives helpful error feedback and can correct.

    Simulates an agent making mistakes and learning from error messages:
    1. Agent tries to create invalid point (out of bounds)
    2. Receives structured error with suggestion
    3. Agent corrects and succeeds
    """
    # Step 1: Agent makes a mistake - point out of bounds
    invalid_request = {
        "jsonrpc": "2.0",
        "method": "entity.create.point",
        "params": {
            "coordinates": [2e6, 0.0]  # Exceeds bounds
        },
        "id": 1
    }

    error_response = call_cli(invalid_request)

    # Verify agent receives structured error feedback
    assert error_response["jsonrpc"] == "2.0"
    assert error_response["id"] == 1
    assert "error" in error_response

    error = error_response["error"]
    assert error["code"] == -32603  # INVALID_GEOMETRY
    assert "bounds" in error["message"].lower()

    # Step 2: Agent learns from error and corrects
    corrected_request = {
        "jsonrpc": "2.0",
        "method": "entity.create.point",
        "params": {
            "coordinates": [100.0, 200.0]  # Within bounds
        },
        "id": 2
    }

    success_response = call_cli(corrected_request)

    # Verify correction succeeded
    assert success_response["result"]["status"] == "success"
    assert success_response["result"]["data"]["coordinates"] == [100.0, 200.0, 0.0]


def test_agent_filters_entity_list():
    """Test agent can filter entities by type.

    Demonstrates agent learning to use filtering:
    1. Create multiple entity types
    2. Filter by specific type
    3. Verify only requested type returned
    """
    # Create entities of different types
    call_cli({
        "jsonrpc": "2.0",
        "method": "entity.create.point",
        "params": {"coordinates": [1.0, 1.0]},
        "id": 1
    })

    call_cli({
        "jsonrpc": "2.0",
        "method": "entity.create.point",
        "params": {"coordinates": [2.0, 2.0]},
        "id": 2
    })

    call_cli({
        "jsonrpc": "2.0",
        "method": "entity.create.line",
        "params": {"start": [0.0, 0.0], "end": [5.0, 5.0]},
        "id": 3
    })

    # Agent filters for only points
    filter_request = {
        "jsonrpc": "2.0",
        "method": "entity.list",
        "params": {
            "entity_type": "point"
        },
        "id": 4
    }

    filter_response = call_cli(filter_request)

    # Verify only points returned
    entities = filter_response["result"]["data"]["entities"]
    for entity in entities:
        assert entity["entity_type"] == "point"


def test_agent_performance_feedback():
    """Test agent receives performance metrics in responses.

    Verifies that responses include execution time for learning:
    1. Create entity
    2. Check response includes performance metadata
    3. Verify execution time is within expected bounds
    """
    request = {
        "jsonrpc": "2.0",
        "method": "entity.create.point",
        "params": {
            "coordinates": [0.0, 0.0]
        },
        "id": 1
    }

    response = call_cli(request)

    # Verify performance metadata is included
    result = response["result"]
    assert "metadata" in result

    metadata = result["metadata"]
    assert "execution_time_ms" in metadata
    assert "operation_type" in metadata
    assert metadata["operation_type"] == "entity.create.point"

    # Simple operations should be fast (<100ms per spec)
    execution_time = metadata["execution_time_ms"]
    assert execution_time < 100, f"Point creation took {execution_time}ms, expected <100ms"
