"""Contract tests for boolean operations JSON-RPC interface.

Tests verify the JSON-RPC contract for boolean operations (union, subtract, intersect).

TDD: These tests should FAIL until implementation is complete.
"""
import json
import subprocess
import sys
import math
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


# ============================================================================
# BOOLEAN UNION TESTS (T099-T101)
# ============================================================================

def test_boolean_union_combines_solids():
    """T100: Test solid.boolean.union combines two solids into one."""
    # Create two separate boxes
    box1_request = {
        "jsonrpc": "2.0",
        "method": "solid.primitive",
        "params": {
            "primitive_type": "box",
            "width": 20.0,
            "depth": 20.0,
            "height": 20.0,
            "position": [0.0, 0.0, 0.0],
            "workspace_id": "main"
        },
        "id": 1
    }

    box2_request = {
        "jsonrpc": "2.0",
        "method": "solid.primitive",
        "params": {
            "primitive_type": "box",
            "width": 20.0,
            "depth": 20.0,
            "height": 20.0,
            "position": [10.0, 0.0, 0.0],  # Overlaps box1 by 10mm
            "workspace_id": "main"
        },
        "id": 2
    }

    box1_response = call_cli(box1_request)
    box2_response = call_cli(box2_request)

    assert box1_response["result"]["status"] == "success"
    assert box2_response["result"]["status"] == "success"

    box1_id = box1_response["result"]["data"]["entity_id"]
    box2_id = box2_response["result"]["data"]["entity_id"]

    # Perform union
    union_request = {
        "jsonrpc": "2.0",
        "method": "solid.boolean.union",
        "params": {
            "operand1_entity_id": box1_id,
            "operand2_entity_id": box2_id,
            "workspace_id": "main"
        },
        "id": 3
    }

    union_response = call_cli(union_request)

    assert union_response["result"]["status"] == "success"
    data = union_response["result"]["data"]

    # Verify result entity created
    assert "entity_id" in data
    assert "volume" in data

    # Verify it's a valid solid
    assert data["topology"]["is_closed"] is True
    assert data["topology"]["is_manifold"] is True


def test_union_volume_calculation():
    """T101: Test union result volume ≈ vol(A) + vol(B) - vol(overlap)."""
    # Create two overlapping boxes with known volumes
    box1_request = {
        "jsonrpc": "2.0",
        "method": "solid.primitive",
        "params": {
            "primitive_type": "box",
            "width": 30.0,
            "depth": 30.0,
            "height": 30.0,
            "position": [0.0, 0.0, 0.0],
            "workspace_id": "main"
        },
        "id": 1
    }

    box2_request = {
        "jsonrpc": "2.0",
        "method": "solid.primitive",
        "params": {
            "primitive_type": "box",
            "width": 30.0,
            "depth": 30.0,
            "height": 30.0,
            "position": [15.0, 0.0, 0.0],  # 50% overlap
            "workspace_id": "main"
        },
        "id": 2
    }

    box1_response = call_cli(box1_request)
    box2_response = call_cli(box2_request)

    vol1 = box1_response["result"]["data"]["volume"]
    vol2 = box2_response["result"]["data"]["volume"]

    box1_id = box1_response["result"]["data"]["entity_id"]
    box2_id = box2_response["result"]["data"]["entity_id"]

    # Union
    union_request = {
        "jsonrpc": "2.0",
        "method": "solid.boolean.union",
        "params": {
            "operand1_entity_id": box1_id,
            "operand2_entity_id": box2_id,
            "workspace_id": "main"
        },
        "id": 3
    }

    union_response = call_cli(union_request)
    union_volume = union_response["result"]["data"]["volume"]

    # Expected: vol(A) + vol(B) - vol(overlap)
    # vol1 = 30³ = 27,000
    # vol2 = 30³ = 27,000
    # overlap = 15×30×30 = 13,500
    # expected = 27,000 + 27,000 - 13,500 = 40,500

    overlap_volume = 15.0 * 30.0 * 30.0  # 13,500
    expected_volume = vol1 + vol2 - overlap_volume

    # Allow 1% tolerance for numerical precision
    assert abs(union_volume - expected_volume) / expected_volume < 0.01, \
        f"Union volume {union_volume:.2f} != expected {expected_volume:.2f}"


