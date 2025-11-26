# Feature Specification: 3D Geometry Kernel

**Feature Branch**: `003-geometry-kernel`
**Created**: 2025-11-26
**Status**: Draft
**Input**: User description: "Implement real 3D geometry kernel using Open CASCADE to replace placeholder code"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Export 3D Models to Viewable Files (Priority: P1)

As a CAD user, I want to export 3D solid models to STL format so that I can view and validate the geometry in external 3D viewers, share designs with manufacturers, and prepare models for 3D printing.

**Why this priority**: This is the most critical functionality because it provides immediate, visible proof that the system works. Users cannot validate their designs or share them without working export. The current system generates empty files, making it completely unusable for any real-world application.

**Independent Test**: Can be fully tested by creating a simple 3D solid (e.g., extruded cylinder), exporting to STL, and opening the file in any STL viewer (online or desktop) to verify actual geometry is visible.

**Acceptance Scenarios**:

1. **Given** a 3D solid exists in the workspace (e.g., extruded cylinder), **When** user exports to STL format, **Then** the exported file contains actual triangle mesh data representing the solid's geometry
2. **Given** an STL file exported from the system, **When** user opens it in an external STL viewer, **Then** the 3D geometry is visible and matches the original solid's dimensions
3. **Given** a complex 3D solid with curved surfaces, **When** user exports to STL, **Then** the mesh accurately represents the curved surfaces with appropriate tessellation density

---

### User Story 2 - Create 3D Solids Using All Creation Operations (Priority: P2)

As a CAD user, I want to create 3D solids using all available creation operations (extrude, revolve, loft, sweep, patterns, mirror, etc.) so that I can build any type of complex 3D model from 2D sketches and existing geometry.

**Why this priority**: Creation operations are the foundation of CAD modeling. Users need the full suite of creation tools to build real-world parts. These operations come after export because we need to verify the geometry kernel can handle and tessellate geometry first, but they're essential for any practical CAD work. Grouping all creation operations together ensures users have complete modeling capabilities in one deliverable slice.

**Independent Test**: Can be fully tested by creating different 2D shapes and applying each operation type, then verifying the resulting 3D solids have correct geometric properties (volume, dimensions, topology).

**Acceptance Scenarios**:

1. **Given** a 2D circle with radius 15mm exists, **When** user extrudes it 50mm, **Then** a 3D cylinder is created with volume π×15²×50 ≈ 35,343 mm³
2. **Given** a 2D profile exists, **When** user revolves it 360° around an axis, **Then** a 3D solid of revolution is created with correct rotational symmetry
3. **Given** two or more 2D profiles at different heights exist, **When** user creates a loft between them, **Then** a 3D solid is created smoothly transitioning between the profiles
4. **Given** a 2D profile and a path curve exist, **When** user sweeps the profile along the path, **Then** a 3D solid is created following the path
5. **Given** a 3D solid exists, **When** user creates a linear or circular pattern, **Then** multiple copies of the solid are created at specified intervals
6. **Given** a 3D solid exists, **When** user applies mirror operation across a plane, **Then** a mirrored copy of the solid is created
7. **Given** primitive parameters (radius, height, dimensions), **When** user creates primitive shapes (cylinders, boxes, spheres, cones), **Then** solids with exact specified dimensions are created

---

### User Story 3 - Combine Solids with Boolean Operations (Priority: P3)

As a CAD user, I want to combine or subtract 3D solids so that I can create complex shapes through addition, subtraction, and intersection of simple primitives.

**Why this priority**: Boolean operations enable advanced modeling but are not essential for basic geometry creation and export. Users can create useful models with just extrusion and export. This adds significant value but can be implemented after core functionality is proven.

**Independent Test**: Can be fully tested by creating two overlapping cylinders, performing a union operation, and verifying the result is a single merged solid.

**Acceptance Scenarios**:

1. **Given** two overlapping 3D solids, **When** user performs a union operation, **Then** a single solid is created representing the combined volume
2. **Given** a large solid and a smaller solid intersecting it, **When** user performs a subtraction operation, **Then** the smaller solid's volume is removed from the larger solid
3. **Given** two intersecting solids, **When** user performs an intersection operation, **Then** a new solid is created representing only the overlapping volume

---

### Edge Cases

