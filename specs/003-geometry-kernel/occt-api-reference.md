# Open CASCADE Technology API Reference

**Version**: OCCT 7.9.0
**Date**: 2025-11-26
**Purpose**: Quick reference for OCCT classes used in geometry kernel implementation
**Source**: https://dev.opencascade.org/

---

## Table of Contents

1. [Overview](#overview)
2. [Core Concepts](#core-concepts)
3. [Primitive Creation](#primitive-creation)
4. [Sweeping Operations](#sweeping-operations)
5. [Boolean Operations](#boolean-operations)
6. [Tessellation](#tessellation)
7. [Geometric Properties](#geometric-properties)
8. [Shape Validation](#shape-validation)
9. [Data Exchange](#data-exchange)

---

## Overview

Open CASCADE Technology (OCCT) provides comprehensive modeling algorithms for geometric and topological operations. The system is organized into modules:

- **Modeling Data**: BRep structures for 3D shape definition
- **Modeling Algorithms**: High-level design operations and mathematical support
- **Data Exchange**: Interoperability with external CAD systems

### Key Architecture Principles

- **Modularity**: Packages grouped into toolkits and modules
- **BRep Representation**: Shapes combine topological descriptions with geometric information
- **Reference Semantics**: TopoDS_TShape manipulated by reference, TopoDS_Shape by value
- **Topology Hierarchy**: VERTEX → EDGE → WIRE → FACE → SHELL → SOLID → COMPSOLID → COMPOUND

---

## Core Concepts

### TopoDS Shapes

**TopoDS_TShape**: Underlying shape definition in reference frame, contains geometric domain information

**TopoDS_Shape**: Reference to a TShape with orientation and local coordinate positioning

**Eight Topological Types** (ordered by complexity):
1. COMPOUND - Collection of shapes
2. COMPSOLID - Composite solid
3. SOLID - Closed 3D volume
4. SHELL - Surface boundary
5. FACE - Bounded surface
6. WIRE - Connected edges
7. EDGE - Bounded curve
8. VERTEX - Point in 3D space

### Shape Orientation

- **FORWARD**: Interior is default region
- **REVERSED**: Interior is complementary
- **INTERNAL**: Interior includes both regions
- **EXTERNAL**: Boundary lies outside material

### BRep Representation

Combines topological descriptions with geometric information. Managed through:
- **TopLoc**: Coordinate systems and transformations
- **TopExp_Explorer**: Traverse topological structures
- **TopTools**: Collections for managing shape sets

### Transformation Rules

Standard operations elevate shape dimensions:
- Vertex → Edge (via extrusion/revolution)
- Edge → Face (via extrusion/revolution)
- Wire → Shell (via extrusion/revolution)
- Face → Solid (via extrusion/revolution)
- Shell → CompSolid (via extrusion/revolution)

---

## Primitive Creation

### BRepPrimAPI_MakeBox

**Purpose**: Create rectangular box primitives

**Usage**:
```cpp
BRepPrimAPI_MakeBox(width, depth, height)
BRepPrimAPI_MakeBox(gp_Pnt point1, gp_Pnt point2)
BRepPrimAPI_MakeBox(gp_Ax2 axes, width, depth, height)
```

**Python Example**:
```python
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox

box = BRepPrimAPI_MakeBox(100.0, 50.0, 30.0)
shape = box.Shape()
```

### BRepPrimAPI_MakeCylinder

**Purpose**: Create cylindrical primitives

**Usage**:
```cpp
BRepPrimAPI_MakeCylinder(radius, height)
BRepPrimAPI_MakeCylinder(gp_Ax2 axes, radius, height)
BRepPrimAPI_MakeCylinder(radius, height, angle)  // Partial cylinder
```

**Python Example**:
```python
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeCylinder

cylinder = BRepPrimAPI_MakeCylinder(15.0, 50.0)
shape = cylinder.Shape()
```

### BRepPrimAPI_MakeSphere

**Purpose**: Create spherical primitives

**Usage**:
```cpp
BRepPrimAPI_MakeSphere(radius)
BRepPrimAPI_MakeSphere(gp_Pnt center, radius)
BRepPrimAPI_MakeSphere(radius, angle)  // Partial sphere
```

**Python Example**:
```python
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeSphere

sphere = BRepPrimAPI_MakeSphere(20.0)
shape = sphere.Shape()
```

### BRepPrimAPI_MakeCone

**Purpose**: Create conical primitives

**Usage**:
```cpp
BRepPrimAPI_MakeCone(radius1, radius2, height)
BRepPrimAPI_MakeCone(gp_Ax2 axes, radius1, radius2, height)
```

**Python Example**:
```python
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeCone

cone = BRepPrimAPI_MakeCone(10.0, 5.0, 30.0)  # radius1, radius2, height
shape = cone.Shape()
```

---

## Sweeping Operations

### BRepPrimAPI_MakePrism (Extrusion)

**Purpose**: Create 3D shapes by sweeping a 2D profile along a linear path

**Constructors**:

1. **Vector-Based Prism** (Finite):
```cpp
BRepPrimAPI_MakePrism(const TopoDS_Shape &S, const gp_Vec &V,
                      const Standard_Boolean Copy = Standard_False,
                      const Standard_Boolean Canonize = Standard_True)
```

2. **Direction-Based Prism** (Infinite/Semi-Infinite):
```cpp
BRepPrimAPI_MakePrism(const TopoDS_Shape &S, const gp_Dir &D,
                      const Standard_Boolean Inf = Standard_True,
                      const Standard_Boolean Copy = Standard_False,
                      const Standard_Boolean Canonize = Standard_True)
```

**Parameters**:
- `S`: Base shape to extrude
- `V`: Extrusion vector (direction and distance)
- `D`: Extrusion direction only
- `Copy`: Whether to duplicate base shape
- `Canonize`: Attempt to simplify generated surfaces
- `Inf`: Create infinite (true) or semi-infinite (false) prism

**Key Methods**:
- `Build()`: Construct the resulting shape
- `FirstShape()`: Returns bottom face
- `LastShape()`: Returns top face
- `Generated(S)`: Returns shapes generated from input
- `IsDeleted(S)`: Check if shape was removed

**Python Example**:
```python
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCC.Core.gp import gp_Vec

# Extrude a face along vector (0, 0, 50)
extrusion_vector = gp_Vec(0, 0, 50.0)
prism = BRepPrimAPI_MakePrism(base_face, extrusion_vector)
solid = prism.Shape()
```

**Transformation Rules**:
- Vertex → Edge
- Edge → Face
- Wire → Shell
- Face → Solid
- Shell → CompSolid

### BRepPrimAPI_MakeRevol (Revolution)

**Purpose**: Create revolved sweep topologies by rotating shapes around an axis

**Constructors**:

1. **With Angle**:
```cpp
BRepPrimAPI_MakeRevol(const TopoDS_Shape &S, const gp_Ax1 &A,
                      const Standard_Real D,
                      const Standard_Boolean Copy = Standard_False)
```

2. **Full Revolution** (2π radians):
```cpp
BRepPrimAPI_MakeRevol(const TopoDS_Shape &S, const gp_Ax1 &A,
                      const Standard_Boolean Copy = Standard_False)
```

**Parameters**:
- `S`: Base shape to revolve
- `A`: Axis of rotation (gp_Ax1: point + direction)
- `D`: Rotation angle in radians
- `Copy`: Whether to duplicate base shape

**Key Methods**:
- `Build()`: Construct swept shape
- `FirstShape()` / `LastShape()`: Retrieve initial and final shapes
- `Generated()`: Returns created shapes
- `HasDegenerated()` / `Degenerated()`: Detect degenerated edges

**Python Example**:
```python
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeRevol
from OCC.Core.gp import gp_Ax1, gp_Pnt, gp_Dir
import math

# Revolve around Z-axis
axis = gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1))
angle = math.pi * 2  # Full 360° revolution
revol = BRepPrimAPI_MakeRevol(profile_face, axis, angle)
solid = revol.Shape()
```

### BRepOffsetAPI_ThruSections (Loft)

**Purpose**: Create 3D solids by blending between multiple 2D profiles

**Constructor**:
```cpp
BRepOffsetAPI_ThruSections(Standard_Boolean isSolid,
                           Standard_Boolean ruled = Standard_False,
                           Standard_Real pres3d = 1.0e-06)
```

**Parameters**:
- `isSolid`: True for solid, False for shell
- `ruled`: False for smooth, True for ruled surface
- `pres3d`: 3D precision tolerance

**Key Methods**:
- `AddWire(TopoDS_Wire)`: Add profile in sequence
- `CheckCompatibility(Standard_Boolean)`: Enable/disable profile compatibility checking
- `Build()`: Construct lofted shape
- `FirstShape()` / `LastShape()`: Retrieve end profiles
- `Generated()`: Get generated surfaces

**Python Example**:
```python
from OCC.Core.BRepOffsetAPI import BRepOffsetAPI_ThruSections

# Create smooth solid loft
loft = BRepOffsetAPI_ThruSections(True, False)  # solid, smooth
loft.AddWire(profile_wire_1)
loft.AddWire(profile_wire_2)
loft.AddWire(profile_wire_3)
loft.Build()
solid = loft.Shape()
```

### BRepOffsetAPI_MakePipe (Sweep)

**Purpose**: Create 3D solids by sweeping profiles along a path

**Constructor**:
```cpp
BRepOffsetAPI_MakePipe(const TopoDS_Wire &Spine,
                       const TopoDS_Shape &Profile)
```

**Parameters**:
- `Spine`: Path wire (must have G1 continuity)
- `Profile`: Shape to sweep along path

**Key Methods**:
- `Build()`: Construct swept shape
- `FirstShape()` / `LastShape()`: Retrieve end shapes
- `Generated()`: Get generated surfaces

**Python Example**:
```python
from OCC.Core.BRepOffsetAPI import BRepOffsetAPI_MakePipe

# Sweep profile along spine curve
pipe = BRepOffsetAPI_MakePipe(spine_wire, profile_face)
solid = pipe.Shape()
```

**Important**: Spine must have G1 continuity (no sharp corners)

---

## Boolean Operations

### Overview

Boolean operations combine or modify solids through union, subtraction, and intersection. All boolean classes inherit from `BRepAlgoAPI_BooleanOperation`.

**Common Workflow**:
1. Create operation instance
2. Set arguments and tools
3. Call `Build()` to execute
4. Retrieve results via `Shape()`
5. Check for errors with `HasErrors()`

**Post-Processing Recommendations**:
- Call `RefineEdges()` to merge collinear edges
- Call `FuseEdges()` to fuse coincident edges
- Use `SimplifyResult()` for cleaner geometry

### BRepAlgoAPI_Fuse (Union)

**Purpose**: Boolean union operation - combine multiple shapes into one

**Constructors**:

1. **Empty Constructor**:
```cpp
BRepAlgoAPI_Fuse()
```

2. **Two-Shape Constructor**:
```cpp
BRepAlgoAPI_Fuse(const TopoDS_Shape &S1, const TopoDS_Shape &S2,
                 const Message_ProgressRange &theRange)
```

3. **With PaveFiller**:
```cpp
BRepAlgoAPI_Fuse(const BOPAlgo_PaveFiller &PF)
```

**Key Methods**:
- `Shape()`: Returns computed result
- `Shape1()`, `Shape2()`: Access input shapes
- `SetTools(TopTools_ListOfShape)`: Define tool shapes
- `Build()`: Execute the operation
- `Modified(TopoDS_Shape)`: List shapes generated from input
- `Generated(TopoDS_Shape)`: Show newly created geometry
- `IsDeleted(TopoDS_Shape)`: Check if shape was removed
- `HasErrors()`, `HasWarnings()`: Status checking
- `DumpErrors()`, `DumpWarnings()`: Diagnostic output
- `SetFuzzyValue()`: Set tolerance
- `SetRunParallel()`: Enable parallel processing
- `SimplifyResult()`: Post-process result

**Python Example**:
```python
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Fuse

# Union two solids
fuse = BRepAlgoAPI_Fuse(solid1, solid2)
fuse.Build()
if fuse.HasErrors():
    print("Fuse operation failed")
else:
    result = fuse.Shape()
```

### BRepAlgoAPI_Cut (Subtract)

**Purpose**: Boolean subtraction - remove one solid from another (A - B)

**Usage**: Similar to BRepAlgoAPI_Fuse

**Python Example**:
```python
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Cut

# Subtract solid2 from solid1
cut = BRepAlgoAPI_Cut(solid1, solid2)
cut.RefineEdges()  # Clean up edges
cut.FuseEdges()
cut.Build()
result = cut.Shape()
```

**Note**: Order matters - result is shape1 minus shape2

### BRepAlgoAPI_Common (Intersection)

**Purpose**: Boolean intersection - create solid from overlapping volume only (A ∩ B)

**Usage**: Similar to BRepAlgoAPI_Fuse

**Python Example**:
```python
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Common

# Intersect two solids
common = BRepAlgoAPI_Common(solid1, solid2)
common.Build()
result = common.Shape()
```

**Error Handling Pattern** (applies to all boolean ops):
```python
builder = BRepAlgoAPI_Fuse(shape1, shape2)
if not builder.BuilderCanWork():
    raise ValueError("Boolean operation cannot proceed")

builder.Build()
if not builder.IsDone():
    raise RuntimeError("Boolean operation failed")

result = builder.Shape()
```

---

## Tessellation

### BRepMesh_IncrementalMesh

**Purpose**: Build triangle mesh of shapes for visualization and export

**Constructors**:

1. **Default**:
```cpp
BRepMesh_IncrementalMesh()
```

2. **Primary Constructor**:
```cpp
BRepMesh_IncrementalMesh(const TopoDS_Shape &theShape,
                         const Standard_Real theLinDeflection,
                         const Standard_Boolean isRelative = Standard_False,
                         const Standard_Real theAngDeflection = 0.5,
                         const Standard_Boolean isInParallel = Standard_False)
```

3. **With Parameters**:
```cpp
BRepMesh_IncrementalMesh(const TopoDS_Shape &theShape,
                         const IMeshTools_Parameters &theParameters,
                         const Message_ProgressRange &theRange)
```

**Parameters**:
- `theShape`: Shape to tessellate
- `theLinDeflection`: Maximum distance from surface (mm) - controls mesh density
- `isRelative`: Whether deflection is relative to shape size
- `theAngDeflection`: Maximum angular deviation (radians) - default 0.5
- `isInParallel`: Enable parallel processing

**Key Methods**:
- `Perform(theRange)`: Execute triangulation
- `Parameters()`: Retrieve parameter configuration
- `ChangeParameters()`: Modify meshing parameters
- `IsModified()`: Check modification status
- `GetStatusFlags()`: Returns processing status
- `IsParallelDefault()`: Query multi-threading setting
- `SetParallelDefault(isInParallel)`: Configure parallel execution

**Python Example**:
```python
from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh

# Tessellate with standard quality
linear_deflection = 0.1  # mm
angular_deflection = 0.5  # radians

mesh = BRepMesh_IncrementalMesh(shape, linear_deflection, False, angular_deflection)
mesh.Perform()
assert mesh.IsDone()
```

**Quality Presets** (recommended):
- **Preview**: linear=1.0mm, angular=1.0rad (~100 triangles for simple shapes)
- **Standard**: linear=0.1mm, angular=0.5rad (~1,000 triangles)
- **High Quality**: linear=0.01mm, angular=0.1rad (~10,000 triangles)

---

## Geometric Properties

### GProp_GProps

**Purpose**: Compute geometric properties (volume, surface area, center of mass)

**Usage with BRepGProp**:

**Volume Properties**:
```python
from OCC.Core.GProp import GProp_GProps
from OCC.Core.BRepGProp import brepgprop_VolumeProperties

props = GProp_GProps()
brepgprop_VolumeProperties(solid, props)

volume = props.Mass()
center_of_mass = props.CentreOfMass()
cog_x, cog_y, cog_z = center_of_mass.Coord()
```

**Surface Area**:
```python
from OCC.Core.GProp import GProp_GProps
from OCC.Core.BRepGProp import brepgprop_SurfaceProperties

props = GProp_GProps()
brepgprop_SurfaceProperties(shape, props)
surface_area = props.Mass()
```

**Key Methods**:
- `Mass()`: Returns computed value (volume, area, or length depending on operation)
- `CentreOfMass()`: Returns center of mass as gp_Pnt
- `MatrixOfInertia()`: Returns inertia matrix

**Note**: `props.Mass()` returns the primary geometric property:
- For volume calculations: volume in cubic units
- For surface calculations: area in square units
- For linear calculations: length in linear units

---

## Shape Validation

### BRepCheck_Analyzer

**Purpose**: Validate topology and geometry of shapes

**Constructor**:
```cpp
BRepCheck_Analyzer(const TopoDS_Shape &S,
                   const Standard_Boolean GeomControls = Standard_True)
```

**Parameters**:
- `S`: Shape to validate
- `GeomControls`: Enable geometric validation (beyond topology)

**Key Methods**:
- `IsValid()`: Returns true if shape is valid
- `Result()`: Get detailed validation results

**Python Example**:
```python
from OCC.Core.BRepCheck import BRepCheck_Analyzer

analyzer = BRepCheck_Analyzer(shape)
if not analyzer.IsValid():
    raise ValueError("Invalid geometry detected")
```

**Validation Checks**:
- Topology correctness (vertices, edges, faces)
- Manifold properties (closed, orientable)
- Geometric consistency
- Edge continuity
- Face bounds

**When to Validate**:
- Before boolean operations (pre-validation)
- After boolean operations (post-validation)
- Before tessellation
- Before STL export

---

## Data Exchange

### StlAPI_Writer (STL Export)

**Purpose**: Export shapes to STL format (binary or ASCII)

**Constructor**:
```cpp
StlAPI_Writer()
```

**Key Methods**:
- `SetASCIIMode(Standard_Boolean)`: True for ASCII, False for binary (default)
- `Write(const TopoDS_Shape &, const Standard_CString)`: Write shape to file

**Python Example**:
```python
from OCC.Core.StlAPI import StlAPI_Writer
from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh

# Mesh first
mesh = BRepMesh_IncrementalMesh(shape, 0.1)
mesh.Perform()

# Write binary STL
writer = StlAPI_Writer()
writer.SetASCIIMode(False)  # Binary format
writer.Write(shape, "output.stl")
```

**Binary STL Format**:
```
Header: 80 bytes (ASCII text, often ignored)
Triangle count: 4 bytes (unsigned int, little-endian)
For each triangle (50 bytes):
  - Normal vector: 12 bytes (3 floats)
  - Vertex 1: 12 bytes (3 floats)
  - Vertex 2: 12 bytes (3 floats)
  - Vertex 3: 12 bytes (3 floats)
  - Attribute: 2 bytes (usually 0)
```

**Best Practices**:
1. Always tessellate before export for quality control
2. Use binary format (much smaller than ASCII)
3. Validate shape before tessellation
4. Choose appropriate linear/angular deflection for use case

### BRepTools (BRep Serialization)

**Purpose**: Serialize/deserialize Open CASCADE shapes to BRep format

**Serialization**:
```python
from OCC.Core.BRepTools import BRepTools_ShapeSet

shape_set = BRepTools_ShapeSet()
shape_set.Add(shape)
brep_string = shape_set.WriteToString()
```

**Deserialization**:
```python
shape_set = BRepTools_ShapeSet()
shape_set.ReadFromString(brep_string)
reconstructed_shape = shape_set.Shape(1)  # Index 1 for first shape
```

**Use Cases**:
- Database storage of exact geometry
- Preserving parametric representation
- Inter-application communication

---

## Common Patterns

### Error Handling

**Always check operation completion**:
```python
builder = BRepPrimAPI_MakePrism(base, vector)
builder.Build()
if not builder.IsDone():
    raise RuntimeError("Prism operation failed")
shape = builder.Shape()
```

**Validate inputs before operations**:
```python
from OCC.Core.BRepCheck import BRepCheck_Analyzer

analyzer = BRepCheck_Analyzer(input_shape)
if not analyzer.IsValid():
    raise ValueError("Invalid input geometry")
```

### Transformation Pattern

**Using gp_Trsf for transformations**:
```python
from OCC.Core.gp import gp_Trsf, gp_Vec
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform

# Translation
transform = gp_Trsf()
transform.SetTranslation(gp_Vec(10.0, 0, 0))
transformed_builder = BRepBuilderAPI_Transform(shape, transform)
result = transformed_builder.Shape()
```

### Shape Exploration

**Traverse topology**:
```python
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopAbs import TopAbs_FACE

# Iterate through all faces
explorer = TopExp_Explorer(shape, TopAbs_FACE)
while explorer.More():
    face = explorer.Current()
    # Process face...
    explorer.Next()
```

---

## Performance Tips

1. **Tessellation Quality**: Lower deflection = higher quality but slower
2. **Parallel Processing**: Enable for complex shapes: `SetRunParallel(True)`
3. **Edge Refinement**: Always apply after boolean ops for cleaner results
4. **Shape Validation**: Skip for trusted geometry to save time
5. **BRep Caching**: Store serialized shapes to avoid recalculation
6. **Fuzzy Tolerance**: Increase for complex boolean ops if strict precision not needed

---

## Critical Implementation Notes

1. **Import from OCC.Core**: Always use `OCC.Core.*` not `OCC.*`
2. **Angles in Radians**: All angular parameters use radians
3. **Call .Shape()**: Builders return builder object, must call `.Shape()` to extract geometry
4. **Validate Results**: Boolean operations can fail silently - always check `IsDone()`
5. **Mesh Before STL**: Use BRepMesh_IncrementalMesh for quality control before export
6. **G1 Continuity**: Required for sweep operations (no sharp corners in spine)
7. **Version Matching**: pythonOCC 7.9.0 requires exactly OCCT 7.9.0

---

## Resources

- **OCCT Documentation**: https://dev.opencascade.org/doc/overview/html/
- **API Reference**: https://dev.opencascade.org/doc/refman/html/
- **pythonOCC GitHub**: https://github.com/tpaviot/pythonocc-core
- **pythonOCC Demos**: https://github.com/tpaviot/pythonocc-demos
- **Conda Package**: https://anaconda.org/conda-forge/pythonocc-core

---

**Last Updated**: 2025-11-26
**OCCT Version**: 7.9.0
**pythonOCC Version**: 7.9.0