# ============================================================================
# BOOLEAN SUBTRACT TESTS (T102-T104)
# ============================================================================

def test_boolean_subtract_removes_tool():
    """T103: Test solid.boolean.subtract removes tool from base."""
    # Create base box
    base_request = {
        "jsonrpc": "2.0",
        "method": "solid.primitive",
        "params": {
            "primitive_type": "box",
            "width": 40.0,
            "depth": 40.0,
            "height": 40.0,
            "position": [0.0, 0.0, 0.0],
            "workspace_id": "main"
        },
        "id": 1
    }

    # Create cylinder (tool to subtract)
    tool_request = {
        "jsonrpc": "2.0",
        "method": "solid.primitive",
        "params": {
            "primitive_type": "cylinder",
            "radius": 10.0,
            "height": 50.0,  # Longer than box to ensure full penetration
            "position": [20.0, 20.0, -5.0],  # Centered in box
            "workspace_id": "main"
        },
        "id": 2
    }

    base_response = call_cli(base_request)
    tool_response = call_cli(tool_request)

    base_id = base_response["result"]["data"]["entity_id"]
    tool_id = tool_response["result"]["data"]["entity_id"]

    # Perform subtraction (drill hole)
    subtract_request = {
        "jsonrpc": "2.0",
        "method": "solid.boolean.subtract",
        "params": {
            "base_entity_id": base_id,
            "tool_entity_id": tool_id,
            "workspace_id": "main"
        },
        "id": 3
    }

    subtract_response = call_cli(subtract_request)

    assert subtract_response["result"]["status"] == "success"
    data = subtract_response["result"]["data"]

    # Verify result entity created
    assert "entity_id" in data
    assert "volume" in data

    # Volume should be less than original base
    base_volume = base_response["result"]["data"]["volume"]
    assert data["volume"] < base_volume

    # Should still be a valid solid
    assert data["topology"]["is_closed"] is True
    assert data["topology"]["is_manifold"] is True


def test_subtract_volume_calculation():
    """T104: Test subtract result volume = vol(base) - vol(overlap)."""
    # Create two overlapping boxes
    base_request = {
        "jsonrpc": "2.0",
        "method": "solid.primitive",
        "params": {
            "primitive_type": "box",
            "width": 50.0,
            "depth": 50.0,
            "height": 50.0,
            "position": [0.0, 0.0, 0.0],
            "workspace_id": "main"
        },
        "id": 1
    }

    tool_request = {
        "jsonrpc": "2.0",
        "method": "solid.primitive",
        "params": {
            "primitive_type": "box",
            "width": 20.0,
            "depth": 20.0,
            "height": 20.0,
            "position": [15.0, 15.0, 15.0],  # Inside base box
            "workspace_id": "main"
        },
        "id": 2
    }

    base_response = call_cli(base_request)
    tool_response = call_cli(tool_request)

    base_volume = base_response["result"]["data"]["volume"]
    tool_volume = tool_response["result"]["data"]["volume"]

    base_id = base_response["result"]["data"]["entity_id"]
    tool_id = tool_response["result"]["data"]["entity_id"]

    # Subtract
    subtract_request = {
        "jsonrpc": "2.0",
        "method": "solid.boolean.subtract",
        "params": {
            "base_entity_id": base_id,
            "tool_entity_id": tool_id,
            "workspace_id": "main"
        },
        "id": 3
    }

    subtract_response = call_cli(subtract_request)
    result_volume = subtract_response["result"]["data"]["volume"]

    # Expected: vol(base) - vol(tool) (since tool is fully inside base)
    expected_volume = base_volume - tool_volume

    # Allow 1% tolerance
    assert abs(result_volume - expected_volume) / expected_volume < 0.01, \
        f"Subtract volume {result_volume:.2f} != expected {expected_volume:.2f}"


