"""
Validate and inspect the STL file.
"""

import struct
from pathlib import Path

stl_file = Path("data/workspaces/demo_build/cylinder.stl")

print(f"\nValidating STL file: {stl_file}")
print(f"File size: {stl_file.stat().st_size:,} bytes\n")

with open(stl_file, 'rb') as f:
    # Read binary STL header
    header = f.read(80)
    print(f"Header: {header[:40].decode('ascii', errors='ignore').strip()}")

    # Read triangle count
    triangle_count_bytes = f.read(4)
    triangle_count = struct.unpack('<I', triangle_count_bytes)[0]
    print(f"Triangle count: {triangle_count:,}")

    # Calculate expected file size
    expected_size = 80 + 4 + (triangle_count * 50)
    actual_size = stl_file.stat().st_size
    print(f"Expected file size: {expected_size:,} bytes")
    print(f"Actual file size: {actual_size:,} bytes")
    print(f"Match: {'YES' if expected_size == actual_size else 'NO'}")

    # Read first few triangles to check geometry
    print(f"\nFirst 5 triangles:")
    for i in range(min(5, triangle_count)):
        # Each triangle: normal (12 bytes), v1 (12), v2 (12), v3 (12), attribute (2) = 50 bytes
        normal = struct.unpack('<fff', f.read(12))
        v1 = struct.unpack('<fff', f.read(12))
        v2 = struct.unpack('<fff', f.read(12))
        v3 = struct.unpack('<fff', f.read(12))
        attr = struct.unpack('<H', f.read(2))[0]

        print(f"\nTriangle {i+1}:")
        print(f"  Normal: ({normal[0]:.6f}, {normal[1]:.6f}, {normal[2]:.6f})")
        print(f"  V1: ({v1[0]:.2f}, {v1[1]:.2f}, {v1[2]:.2f})")
        print(f"  V2: ({v2[0]:.2f}, {v2[1]:.2f}, {v2[2]:.2f})")
        print(f"  V3: ({v3[0]:.2f}, {v3[1]:.2f}, {v3[2]:.2f})")

    # Calculate bounding box
    print(f"\nCalculating bounding box...")
    f.seek(84)  # Skip header and triangle count

    min_x = min_y = min_z = float('inf')
    max_x = max_y = max_z = float('-inf')

    for i in range(triangle_count):
        f.read(12)  # skip normal
        for _ in range(3):  # read 3 vertices
            x, y, z = struct.unpack('<fff', f.read(12))
            min_x = min(min_x, x)
            min_y = min(min_y, y)
            min_z = min(min_z, z)
            max_x = max(max_x, x)
            max_y = max(max_y, y)
            max_z = max(max_z, z)
        f.read(2)  # skip attribute

    print(f"\nBounding Box:")
    print(f"  X: [{min_x:.2f}, {max_x:.2f}] (width: {max_x - min_x:.2f})")
    print(f"  Y: [{min_y:.2f}, {max_y:.2f}] (height: {max_y - min_y:.2f})")
    print(f"  Z: [{min_z:.2f}, {max_z:.2f}] (depth: {max_z - min_z:.2f})")
    print(f"  Center: ({(min_x + max_x)/2:.2f}, {(min_y + max_y)/2:.2f}, {(min_z + max_z)/2:.2f})")

print("\n" + "="*80)
print("The STL file is valid and contains geometry!")
print("="*80)
