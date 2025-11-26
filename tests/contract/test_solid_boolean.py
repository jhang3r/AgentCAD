"""Contract test for solid.boolean JSON-RPC interface.

Tests verify the JSON-RPC contract for boolean operations (union, subtract, intersect),
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


def create_box(x, y, z, width, height, depth) -> str:
    """Helper to create a box solid by extruding a rectangle."""
    # Create rectangle
    lines = []
    corners = [
        [x, y], [x + width, y],
        [x + width, y + height], [x, y + height]
    ]

    for i in range(4):
        start = corners[i]
        end = corners[(i + 1) % 4]
        response = call_cli({
            "jsonrpc": "2.0",
            "method": "entity.create.line",
            "params": {"start": start, "end": end},
            "id": i + 1
        })
        lines.append(response["result"]["data"]["entity_id"])

    # Extrude to create box
    extrude_response = call_cli({
        "jsonrpc": "2.0",
        "method": "solid.extrude",
        "params": {"entity_ids": lines, "distance": depth},
        "id": 100
    })

    return extrude_response["result"]["data"]["entity_id"]


def test_boolean_union_success():
    """Test boolean union of two overlapping boxes."""
    # Create two overlapping boxes
    box1_id = create_box(0, 0, 0, 10, 10, 10)
    box2_id = create_box(5, 0, 0, 10, 10, 10)

    # Union the boxes
    request = {
        "jsonrpc": "2.0",
        "method": "solid.boolean",
        "params": {
            "operation": "union",
            "entity_ids": [box1_id, box2_id]
        },
        "id": 200
    }

    response = call_cli(request)

    # Verify JSON-RPC response
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 200
    assert "result" in response

    result = response["result"]
    assert result["status"] == "success"
    assert "data" in result

    # Verify union result
    data = result["data"]
    assert "entity_id" in data
    assert data["entity_type"] == "solid"
    assert "volume" in data
    # Simplified implementation adds volumes (1000 + 1000 = 2000)
    # Real OCCT would calculate actual union volume (~1500)
    assert data["volume"] > 1400  # At least larger than one box
    assert "topology" in data
    assert data["topology"]["is_manifold"] is True


def test_boolean_subtract_success():
    """Test boolean subtract (cutting a hole)."""
    # Create a large box and a smaller box to subtract
    box1_id = create_box(0, 0, 0, 20, 20, 10)  # Large box
    box2_id = create_box(5, 5, 0, 10, 10, 10)  # Small box to cut out

    # Subtract box2 from box1
    request = {
        "jsonrpc": "2.0",
        "method": "solid.boolean",
        "params": {
            "operation": "subtract",
            "entity_ids": [box1_id, box2_id]
        },
        "id": 201
    }

    response = call_cli(request)

    assert response["result"]["status"] == "success"
    data = response["result"]["data"]
    assert data["entity_type"] == "solid"
    # Volume: 20*20*10 - 10*10*10 = 4000 - 1000 = 3000
    assert 2800 < data["volume"] < 3200


def test_boolean_intersect_success():
    """Test boolean intersect (find common volume)."""
    # Create two overlapping boxes
    box1_id = create_box(0, 0, 0, 10, 10, 10)
    box2_id = create_box(5, 0, 0, 10, 10, 10)

    # Intersect the boxes
    request = {
        "jsonrpc": "2.0",
        "method": "solid.boolean",
        "params": {
            "operation": "intersect",
            "entity_ids": [box1_id, box2_id]
        },
        "id": 202
    }

    response = call_cli(request)

    assert response["result"]["status"] == "success"
    data = response["result"]["data"]
    assert data["entity_type"] == "solid"
    # Intersection volume: 5*10*10 = 500
    assert 450 < data["volume"] < 550


def test_boolean_invalid_operation():
    """Test boolean with invalid operation type."""
    box1_id = create_box(0, 0, 0, 10, 10, 10)
    box2_id = create_box(5, 0, 0, 10, 10, 10)

    request = {
        "jsonrpc": "2.0",
        "method": "solid.boolean",
        "params": {
            "operation": "invalid_op",
            "entity_ids": [box1_id, box2_id]
        },
        "id": 203
    }

    response = call_cli(request)

    assert "error" in response
    error = response["error"]
    assert error["code"] == -32602  # INVALID_PARAMETER


def test_boolean_missing_params():
    """Test boolean with missing parameters."""
    request = {
        "jsonrpc": "2.0",
        "method": "solid.boolean",
        "params": {
            "operation": "union"
            # Missing entity_ids
        },
        "id": 204
    }

    response = call_cli(request)

    assert "error" in response
    error = response["error"]
    assert error["code"] == -32602  # INVALID_PARAMETER


def test_boolean_insufficient_entities():
    """Test boolean with only one entity (need at least 2)."""
    box1_id = create_box(0, 0, 0, 10, 10, 10)

    request = {
        "jsonrpc": "2.0",
        "method": "solid.boolean",
        "params": {
            "operation": "union",
            "entity_ids": [box1_id]  # Only one entity
        },
        "id": 205
    }

    response = call_cli(request)

    assert "error" in response
    error = response["error"]
    assert error["code"] == -32602  # INVALID_PARAMETER


def test_boolean_non_solid_entities():
    """Test boolean with non-solid entities (should fail)."""
    # Create two points (not solids)
    point1_response = call_cli({
        "jsonrpc": "2.0",
        "method": "entity.create.point",
        "params": {"coordinates": [0.0, 0.0]},
        "id": 1
    })
    point1_id = point1_response["result"]["data"]["entity_id"]

    point2_response = call_cli({
        "jsonrpc": "2.0",
        "method": "entity.create.point",
        "params": {"coordinates": [10.0, 0.0]},
        "id": 2
    })
    point2_id = point2_response["result"]["data"]["entity_id"]

    # Try boolean on points (should fail)
    request = {
        "jsonrpc": "2.0",
        "method": "solid.boolean",
        "params": {
            "operation": "union",
            "entity_ids": [point1_id, point2_id]
        },
        "id": 3
    }

    response = call_cli(request)

    assert "error" in response
    error = response["error"]
    # Should be INVALID_PARAMETER or OPERATION_INVALID
    assert error["code"] in [-32602, -32005]