# ============================================================================
# BOOLEAN INTERSECT TESTS (T105-T107)
# ============================================================================

def test_boolean_intersect_creates_overlap_solid():
    """T106: Test solid.boolean.intersect creates solid from overlap only."""
    # Create two overlapping cylinders
    cyl1_request = {
        "jsonrpc": "2.0",
        "method": "solid.primitive",
        "params": {
            "primitive_type": "cylinder",
            "radius": 15.0,
            "height": 50.0,
            "position": [0.0, 0.0, 0.0],
            "workspace_id": "main"
        },
        "id": 1
    }

    cyl2_request = {
        "jsonrpc": "2.0",
        "method": "solid.primitive",
        "params": {
            "primitive_type": "cylinder",
            "radius": 15.0,
            "height": 50.0,
            "position": [20.0, 0.0, 0.0],  # Partially overlaps
            "workspace_id": "main"
        },
        "id": 2
    }

    cyl1_response = call_cli(cyl1_request)
    cyl2_response = call_cli(cyl2_request)

    cyl1_id = cyl1_response["result"]["data"]["entity_id"]
    cyl2_id = cyl2_response["result"]["data"]["entity_id"]

    # Perform intersection
    intersect_request = {
        "jsonrpc": "2.0",
        "method": "solid.boolean.intersect",
        "params": {
            "operand1_entity_id": cyl1_id,
            "operand2_entity_id": cyl2_id,
            "workspace_id": "main"
        },
        "id": 3
    }

    intersect_response = call_cli(intersect_request)

    assert intersect_response["result"]["status"] == "success"
    data = intersect_response["result"]["data"]

    # Verify result entity created
    assert "entity_id" in data
    assert "volume" in data

    # Volume should be less than both inputs
    vol1 = cyl1_response["result"]["data"]["volume"]
    vol2 = cyl2_response["result"]["data"]["volume"]

    assert data["volume"] < vol1
    assert data["volume"] < vol2
    assert data["volume"] > 0

    # Should be a valid solid
    assert data["topology"]["is_closed"] is True
    assert data["topology"]["is_manifold"] is True


def test_intersect_volume_calculation():
    """T107: Test intersect result volume = vol(overlap)."""
    # Create two boxes with known overlap
    box1_request = {
        "jsonrpc": "2.0",
        "method": "solid.primitive",
        "params": {
            "primitive_type": "box",
            "width": 40.0,
            "depth": 40.0,
            "height": 40.0,
            "position": [0.0, 0.0, 0.0],
            "workspace_id": "main"
        },
        "id": 1
    }

    box2_request = {
        "jsonrpc": "2.0",
        "method": "solid.primitive",
        "params": {
            "primitive_type": "box",
            "width": 40.0,
            "depth": 40.0,
            "height": 40.0,
            "position": [20.0, 20.0, 20.0],  # 20mm overlap in each dimension
            "workspace_id": "main"
        },
        "id": 2
    }

    box1_response = call_cli(box1_request)
    box2_response = call_cli(box2_request)

    box1_id = box1_response["result"]["data"]["entity_id"]
    box2_id = box2_response["result"]["data"]["entity_id"]

    # Intersect
    intersect_request = {
        "jsonrpc": "2.0",
        "method": "solid.boolean.intersect",
        "params": {
            "operand1_entity_id": box1_id,
            "operand2_entity_id": box2_id,
            "workspace_id": "main"
        },
        "id": 3
    }

    intersect_response = call_cli(intersect_request)
    result_volume = intersect_response["result"]["data"]["volume"]

    # Expected overlap volume: 20×20×20 = 8,000
    expected_overlap = 20.0 * 20.0 * 20.0

    # Allow 1% tolerance
    assert abs(result_volume - expected_overlap) / expected_overlap < 0.01, \
        f"Intersect volume {result_volume:.2f} != expected {expected_overlap:.2f}"


