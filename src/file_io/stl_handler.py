"""STL format export for CAD solids.

STL (STereoLithography) is a triangulated mesh format widely used for 3D printing.
"""
import math
from pathlib import Path
from typing import Any


def export_stl(solids: list[dict[str, Any]], file_path: str, ascii_format: bool = False) -> dict[str, Any]:
    """Export solids to STL format.

    Args:
        solids: List of solid dictionaries with topology
        file_path: Output file path
        ascii_format: If True, write ASCII STL; otherwise binary

    Returns:
        Export report with statistics
    """
    output_path = Path(file_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # For simplicity, create a basic tessellation
    # In a real implementation, this would use OCCT's tessellation
    triangles = []

    for solid in solids:
        # Generate simple tessellation based on geometry
        # This is a placeholder - real OCCT would provide actual mesh
        if "volume" in solid and "surface_area" in solid:
            # Approximate triangle count from surface area
            # Assuming average triangle size of 1 square unit
            triangle_count = max(8, int(solid["surface_area"] / 1.0))

            # Generate dummy triangles (in real impl, from OCCT mesh)
            for i in range(triangle_count):
                triangles.append({
                    "normal": [0.0, 0.0, 1.0],
                    "vertices": [
                        [0.0, 0.0, 0.0],
                        [1.0, 0.0, 0.0],
                        [0.5, 1.0, 0.0]
                    ]
                })

    # Write STL file
    if ascii_format:
        _write_ascii_stl(output_path, triangles)
    else:
        _write_binary_stl(output_path, triangles)

    file_size = output_path.stat().st_size

    return {
        "file_path": str(output_path),
        "format": "stl",
        "entity_count": len(solids),
        "triangle_count": len(triangles),
        "file_size": file_size,
        "data_loss": True,  # STL loses exact geometry (only mesh)
        "warnings": [
            "STL format is triangulated mesh - exact geometry information is lost",
            "Consider using STEP format for preserving exact geometry"
        ]
    }


def _write_ascii_stl(file_path: Path, triangles: list[dict]) -> None:
    """Write ASCII STL file."""
    with open(file_path, 'w') as f:
        f.write("solid exported\n")
        for tri in triangles:
            normal = tri["normal"]
            vertices = tri["vertices"]

            f.write(f"  facet normal {normal[0]} {normal[1]} {normal[2]}\n")
            f.write("    outer loop\n")
            for vertex in vertices:
                f.write(f"      vertex {vertex[0]} {vertex[1]} {vertex[2]}\n")
            f.write("    endloop\n")
            f.write("  endfacet\n")
        f.write("endsolid exported\n")


def _write_binary_stl(file_path: Path, triangles: list[dict]) -> None:
    """Write binary STL file."""
    import struct

    with open(file_path, 'wb') as f:
        # Header (80 bytes)
        header = b'Binary STL exported by CAD system' + b' ' * (80 - 34)
        f.write(header)

        # Triangle count (4 bytes)
        f.write(struct.pack('<I', len(triangles)))

        # Triangles
        for tri in triangles:
            normal = tri["normal"]
            vertices = tri["vertices"]

            # Normal vector (3 floats)
            f.write(struct.pack('<fff', *normal))

            # Vertices (3 * 3 floats)
            for vertex in vertices:
                f.write(struct.pack('<fff', *vertex))

            # Attribute byte count (2 bytes, usually 0)
            f.write(struct.pack('<H', 0))
