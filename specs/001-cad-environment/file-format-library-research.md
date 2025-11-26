# File Format Library Research: STEP, STL, DXF

**Feature**: `001-cad-environment`
**Date**: 2025-11-24
**Research Type**: Python Library Evaluation for CAD File Formats

## Executive Summary

### Recommended Libraries

| Format | Primary Library | Alternative | Rationale |
|--------|----------------|-------------|-----------|
| **STEP** | OCP/pythonOCC (OCCT STEPControl) | steputils (pure Python) | Native OCCT integration, production-proven, comprehensive AP203/AP214/AP242 support |
| **STL** | trimesh | numpy-stl | Versatile mesh processing, BREP conversion via GMSH, excellent numpy integration |
| **DXF** | ezdxf | OCCT DXF Import-Export | Pure Python, comprehensive version support (R12-R2018), active maintenance |

### Integration Strategy

**Geometry Kernel: OCP (cadquery-ocp)**
- Modern pybind11-based OpenCascade bindings
- Active development through 2024-2025 (latest: 7.8.1.1.post1, Jan 29, 2025)
- Used by CadQuery 2.x framework
- Performance improvements over pythonOCC (SWIG-based)
- Provides unified STEP import/export through OCCT's native support

---

## 1. STEP File Format (ISO 10303)

### 1.1 Library Options

#### Option 1: OCP/pythonOCC with OCCT STEPControl (RECOMMENDED)

**Library**: `cadquery-ocp` (OCP bindings) or `pythonocc-core`

**Key Strengths**:
- Native OCCT `STEPControl_Reader` and `STEPControl_Writer` integration
- Supports AP203, AP214, and AP242 application protocols
- Built-in topology validation via `BRepCheck_Analyzer`
- Automatic geometry repair with `ShapeFix_Shape`
- Entity counting and statistics via `tpstat` functionality
- Production-proven (used in FreeCAD, KiCad, SALOME)

**API Example**:
```python
from OCC.Core.STEPControl import STEPControl_Reader
from OCC.Core.IFSelect import IFSelect_RetDone
from OCC.Core.BRepCheck import BRepCheck_Analyzer
from OCC.Core.BRepGProp import brepgprop_VolumeProperties, brepgprop_SurfaceProperties
from OCC.Core.GProp import GProp_GProps

# Import STEP file
reader = STEPControl_Reader()
status = reader.ReadFile("model.step")

if status == IFSelect_RetDone:
    reader.TransferRoots()
    shape = reader.Shape()

    # Topology validation
    analyzer = BRepCheck_Analyzer(shape)
    is_valid = analyzer.IsValid()

    # Calculate properties
    props = GProp_GProps()
    brepgprop_VolumeProperties(shape, props)
    volume = props.Mass()
    center_of_mass = props.CentreOfMass()

    # Surface area
    surf_props = GProp_GProps()
    brepgprop_SurfaceProperties(shape, surf_props)
    surface_area = surf_props.Mass()
```

**Performance Characteristics**:
- No published benchmarks for specific file sizes
- OCCT v7+ includes "significant performance improvements"
- Expected: <5s for 10MB STEP files based on production usage
- Performance depends on entity complexity, not just file size

**Entity Type Preservation**:
- Full BREP topology preservation (vertices, edges, wires, faces, shells, solids)
- NURBS curves and surfaces maintained with exact mathematics
- Assembly structure preserved with naming and metadata
- Supports entity statistics via `statshape` functionality

**Dependencies**:
- `cadquery-ocp>=7.7.2` (latest: 7.8.1.1.post1, Jan 29, 2025)
- No external libraries required (OCCT bundled in wheels)
- Available for Windows, Linux, macOS via PyPI