# ============================================================================
# ERROR HANDLING TESTS (T108-T109)
# ============================================================================

def test_boolean_error_invalid_geometry():
    """T108: Test error handling for invalid geometry inputs."""
    # Try to perform boolean with non-existent entity
    union_request = {
        "jsonrpc": "2.0",
        "method": "solid.boolean.union",
        "params": {
            "operand1_entity_id": "nonexistent_id_1",
            "operand2_entity_id": "nonexistent_id_2",
            "workspace_id": "main"
        },
        "id": 1
    }

    union_response = call_cli(union_request)

    # Should return error
    assert "error" in union_response
    error = union_response["error"]
    assert error["code"] in [-32602, -32603]  # Invalid params or internal error


def test_intersect_error_non_overlapping():
    """T109: Test error handling for non-overlapping solids (intersect)."""
    # Create two non-overlapping boxes
    box1_request = {
        "jsonrpc": "2.0",
        "method": "solid.primitive",
        "params": {
            "primitive_type": "box",
            "width": 10.0,
            "depth": 10.0,
            "height": 10.0,
            "position": [0.0, 0.0, 0.0],
            "workspace_id": "main"
        },
        "id": 1
    }

    box2_request = {
        "jsonrpc": "2.0",
        "method": "solid.primitive",
        "params": {
            "primitive_type": "box",
            "width": 10.0,
            "depth": 10.0,
            "height": 10.0,
            "position": [100.0, 100.0, 100.0],  # Far apart
            "workspace_id": "main"
        },
        "id": 2
    }

    box1_response = call_cli(box1_request)
    box2_response = call_cli(box2_request)

    box1_id = box1_response["result"]["data"]["entity_id"]
    box2_id = box2_response["result"]["data"]["entity_id"]

    # Try to intersect non-overlapping solids
    intersect_request = {
        "jsonrpc": "2.0",
        "method": "solid.boolean.intersect",
        "params": {
            "operand1_entity_id": box1_id,
            "operand2_entity_id": box2_id,
            "workspace_id": "main"
        },
        "id": 3
    }

    intersect_response = call_cli(intersect_request)

    # Should return error (empty intersection not allowed)
    assert "error" in intersect_response
    error = intersect_response["error"]
    assert error["code"] in [-32602, -32603]


def test_boolean_operations_preserve_manifold():
    """Test that boolean operations preserve manifold property."""
    # Create two spheres
    sphere1_request = {
        "jsonrpc": "2.0",
        "method": "solid.primitive",
        "params": {
            "primitive_type": "sphere",
            "radius": 20.0,
            "center": [0.0, 0.0, 0.0],
            "workspace_id": "main"
        },
        "id": 1
    }

    sphere2_request = {
        "jsonrpc": "2.0",
        "method": "solid.primitive",
        "params": {
            "primitive_type": "sphere",
            "radius": 20.0,
            "center": [25.0, 0.0, 0.0],
            "workspace_id": "main"
        },
        "id": 2
    }

    sphere1_response = call_cli(sphere1_request)
    sphere2_response = call_cli(sphere2_request)

    sphere1_id = sphere1_response["result"]["data"]["entity_id"]
    sphere2_id = sphere2_response["result"]["data"]["entity_id"]

    # Test all three boolean operations preserve manifold
    for operation in ["union", "subtract", "intersect"]:
        boolean_request = {
            "jsonrpc": "2.0",
            "method": f"solid.boolean.{operation}",
            "params": {
                "operand1_entity_id" if operation != "subtract" else "base_entity_id": sphere1_id,
                "operand2_entity_id" if operation != "subtract" else "tool_entity_id": sphere2_id,
                "workspace_id": "main"
            },
            "id": 3
        }

        boolean_response = call_cli(boolean_request)

        if boolean_response.get("result", {}).get("status") == "success":
            data = boolean_response["result"]["data"]
            assert data["topology"]["is_manifold"] is True, \
                f"{operation} operation did not preserve manifold property"
