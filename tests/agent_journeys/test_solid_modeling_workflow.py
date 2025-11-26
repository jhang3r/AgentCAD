"""Agent journey test for solid modeling workflow.

Tests a complete agent workflow: create sketch → extrude → boolean operations → verify results.

This simulates how an AI agent would learn solid modeling through practice.
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


def test_agent_creates_box_and_measures():
    """Test agent creating a box and measuring its properties."""
    # Agent creates a rectangular sketch
    line1 = call_cli({
        "jsonrpc": "2.0",
        "method": "entity.create.line",
        "params": {"start": [0.0, 0.0], "end": [10.0, 0.0]},
        "id": 1
    })
    line1_id = line1["result"]["data"]["entity_id"]

    line2 = call_cli({
        "jsonrpc": "2.0",
        "method": "entity.create.line",
        "params": {"start": [10.0, 0.0], "end": [10.0, 10.0]},
        "id": 2
    })
    line2_id = line2["result"]["data"]["entity_id"]

    line3 = call_cli({
        "jsonrpc": "2.0",
        "method": "entity.create.line",
        "params": {"start": [10.0, 10.0], "end": [0.0, 10.0]},
        "id": 3
    })
    line3_id = line3["result"]["data"]["entity_id"]

    line4 = call_cli({
        "jsonrpc": "2.0",
        "method": "entity.create.line",
        "params": {"start": [0.0, 10.0], "end": [0.0, 0.0]},
        "id": 4
    })
    line4_id = line4["result"]["data"]["entity_id"]

    # Agent extrudes the sketch
    extrude_response = call_cli({
        "jsonrpc": "2.0",
        "method": "solid.extrude",
        "params": {
            "entity_ids": [line1_id, line2_id, line3_id, line4_id],
            "distance": 10.0
        },
        "id": 5
    })

    # Verify extrusion succeeded
    assert extrude_response["result"]["status"] == "success"
    solid_data = extrude_response["result"]["data"]
    box_id = solid_data["entity_id"]

    # Agent verifies the box properties
    assert solid_data["entity_type"] == "solid"
    assert 950 < solid_data["volume"] < 1050  # Should be ~1000
    assert 550 < solid_data["surface_area"] < 650  # Should be ~600

    # Agent queries the entity
    query_response = call_cli({
        "jsonrpc": "2.0",
        "method": "entity.query",
        "params": {"entity_id": box_id},
        "id": 6
    })

    assert query_response["result"]["status"] == "success"
    queried_data = query_response["result"]["data"]
    assert queried_data["entity_type"] == "solid"
    assert "volume" in queried_data


def test_agent_boolean_workflow():
    """Test agent performing boolean operations (subtract)."""
    # Agent creates first box (10x10x10)
    lines1 = []
    corners = [[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0]]
    for i in range(4):
        response = call_cli({
            "jsonrpc": "2.0",
            "method": "entity.create.line",
            "params": {
                "start": corners[i],
                "end": corners[(i + 1) % 4]
            },
            "id": i + 1
        })
        lines1.append(response["result"]["data"]["entity_id"])

    box1_response = call_cli({
        "jsonrpc": "2.0",
        "method": "solid.extrude",
        "params": {"entity_ids": lines1, "distance": 10.0},
        "id": 10
    })
    box1_id = box1_response["result"]["data"]["entity_id"]
    box1_volume = box1_response["result"]["data"]["volume"]

    # Agent creates second smaller box (5x5x10) to subtract
    lines2 = []
    corners2 = [[2.0, 2.0], [7.0, 2.0], [7.0, 7.0], [2.0, 7.0]]
    for i in range(4):
        response = call_cli({
            "jsonrpc": "2.0",
            "method": "entity.create.line",
            "params": {
                "start": corners2[i],
                "end": corners2[(i + 1) % 4]
            },
            "id": i + 20
        })
        lines2.append(response["result"]["data"]["entity_id"])

    box2_response = call_cli({
        "jsonrpc": "2.0",
        "method": "solid.extrude",
        "params": {"entity_ids": lines2, "distance": 10.0},
        "id": 30
    })
    box2_id = box2_response["result"]["data"]["entity_id"]
    box2_volume = box2_response["result"]["data"]["volume"]

    # Agent performs boolean subtract
    subtract_response = call_cli({
        "jsonrpc": "2.0",
        "method": "solid.boolean",
        "params": {
            "operation": "subtract",
            "entity_ids": [box1_id, box2_id]
        },
        "id": 40
    })

    assert subtract_response["result"]["status"] == "success"
    result_data = subtract_response["result"]["data"]

    # Agent verifies the volume decreased
    result_volume = result_data["volume"]
    expected_volume = box1_volume - box2_volume
    assert abs(result_volume - expected_volume) < 50  # Allow some tolerance

    # Agent verifies topology is still valid
    assert result_data["topology"]["is_manifold"] is True
    assert result_data["topology"]["is_closed"] is True


def test_agent_learns_from_errors():
    """Test agent learning from invalid operations."""
    # Agent tries to extrude with invalid distance
    circle_response = call_cli({
        "jsonrpc": "2.0",
        "method": "entity.create.circle",
        "params": {"center": [0.0, 0.0], "radius": 5.0},
        "id": 1
    })
    circle_id = circle_response["result"]["data"]["entity_id"]

    # Try zero distance (should fail)
    extrude_response = call_cli({
        "jsonrpc": "2.0",
        "method": "solid.extrude",
        "params": {
            "entity_ids": [circle_id],
            "distance": 0.0
        },
        "id": 2
    })

    # Agent receives error and learns
    assert "error" in extrude_response
    error = extrude_response["error"]
    assert error["code"] == -32602  # INVALID_PARAMETER
    assert "distance" in error["message"].lower()

    # Agent corrects and tries again with valid distance
    extrude_response2 = call_cli({
        "jsonrpc": "2.0",
        "method": "solid.extrude",
        "params": {
            "entity_ids": [circle_id],
            "distance": 10.0
        },
        "id": 3
    })

    # This time it succeeds
    assert extrude_response2["result"]["status"] == "success"
    assert extrude_response2["result"]["data"]["volume"] > 0


def test_agent_complex_workflow():
    """Test agent performing a complex multi-step workflow."""
    # Agent creates a base box
    base_lines = []
    corners = [[0.0, 0.0], [20.0, 0.0], [20.0, 20.0], [0.0, 20.0]]
    for i in range(4):
        response = call_cli({
            "jsonrpc": "2.0",
            "method": "entity.create.line",
            "params": {
                "start": corners[i],
                "end": corners[(i + 1) % 4]
            },
            "id": i + 1
        })
        base_lines.append(response["result"]["data"]["entity_id"])

    base_response = call_cli({
        "jsonrpc": "2.0",
        "method": "solid.extrude",
        "params": {"entity_ids": base_lines, "distance": 5.0},
        "id": 10
    })
    base_id = base_response["result"]["data"]["entity_id"]

    # Agent creates a cylinder to add on top
    cylinder_response = call_cli({
        "jsonrpc": "2.0",
        "method": "entity.create.circle",
        "params": {"center": [10.0, 10.0], "radius": 8.0},
        "id": 20
    })
    circle_id = cylinder_response["result"]["data"]["entity_id"]

    cylinder_extrude = call_cli({
        "jsonrpc": "2.0",
        "method": "solid.extrude",
        "params": {"entity_ids": [circle_id], "distance": 10.0},
        "id": 21
    })
    cylinder_id = cylinder_extrude["result"]["data"]["entity_id"]

    # Agent unions the base and cylinder
    union_response = call_cli({
        "jsonrpc": "2.0",
        "method": "solid.boolean",
        "params": {
            "operation": "union",
            "entity_ids": [base_id, cylinder_id]
        },
        "id": 30
    })

    assert union_response["result"]["status"] == "success"
    final_solid = union_response["result"]["data"]

    # Agent verifies the final result
    assert final_solid["entity_type"] == "solid"
    assert final_solid["volume"] > 0
    assert final_solid["topology"]["is_manifold"] is True

    # Agent lists all entities to see what was created
    list_response = call_cli({
        "jsonrpc": "2.0",
        "method": "entity.list",
        "params": {},
        "id": 40
    })

    assert list_response["result"]["status"] == "success"
    entities = list_response["result"]["data"]["entities"]
    # Should have multiple entities (lines, circles, solids)
    assert len(entities) > 0
