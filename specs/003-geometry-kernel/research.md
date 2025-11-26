# Research: pythonOCC-core Integration

**Date**: 2025-11-26
**Feature**: 3D Geometry Kernel
**Purpose**: Document technology decisions and API patterns for implementing geometry operations

---

## Decision Summary

### Primary Technology: pythonOCC-core 7.9.0 + System OCCT 7.9.0 (Dynamic Linking)

**Decision**: Use pythonOCC-core built against system-installed Open CASCADE Technology (OCCT) 7.9.0 as dynamically linked libraries for both development and deployment.

**Rationale**:
- Industry-standard geometry kernel used by FreeCAD, Salome, and other professional CAD systems
- Complete API for all required operations (extrude, revolve, loft, sweep, boolean, tessellation)
- Active maintenance and Python 3.11+ support
- **Dynamic linking provides**: Better deployment control, smaller footprint, shared libraries across applications
- **System OCCT allows**: Custom build configurations, optimization for specific use cases, standard library deployment
- **Clean end-user experience**: Bundle OCCT shared libraries with app - no conda requirement for users
- Strong validation and error handling capabilities
- No placeholder code needed - all operations work immediately

**Deployment Strategy**:
- **Development**: Build pythonOCC-core against system OCCT 7.9.0 (ensures production parity from day one)
- **Production**: Bundle OCCT shared libraries (~50-100MB) with application, configure launcher script
- **Fallback only**: Conda available for quick prototyping but NOT for deployment

**Alternatives Considered**:
1. **Bundled conda package only**: Rejected - larger footprint, less deployment control
2. **Build from scratch**: Rejected - would take months/years, require placeholder code during development, violate constitution
3. **CadQuery/Build123d**: Rejected - higher-level wrappers add abstraction layer, prefer direct Open CASCADE access for full control
4. **trimesh**: Rejected - mesh-only library, lacks parametric CAD operations
5. **Direct ctypes/cffi**: Rejected - OCCT's complex C++ API requires sophisticated binding generator

---

## Installation & Dependencies

### Installation Methods

**Two Approaches Supported**:

#### Approach 1: Conda Package (Development/Prototyping)

```bash
conda create --name=cad-dev python=3.11
conda activate cad-dev
conda install -c conda-forge pythonocc-core=7.9.0
```

**Advantages**: Fast setup, automatic dependency management, cross-platform
**Disadvantages**: Bundled OCCT (~100MB), less control, conda dependency

#### Approach 2: System OCCT + Custom pythonOCC Build (Production)

**Step 1 - Install OCCT 7.9.0** (choose one):
- **vcpkg** (recommended): `vcpkg install opencascade`
- **Build from source**: Install to `/opt/occt790` (Linux) or `C:\occt-7.9.0` (Windows)

**Step 2 - Build pythonOCC-core against system OCCT**:
```bash
git clone https://github.com/tpaviot/pythonocc-core.git
cd pythonocc-core
mkdir build && cd build

cmake .. \
  -DOCCT_INCLUDE_DIR=/opt/occt790/include/opencascade \
  -DOCCT_LIBRARY_DIR=/opt/occt790/lib \
  -DCMAKE_BUILD_TYPE=Release \
  -DPYTHONOCC_MESHDS_NUMPY=ON

make -j$(nproc)
sudo make install
```

**Step 3 - Configure library paths**:
```bash
# Linux
sudo ldconfig /opt/occt790/lib
export LD_LIBRARY_PATH=/opt/occt790/lib:$LD_LIBRARY_PATH

# Windows
set PATH=C:\occt-7.9.0\win64\vc14\bin;%PATH%
```

**Advantages**: Full control, dynamic linking, smaller footprint, no conda
**Disadvantages**: Complex build, manual dependency management, strict version matching

**Platform Support**:
- Windows 64-bit ✓
- Linux x64/aarch64 ✓
- macOS x64/ARM64 ✓

**Python Compatibility**: 3.9, 3.10, 3.11, 3.12

**Critical Requirement**: pythonOCC 7.9.0 requires **exactly** OCCT 7.9.0 (strict version matching)

---

## API Patterns

### 1. Creation Operations

#### Extrusion (BRepPrimAPI_MakePrism)

**Usage Pattern**:
```python
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCC.Core.gp import gp_Vec

extrusion_vector = gp_Vec(0, 0, distance)
prism = BRepPrimAPI_MakePrism(base_face, extrusion_vector)
result = prism.Shape()
```

**Implementation Notes**:
- Input: TopoDS_Wire or TopoDS_Face
- Vector defines both direction and distance
- Returns TopoDS_Shape

#### Revolve (BRepPrimAPI_MakeRevol)

**Usage Pattern**:
```python
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeRevol
from OCC.Core.gp import gp_Ax1, gp_Pnt, gp_Dir

axis = gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1))
revol = BRepPrimAPI_MakeRevol(profile_face, axis, angle_radians)
result = revol.Shape()
```

**Implementation Notes**:
- Angle in radians (360° = 2π)
- Axis defined by point and direction

#### Loft (BRepOffsetAPI_ThruSections)

