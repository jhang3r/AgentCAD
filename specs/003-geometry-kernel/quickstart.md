# Quickstart: 3D Geometry Kernel Development

**Date**: 2025-11-26
**Feature**: 3D Geometry Kernel
**Purpose**: Developer environment setup and first-time contribution guide

---

## Prerequisites

- Python 3.11 or higher
- Conda package manager
- Git
- 2GB free disk space (for pythonOCC-core and dependencies)

---

## Environment Setup

**Two setup options**: Choose based on your use case.

### Option 1: Production Setup (System OCCT - Recommended)

Uses OCCT as dynamically linked libraries. This is the deployment configuration and should be used for all development to ensure production parity.

#### 1. Install OCCT 7.9.0

**Option A - vcpkg (Recommended)**:
```bash
# Install vcpkg
git clone https://github.com/microsoft/vcpkg.git
./vcpkg/bootstrap-vcpkg.sh  # Linux/Mac
# .\vcpkg\bootstrap-vcpkg.bat  # Windows

# Install OCCT
./vcpkg/vcpkg install opencascade
```

**Option B - Build from Source (Linux)**:
```bash
# Install dependencies
sudo apt-get install libfreetype6-dev libfreeimage-dev \
  libtbb-dev libgl1-mesa-dev rapidjson-dev cmake

# Clone and build OCCT
git clone https://github.com/Open-Cascade-SAS/OCCT.git
cd OCCT && git checkout V7_9_0
mkdir build && cd build

cmake .. \
  -DCMAKE_INSTALL_PREFIX=/opt/occt790 \
  -DBUILD_LIBRARY_TYPE=Shared \
  -DUSE_FREETYPE=ON \
  -DUSE_TBB=ON

make -j$(nproc)
sudo make install
sudo ldconfig /opt/occt790/lib
```

#### 2. Build pythonOCC-core Against System OCCT

```bash
# Install SWIG 4.3.0
# (Download from https://sourceforge.net/projects/swig/files/swig/)

# Clone pythonOCC
git clone https://github.com/tpaviot/pythonocc-core.git
cd pythonocc-core
mkdir build && cd build

# Configure
cmake .. \
  -DOCCT_INCLUDE_DIR=/opt/occt790/include/opencascade \
  -DOCCT_LIBRARY_DIR=/opt/occt790/lib \
  -DCMAKE_BUILD_TYPE=Release \
  -DPYTHONOCC_MESHDS_NUMPY=ON

# Build and install
make -j$(nproc)
sudo make install
```

#### 3. Configure Library Paths

**Linux**:
```bash
# Add to ~/.bashrc
export LD_LIBRARY_PATH=/opt/occt790/lib:$LD_LIBRARY_PATH
```

**Windows**:
```cmd
set PATH=C:\occt-7.9.0\win64\vc14\bin;%PATH%
```

#### 4. Install Project Dependencies

```bash
pip install pytest numpy
```

---

### Option 2: Quick Prototyping (Conda - Fallback Only)

**WARNING**: This bundles OCCT and should ONLY be used for quick prototyping. Production deployment MUST use Option 1.

#### 1. Install Conda