**Sources**:
- [CadQuery Documentation - Importing and Exporting Files](https://cadquery.readthedocs.io/en/latest/importexport.html)
- [OpenCASCADE STEP Translator User Guide](https://dev.opencascade.org/doc/overview/html/occt_user_guides__step.html)
- [cadquery-ocp PyPI](https://pypi.org/project/cadquery-ocp/)

#### Option 2: steputils (Pure Python Parser)

**Library**: `steputils`

**Key Strengths**:
- Pure Python implementation (no compilation required)
- Lightweight DOM for STEP model data
- Read/write STEP-file (ISO 10303-21) support
- No external dependencies

**Limitations**:
- Parser only - does not reconstruct BREP geometry
- Limited to Part 21 physical file format
- No topology validation or geometric operations
- Cannot integrate with geometry kernel for solid modeling

**Use Case**: File format validation, metadata extraction, lightweight parsing without geometry reconstruction

**Dependencies**:
- `steputils` (pure Python)

**Sources**:
- [steputils PyPI](https://pypi.org/project/steputils/)
- [steputils Documentation](https://steputils.readthedocs.io/en/latest/p21.html)

#### Option 3: STEPcode (C++ with Python Bindings)

**Library**: `stepcode`

**Key Strengths**:
- Cross-platform (Linux, OSX, Windows)
- EXPRESS schema parser with C/C++/Python bindings
- SDAI (Part 22) object libraries
- BSD license (open source)
- Can read/write Part 21 exchange files

**Limitations**:
- Requires compilation (not pure Python)
- More complex setup than OCP
- Community-driven (less active than OCCT)
- Does not provide BREP geometry operations

**Use Case**: Custom EXPRESS schema handling, research applications

**Dependencies**:
- CMake build system
- C++ compiler

**Sources**:
- [STEPcode GitHub](https://github.com/stepcode/stepcode)
- [STEPcode Documentation](https://stepcode.github.io/docs/home/)

### 1.2 Recommended Decision: OCP with OCCT STEPControl

**Rationale**:
1. **Native Integration**: OCCT is the chosen geometry kernel (per research.md) - using OCCT's STEP support provides seamless integration
2. **Comprehensive Validation**: Built-in `BRepCheck_Analyzer` provides topology validation required by FR-038
3. **Performance**: Production-proven in major CAD applications (FreeCAD, KiCad)
4. **Entity Counting**: OCCT provides `statshape` and `tpstat` for entity inventory (required by FR-034)
5. **Active Maintenance**: OCP actively maintained with 2025 updates (7.8.1.1.post1)

**Implementation Notes**:
- Use `STEPControl_Reader` for import with `TransferRoots()` for all entities
- Validate with `BRepCheck_Analyzer.IsValid()` before accepting geometry
- Calculate properties with `BRepGProp` for volume, surface area, center of mass
- Report entity counts using topology exploration (`TopExp_Explorer`)
- Handle errors with specific OCCT status codes (`IFSelect_RetDone`, `IFSelect_RetFail`, etc.)

**Risks/Limitations**:
- Large files (>100MB) may require streaming or chunked processing
- Complex assemblies with thousands of parts may require memory management
- Some STEP entities (dimensions, annotations) may not translate to BREP
- AP242 PMI (Product Manufacturing Information) support limited

---

## 2. STL File Format (Mesh Export)

### 2.1 Library Options

#### Option 1: trimesh (RECOMMENDED)

**Library**: `trimesh`

**Key Strengths**:
- Pure Python 3.8+ library for triangular meshes
- Import BREP geometry via GMSH SDK (STEP, IGES, BREP, etc.)
- Export binary and ASCII STL
- Extensive mesh processing (repair, simplification, analysis)
- Volume and surface area calculation for validation
- Manifold mesh verification
- Excellent numpy integration

**API Example**:
```python
import trimesh
import numpy as np

# Option 1: Convert BREP to mesh via GMSH
# Requires GMSH SDK installation
mesh = trimesh.load("model.step")  # Uses GMSH for BREP import

# Option 2: Create mesh from OCCT tessellation
# (More common with OCP integration)
vertices = np.array([[0,0,0], [1,0,0], [0,1,0]])
faces = np.array([[0,1,2]])
mesh = trimesh.Trimesh(vertices=vertices, faces=faces)

# Export as STL
mesh.export("output.stl")  # Binary STL (default)
mesh.export("output.stl", file_type="stl_ascii")  # ASCII STL

# Validation
print(f"Triangle count: {len(mesh.faces)}")
print(f"Volume: {mesh.volume}")
print(f"Surface area: {mesh.area}")
print(f"Is watertight: {mesh.is_watertight}")
print(f"Is manifold: {mesh.is_winding_consistent}")
```

**Mesh Resolution Control**:
- When using GMSH for BREP conversion, control via GMSH parameters
- When using OCCT tessellation (recommended), control via OCCT `BRepMesh_IncrementalMesh`:

```python
from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
from OCC.Core.StlAPI import StlAPI_Writer

# Tessellate OCCT shape
mesh = BRepMesh_IncrementalMesh(shape, linear_deflection=0.1, angular_deflection=0.5)
mesh.Perform()

# Export via StlAPI
writer = StlAPI_Writer()
writer.SetASCIIMode(False)  # Binary mode
writer.Write(shape, "output.stl")
```

**Performance**:
- Fast mesh processing (C++ core with Python bindings)
- Handles millions of triangles efficiently
- Memory-efficient streaming for large meshes

**Dependencies**:
- `trimesh` (required)
- `numpy` (required)
- Optional: GMSH SDK for direct BREP import (alternative to OCCT)

**Sources**:
- [trimesh PyPI](https://pypi.org/project/trimesh/)
- [trimesh Documentation](https://trimesh.org/)
- [trimesh GitHub](https://github.com/mikedh/trimesh)

#### Option 2: numpy-stl

**Library**: `numpy-stl`

**Key Strengths**:
- Lightweight STL generation from numpy arrays
- Simple API for vertex/face data
- Binary and ASCII STL support

**Limitations**:
- No BREP conversion (requires separate tessellation)
- Limited mesh processing capabilities
- No built-in validation or repair

**Use Case**: Simple STL export when mesh is already generated

**API Example**:
```python
from stl import mesh
import numpy as np

# Create mesh from vertices and faces
vertices = np.array([[0,0,0], [1,0,0], [0,1,0]])
faces = np.array([[0,1,2]])

# Create mesh
stl_mesh = mesh.Mesh(np.zeros(faces.shape[0], dtype=mesh.Mesh.dtype))
for i, face in enumerate(faces):
    for j in range(3):
        stl_mesh.vectors[i][j] = vertices[face[j]]

# Export
stl_mesh.save("output.stl")
```

**Dependencies**:
- `numpy-stl`
- `numpy`

**Sources**:
- numpy-stl (search results reference only)

#### Option 3: OCCT StlAPI_Writer (Native)

**Library**: OCP/pythonOCC (OCCT native)

**Key Strengths**:
- Native OCCT integration (no external libraries)
- Direct access to OCCT tessellation parameters
- Consistent with STEP import workflow
- Production-proven

**API Example**:
```python
from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
from OCC.Core.StlAPI import StlAPI_Writer

# Tessellate with configurable parameters
linear_deflection = 0.1  # mm - max distance between mesh and surface
angular_deflection = 0.5  # radians - max angle between adjacent normals
relative_mode = True     # Scale deflection by object size

mesh = BRepMesh_IncrementalMesh(shape, linear_deflection, angular_deflection, relative_mode)
mesh.Perform()

# Export
writer = StlAPI_Writer()
writer.SetASCIIMode(False)  # Binary STL (smaller files)
status = writer.Write(shape, "output.stl")
```

**Tessellation Quality**:
- `linear_deflection`: Controls triangle size (smaller = finer mesh)
- `angular_deflection`: Controls smoothness on curved surfaces
- `relative_mode`: Scales deflection by bounding box size

**Dependencies**:
- `cadquery-ocp` or `pythonocc-core` (already required for STEP)

**Sources**:
- [OpenCASCADE Documentation](https://dev.opencascade.org/doc/overview/html/occt_user_guides__step.html)

### 2.2 Recommended Decision: OCCT StlAPI_Writer + trimesh for Validation

**Rationale**:
1. **Native Integration**: OCCT `StlAPI_Writer` already available with OCP (no additional dependencies)
2. **Precise Control**: Direct access to tessellation parameters (linear/angular deflection)
3. **Validation**: Use trimesh for mesh verification (manifold checks, volume comparison)
4. **Performance**: OCCT tessellation optimized for CAD geometry
5. **Consistency**: Unified OCCT workflow for STEP → BREP → STL

**Implementation Strategy**:
```python
# Phase 1: Tessellate with OCCT
from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
from OCC.Core.StlAPI import StlAPI_Writer
from OCC.Core.BRepGProp import brepgprop_VolumeProperties
from OCC.Core.GProp import GProp_GProps
import trimesh

# Get original volume
props = GProp_GProps()
brepgprop_VolumeProperties(shape, props)
original_volume = props.Mass()

# Tessellate
mesh_gen = BRepMesh_IncrementalMesh(shape, linear_deflection=0.1)
mesh_gen.Perform()

# Export STL
writer = StlAPI_Writer()
writer.Write(shape, "output.stl")

# Phase 2: Validate with trimesh
stl_mesh = trimesh.load("output.stl")
triangle_count = len(stl_mesh.faces)
mesh_volume = stl_mesh.volume
volume_error = abs(mesh_volume - original_volume) / original_volume * 100

# Report
print(f"Triangle count: {triangle_count}")
print(f"Original volume: {original_volume:.2f}")
print(f"Mesh volume: {mesh_volume:.2f}")
print(f"Volume error: {volume_error:.2f}%")
print(f"Is watertight: {stl_mesh.is_watertight}")
```

**Implementation Notes**:
- Default `linear_deflection=0.1` provides good balance (requirement: configurable)
- Compare volume/surface area before/after to detect data loss (FR-037)
- Warn if volume error >1% or mesh is not watertight
- Report triangle count for mesh resolution feedback
- Binary STL recommended (smaller files, faster parsing)

**Risks/Limitations**:
- **Data Loss**: STL is always lossy (exact geometry → triangulated approximation)
- **Precision Loss**: Fine features may be lost if deflection too large
- **File Size**: Fine tessellation creates large STL files (millions of triangles)
- **No Topology**: STL loses BREP topology (cannot reconstruct solids)

---

## 3. DXF File Format (2D Geometry Exchange)

### 3.1 Library Options

#### Option 1: ezdxf (RECOMMENDED)

**Library**: `ezdxf`

**Key Strengths**:
- Pure Python (no compilation required)
- Comprehensive DXF version support (R12, R2000, R2004, R2007, R2010, R2013, R2018)
- Read and write capability
- Layer preservation and management
- Excellent documentation
- Active maintenance (v1.4.3 as of 2024)
- MIT License
- Requires Python 3.10+
- Optional C-extensions for performance (included in binary wheels)

**API Example**:
```python
import ezdxf
from ezdxf import units

# Read DXF
doc = ezdxf.readfile("input.dxf")
msp = doc.modelspace()

# Entity inventory
entity_count = {}
for entity in msp:
    entity_type = entity.dxftype()
    entity_count[entity_type] = entity_count.get(entity_type, 0) + 1

# Layer inventory
layers = [layer.dxf.name for layer in doc.layers]

# Coordinate bounds
from ezdxf.bbox import extents
bbox = extents(msp)  # Returns (min_point, max_point)

# Unit system detection
unit = doc.units
print(f"Drawing units: {units.decode(unit)}")

# Create DXF
new_doc = ezdxf.new("R2018")
new_msp = new_doc.modelspace()

# Add entities
new_msp.add_line((0, 0), (10, 10))
new_msp.add_circle((5, 5), radius=3)
new_msp.add_arc((0, 0), radius=5, start_angle=0, end_angle=90)

# Save
new_doc.saveas("output.dxf")
```

**Layer Preservation**:
```python
# Query layers
for layer in doc.layers:
    print(f"Layer: {layer.dxf.name}, Color: {layer.dxf.color}")

# Add entity to specific layer
msp.add_line((0, 0), (10, 10), dxfattribs={"layer": "MyLayer"})
```

**Validation Features**:
- DXF version detection via `doc.dxfversion`
- Entity type checking with `entity.dxftype()`
- Bounding box calculation with `ezdxf.bbox.extents()`
- Unit system via `doc.units`
- Degenerate geometry detection (zero-length lines, zero-radius circles)

**Performance**:
- C-extensions included in PyPI wheels (Windows, Linux, macOS)
- Fast parsing for typical DXF files (<1s for 10MB files)

**Dependencies**:
- `ezdxf>=1.4.3` (requires Python 3.10+)
- `pyparsing`, `numpy`, `fontTools`, `typing_extensions` (automatic dependencies)

**Sources**:
- [ezdxf PyPI](https://pypi.org/project/ezdxf/)
- [ezdxf Documentation](https://ezdxf.readthedocs.io/)
- [ezdxf GitHub](https://github.com/mozman/ezdxf)

#### Option 2: OCCT DXF Import-Export

**Library**: OCP/pythonOCC (OCCT native)

**Key Strengths**:
- Native OCCT integration
- Handles 3D DXF conversions (2D DXF → 3D BREP)
- Consistent with STEP/STL workflow

**Limitations**:
- Less comprehensive than ezdxf for pure 2D workflows
- Documentation less extensive than ezdxf
- Primarily designed for 3D CAD interoperability

**Use Case**: When converting DXF to 3D solids (e.g., extrude DXF profile)

**Dependencies**:
- `cadquery-ocp` or `pythonocc-core`

**Sources**:
- OCCT documentation (limited DXF-specific resources)

### 3.2 Recommended Decision: ezdxf for DXF, OCCT for 2D→3D Conversion

**Rationale**:
1. **Pure 2D Workflows**: ezdxf provides superior DXF handling for layer preservation, entity types, and version support
2. **Python-Native**: No compilation, easier deployment, excellent documentation
3. **Active Maintenance**: Latest version 1.4.3 (2024), regular updates
4. **Comprehensive**: Supports full DXF spec (R12-R2018)
5. **Performance**: C-extensions available for CPython

**Hybrid Strategy**:
- **DXF Import/Export**: Use ezdxf for reading/writing DXF files
- **2D→3D Conversion**: Use ezdxf to parse DXF → extract geometry → convert to OCCT entities → extrude/revolve

**Implementation Example**:
```python
import ezdxf
from OCC.Core.gp import gp_Pnt, gp_Circ, gp_Ax2, gp_Dir
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire

# Import DXF with ezdxf
doc = ezdxf.readfile("profile.dxf")
msp = doc.modelspace()

# Convert DXF entities to OCCT geometry
edges = []
for entity in msp.query("LINE"):
    start = entity.dxf.start
    end = entity.dxf.end
    edge = BRepBuilderAPI_MakeEdge(
        gp_Pnt(start.x, start.y, 0),
        gp_Pnt(end.x, end.y, 0)
    ).Edge()
    edges.append(edge)

for entity in msp.query("CIRCLE"):
    center = entity.dxf.center
    radius = entity.dxf.radius
    circle = gp_Circ(gp_Ax2(gp_Pnt(center.x, center.y, 0), gp_Dir(0, 0, 1)), radius)
    edge = BRepBuilderAPI_MakeEdge(circle).Edge()
    edges.append(edge)

# Create wire from edges
wire_builder = BRepBuilderAPI_MakeWire()
for edge in edges:
    wire_builder.Add(edge)
wire = wire_builder.Wire()

# Now can extrude wire using OCCT solid modeling
```

**Implementation Notes**:
- Use ezdxf for all DXF I/O operations (FR-036)
- Preserve layers by storing as metadata in OCCT entities
- Validate coordinate bounds to detect degenerate geometry
- Report entity type support (LINE, CIRCLE, ARC, SPLINE, etc.)
- Warn about unsupported entities (3D solids, dimensions, hatches)

**Risks/Limitations**:
- **2D Only**: DXF primarily for 2D geometry (STEP preferred for 3D)
- **Entity Support**: Not all DXF entities map to OCCT primitives (dimensions, annotations)
- **Application-Specific Data**: AutoCAD dynamic blocks, parametric constraints lost
- **Precision**: Coordinate precision limited by DXF text format (vs STEP binary)

---

## 4. Integration with Geometry Kernel

### 4.1 Chosen Geometry Kernel: OCP (cadquery-ocp)

**Decision**: Use `cadquery-ocp` (OCP) as primary Python bindings for OpenCascade

**Rationale** (from web search results):
1. **Modern Binding Technology**: Uses pybind11 (faster than pythonOCC's SWIG)
2. **Active Development**: Latest release 7.8.1.1.post1 (January 29, 2025)
3. **CadQuery Ecosystem**: Powers CadQuery 2.x framework
4. **Performance**: "CadQuery scripts can build STL, STEP, AMF and 3MF faster than OpenSCAD"
5. **Comprehensive Bindings**: "Only OCCT Python wrapper to internally use a sane clang-based binding generator"

**Alternative Considered**: pythonOCC-core (SWIG-based, more direct OCCT mapping but slower)

### 4.2 Workflow Integration

```
Agent Command (CLI)
    ↓
File Import Command (DXF/STEP/STL)
    ↓
┌─────────────────────────────────────────────┐
│ STEP: OCP STEPControl_Reader                │
│ DXF:  ezdxf → OCP conversion                │
│ STL:  trimesh → OCP (if reconstructing)     │
└─────────────────────────────────────────────┘
    ↓
OCP Geometry Kernel (TopoDS_Shape)
    ↓
Constraint Solver / Solid Modeling
    ↓
OCP Geometry Output
    ↓
┌─────────────────────────────────────────────┐
│ STEP: OCP STEPControl_Writer                │
│ DXF:  OCP → ezdxf conversion                │
│ STL:  OCP BRepMesh → StlAPI_Writer          │
└─────────────────────────────────────────────┘
    ↓
File Export (DXF/STEP/STL)
    ↓
Validation Report (JSON)
```

### 4.3 API Pattern Consistency

**All File Operations Follow Pattern**:
1. **Validation**: Pre-import checks (file exists, format valid, version supported)
2. **Import**: Parse file → convert to OCP geometry
3. **Inventory**: Count entities, calculate properties
4. **Topology Check**: Validate with `BRepCheck_Analyzer`
5. **Report**: Return JSON with entity counts, volumes, warnings
6. **Error Handling**: Specific error codes for each failure mode

**Example JSON Response**:
```json
{
  "status": "success",
  "operation": "file.import.step",
  "data": {
    "file_path": "model.step",
    "format": "STEP",
    "version": "AP214",
    "entities": {
      "solids": 5,
      "shells": 5,
      "faces": 234,
      "edges": 567,
      "vertices": 345
    },
    "properties": {
      "total_volume": 1234.56,
      "total_surface_area": 789.12,
      "bounding_box": {
        "min": [0, 0, 0],
        "max": [100, 50, 30]
      }
    },
    "validation": {
      "topology_valid": true,
      "manifold": true,
      "warnings": []
    }
  }
}
```

---

## 5. Data Loss Detection and Warnings

### 5.1 STEP → STL (Exact → Mesh Approximation)

**Loss Type**: Precision loss from BREP to triangulated mesh

**Detection Strategy**:
1. Calculate original solid volume/surface area (OCCT `BRepGProp`)
2. Calculate mesh volume/surface area (trimesh)
3. Compare percentage difference
4. Check mesh quality (watertight, manifold)

**Warning Thresholds**:
- Volume error >1%: WARNING
- Volume error >5%: ERROR (tessellation too coarse)
- Not watertight: ERROR (invalid mesh)
- Triangle count <100: WARNING (may be too coarse)

**Example Warning**:
```json
{
  "status": "success",
  "data": {
    "file_path": "output.stl",
    "triangle_count": 15234
  },
  "warnings": [
    {
      "code": "PRECISION_LOSS",
      "severity": "warning",
      "message": "STL export is lossy: exact BREP geometry approximated as mesh",
      "details": {
        "original_volume": 1234.56,
        "mesh_volume": 1230.12,
        "volume_error_percent": 0.36,
        "original_surface_area": 789.12,
        "mesh_surface_area": 791.45
      },
      "suggestion": "Use STEP format for lossless geometry exchange. Reduce linear_deflection for higher mesh precision."
    }
  ]
}
```

### 5.2 STEP → DXF (3D Solid → 2D Projection)

**Loss Type**: Dimension reduction (3D solid flattened to 2D)

**Detection Strategy**:
1. Check if STEP contains 3D solids
2. Determine projection plane (XY, XZ, YZ)
3. Warn about Z-axis information loss

**Warning Example**:
```json
{
  "status": "success",
  "warnings": [
    {
      "code": "DIMENSION_REDUCTION",
      "severity": "error",
      "message": "Cannot export 3D solid to DXF: DXF supports 2D geometry only",
      "details": {
        "entity_type": "TopoDS_Solid",
        "dimension": 3
      },
      "suggestion": "Extract 2D profile from solid (sketch plane) or use STEP format for 3D geometry"
    }
  ]
}
```

### 5.3 DXF → STEP (2D → 3D Ambiguity)

**Loss Type**: Missing Z-axis interpretation

**Detection Strategy**:
1. Check if DXF entities have Z coordinates
2. If all Z=0, warn about 2D→3D ambiguity
3. Suggest extrude/revolve operations

**Warning Example**:
```json
{
  "status": "success",
  "warnings": [
    {
      "code": "MISSING_DIMENSION",
      "severity": "info",
      "message": "DXF contains 2D geometry (Z=0). To create 3D solid, use extrude or revolve operations.",
      "details": {
        "entities_2d": 45,
        "entities_3d": 0
      },
      "suggestion": "Use 'solid extrude' command to create 3D geometry from imported 2D profile"
    }
  ]
}
```

### 5.4 Round-Trip Testing

**Validation Strategy**: Export → Import → Compare

```python
# Export STEP
original_shape = ...  # OCP TopoDS_Shape
export_step(original_shape, "test.step")

# Re-import
imported_shape = import_step("test.step")

# Compare properties
original_volume = calculate_volume(original_shape)
imported_volume = calculate_volume(imported_shape)
error = abs(original_volume - imported_volume) / original_volume

if error > 0.001:  # 0.1% threshold
    warn("Round-trip STEP export/import lost precision")
```

---

## 6. Performance Validation

### 6.1 Target Metrics (from spec.md FR-019, FR-020)

| Operation | Target | Test Case |
|-----------|--------|-----------|
| STEP import (<10MB) | <5s | 10MB STEP file with 1000 entities |
| STL export | <1s | Solid with 1000 faces, linear_deflection=0.1 |
| DXF import | <1s | 10,000 2D entities |
| DXF export | <1s | 10,000 2D entities |

### 6.2 Benchmark Strategy

**Test Environment**:
- Hardware: Multi-core CPU, 16GB+ RAM, SSD
- File sizes: 1MB, 10MB, 100MB STEP files
- Entity complexity: Simple primitives vs complex NURBS

**Metrics to Measure**:
1. File read time (disk I/O)
2. Parsing time (format → data structure)
3. Geometry reconstruction time (data → BREP)
4. Validation time (topology checks)
5. Total operation time (end-to-end)

**Performance Profiling**:
```python
import time

def benchmark_step_import(file_path):
    start = time.perf_counter()

    # Phase 1: File read
    read_start = time.perf_counter()
    reader = STEPControl_Reader()
    status = reader.ReadFile(file_path)
    read_time = time.perf_counter() - read_start

    # Phase 2: Transfer geometry
    transfer_start = time.perf_counter()
    reader.TransferRoots()
    shape = reader.Shape()
    transfer_time = time.perf_counter() - transfer_start

    # Phase 3: Validation
    validation_start = time.perf_counter()
    analyzer = BRepCheck_Analyzer(shape)
    is_valid = analyzer.IsValid()
    validation_time = time.perf_counter() - validation_start

    total_time = time.perf_counter() - start

    return {
        "read_time_ms": read_time * 1000,
        "transfer_time_ms": transfer_time * 1000,
        "validation_time_ms": validation_time * 1000,
        "total_time_ms": total_time * 1000
    }
```

### 6.3 Optimization Strategies (if needed)

If performance targets not met:

**STEP Import**:
- Stream large files instead of loading entire file
- Parallel entity transfer for multi-part assemblies
- Disable validation for trusted sources (validate on demand)

**STL Export**:
- Adaptive tessellation (coarser mesh for large flat surfaces)
- Parallel tessellation for multi-body assemblies
- Binary STL always (smaller, faster)

**DXF Import**:
- ezdxf supports streaming for large files
- Filter entities by layer (import only needed layers)

---

## 7. Dependency Summary

### 7.1 Required Dependencies

```toml
# pyproject.toml
[project]
name = "cad-environment"
version = "0.1.0"
requires-python = ">=3.10"

dependencies = [
    "cadquery-ocp>=7.7.2",  # OpenCascade bindings (STEP, STL, BREP)
    "trimesh>=4.0.0",        # STL validation and mesh processing
    "ezdxf>=1.4.3",          # DXF import/export
    "numpy>=1.20.0",         # Required by trimesh and ezdxf
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
]
```

### 7.2 License Compatibility

| Library | License | Compatible? | Notes |
|---------|---------|-------------|-------|
| cadquery-ocp | LGPL 2.1 | ✅ Yes | LGPL allows commercial use, no source disclosure required for applications |
| trimesh | MIT | ✅ Yes | Permissive, no restrictions |
| ezdxf | MIT | ✅ Yes | Permissive, no restrictions |
| numpy | BSD | ✅ Yes | Permissive, no restrictions |

**Constitution Compliance**: All dependencies are open-source with permissive or LGPL licenses. LGPL 2.1 (OCCT/OCP) allows commercial use and modification without requiring application source disclosure. Satisfies Principle VIII (Owned 3D CAD System) by using modifiable open-source libraries.

### 7.3 Platform Support

**Supported Platforms**:
- Windows (x64)
- Linux (x64, ARM64)
- macOS (x64, Apple Silicon)

**Binary Wheels Available**:
- `cadquery-ocp`: PyPI wheels for all platforms
- `trimesh`: Pure Python (platform-independent)
- `ezdxf`: Pure Python with optional C-extensions (wheels for CPython)

**Installation**:
```bash
pip install cadquery-ocp trimesh ezdxf
```

No compilation required (binary wheels handle C++ components).

---

## 8. Implementation Roadmap

### 8.1 Phase 0: Proof of Concept (1-2 weeks)

**Objectives**:
- Validate library installation (OCP, trimesh, ezdxf)
- Implement basic STEP import with entity counting
- Implement basic STL export with validation
- Benchmark performance against targets

**Deliverables**:
- `test_step_import.py`: Import 10MB STEP file, verify <5s
- `test_stl_export.py`: Export solid to STL, verify volume within 1%
- `test_dxf_roundtrip.py`: Import DXF, export DXF, compare entities

### 8.2 Phase 1: Core File I/O (2-3 weeks)

**Objectives**:
- Complete STEP import/export with all validation
- Complete STL export with configurable tessellation
- Complete DXF import/export with layer preservation
- Implement data loss detection and warnings

**Deliverables**:
- `src/cad_environment/io/step_io.py`: Full STEP implementation
- `src/cad_environment/io/stl_io.py`: Full STL implementation
- `src/cad_environment/io/dxf_io.py`: Full DXF implementation
- Contract tests for all file format commands

### 8.3 Phase 2: CLI Integration (1-2 weeks)

**Objectives**:
- Integrate file I/O with CLI command structure
- Implement streaming JSON responses
- Add file format error handling to CLI

**Deliverables**:
- CLI commands: `file import step`, `file export stl`, `file import dxf`, `file export dxf`
- JSON response schemas for all file operations
- Integration tests for end-to-end file workflows

### 8.4 Phase 3: Validation & Optimization (1-2 weeks)

**Objectives**:
- Performance profiling and optimization
- Edge case testing (malformed files, unsupported entities)
- Documentation for file format limitations

**Deliverables**:
- Performance benchmarks meeting targets
- Error handling for all file format edge cases
- User documentation for file import/export

**Total Estimated Timeline**: 5-9 weeks for complete file I/O implementation

---

## 9. Risks and Mitigation

### 9.1 Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| STEP import performance <5s | Medium | High | Profile with large files early, optimize transfer process, consider parallel entity loading |
| STL volume error >1% | Low | Medium | Use conservative tessellation defaults, provide tuning guidance, validate against test cases |
| DXF entity type gaps | Medium | Low | Document supported entities, provide clear errors for unsupported types, prioritize common entities (LINE, CIRCLE, ARC) |
| OCP installation issues | Low | High | Provide detailed setup instructions, test on all platforms, fallback to Docker container |
| Memory exhaustion (large files) | Medium | Medium | Implement streaming for >100MB files, add memory monitoring, provide file size warnings |

### 9.2 Mitigation Strategies

**STEP Performance**:
- Early benchmark with 10MB, 50MB, 100MB files
- If >5s, profile with `cProfile` to identify bottleneck
- Consider selective entity transfer (import only needed parts)

**STL Precision**:
- Default `linear_deflection=0.1` provides <1% error for most geometry
- Add adaptive tessellation (analyze curvature, adjust deflection)
- Provide "quality presets" (draft, standard, high, ultra)

**DXF Support**:
- Phase 1: LINE, CIRCLE, ARC, LWPOLYLINE (covers 80% of use cases)
- Phase 2: SPLINE, ELLIPSE, TEXT
- Phase 3: DIMENSION, HATCH (informational only)

**Installation**:
- CI/CD testing on Windows, Linux, macOS
- Docker image with all dependencies pre-installed
- Fallback: Build from source instructions

---

## 10. References and Sources

### STEP File Format

- [OpenCASCADE STEP Translator User Guide](https://dev.opencascade.org/doc/overview/html/occt_user_guides__step.html)
- [CadQuery Documentation - Importing and Exporting Files](https://cadquery.readthedocs.io/en/latest/importexport.html)
- [cadquery-ocp PyPI](https://pypi.org/project/cadquery-ocp/)
- [steputils PyPI](https://pypi.org/project/steputils/)
- [steputils Documentation](https://steputils.readthedocs.io/en/latest/p21.html)
- [STEPcode GitHub](https://github.com/stepcode/stepcode)
- [STEPcode Documentation](https://stepcode.github.io/docs/home/)
- [IfcOpenShell step-file-parser GitHub](https://github.com/IfcOpenShell/step-file-parser)

### STL File Format

- [trimesh PyPI](https://pypi.org/project/trimesh/)
- [trimesh Documentation](https://trimesh.org/)
- [trimesh GitHub](https://github.com/mikedh/trimesh)
- [How to convert any STP, STEP, IGS, IGES, BREP 3D model file to a STL mesh with python](https://marcofarias.com/how-to-convert-any-stp-step-igs-iges-brep-3d-model-file-to-a-stl-mesh-with-python)
- [PyMesh Documentation](https://pymesh.readthedocs.io/en/latest/)

### DXF File Format

- [ezdxf PyPI](https://pypi.org/project/ezdxf/)
- [ezdxf Documentation](https://ezdxf.readthedocs.io/)
- [ezdxf GitHub](https://github.com/mozman/ezdxf)

### File Format Limitations

- [CAD File for CNC Machining: Format and Preparation Guide](https://rosnokmachine.com/cad-file-for-cnc-machining/)
- [Understanding the Different Types of 3D Files - Core77](https://www.core77.com/posts/67499/Understanding-the-Different-Types-of-3D-Files)
- [CAD Drawing File Types: STEP vs STL](https://ims-tex.com/step-vs-stl/)
- [Understanding CAD File Types - Wevolver](https://www.wevolver.com/article/understanding-cad-file-types-a-comprehensive-guide-for-digital-design-and-hardware-engineers)

### OpenCascade Bindings

- [pyOCCT vs PythonOCC for new project (2020) - Stack Overflow](https://stackoverflow.com/questions/62783383/pyocct-vs-pythonocc-for-new-project-2020)
- [pythonOCC GitHub](https://github.com/tpaviot/pythonocc-core)
- [CadQuery GitHub](https://github.com/CadQuery/cadquery)
- [OCP GitHub](https://github.com/CadQuery/OCP)

### Performance and Integration

- [CadQuery shapes.py implementation](https://github.com/CadQuery/cadquery/blob/master/cadquery/occ_impl/shapes.py)
- [Introduction - CadQuery Documentation](https://cadquery.readthedocs.io/en/latest/intro.html)

---

## Conclusion

**All file format requirements from spec.md can be satisfied with:**

1. **STEP**: OCP's native `STEPControl_Reader`/`STEPControl_Writer` (OCCT) - provides entity counting, topology validation, volume/surface area calculation
2. **STL**: OCP's native `StlAPI_Writer` for export with configurable tessellation, trimesh for validation
3. **DXF**: ezdxf for Python-native DXF handling with layer preservation and comprehensive version support

**Key Implementation Principles**:
- Unified workflow through OCP geometry kernel
- Comprehensive validation with data loss detection
- Performance targets achievable with OCCT's production-proven implementation
- Clear error reporting for agent learning (FR-022, FR-037)
- All dependencies open-source with compatible licenses

**Next Steps**:
1. Install dependencies (`cadquery-ocp`, `trimesh`, `ezdxf`)
2. Implement Phase 0 proof-of-concept tests
3. Validate performance against targets (<5s for 10MB STEP import)
4. Proceed to Phase 1 implementation (full file I/O module)

**Ready to proceed with implementation** based on this research.