**Usage Pattern**:
```python
from OCC.Core.BRepOffsetAPI import BRepOffsetAPI_ThruSections

loft = BRepOffsetAPI_ThruSections(True, False)  # solid, smooth
for wire in profile_wires:
    loft.AddWire(wire)
loft.Build()
result = loft.Shape()
```

**Implementation Notes**:
- Add wires in sequence
- First parameter: True for solid, False for shell
- Second parameter: False for smooth, True for ruled
- Use CheckCompatibility() for validation

#### Sweep (BRepOffsetAPI_MakePipe)

**Usage Pattern**:
```python
from OCC.Core.BRepOffsetAPI import BRepOffsetAPI_MakePipe

pipe = BRepOffsetAPI_MakePipe(spine_wire, profile_face)
result = pipe.Shape()
```

**Implementation Notes**:
- Spine must have G1 continuity
- Profile orientation matters

#### Primitives (BRepPrimAPI_Make*)

**Usage Patterns**:
```python
from OCC.Core.BRepPrimAPI import (
    BRepPrimAPI_MakeBox,
    BRepPrimAPI_MakeCylinder,
    BRepPrimAPI_MakeSphere,
    BRepPrimAPI_MakeCone
)

box = BRepPrimAPI_MakeBox(width, depth, height).Shape()
cylinder = BRepPrimAPI_MakeCylinder(radius, height).Shape()
sphere = BRepPrimAPI_MakeSphere(center_point, radius).Shape()
cone = BRepPrimAPI_MakeCone(radius1, radius2, height).Shape()
```

**Implementation Notes**:
- All support custom positioning via gp_Ax2
- Always call .Shape() to extract geometry

### 2. Boolean Operations

**Usage Patterns**:
```python
from OCC.Core.BRepAlgoAPI import (
    BRepAlgoAPI_Fuse,   # Union
    BRepAlgoAPI_Cut,    # Subtract
    BRepAlgoAPI_Common  # Intersect
)

# Union
fuse = BRepAlgoAPI_Fuse(shape1, shape2)
result = fuse.Shape()

# Subtract (shape1 - shape2)
cut = BRepAlgoAPI_Cut(shape1, shape2)
cut.RefineEdges()
cut.FuseEdges()
result = cut.Shape()

# Intersect
common = BRepAlgoAPI_Common(shape1, shape2)
result = common.Shape()
```

**Implementation Notes**:
- Call RefineEdges() and FuseEdges() for cleaner results
- Check BuilderCanWork() before operation
- Use ErrorStatus() to diagnose failures
- Always validate results with BRepCheck_Analyzer

### 3. Pattern & Transform Operations

**Linear Pattern**:
```python
from OCC.Core.gp import gp_Trsf, gp_Vec
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform

transform = gp_Trsf()
transform.SetTranslation(gp_Vec(spacing, 0, 0))

shapes = []
for i in range(count):
    tx = BRepBuilderAPI_Transform(base_shape, transform)
    shapes.append(tx.Shape())
```

**Circular Pattern**:
```python
from OCC.Core.gp import gp_Ax1, gp_Trsf

axis = gp_Ax1(center_point, direction)
angle_increment = 2 * math.pi / count

for i in range(count):
    transform = gp_Trsf()
    transform.SetRotation(axis, i * angle_increment)
    # Apply transform...
```

**Mirror**:
```python
from OCC.Core.gp import gp_Ax2, gp_Trsf

mirror_plane = gp_Ax2(point, normal_direction)
transform = gp_Trsf()
transform.SetMirror(mirror_plane)

mirrored = BRepBuilderAPI_Transform(shape, transform)
result = mirrored.Shape()
```

**Implementation Notes**:
- All angles in radians
- gp_Trsf handles all transformations
- Use BRepBuilderAPI_Transform to apply

### 4. Tessellation & STL Export

**Tessellation Pattern**:
```python
from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh

linear_deflection = 0.1  # mm - smaller = finer mesh
angular_deflection = 0.5  # radians

mesh = BRepMesh_IncrementalMesh(shape, linear_deflection, False, angular_deflection)
mesh.Perform()
assert mesh.IsDone()
```

**STL Export Pattern**:
```python
from OCC.Core.StlAPI import StlAPI_Writer

# Mesh first
mesh = BRepMesh_IncrementalMesh(shape, 0.1)
mesh.Perform()

# Write STL
writer = StlAPI_Writer()
writer.SetASCIIMode(False)  # Binary format
writer.Write(shape, filepath)
```

**Implementation Notes**:
- Always mesh before STL export for quality control
- Linear deflection: max distance from surface (smaller = better quality)
- Angular deflection: max angular deviation in radians
- Binary STL is much smaller than ASCII

**Tessellation Quality Parameters**:
- **Default**: linear_deflection=0.1mm, angular_deflection=0.5rad
- **High quality**: linear_deflection=0.01mm, angular_deflection=0.1rad
- **Performance**: linear_deflection=1.0mm, angular_deflection=1.0rad

### 5. Geometric Properties