- What happens when exporting a very complex solid with thousands of faces (performance and file size)?
- How does the system handle degenerate geometry (zero-thickness surfaces, self-intersecting shapes)?
- What happens when boolean operations result in invalid geometry (e.g., subtracting a larger solid from a smaller one)?
- How does the system tessellate curved surfaces with extreme curvature or very small features?
- What happens when exporting solids with multiple disconnected components?
- How does the system handle loft operations between incompatible profiles (different numbers of vertices)?
- What happens when sweep paths are self-intersecting or have zero radius curves?
- How does the system handle revolve operations with profiles that intersect the axis of rotation?
- What happens when pattern operations create overlapping geometry?
- How does the system handle mirror operations on asymmetric solids with specific orientations?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST generate actual 3D triangle mesh data when exporting solids to STL format
- **FR-002**: System MUST accurately tessellate curved surfaces (circles, spheres, fillets) into triangle meshes
- **FR-003**: Exported STL files MUST be readable by standard 3D viewing software (e.g., MeshLab, FreeCAD, online STL viewers)
- **FR-004**: System MUST calculate and store correct geometric properties for 3D solids (volume, surface area, center of mass)
- **FR-005**: System MUST support extrusion of 2D shapes (circles, rectangles, polygons) into 3D solids with specified distance
- **FR-006**: System MUST support revolve operation to create 3D solids by rotating 2D profiles around an axis
- **FR-007**: System MUST support loft operation to create 3D solids by blending between multiple 2D profiles
- **FR-008**: System MUST support sweep operation to create 3D solids by moving 2D profiles along a path
- **FR-009**: System MUST support creation of primitive solids (boxes, cylinders, spheres, cones) with specified dimensions
- **FR-010**: System MUST support linear pattern operation to create multiple copies of solids along a direction
- **FR-011**: System MUST support circular pattern operation to create multiple copies of solids around an axis
- **FR-012**: System MUST support mirror operation to create mirrored copies of solids across a plane
- **FR-013**: System MUST preserve geometric accuracy when converting from parametric representation to triangle mesh
- **FR-014**: System MUST support boolean union operations (combining two solids into one)
- **FR-015**: System MUST support boolean subtraction operations (removing one solid's volume from another)
- **FR-016**: System MUST support boolean intersection operations (creating solid from overlapping volume)
- **FR-017**: System MUST validate all geometric operations and provide clear error messages for invalid inputs
- **FR-018**: System MUST handle topology correctly (faces, edges, vertices) for all 3D solids
- **FR-019**: System MUST maintain geometric consistency across multiple operations on the same solid

### Key Entities

- **3D Solid**: Represents a closed, manifold 3D volume with defined faces, edges, and vertices. Has calculable volume, surface area, and center of mass.
- **Triangle Mesh**: Represents tessellated surface of a solid as collection of triangles. Each triangle has 3 vertices and a normal vector.
- **Creation Operation**: Operations that generate new 3D solids from 2D geometry or parameters (extrude, revolve, loft, sweep, primitives).
- **Pattern Operation**: Operations that create multiple copies of solids (linear pattern, circular pattern, mirror).
- **Boolean Operation**: Geometric operation that combines or modifies solids (union, subtraction, intersection).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Exported STL files contain non-zero triangle data and are viewable in external 3D software within 5 seconds of export
- **SC-002**: Geometric properties (volume, surface area) calculated by the system match mathematical expectations within 0.1% tolerance
- **SC-003**: Users can create a 3D model using any creation operation and export it for viewing externally in under 2 minutes
- **SC-004**: Tessellation of curved surfaces produces smooth visual appearance with no visible faceting at standard viewing distances
- **SC-005**: Boolean operations complete without errors for valid geometric inputs 100% of the time
- **SC-006**: System handles solids with up to 10,000 faces without performance degradation (operations complete in under 5 seconds)
- **SC-007**: 95% of exported STL files open successfully in at least 3 different external viewers (online and desktop)
- **SC-008**: All created solids have dimensions that match user-specified parameters within 0.01mm tolerance
- **SC-009**: Revolve operations create solids with correct rotational symmetry (360° revolve creates closed solid)
- **SC-010**: Pattern operations create the exact specified number of copies with correct spacing

## Assumptions

- Users will primarily export to STL format initially (other formats like STEP can be added later)
- Standard tessellation tolerance (0.1mm linear deflection) is acceptable for most use cases
- Boolean operations will primarily be used on relatively simple solids (not extremely complex multi-thousand-face models)
- Users have access to standard STL viewing software or online viewers
- The geometry kernel library (Open CASCADE) is available and can be integrated as a dependency

## Dependencies

- Existing CAD agent interface must be functional
- File I/O system must support writing binary STL format
- Multi-agent controller must be able to invoke geometry operations
- Database must store solid geometric properties and topology