**Windows**: Download [Miniconda](https://docs.conda.io/en/latest/miniconda.html)

**Linux/Mac**:
```bash
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh
```

#### 2. Clone Repository

```bash
git clone <repository-url>
cd multi-agent
git checkout 003-geometry-kernel
```

#### 3. Create Conda Environment

```bash
conda create --name=cad-geo python=3.11
conda activate cad-geo
conda install -c conda-forge pythonocc-core=7.9.0

# Install other dependencies
pip install pytest numpy
```

**Important**: Always `conda activate cad-geo` before working.

**Limitations**: End users would need conda (unacceptable for deployment). Use this ONLY for quick experiments.

---

## Verify Installation (Both Options)

```bash
# Test pythonOCC-core import
python -c "from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox; print('pythonOCC-core OK')"

# Should print: pythonOCC-core OK

# Test dynamic linking (Option 2 only)
ldd $(python -c "import OCC.Core._BRepPrimAPI as m; print(m.__file__)") | grep TKBO
# Should show: libTKBO.so => /opt/occt790/lib/libTKBO.so
```

### 5. Run Existing Tests

```bash
# From repository root
cd multi-agent

# Run all tests
pytest tests/

# Run geometry kernel tests (once implemented)
pytest tests/contract/test_creation_ops_contract.py
pytest tests/integration/test_geometry_workflows.py
```

---

## Project Structure Overview

```
multi-agent/
├── specs/003-geometry-kernel/     # This feature's documentation
│   ├── spec.md                    # Feature specification
│   ├── plan.md                    # Implementation plan (this planning phase)
│   ├── research.md                # pythonOCC-core research
│   ├── data-model.md              # Entity and data models
│   ├── contracts/                 # API contracts
│   └── quickstart.md              # This file
│
├── src/
│   ├── cad_kernel/                # NEW: Geometry kernel wrapper
│   │   ├── geometry_engine.py      # Open CASCADE interface
│   │   ├── creation_ops.py         # Extrude, revolve, loft, sweep
│   │   ├── primitive_ops.py        # Box, cylinder, sphere, cone
│   │   ├── pattern_ops.py          # Linear, circular, mirror
│   │   ├── boolean_ops.py          # Union, subtract, intersect
│   │   └── tessellation.py         # Mesh generation
│   │
│   ├── file_io/
│   │   └── stl_handler.py         # REPLACE placeholder code
│   │
│   ├── agent_interface/
│   │   └── cli.py                 # UPDATE: Add geometry operations
│   │
│   └── multi_agent/
│       └── controller.py          # UPDATE: Route geometry operations
│
└── tests/
    ├── contract/                  # NEW: Operation contract tests
    ├── integration/               # NEW: End-to-end geometry tests
    └── unit/                      # NEW: Geometry calculation tests
```

---

## Development Workflow

### 1. Create a Feature Task

When implementing from `tasks.md`:

1. Check task dependencies (tasks must be completed in order)
2. Create a branch if needed: `git checkout -b task-XXX-description`
3. Mark task as in-progress in tasks.md

### 2. Write Contract Tests First

Before implementing any operation, write contract tests:

```bash
# Create test file
touch tests/contract/test_extrude_contract.py

# Run tests (they should fail initially)
pytest tests/contract/test_extrude_contract.py -v
```

Example contract test:
```python
def test_extrude_valid_input():
    """Contract: Valid extrude parameters return success"""
    result = cli.execute("solid.extrude", {
        "base_entity_id": "ws:circle_1",
        "distance": 50.0,
        "workspace_id": "test_ws"
    })

    assert result["status"] == "success"
    assert "entity_id" in result["data"]
    assert result["data"]["volume"] > 0
```

### 3. Implement Operation

Implement the operation to pass contract tests:

```python
# src/cad_kernel/creation_ops.py
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCC.Core.gp import gp_Vec

def extrude(base_shape, distance, direction=[0, 0, 1]):
    """Extrude 2D shape into 3D solid."""
    vec = gp_Vec(*direction)
    vec.Normalize()
    vec.Multiply(distance)

    prism = BRepPrimAPI_MakePrism(base_shape, vec)
    if not prism.IsDone():
        raise RuntimeError("Extrusion failed")

    return prism.Shape()
```

### 4. Integration Test

Write integration test to verify end-to-end flow:

```python
def test_extrude_cylinder_workflow():
    """Integration: Create circle, extrude, export STL"""
    # Create 2D circle
    circle_id = create_circle(...)

    # Extrude to cylinder
    cylinder_id = extrude(circle_id, distance=50.0)

    # Export to STL
    export_stl([cylinder_id], "test_cylinder.stl")

    # Verify STL file has real geometry
    triangles = read_stl("test_cylinder.stl")
    assert len(triangles) > 0
    assert not all_zeros(triangles)  # NOT placeholder data
```

### 5. Run Tests

```bash
# Run specific test file
pytest tests/contract/test_extrude_contract.py -v

# Run all geometry tests
pytest tests/contract/ tests/integration/ -v

# Run with coverage
pytest --cov=src/cad_kernel tests/
```

### 6. Manual Testing

Test via CLI:

```bash
# Activate conda environment
conda activate cad-geo

# Create workspace
py -m src.agent_interface.cli workspace.create --params '{"workspace_id": "test_ws"}'

# Create 2D circle
py -m src.agent_interface.cli entity.create_circle --params '{
    "center": {"x": 0, "y": 0, "z": 0},
    "radius": 15.0,
    "workspace_id": "test_ws"
}'

# Extrude to cylinder
py -m src.agent_interface.cli solid.extrude --params '{
    "base_entity_id": "test_ws:circle_xxx",
    "distance": 50.0,
    "workspace_id": "test_ws"
}'

# Export to STL
py -m src.agent_interface.cli file.export --params '{
    "file_path": "cylinder.stl",
    "format": "stl",
    "workspace_id": "test_ws"
}'

# Verify STL file
# Open in: https://www.viewstl.com/
```

---

## Common Development Tasks

### Add New Geometry Operation

1. Research Open CASCADE API in `research.md`
2. Add operation to appropriate module (`creation_ops.py`, `boolean_ops.py`, etc.)
3. Write contract test
4. Implement operation
5. Add CLI handler in `cli.py`
6. Add controller routing in `controller.py`
7. Write integration test
8. Update `contracts/*.md` documentation

### Debug Geometry Issues

```python
# Enable validation
from OCC.Core.BRepCheck import BRepCheck_Analyzer

analyzer = BRepCheck_Analyzer(shape)
if not analyzer.IsValid():
    print("Invalid geometry detected")
    # Investigate further...

# Check properties
from OCC.Core.GProp import GProp_GProps
from OCC.Core.BRepGProp import brepgprop_VolumeProperties

props = GProp_GProps()
brepgprop_VolumeProperties(shape, props)
print(f"Volume: {props.Mass()}")
```

### Visualize Geometry (Optional)

For debugging complex geometry:

```python
from OCC.Display.SimpleGui import init_display

display, start_display, add_menu, add_function_to_menu = init_display()
display.DisplayShape(shape, update=True)
start_display()
```

---

## Constitution Compliance Checklist

When implementing any task:

- [ ] **No placeholder code**: All functions fully implemented
- [ ] **No mocks in tests**: Use real pythonOCC objects, real database, real files
- [ ] **Contract tests first**: Write tests before implementation
- [ ] **Validate geometry**: Use BRepCheck_Analyzer for all outputs
- [ ] **Real tessellation**: STL files contain actual geometry
- [ ] **Error handling**: Clear messages for invalid inputs
- [ ] **Performance**: Operations complete in <5s for standard shapes
- [ ] **Documentation**: Update contracts/*.md for any API changes

---

## Troubleshooting

### "No module named 'OCC'"

**Problem**: pythonOCC-core not installed or wrong environment

**Solution**:

**If using conda**:
```bash
conda activate cad-geo
conda install -c conda-forge pythonocc-core
```

**If using system OCCT**:
- Verify pythonOCC build completed: Check for `.so` files in site-packages
- Verify PYTHONPATH includes pythonOCC install directory
- Rebuild pythonOCC-core if needed

### Library Not Found Errors (System OCCT)

**Problem**: `ImportError: libTKBO.so: cannot open shared object file`

**Solution**:
```bash
# Linux: Configure library path
export LD_LIBRARY_PATH=/opt/occt790/lib:$LD_LIBRARY_PATH
sudo ldconfig /opt/occt790/lib

# Verify libraries are found
ldd $(python -c "import OCC; print(OCC.__path__[0])")/_BRepPrimAPI.so
```

**Windows**: Add OCCT bin directory to PATH:
```cmd
set PATH=C:\occt-7.9.0\win64\vc14\bin;%PATH%
```

### Version Mismatch Errors

**Problem**: `Segmentation fault` or crashes on import

**Solution**: Ensure exact version match:
- pythonOCC 7.9.0 requires OCCT 7.9.0
- Check versions:
```bash
# OCCT version
strings /opt/occt790/lib/libTKernel.so | grep "VERSION 7.9"

# pythonOCC version
python -c "import OCC; print(OCC.VERSION)"
```

### Tests Fail with "Entity not found"

**Problem**: Test database not initialized or wrong workspace ID

**Solution**:
```python
# In test setup, create workspace first
def setup_workspace():
    controller = Controller()
    controller.create_workspace("test_ws")
    return "test_ws"
```

### STL File Contains Zeros

**Problem**: Using old placeholder code instead of real tessellation

**Solution**:
- Ensure `stl_handler.py` uses `BRepMesh_IncrementalMesh`
- Check that shape is valid before tessellation
- Verify Open CASCADE shape is not null

### "Boolean operation failed"

**Problem**: Invalid input geometry or incompatible solids

**Solution**:
1. Validate both input solids with BRepCheck_Analyzer
2. Check that solids actually overlap (for intersect/union)
3. Try RefineEdges() on inputs before boolean operation
4. Check for very small features or degenerate geometry

---

## Getting Help

1. **Check documentation first**:
   - `occt-api-reference.md`: Complete OCCT 7.9.0 API reference (local)
   - `research.md`: pythonOCC-core API patterns
   - `contracts/*.md`: API specifications
   - `data-model.md`: Entity definitions

2. **Review existing tests**:
   - Look at passing tests for similar operations
   - Check integration tests for workflow examples

3. **Constitution**: If uncertain about approach, review `.specify/memory/constitution.md`

4. **External resources**:
   - [pythonocc-demos repository](https://github.com/tpaviot/pythonocc-demos)
   - [OCCT official documentation](https://dev.opencascade.org/doc/overview/html/)
   - [OCCT API reference](https://dev.opencascade.org/doc/refman/html/)

---

## Next Steps

After environment setup:

1. Review `spec.md` to understand feature requirements
2. Review `research.md` to learn pythonOCC-core API
3. Review `data-model.md` to understand entity structure
4. Review `contracts/*.md` to understand API contracts
5. Wait for `tasks.md` generation (`/speckit.tasks` command)
6. Start implementing tasks in order

---

**Remember**:

**If using conda**: Always activate environment:
```bash
conda activate cad-geo
```

**If using system OCCT**: Ensure library paths are configured:
```bash
export LD_LIBRARY_PATH=/opt/occt790/lib:$LD_LIBRARY_PATH  # Linux
# Or add to ~/.bashrc for persistence
```

## Deployment Notes

**For Production/Distribution**:
- Use system OCCT with dynamic linking
- Include OCCT shared libraries with application
- Configure library paths in launcher script
- Document OCCT version requirement (7.9.0)

**For Development/Testing**:
- Use conda package for simplicity
- Faster setup, automatic dependency management
