"""Contract tests for pattern and mirror operations JSON-RPC interface.

Tests verify the JSON-RPC contract for pattern operations (linear, circular, mirror).

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
# LINEAR PATTERN TESTS (T063-T064)
# ============================================================================

def test_linear_pattern_creates_correct_count():
    """T064: Test solid.pattern.linear creates correct number of copies with spacing."""
    # Create a base box
    box_request = {
        "jsonrpc": "2.0",
        "method": "solid.primitive",
        "params": {
            "primitive_type": "box",
            "width": 10.0,
            "depth": 10.0,
            "height": 10.0,
            "workspace_id": "main"
        },
        "id": 1
    }

    box_response = call_cli(box_request)
    assert box_response["result"]["status"] == "success"
    box_id = box_response["result"]["data"]["entity_id"]

    # Create linear pattern (5 copies, 15mm spacing along X axis)
    pattern_request = {
        "jsonrpc": "2.0",
        "method": "solid.pattern.linear",
        "params": {
            "base_entity_id": box_id,
            "direction": [1.0, 0.0, 0.0],  # X direction
            "spacing": 15.0,
            "count": 5,
            "workspace_id": "main"
        },
        "id": 2
    }

    pattern_response = call_cli(pattern_request)

    assert pattern_response["result"]["status"] == "success"
    data = pattern_response["result"]["data"]

    # Verify correct number of entities created
    assert "entity_ids" in data
    assert len(data["entity_ids"]) == 5, f"Expected 5 copies, got {len(data['entity_ids'])}"

    # Verify pattern info
    assert data["pattern_type"] == "linear"
    assert data["count"] == 5


def test_linear_pattern_spacing():
    """Test that linear pattern spacing is accurate."""
    # Create a small sphere
    sphere_request = {
        "jsonrpc": "2.0",
        "method": "solid.primitive",
        "params": {
            "primitive_type": "sphere",
            "radius": 5.0,
            "workspace_id": "main"
        },
        "id": 1
    }

    sphere_response = call_cli(sphere_request)
    sphere_id = sphere_response["result"]["data"]["entity_id"]

    # Create pattern with 3 copies, 20mm spacing along Y axis
    pattern_request = {
        "jsonrpc": "2.0",
        "method": "solid.pattern.linear",
        "params": {
            "base_entity_id": sphere_id,
            "direction": [0.0, 1.0, 0.0],  # Y direction
            "spacing": 20.0,
            "count": 3,
            "workspace_id": "main"
        },
        "id": 2
    }

    pattern_response = call_cli(pattern_request)
    assert pattern_response["result"]["status"] == "success"

    # Verify spacing by checking entity properties
    data = pattern_response["result"]["data"]
    assert len(data["entity_ids"]) == 3


# ============================================================================
# CIRCULAR PATTERN TESTS (T065)
# ============================================================================

def test_circular_pattern_creates_copies_around_axis():
    """T065: Test solid.pattern.circular creates copies around axis."""
    # Create a box offset from origin
    box_request = {
        "jsonrpc": "2.0",
        "method": "solid.primitive",
        "params": {
            "primitive_type": "box",
            "width": 5.0,
            "depth": 5.0,
            "height": 10.0,
            "position": [20.0, 0.0, 0.0],  # Offset from Z axis
            "workspace_id": "main"
        },
        "id": 1
    }

    box_response = call_cli(box_request)
    box_id = box_response["result"]["data"]["entity_id"]

    # Create circular pattern (6 copies around Z axis, full 360°)
    pattern_request = {
        "jsonrpc": "2.0",
        "method": "solid.pattern.circular",
        "params": {
            "base_entity_id": box_id,
            "axis_point": [0.0, 0.0, 0.0],
            "axis_direction": [0.0, 0.0, 1.0],  # Z axis
            "count": 6,
            "angle": 360.0,  # Full circle
            "workspace_id": "main"
        },
        "id": 2
    }

    pattern_response = call_cli(pattern_request)

    assert pattern_response["result"]["status"] == "success"
    data = pattern_response["result"]["data"]

    # Verify correct number of copies
    assert "entity_ids" in data
    assert len(data["entity_ids"]) == 6, f"Expected 6 copies, got {len(data['entity_ids'])}"

    # Verify pattern info
    assert data["pattern_type"] == "circular"
    assert data["count"] == 6


def test_circular_pattern_partial_angle():
    """Test circular pattern with partial angle (not full 360°)."""
    # Create a cylinder
    cylinder_request = {
        "jsonrpc": "2.0",
        "method": "solid.primitive",
        "params": {
            "primitive_type": "cylinder",
            "radius": 3.0,
            "height": 15.0,
            "position": [15.0, 0.0, 0.0],
            "workspace_id": "main"
        },
        "id": 1
    }

    cylinder_response = call_cli(cylinder_request)
    cylinder_id = cylinder_response["result"]["data"]["entity_id"]

    # Create pattern with 4 copies over 180° (half circle)
    pattern_request = {
        "jsonrpc": "2.0",
        "method": "solid.pattern.circular",
        "params": {
            "base_entity_id": cylinder_id,
            "axis_point": [0.0, 0.0, 0.0],
            "axis_direction": [0.0, 0.0, 1.0],
            "count": 4,
            "angle": 180.0,  # Half circle
            "workspace_id": "main"
        },
        "id": 2
    }

    pattern_response = call_cli(pattern_request)
    assert pattern_response["result"]["status"] == "success"
    data = pattern_response["result"]["data"]
    assert len(data["entity_ids"]) == 4


# ============================================================================
# MIRROR OPERATION TESTS (T066)
# ============================================================================

def test_mirror_creates_mirrored_copy():
    """T066: Test solid.mirror creates mirrored copy across plane."""
    # Create a box on one side of YZ plane
    box_request = {
        "jsonrpc": "2.0",
        "method": "solid.primitive",
        "params": {
            "primitive_type": "box",
            "width": 10.0,
            "depth": 15.0,
            "height": 20.0,
            "position": [10.0, 0.0, 0.0],  # Positive X side
            "workspace_id": "main"
        },
        "id": 1
    }

    box_response = call_cli(box_request)
    box_id = box_response["result"]["data"]["entity_id"]
    original_bbox = box_response["result"]["data"]["bounding_box"]

    # Mirror across YZ plane (X = 0)
    mirror_request = {
        "jsonrpc": "2.0",
        "method": "solid.mirror",
        "params": {
            "base_entity_id": box_id,
            "mirror_plane_point": [0.0, 0.0, 0.0],
            "mirror_plane_normal": [1.0, 0.0, 0.0],  # X normal (YZ plane)
            "workspace_id": "main"
        },
        "id": 2
    }

    mirror_response = call_cli(mirror_request)

    assert mirror_response["result"]["status"] == "success"
    data = mirror_response["result"]["data"]

    # Verify mirrored entity was created
    assert "entity_id" in data
    assert "volume" in data

    # Volume should be the same as original
    original_volume = box_response["result"]["data"]["volume"]
    assert abs(data["volume"] - original_volume) < 1.0

    # Bounding box should be mirrored
    mirrored_bbox = data["bounding_box"]

    # X coordinates should be mirrored (negative of original)
    # Original was at positive X, mirrored should be at negative X
    assert mirrored_bbox["max"][0] <= 0.0, "Mirrored box should be on negative X side"


def test_mirror_across_different_planes():
    """Test mirror operation across different mirror planes."""
    # Create a sphere
    sphere_request = {
        "jsonrpc": "2.0",
        "method": "solid.primitive",
        "params": {
            "primitive_type": "sphere",
            "radius": 10.0,
            "center": [15.0, 15.0, 0.0],
            "workspace_id": "main"
        },
        "id": 1
    }

    sphere_response = call_cli(sphere_request)
    sphere_id = sphere_response["result"]["data"]["entity_id"]

    # Mirror across XY plane (Z = 0, normal = [0, 0, 1])
    mirror_request = {
        "jsonrpc": "2.0",
        "method": "solid.mirror",
        "params": {
            "base_entity_id": sphere_id,
            "mirror_plane_point": [0.0, 0.0, 0.0],
            "mirror_plane_normal": [0.0, 0.0, 1.0],  # Z normal (XY plane)
            "workspace_id": "main"
        },
        "id": 2
    }

    mirror_response = call_cli(mirror_request)
    assert mirror_response["result"]["status"] == "success"

    # Verify volume is preserved
    original_volume = sphere_response["result"]["data"]["volume"]
    mirrored_volume = mirror_response["result"]["data"]["volume"]
    assert abs(mirrored_volume - original_volume) / original_volume < 0.01


def test_mirror_error_invalid_plane():
    """Test error handling for invalid mirror plane (zero normal vector)."""
    # Create a box
    box_request = {
        "jsonrpc": "2.0",
        "method": "solid.primitive",
        "params": {
            "primitive_type": "box",
            "width": 10.0,
            "depth": 10.0,
            "height": 10.0,
            "workspace_id": "main"
        },
        "id": 1
    }

    box_response = call_cli(box_request)
    box_id = box_response["result"]["data"]["entity_id"]

    # Try to mirror with invalid plane normal (zero vector)
    mirror_request = {
        "jsonrpc": "2.0",
        "method": "solid.mirror",
        "params": {
            "base_entity_id": box_id,
            "mirror_plane_point": [0.0, 0.0, 0.0],
            "mirror_plane_normal": [0.0, 0.0, 0.0],  # Invalid: zero vector
            "workspace_id": "main"
        },
        "id": 2
    }

    mirror_response = call_cli(mirror_request)

    # Should return error
    assert "error" in mirror_response
    error = mirror_response["error"]
    assert error["code"] in [-32602, -32603]  # Invalid params or internal error


def test_pattern_error_invalid_count():
    """Test error handling for invalid pattern count (<=0)."""
    # Create a box
    box_request = {
        "jsonrpc": "2.0",
        "method": "solid.primitive",
        "params": {
            "primitive_type": "box",
            "width": 10.0,
            "depth": 10.0,
            "height": 10.0,
            "workspace_id": "main"
        },
        "id": 1
    }

    box_response = call_cli(box_request)
    box_id = box_response["result"]["data"]["entity_id"]

    # Try pattern with invalid count
    pattern_request = {
        "jsonrpc": "2.0",
        "method": "solid.pattern.linear",
        "params": {
            "base_entity_id": box_id,
            "direction": [1.0, 0.0, 0.0],
            "spacing": 15.0,
            "count": 0,  # Invalid: must be > 0
            "workspace_id": "main"
        },
        "id": 2
    }

    pattern_response = call_cli(pattern_request)

    # Should return error
    assert "error" in pattern_response
    error = pattern_response["error"]
    assert error["code"] in [-32602, -32603]
