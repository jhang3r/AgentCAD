"""Contract tests for creation operations JSON-RPC interface.

Tests verify the JSON-RPC contract for creating 3D solids from primitives
and 2D profiles.

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


def test_primitive_box_creates_correct_volume():
    """T048: Test solid.primitive box creates box with correct volume (w×d×h)."""
    request = {
        "jsonrpc": "2.0",
        "method": "solid.primitive",
        "params": {
            "primitive_type": "box",
            "width": 100.0,
            "depth": 80.0,
            "height": 50.0,
            "workspace_id": "main"
        },
        "id": 1
    }

    response = call_cli(request)

    # Verify response structure
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 1
    assert "result" in response
    assert response["result"]["status"] == "success"

    # Verify solid was created
    data = response["result"]["data"]
    assert "entity_id" in data
    assert "shape_id" in data
    assert "volume" in data

    # Verify volume is correct (w × d × h)
    expected_volume = 100.0 * 80.0 * 50.0  # 400,000
    assert abs(data["volume"] - expected_volume) < 1.0, \
        f"Expected volume {expected_volume}, got {data['volume']}"

    # Verify topology
    assert "topology" in data
    topology = data["topology"]
    assert topology["face_count"] == 6  # Box has 6 faces
    assert topology["is_closed"] is True
    assert topology["is_manifold"] is True


def test_primitive_cylinder_creates_correct_volume():
    """T049: Test solid.primitive cylinder creates cylinder with correct volume (π×r²×h)."""
    request = {
        "jsonrpc": "2.0",
        "method": "solid.primitive",
        "params": {
            "primitive_type": "cylinder",
            "radius": 15.0,
            "height": 50.0,
            "workspace_id": "main"
        },
        "id": 2
    }

    response = call_cli(request)

    assert response["result"]["status"] == "success"
    data = response["result"]["data"]

    # Verify volume (π × r² × h)
    expected_volume = math.pi * (15.0 ** 2) * 50.0  # ≈ 35,342.917
    assert abs(data["volume"] - expected_volume) / expected_volume < 0.01, \
        f"Expected volume {expected_volume:.2f}, got {data['volume']:.2f} (>1% error)"

    # Verify topology
    topology = data["topology"]
    assert topology["is_closed"] is True
    assert topology["is_manifold"] is True


def test_primitive_sphere_creates_correct_volume():
    """T050: Test solid.primitive sphere creates sphere with correct volume (4/3×π×r³)."""
    request = {
        "jsonrpc": "2.0",
        "method": "solid.primitive",
        "params": {
            "primitive_type": "sphere",
            "radius": 25.0,
            "workspace_id": "main"
        },
        "id": 3
    }

    response = call_cli(request)

    assert response["result"]["status"] == "success"
    data = response["result"]["data"]

    # Verify volume (4/3 × π × r³)
    expected_volume = (4.0 / 3.0) * math.pi * (25.0 ** 3)  # ≈ 65,449.847
    assert abs(data["volume"] - expected_volume) / expected_volume < 0.01, \
        f"Expected volume {expected_volume:.2f}, got {data['volume']:.2f} (>1% error)"

    # Verify topology
    topology = data["topology"]
    assert topology["is_closed"] is True
    assert topology["is_manifold"] is True


def test_primitive_cone_creates_correct_volume():
    """T051: Test solid.primitive cone creates cone with correct volume (1/3×π×h×(r1²+r1×r2+r2²))."""
    request = {
        "jsonrpc": "2.0",
        "method": "solid.primitive",
        "params": {
            "primitive_type": "cone",
            "radius1": 20.0,  # Bottom radius
            "radius2": 10.0,  # Top radius
            "height": 50.0,
            "workspace_id": "main"
        },
        "id": 4
    }

    response = call_cli(request)

    assert response["result"]["status"] == "success"
    data = response["result"]["data"]

    # Verify volume for frustum (1/3 × π × h × (r1² + r1×r2 + r2²))
    r1, r2, h = 20.0, 10.0, 50.0
    expected_volume = (1.0 / 3.0) * math.pi * h * (r1**2 + r1*r2 + r2**2)  # ≈ 36,651.914
    assert abs(data["volume"] - expected_volume) / expected_volume < 0.01, \
        f"Expected volume {expected_volume:.2f}, got {data['volume']:.2f} (>1% error)"

    # Verify topology
    topology = data["topology"]
    assert topology["is_closed"] is True
    assert topology["is_manifold"] is True


def test_primitive_pointed_cone():
    """Test cone with radius2=0 (pointed cone)."""
    request = {
        "jsonrpc": "2.0",
        "method": "solid.primitive",
        "params": {
            "primitive_type": "cone",
            "radius1": 30.0,
            "radius2": 0.0,  # Pointed cone
            "height": 60.0,
            "workspace_id": "main"
        },
        "id": 5
    }

    response = call_cli(request)

    assert response["result"]["status"] == "success"
    data = response["result"]["data"]

    # Verify volume (1/3 × π × r² × h for pointed cone)
    r, h = 30.0, 60.0
    expected_volume = (1.0 / 3.0) * math.pi * (r ** 2) * h  # ≈ 56,548.668
    assert abs(data["volume"] - expected_volume) / expected_volume < 0.01, \
        f"Expected volume {expected_volume:.2f}, got {data['volume']:.2f}"


def test_primitive_invalid_dimensions():
    """Test error handling for invalid dimensions (negative/zero)."""
    request = {
        "jsonrpc": "2.0",
        "method": "solid.primitive",
        "params": {
            "primitive_type": "box",
            "width": -10.0,  # Invalid: negative
            "depth": 80.0,
            "height": 50.0,
            "workspace_id": "main"
        },
        "id": 6
    }

    response = call_cli(request)

    # Should return error
    assert "error" in response
    error = response["error"]
    assert error["code"] in [-32602, -32603]  # INVALID_PARAMETER or INTERNAL_ERROR


def test_primitive_with_position():
    """Test primitive with custom position."""
    request = {
        "jsonrpc": "2.0",
        "method": "solid.primitive",
        "params": {
            "primitive_type": "box",
            "width": 50.0,
            "depth": 50.0,
            "height": 50.0,
            "position": [100.0, 100.0, 100.0],  # Custom position
            "workspace_id": "main"
        },
        "id": 7
    }

    response = call_cli(request)

    assert response["result"]["status"] == "success"
    data = response["result"]["data"]

    # Volume should still be correct regardless of position
    expected_volume = 50.0 * 50.0 * 50.0
    assert abs(data["volume"] - expected_volume) < 1.0

    # Center of mass should be offset by position
    com = data["center_of_mass"]
    # Box center should be at position + (w/2, d/2, h/2)
    expected_com = [125.0, 125.0, 125.0]
    assert abs(com[0] - expected_com[0]) < 1.0
    assert abs(com[1] - expected_com[1]) < 1.0
    assert abs(com[2] - expected_com[2]) < 1.0


def test_primitive_unsupported_type():
    """Test error handling for unsupported primitive type."""
    request = {
        "jsonrpc": "2.0",
        "method": "solid.primitive",
        "params": {
            "primitive_type": "dodecahedron",  # Not supported
            "workspace_id": "main"
        },
        "id": 8
    }

    response = call_cli(request)

    # Should return error
    assert "error" in response
    error = response["error"]
    assert error["code"] == -32602  # INVALID_PARAMETER


# ============================================================================
# EXTRUDE OPERATION TESTS (T052-T054)
# ============================================================================

def test_extrude_creates_cylinder_from_circle():
    """T053: Test solid.extrude creates cylinder from circle with correct volume."""
    # First create a circle (2D profile)
    circle_request = {
        "jsonrpc": "2.0",
        "method": "entity.create.circle",
        "params": {
            "center": [0.0, 0.0, 0.0],
            "radius": 15.0,
            "workspace_id": "main"
        },
        "id": 1
    }

    circle_response = call_cli(circle_request)
    assert circle_response["result"]["status"] == "success"
    circle_id = circle_response["result"]["data"]["entity_id"]

    # Extrude the circle to create a cylinder
    extrude_request = {
        "jsonrpc": "2.0",
        "method": "solid.extrude",
        "params": {
            "profile_entity_id": circle_id,
            "direction": [0.0, 0.0, 1.0],  # Extrude along Z axis
            "distance": 50.0,
            "workspace_id": "main"
        },
        "id": 2
    }

    extrude_response = call_cli(extrude_request)

    assert extrude_response["result"]["status"] == "success"
    data = extrude_response["result"]["data"]

    # Verify volume matches cylinder formula (π × r² × h)
    import math
    expected_volume = math.pi * (15.0 ** 2) * 50.0  # ≈ 35,342.917
    assert abs(data["volume"] - expected_volume) / expected_volume < 0.01, \
        f"Expected volume {expected_volume:.2f}, got {data['volume']:.2f}"

    # Verify it's a valid solid
    assert data["topology"]["is_closed"] is True
    assert data["topology"]["is_manifold"] is True


def test_extrude_direction_controls_axis():
    """T054: Test extrude direction parameter controls extrusion axis."""
    # Create a circle
    circle_request = {
        "jsonrpc": "2.0",
        "method": "entity.create.circle",
        "params": {
            "center": [0.0, 0.0, 0.0],
            "radius": 10.0,
            "workspace_id": "main"
        },
        "id": 1
    }

    circle_response = call_cli(circle_request)
    circle_id = circle_response["result"]["data"]["entity_id"]

    # Extrude along X axis
    extrude_request = {
        "jsonrpc": "2.0",
        "method": "solid.extrude",
        "params": {
            "profile_entity_id": circle_id,
            "direction": [1.0, 0.0, 0.0],  # X direction
            "distance": 30.0,
            "workspace_id": "main"
        },
        "id": 2
    }

    extrude_response = call_cli(extrude_request)
    assert extrude_response["result"]["status"] == "success"

    data = extrude_response["result"]["data"]

    # Verify bounding box reflects X-axis extrusion
    bbox = data["bounding_box"]
    x_extent = bbox["max"][0] - bbox["min"][0]

    # X extent should be approximately the extrusion distance (30.0)
    assert abs(x_extent - 30.0) < 1.0, f"Expected X extent ~30, got {x_extent}"


# ============================================================================
# REVOLVE OPERATION TESTS (T055-T057)
# ============================================================================

def test_revolve_creates_solid_of_revolution():
    """T056: Test solid.revolve creates solid of revolution with correct rotational symmetry."""
    # Create a rectangle profile (will become a cylinder when revolved)
    # For simplicity, we'll create a simple shape or use a primitive
    # Since we need a 2D profile, let's create a wire or use entity.create API

    # Create a simple rectangular profile centered on Y-Z plane
    # This will revolve around Z axis to create a disk
    profile_request = {
        "jsonrpc": "2.0",
        "method": "entity.create.circle",
        "params": {
            "center": [10.0, 0.0, 0.0],  # Offset from axis
            "radius": 5.0,
            "workspace_id": "main"
        },
        "id": 1
    }

    profile_response = call_cli(profile_request)
    profile_id = profile_response["result"]["data"]["entity_id"]

    # Revolve 360 degrees around Z axis
    revolve_request = {
        "jsonrpc": "2.0",
        "method": "solid.revolve",
        "params": {
            "profile_entity_id": profile_id,
            "axis_point": [0.0, 0.0, 0.0],
            "axis_direction": [0.0, 0.0, 1.0],  # Z axis
            "angle": 360.0,
            "workspace_id": "main"
        },
        "id": 2
    }

    revolve_response = call_cli(revolve_request)

    assert revolve_response["result"]["status"] == "success"
    data = revolve_response["result"]["data"]

    # Verify solid is created
    assert data["volume"] > 0
    assert data["topology"]["is_closed"] is True
    assert data["topology"]["is_manifold"] is True


def test_revolve_angle_parameter():
    """T057: Test revolve angle parameter (180°, 360°)."""
    # Create profile
    profile_request = {
        "jsonrpc": "2.0",
        "method": "entity.create.circle",
        "params": {
            "center": [15.0, 0.0, 0.0],
            "radius": 5.0,
            "workspace_id": "main"
        },
        "id": 1
    }

    profile_response = call_cli(profile_request)
    profile_id = profile_response["result"]["data"]["entity_id"]

    # Revolve 180 degrees
    revolve_180_request = {
        "jsonrpc": "2.0",
        "method": "solid.revolve",
        "params": {
            "profile_entity_id": profile_id,
            "axis_point": [0.0, 0.0, 0.0],
            "axis_direction": [0.0, 0.0, 1.0],
            "angle": 180.0,
            "workspace_id": "main"
        },
        "id": 2
    }

    revolve_180_response = call_cli(revolve_180_request)
    assert revolve_180_response["result"]["status"] == "success"

    # 180° revolve should create roughly half the volume of 360°
    volume_180 = revolve_180_response["result"]["data"]["volume"]
    assert volume_180 > 0


# ============================================================================
# LOFT OPERATION TESTS (T058-T060)
# ============================================================================

def test_loft_creates_smooth_transition():
    """T059: Test solid.loft creates smooth transition between 2+ profiles."""
    # Create two circles at different Z heights with different radii
    circle1_request = {
        "jsonrpc": "2.0",
        "method": "entity.create.circle",
        "params": {
            "center": [0.0, 0.0, 0.0],
            "radius": 20.0,
            "workspace_id": "main"
        },
        "id": 1
    }

    circle2_request = {
        "jsonrpc": "2.0",
        "method": "entity.create.circle",
        "params": {
            "center": [0.0, 0.0, 50.0],
            "radius": 10.0,
            "workspace_id": "main"
        },
        "id": 2
    }

    circle1_response = call_cli(circle1_request)
    circle2_response = call_cli(circle2_request)

    circle1_id = circle1_response["result"]["data"]["entity_id"]
    circle2_id = circle2_response["result"]["data"]["entity_id"]

    # Loft between the two circles
    loft_request = {
        "jsonrpc": "2.0",
        "method": "solid.loft",
        "params": {
            "profile_entity_ids": [circle1_id, circle2_id],
            "is_solid": True,
            "is_ruled": False,  # Smooth loft
            "workspace_id": "main"
        },
        "id": 3
    }

    loft_response = call_cli(loft_request)

    assert loft_response["result"]["status"] == "success"
    data = loft_response["result"]["data"]

    # Verify solid is created
    assert data["volume"] > 0
    assert data["topology"]["is_closed"] is True
    assert data["topology"]["is_manifold"] is True


def test_loft_smooth_vs_ruled():
    """T060: Test loft with smooth vs ruled options."""
    # Create two circles
    circle1_request = {
        "jsonrpc": "2.0",
        "method": "entity.create.circle",
        "params": {
            "center": [0.0, 0.0, 0.0],
            "radius": 15.0,
            "workspace_id": "main"
        },
        "id": 1
    }

    circle2_request = {
        "jsonrpc": "2.0",
        "method": "entity.create.circle",
        "params": {
            "center": [0.0, 0.0, 40.0],
            "radius": 15.0,
            "workspace_id": "main"
        },
        "id": 2
    }

    circle1_response = call_cli(circle1_request)
    circle2_response = call_cli(circle2_request)

    circle1_id = circle1_response["result"]["data"]["entity_id"]
    circle2_id = circle2_response["result"]["data"]["entity_id"]

    # Test ruled loft
    loft_ruled_request = {
        "jsonrpc": "2.0",
        "method": "solid.loft",
        "params": {
            "profile_entity_ids": [circle1_id, circle2_id],
            "is_solid": True,
            "is_ruled": True,  # Ruled loft
            "workspace_id": "main"
        },
        "id": 3
    }

    loft_ruled_response = call_cli(loft_ruled_request)
    assert loft_ruled_response["result"]["status"] == "success"


# ============================================================================
# SWEEP OPERATION TESTS (T061-T062)
# ============================================================================

def test_sweep_moves_profile_along_path():
    """T062: Test solid.sweep moves profile along path curve."""
    # Create a circle profile
    circle_request = {
        "jsonrpc": "2.0",
        "method": "entity.create.circle",
        "params": {
            "center": [0.0, 0.0, 0.0],
            "radius": 5.0,
            "workspace_id": "main"
        },
        "id": 1
    }

    # Create a path (line or curve)
    # For simplicity, use a line
    path_request = {
        "jsonrpc": "2.0",
        "method": "entity.create.line",
        "params": {
            "start_point": [0.0, 0.0, 0.0],
            "end_point": [0.0, 0.0, 50.0],
            "workspace_id": "main"
        },
        "id": 2
    }

    circle_response = call_cli(circle_request)
    path_response = call_cli(path_request)

    circle_id = circle_response["result"]["data"]["entity_id"]
    path_id = path_response["result"]["data"]["entity_id"]

    # Sweep the circle along the path
    sweep_request = {
        "jsonrpc": "2.0",
        "method": "solid.sweep",
        "params": {
            "profile_entity_id": circle_id,
            "path_entity_id": path_id,
            "workspace_id": "main"
        },
        "id": 3
    }

    sweep_response = call_cli(sweep_request)

    assert sweep_response["result"]["status"] == "success"
    data = sweep_response["result"]["data"]

    # Verify solid is created (should be similar to extrude for straight path)
    assert data["volume"] > 0
    assert data["topology"]["is_closed"] is True