**Volume & Surface Area**:
```python
from OCC.Core.GProp import GProp_GProps
from OCC.Core.BRepGProp import (
    brepgprop_VolumeProperties,
    brepgprop_SurfaceProperties
)

# Volume properties
props = GProp_GProps()
brepgprop_VolumeProperties(solid, props)

volume = props.Mass()
center_of_mass = props.CentreOfMass()
cog_x, cog_y, cog_z = center_of_mass.Coord()

# Surface area
props = GProp_GProps()
brepgprop_SurfaceProperties(shape, props)
surface_area = props.Mass()
```

**Implementation Notes**:
- props.Mass() returns the computed value (volume, area, or length)
- Center of mass returned as gp_Pnt
- Use brepgprop_VolumeProperties for solids
- Use brepgprop_SurfaceProperties for faces/shells

### 6. Validation & Error Handling

**Shape Validation**:
```python
from OCC.Core.BRepCheck import BRepCheck_Analyzer

analyzer = BRepCheck_Analyzer(shape)
if not analyzer.IsValid():
    raise ValueError("Invalid geometry")
```

**Builder Check Pattern**:
```python
builder = BRepAlgoAPI_Fuse(shape1, shape2)
if not builder.BuilderCanWork():
    raise ValueError("Boolean operation cannot proceed")

builder.Build()
if not builder.IsDone():
    raise RuntimeError("Boolean operation failed")

result = builder.Shape()
```

**Implementation Notes**:
- Always validate complex operation results
- Check IsDone() before calling .Shape()
- Use BRepCheck_Analyzer for topology validation
- Call RefineEdges() and FuseEdges() on boolean results

---

## Integration Strategy

### Data Flow

1. **Input**: User provides operation parameters via CLI
2. **2D to 3D**: Convert existing 2D entities (circles, lines) to Open CASCADE wires/faces
3. **Operation**: Execute Open CASCADE operation (extrude, boolean, etc.)
4. **Storage**: Serialize TopoDS_Shape to database (BRep format or properties)
5. **Export**: Tessellate and export to STL when requested

### Serialization Approach

**Decision**: Store geometric properties + BRep string in database

```python
# Serialize shape to BRep string
from OCC.Core.BRepTools import BRepTools_ShapeSet

shape_set = BRepTools_ShapeSet()
shape_set.Add(shape)
brep_string = shape_set.WriteToString()

# Deserialize from BRep string
shape_set = BRepTools_ShapeSet()
shape_set.ReadFromString(brep_string)
reconstructed_shape = shape_set.Shape(1)
```

**Rationale**: BRep format is Open CASCADE's native format, preserves exact geometry

### Error Handling Strategy

1. **Input Validation**: Check parameters before operation
2. **Pre-operation Check**: Validate input geometry with BRepCheck_Analyzer
3. **Operation Execution**: Wrap in try/except, check IsDone()
4. **Post-operation Validation**: Verify result is valid solid
5. **User Feedback**: Return clear error messages

---

## Performance Considerations

### Tessellation Quality vs Performance

| Use Case | Linear Deflection | Angular Deflection | Triangle Count (cylinder) | Export Time |
|----------|------------------|-------------------|--------------------------|-------------|
| Preview | 1.0mm | 1.0 rad | ~100 | <1s |
| Standard | 0.1mm | 0.5 rad | ~1,000 | 1-2s |
| High Quality | 0.01mm | 0.1 rad | ~10,000 | 2-5s |

**Recommendation**: Use 0.1mm linear deflection as default (meets success criteria: "smooth appearance at standard viewing distances")

### Operation Performance

- Simple operations (extrude, revolve): <0.1s for basic shapes
- Boolean operations: 0.1-1s for simple shapes, 1-5s for complex
- Tessellation: 0.1-2s depending on quality settings
- Target: All operations <5s for solids up to 10,000 faces (success criterion)

---

## Key Implementation Gotchas

1. **Import from OCC.Core**: Always use `OCC.Core.*` not `OCC.*`
2. **Angles in Radians**: All angular parameters
3. **Call .Shape()**: Builders return builder object, must call .Shape()
4. **Validate Results**: Boolean operations can fail silently
5. **Mesh Before STL**: Use BRepMesh_IncrementalMesh for control
6. **G1 Continuity**: Required for sweep operations
7. **No pip Install**: Must use conda

---

## Documentation Sources

- **Local OCCT API Reference**: [occt-api-reference.md](occt-api-reference.md) - Complete API documentation for OCCT 7.9.0 classes used in this project
- [pythonocc-core GitHub](https://github.com/tpaviot/pythonocc-core)
- [pythonocc-demos](https://github.com/tpaviot/pythonocc-demos)
- [Open CASCADE Documentation](https://dev.opencascade.org/doc/overview/html/)
- [OCCT API Reference](https://dev.opencascade.org/doc/refman/html/)
- [Conda Package](https://anaconda.org/conda-forge/pythonocc-core)

---

## Next Steps

Phase 1 will design:
- Data models for geometry entities
- API contracts for each operation type
- Integration with existing CAD CLI and multi-agent controller
- Quickstart guide for development environment setup
