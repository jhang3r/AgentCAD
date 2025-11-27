#!/usr/bin/env python
"""Build a servo motor mounting bracket.

Demonstrates the full geometry kernel capabilities:
- Primitive creation (box, cylinder)
- Boolean operations (subtract for holes, union for posts)
- Export to STL for 3D printing

Design specs:
- Base plate: 60x40x3mm
- 4 corner mounting holes: M3 (3.2mm diameter)
- 2 servo mounting posts: 5mm diameter, 10mm height

Run after installing pythonOCC-core:
    python examples/build_servo_bracket.py
"""

import json
import subprocess
import sys
from pathlib import Path


def call_cli(request: dict) -> dict:
    """Call the CAD CLI with a JSON-RPC request."""
    input_data = json.dumps(request) + "\n"
    result = subprocess.run(
        [sys.executable, "-m", "src.agent_interface.cli"],
        input=input_data,
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )

    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        sys.exit(1)

    return json.loads(result.stdout.strip())


def main():
    print("🔧 Building Servo Motor Mounting Bracket...")
    print("=" * 60)

    # Step 1: Create base plate (60x40x3mm box)
    print("\n1. Creating base plate (60x40x3mm)...")
    base_response = call_cli({
        "jsonrpc": "2.0",
        "method": "solid.primitive",
        "params": {
            "primitive_type": "box",
            "width": 60.0,
            "depth": 40.0,
            "height": 3.0,
            "position": [0.0, 0.0, 0.0],
            "workspace_id": "main"
        },
        "id": 1
    })

    base_id = base_response["result"]["data"]["entity_id"]
    base_volume = base_response["result"]["data"]["volume"]
    print(f"   ✓ Base plate created: {base_id}")
    print(f"   ✓ Volume: {base_volume:.2f} mm³")

    # Step 2: Create mounting holes (4 corners, M3 = 3.2mm diameter)
    print("\n2. Creating mounting holes (M3, 3.2mm diameter)...")
    hole_positions = [
        [5.0, 5.0, -1.0],    # Bottom-left
        [55.0, 5.0, -1.0],   # Bottom-right
        [5.0, 35.0, -1.0],   # Top-left
        [55.0, 35.0, -1.0],  # Top-right
    ]

    current_part = base_id

    for i, pos in enumerate(hole_positions, 1):
        # Create hole cylinder (5mm tall to ensure full penetration)
        hole_response = call_cli({
            "jsonrpc": "2.0",
            "method": "solid.primitive",
            "params": {
                "primitive_type": "cylinder",
                "radius": 1.6,  # M3 = 3.2mm diameter
                "height": 5.0,
                "position": pos,
                "workspace_id": "main"
            },
            "id": 10 + i
        })

        hole_id = hole_response["result"]["data"]["entity_id"]

        # Subtract hole from current part
        subtract_response = call_cli({
            "jsonrpc": "2.0",
            "method": "solid.boolean.subtract",
            "params": {
                "base_entity_id": current_part,
                "tool_entity_id": hole_id,
                "workspace_id": "main"
            },
            "id": 20 + i
        })

        # Debug: print response
        if "error" in subtract_response:
            print(f"   ✗ ERROR: {subtract_response['error']}")
            sys.exit(1)

        current_part = subtract_response["result"]["data"]["entity_id"]
        print(f"   ✓ Hole {i} drilled at ({pos[0]}, {pos[1]})")

    final_volume = subtract_response["result"]["data"]["volume"]
    print(f"   ✓ Plate after holes: {final_volume:.2f} mm³")
    print(f"   ✓ Material removed: {base_volume - final_volume:.2f} mm³")

    # Step 3: Add servo mounting posts (2 posts, 5mm diameter, 10mm tall)
    print("\n3. Adding servo mounting posts (5mm diameter, 10mm tall)...")
    post_positions = [
        [20.0, 20.0, 3.0],   # Left post
        [40.0, 20.0, 3.0],   # Right post
    ]

    for i, pos in enumerate(post_positions, 1):
        # Create post cylinder
        post_response = call_cli({
            "jsonrpc": "2.0",
            "method": "solid.primitive",
            "params": {
                "primitive_type": "cylinder",
                "radius": 2.5,  # 5mm diameter
                "height": 10.0,
                "position": pos,
                "workspace_id": "main"
            },
            "id": 30 + i
        })

        post_id = post_response["result"]["data"]["entity_id"]

        # Union post with current part
        union_response = call_cli({
            "jsonrpc": "2.0",
            "method": "solid.boolean.union",
            "params": {
                "operand1_entity_id": current_part,
                "operand2_entity_id": post_id,
                "workspace_id": "main"
            },
            "id": 40 + i
        })

        current_part = union_response["result"]["data"]["entity_id"]
        print(f"   ✓ Post {i} added at ({pos[0]}, {pos[1]})")

    final_volume = union_response["result"]["data"]["volume"]
    topology = union_response["result"]["data"]["topology"]
    print(f"   ✓ Final bracket volume: {final_volume:.2f} mm³")
    print(f"   ✓ Topology: {topology['face_count']} faces, {topology['edge_count']} edges")

    # Step 4: Export to STL
    print("\n4. Exporting to STL for 3D printing...")
    export_response = call_cli({
        "jsonrpc": "2.0",
        "method": "file.export",
        "params": {
            "entity_ids": [current_part],
            "file_path": "examples/servo_bracket.stl",
            "format": "stl",
            "quality": "standard",
            "workspace_id": "main"
        },
        "id": 50
    })

    if export_response["result"]["status"] == "success":
        stl_path = export_response["result"]["data"]["file_path"]
        triangle_count = export_response["result"]["data"]["triangle_count"]
        file_size = export_response["result"]["data"]["file_size_bytes"]

        print(f"   ✓ STL exported: {stl_path}")
        print(f"   ✓ Triangles: {triangle_count:,}")
        print(f"   ✓ File size: {file_size:,} bytes ({file_size/1024:.1f} KB)")

        print("\n" + "=" * 60)
        print("✅ BUILD COMPLETE!")
        print("=" * 60)
        print(f"\nServo bracket ready for 3D printing!")
        print(f"Final part ID: {current_part}")
        print(f"Volume: {final_volume:.2f} mm³")
        print(f"STL file: {stl_path}")
        print("\nView the STL file at: https://www.viewstl.com/")
        print("Or open in FreeCAD, MeshLab, or your slicer software.")
    else:
        print("   ✗ Export failed!")
        print(f"   Error: {export_response.get('error', 'Unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
