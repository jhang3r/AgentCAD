"""
Visualize the geometry created by multi-agent build demo.
"""

import json
import subprocess
import sys
from pathlib import Path


def export_workspace(workspace_id, output_file):
    """Export workspace geometry to JSON."""
    print(f"Exporting workspace '{workspace_id}' to {output_file}...")

    result = subprocess.run(
        [sys.executable, "-m", "src.agent_interface.cli", "file.export",
         "--params", json.dumps({
             "file_path": str(output_file),
             "format": "json",
             "workspace_id": workspace_id
         })],
        capture_output=True,
        text=True,
        timeout=10,
        cwd=Path(__file__).parent
    )

    if result.returncode == 0:
        print(f"   [OK] Export successful")
        return True
    else:
        print(f"   [ERROR] Export failed: {result.stderr}")
        return False


def visualize_2d_ascii(entities):
    """Create a simple ASCII visualization of 2D geometry."""
    print("\n" + "="*80)
    print("2D GEOMETRY VISUALIZATION (ASCII)")
    print("="*80 + "\n")

    points = []
    circles = []

    for entity in entities:
        if entity.get("entity_type") == "point":
            coords = entity.get("coordinates", [0, 0, 0])
            points.append((coords[0], coords[1], entity.get("entity_id", "unknown")))
        elif entity.get("entity_type") == "circle":
            center = entity.get("center", [0, 0, 0])
            radius = entity.get("radius", 0)
            circles.append((center[0], center[1], radius, entity.get("entity_id", "unknown")))

    if points:
        print(f"POINTS ({len(points)}):")
        for x, y, eid in sorted(points):
            print(f"  * ({x:6.1f}, {y:6.1f}) - {eid}")

    if circles:
        print(f"\nCIRCLES ({len(circles)}):")
        for cx, cy, r, eid in circles:
            print(f"  O center=({cx:6.1f}, {cy:6.1f}), radius={r:6.1f} - {eid}")
            print(f"    area={3.14159 * r * r:.2f}, circumference={2 * 3.14159 * r:.2f}")

    # Simple ASCII grid visualization (scaled to fit)
    if points or circles:
        print("\n" + "="*80)
        print("ASCII GRID VISUALIZATION")
        print("="*80 + "\n")

        # Find bounds
        all_x = [p[0] for p in points]
        all_y = [p[1] for p in points]
        for cx, cy, r, _ in circles:
            all_x.extend([cx - r, cx + r])
            all_y.extend([cy - r, cy + r])

        if all_x and all_y:
            min_x, max_x = min(all_x), max(all_x)
            min_y, max_y = min(all_y), max(all_y)

            # Create grid
            width = 60
            height = 20
            grid = [[' ' for _ in range(width)] for _ in range(height)]

            # Scale points to grid
            def scale_x(x):
                if max_x == min_x:
                    return width // 2
                return int((x - min_x) / (max_x - min_x) * (width - 1))

            def scale_y(y):
                if max_y == min_y:
                    return height // 2
                return int((max_y - min_y) / (max_y - min_y) * (height - 1))

            # Plot points
            for x, y, _ in points:
                gx, gy = scale_x(x), scale_y(y)
                if 0 <= gy < height and 0 <= gx < width:
                    grid[height - 1 - gy][gx] = '*'

            # Plot circles (just center)
            for cx, cy, r, _ in circles:
                gx, gy = scale_x(cx), scale_y(cy)
                if 0 <= gy < height and 0 <= gx < width:
                    grid[height - 1 - gy][gx] = 'O'

            # Print grid
            print("  +" + "-" * width + "+")
            for row in grid:
                print("  |" + "".join(row) + "|")
            print("  +" + "-" * width + "+")
            print(f"\n  Scale: X=[{min_x:.1f}, {max_x:.1f}], Y=[{min_y:.1f}, {max_y:.1f}]")
            print("  Legend: * = point, O = circle center")


def main():
    print("\n" + "="*80)
    print("MULTI-AGENT BUILD VISUALIZATION")
    print("="*80 + "\n")

    # Set workspace directory
    import os
    workspace_dir = Path("data/workspaces/demo_build").absolute()
    os.environ["MULTI_AGENT_WORKSPACE_DIR"] = str(workspace_dir)

    # Export design workspace
    design_export = workspace_dir / "design_export.json"
    if export_workspace("default_agent:box_design_ws", design_export):
        # Load and visualize
        with open(design_export, 'r') as f:
            data = json.load(f)
            entities = data.get("entities", [])

            print(f"\nDesign Workspace: {len(entities)} entities")
            visualize_2d_ascii(entities)

    print("\n" + "="*80)

    # Export 3D workspace
    print("\n3D WORKSPACE:")
    model_export = workspace_dir / "model_export.json"
    if export_workspace("default_agent:box_3d_ws", model_export):
        with open(model_export, 'r') as f:
            data = json.load(f)
            entities = data.get("entities", [])

            print(f"\n3D Workspace: {len(entities)} entities")
            for entity in entities:
                etype = entity.get("entity_type", "unknown")
                eid = entity.get("entity_id", "unknown")
                print(f"  - {etype}: {eid}")
                if etype == "circle":
                    center = entity.get("center", [0, 0, 0])
                    radius = entity.get("radius", 0)
                    print(f"    Center: ({center[0]}, {center[1]}, {center[2]})")
                    print(f"    Radius: {radius}")
                elif etype == "solid":
                    solid_type = entity.get("solid_type", "unknown")
                    print(f"    Solid type: {solid_type}")
                    if "height" in entity:
                        print(f"    Height: {entity['height']}")

    print("\n" + "="*80)
    print("[OK] Visualization complete!")
    print(f"Exported files:")
    print(f"  - {design_export}")
    print(f"  - {model_export}")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
