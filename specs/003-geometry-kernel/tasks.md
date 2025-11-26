# Tasks: 3D Geometry Kernel

**Input**: Design documents from `/specs/003-geometry-kernel/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, occt-api-reference.md

**Total Tasks**: 138 (8 setup, 17 foundational, 21 US1, 52 US2, 28 US3, 12 polish)
**MVP Scope**: 46 tasks (Phases 1-3)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

**IMPORTANT**: System OCCT with dynamic linking is now required (not conda). See quickstart.md Option 1.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create src/cad_kernel/ directory structure with __init__.py
- [x] T002 [P] Create tests/contract/ directory for geometry operation tests
- [x] T003 [P] Create tests/integration/ directory for end-to-end geometry tests
- [x] T004 [P] Create tests/unit/ directory for geometry calculation tests
- [ ] T005 Install OCCT 7.9.0 via vcpkg or build from source per quickstart.md Option 1
- [ ] T006 Build pythonOCC-core 7.9.0 against system OCCT per quickstart.md Option 1
- [ ] T007 Configure library paths (LD_LIBRARY_PATH or PATH) per quickstart.md Option 1
- [ ] T008 Verify pythonOCC installation by running test import in quickstart.md

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T009 Create database migration script for 6 new tables in src/database/migrations/003_geometry_kernel.sql
- [ ] T010 Add geometry_shapes table per data-model.md schema
- [ ] T011 Add solid_properties table per data-model.md schema
- [ ] T012 Add creation_operations table per data-model.md schema
- [ ] T013 Add boolean_operations table per data-model.md schema
- [ ] T014 Add tessellation_configs table per data-model.md schema
- [ ] T015 Add mesh_data table per data-model.md schema
- [ ] T016 Add shape_id column to existing entities table
- [ ] T017 Run database migration and verify all tables created
- [ ] T018 [P] Populate tessellation_configs with 3 presets (preview, standard, high_quality) per data-model.md
- [ ] T019 Create src/cad_kernel/geometry_engine.py with GeometryShape class (from_shape, to_shape, validate methods)
- [ ] T020 Implement BRep serialization in GeometryShape.from_shape() using BRepTools_ShapeSet
- [ ] T021 Implement BRep deserialization in GeometryShape.to_shape() using BRepTools_ShapeSet
- [ ] T022 [P] Create src/cad_kernel/properties.py with SolidProperties class
- [ ] T023 Implement compute_from_shape() in SolidProperties using GProp_GProps and BRepGProp per research.md
- [ ] T024 Implement shape validation using BRepCheck_Analyzer in GeometryShape.validate()
- [ ] T025 Create error handling utilities in src/cad_kernel/exceptions.py (InvalidGeometryError, OperationFailedError, TessellationError)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Export 3D Models to Viewable Files (Priority: P1) 🎯 MVP

**Goal**: Replace placeholder STL export with real tessellation so users can view actual 3D geometry in external viewers

**Independent Test**: Create simple extruded cylinder, export to STL, open in online STL viewer to verify real geometry is visible

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T026 [P] [US1] Contract test for file.export operation in tests/contract/test_export_contract.py per contracts/export-ops.md
- [ ] T027 [P] [US1] Test valid solid exports to STL with non-zero triangle data
- [ ] T028 [P] [US1] Test tessellation quality presets (preview, standard, high_quality) produce different triangle counts
- [ ] T029 [P] [US1] Test multi-solid export to single STL file
- [ ] T030 [P] [US1] Test error handling for invalid geometry and file write failures
- [ ] T031 [US1] Integration test for create-export-verify workflow in tests/integration/test_stl_export_real_files.py
- [ ] T032 [US1] Test exported STL file contains actual geometry data (not all zeros)
- [ ] T033 [US1] Test STL file opens in external viewer (manual verification step documented)

### Implementation for User Story 1

- [ ] T034 [US1] Create src/cad_kernel/tessellation.py with TessellationConfig class and quality presets
- [ ] T035 [US1] Implement mesh generation using BRepMesh_IncrementalMesh in tessellation.py per research.md line 272
- [ ] T036 [US1] Implement triangle extraction from meshed shape in tessellation.py
- [ ] T037 [US1] REPLACE placeholder code in src/file_io/stl_handler.py with real tessellation using StlAPI_Writer per research.md line 283
- [ ] T038 [US1] Remove all placeholder comments and dummy triangle generation from stl_handler.py
- [ ] T039 [US1] Implement binary STL export (default) and ASCII STL export (optional) per contracts/export-ops.md
- [ ] T040 [US1] Add tessellation quality parameter support to stl_handler.py
- [ ] T041 [US1] Add validation step before tessellation using BRepCheck_Analyzer
- [ ] T042 [US1] Add file.export handler to src/agent_interface/cli.py per contracts/export-ops.md
- [ ] T043 [US1] Implement multi-solid export logic (tessellate each, combine triangles)
- [ ] T044 [US1] Add error handling for tessellation failures and file write errors
- [ ] T045 [US1] Add logging for export operations (triangle count, file size, execution time)
- [ ] T046 [US1] Update src/multi_agent/controller.py to route file.export to geometry kernel

**Checkpoint**: At this point, User Story 1 should be fully functional - users can export real 3D geometry to viewable STL files

---

## Phase 4: User Story 2 - Create 3D Solids Using All Creation Operations (Priority: P2)

**Goal**: Implement complete suite of creation operations (extrude, revolve, loft, sweep, primitives, patterns, mirror) so users can build any 3D model

**Independent Test**: Create circle, extrude to cylinder, verify volume matches π×r²×h formula

### Tests for User Story 2

- [ ] T047 [P] [US2] Contract tests for primitive operations in tests/contract/test_creation_ops_contract.py
- [ ] T048 [P] [US2] Test solid.primitive.box creates box with correct volume (w×d×h)
- [ ] T049 [P] [US2] Test solid.primitive.cylinder creates cylinder with correct volume (π×r²×h)
- [ ] T050 [P] [US2] Test solid.primitive.sphere creates sphere with correct volume (4/3×π×r³)
- [ ] T051 [P] [US2] Test solid.primitive.cone creates cone with correct volume (1/3×π×r²×h)
- [ ] T052 [P] [US2] Contract tests for extrude operation
- [ ] T053 [P] [US2] Test solid.extrude creates cylinder from circle with correct volume
- [ ] T054 [P] [US2] Test extrude direction parameter controls extrusion axis
- [ ] T055 [P] [US2] Contract tests for revolve operation
- [ ] T056 [P] [US2] Test solid.revolve creates solid of revolution with correct rotational symmetry
- [ ] T057 [P] [US2] Test revolve angle parameter (180°, 360°)
- [ ] T058 [P] [US2] Contract tests for loft operation
- [ ] T059 [P] [US2] Test solid.loft creates smooth transition between 2+ profiles
- [ ] T060 [P] [US2] Test loft with smooth vs ruled options
- [ ] T061 [P] [US2] Contract tests for sweep operation
- [ ] T062 [P] [US2] Test solid.sweep moves profile along path curve
- [ ] T063 [P] [US2] Contract tests for pattern operations
- [ ] T064 [P] [US2] Test solid.pattern.linear creates correct number of copies with spacing
- [ ] T065 [P] [US2] Test solid.pattern.circular creates copies around axis
- [ ] T066 [P] [US2] Test solid.mirror creates mirrored copy across plane
- [ ] T067 [US2] Integration test for multi-operation workflow in tests/integration/test_geometry_workflows.py
- [ ] T068 [US2] Test create circle → extrude → export → verify geometry

### Implementation for User Story 2

#### Primitives

- [ ] T069 [P] [US2] Create src/cad_kernel/primitive_ops.py
- [ ] T070 [P] [US2] Implement create_box() using BRepPrimAPI_MakeBox per research.md line 181
- [ ] T071 [P] [US2] Implement create_cylinder() using BRepPrimAPI_MakeCylinder per research.md line 182
- [ ] T072 [P] [US2] Implement create_sphere() using BRepPrimAPI_MakeSphere per research.md line 183
- [ ] T073 [P] [US2] Implement create_cone() using BRepPrimAPI_MakeCone per research.md line 184
- [ ] T074 [US2] Add solid.primitive.box handler to src/agent_interface/cli.py per contracts/creation-ops.md
- [ ] T075 [US2] Add solid.primitive.cylinder handler to src/agent_interface/cli.py
- [ ] T076 [US2] Add solid.primitive.sphere handler to src/agent_interface/cli.py
- [ ] T077 [US2] Add solid.primitive.cone handler to src/agent_interface/cli.py

#### Creation Operations

- [ ] T078 [P] [US2] Create src/cad_kernel/creation_ops.py
- [ ] T079 [P] [US2] Implement extrude() using BRepPrimAPI_MakePrism per research.md line 107
- [ ] T080 [P] [US2] Implement revolve() using BRepPrimAPI_MakeRevol per research.md line 123
- [ ] T081 [P] [US2] Implement loft() using BRepOffsetAPI_ThruSections per research.md line 139
- [ ] T082 [P] [US2] Implement sweep() using BRepOffsetAPI_MakePipe per research.md line 157
- [ ] T083 [US2] Add solid.extrude handler to src/agent_interface/cli.py per contracts/creation-ops.md
- [ ] T084 [US2] Add solid.revolve handler to src/agent_interface/cli.py
- [ ] T085 [US2] Add solid.loft handler to src/agent_interface/cli.py
- [ ] T086 [US2] Add solid.sweep handler to src/agent_interface/cli.py

#### Pattern and Transform Operations

- [ ] T087 [P] [US2] Create src/cad_kernel/pattern_ops.py
- [ ] T088 [P] [US2] Implement linear_pattern() using gp_Trsf and BRepBuilderAPI_Transform per research.md line 225
- [ ] T089 [P] [US2] Implement circular_pattern() using gp_Trsf rotation per research.md line 239
- [ ] T090 [P] [US2] Implement mirror() using gp_Trsf SetMirror per research.md line 252
- [ ] T091 [US2] Add solid.pattern.linear handler to src/agent_interface/cli.py per contracts/creation-ops.md
- [ ] T092 [US2] Add solid.pattern.circular handler to src/agent_interface/cli.py
- [ ] T093 [US2] Add solid.mirror handler to src/agent_interface/cli.py

#### Integration and Error Handling

- [ ] T094 [US2] Implement operation result validation (volume > 0, is_closed, is_manifold) in creation_ops.py
- [ ] T095 [US2] Add error handling for invalid inputs (check IsDone() per research.md line 350)
- [ ] T096 [US2] Implement CreationOperation record logging in database per data-model.md
- [ ] T097 [US2] Compute and store SolidProperties for all created solids
- [ ] T098 [US2] Update src/multi_agent/controller.py to route all creation operations

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently - users can create any 3D solid and export it

---

## Phase 5: User Story 3 - Combine Solids with Boolean Operations (Priority: P3)

**Goal**: Enable advanced modeling through union, subtraction, and intersection of solids

**Independent Test**: Create two overlapping cylinders, perform union, verify single merged solid with correct volume

### Tests for User Story 3

- [ ] T099 [P] [US3] Contract tests for boolean union in tests/contract/test_boolean_ops_contract.py
- [ ] T100 [P] [US3] Test solid.boolean.union combines two solids into one
- [ ] T101 [P] [US3] Test union result volume ≈ vol(A) + vol(B) - vol(overlap)
- [ ] T102 [P] [US3] Contract tests for boolean subtract
- [ ] T103 [P] [US3] Test solid.boolean.subtract removes tool from base
- [ ] T104 [P] [US3] Test subtract result volume = vol(base) - vol(overlap)
- [ ] T105 [P] [US3] Contract tests for boolean intersect
- [ ] T106 [P] [US3] Test solid.boolean.intersect creates solid from overlap only
- [ ] T107 [P] [US3] Test intersect result volume = vol(overlap)
- [ ] T108 [P] [US3] Test error handling for invalid geometry inputs
- [ ] T109 [P] [US3] Test error handling for non-overlapping solids (intersect)
- [ ] T110 [US3] Integration test for complex boolean workflow in tests/integration/test_geometry_workflows.py
- [ ] T111 [US3] Test create box → create cylinder → subtract → export → verify hole

### Implementation for User Story 3

- [ ] T112 [P] [US3] Create src/cad_kernel/boolean_ops.py
- [ ] T113 [P] [US3] Implement union() using BRepAlgoAPI_Fuse per research.md line 196
- [ ] T114 [P] [US3] Implement subtract() using BRepAlgoAPI_Cut per research.md line 206
- [ ] T115 [P] [US3] Implement intersect() using BRepAlgoAPI_Common per research.md line 213
- [ ] T116 [US3] Add edge refinement (RefineEdges, FuseEdges) to all boolean operations per research.md line 207
- [ ] T117 [US3] Add pre-validation for both input solids using BRepCheck_Analyzer per contracts/boolean-ops.md
- [ ] T118 [US3] Add post-validation for result solid
- [ ] T119 [US3] Implement error handling for operation failures (BuilderCanWork, IsDone checks)
- [ ] T120 [US3] Add solid.boolean.union handler to src/agent_interface/cli.py per contracts/boolean-ops.md
- [ ] T121 [US3] Add solid.boolean.subtract handler to src/agent_interface/cli.py
- [ ] T122 [US3] Add solid.boolean.intersect handler to src/agent_interface/cli.py
- [ ] T123 [US3] Implement BooleanOperation record logging in database per data-model.md
- [ ] T124 [US3] Compute and update SolidProperties for boolean operation results
- [ ] T125 [US3] Update src/multi_agent/controller.py to route all boolean operations
- [ ] T126 [US3] Add logging for boolean operations (execution time, operand volumes, result volume)

**Checkpoint**: All user stories should now be independently functional - complete 3D CAD creation, modification, and export

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T127 [P] Add comprehensive error messages to all geometry operations with troubleshooting hints
- [ ] T128 [P] Add performance logging for operations exceeding 5s target per data-model.md
- [ ] T129 [P] Optimize tessellation parameters for performance vs quality tradeoff
- [ ] T130 Validate all operations complete in <5s for solids up to 10k faces per success criteria SC-006
- [ ] T131 Validate geometric property accuracy within 0.1% per success criteria SC-002
- [ ] T132 Validate dimensional accuracy within 0.01mm per success criteria SC-008
- [ ] T133 [P] Run quickstart.md setup validation on clean environment
- [ ] T134 [P] Test exported STL files in 3+ different viewers per success criteria SC-007
- [ ] T135 [P] Add constitution compliance verification (no placeholder code, no mocks in tests)
- [ ] T136 Code cleanup: Remove any remaining TODO/placeholder comments
- [ ] T137 Performance profiling: Identify bottlenecks in complex operations
- [ ] T138 Memory profiling: Verify no leaks in Open CASCADE shape lifecycle

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Integrates with US1 for export verification but independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Uses primitives from US2 for testing but independently testable

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Infrastructure (geometry_engine.py, exceptions.py) before operations
- Operations implementation before CLI handlers
- CLI handlers before controller routing
- Core implementation before integration tests
- Story complete before moving to next priority

### Parallel Opportunities

#### Setup Phase (Phase 1)
```bash
# All directory creation tasks can run in parallel:
T002, T003, T004 (test directories)
```

#### Foundational Phase (Phase 2)
```bash
# Database table creation can run in parallel:
T008, T009, T010, T011, T012, T013, T014

# Class creation can run in parallel after DB:
T017, T020 (GeometryShape, SolidProperties)
```

#### User Story 1 (Phase 3)
```bash
# All contract tests can run in parallel:
T024, T025, T026, T027, T028

# Core implementation files can be created in parallel:
T032 (tessellation.py), T035 (stl_handler.py), T040 (cli.py handler)
```

#### User Story 2 (Phase 4)
```bash
# All primitive tests can run in parallel:
T046, T047, T048, T049

# All operation tests can run in parallel:
T050-T064

# All primitive implementations can run in parallel:
T068, T069, T070, T071 (primitives)

# All creation operation implementations can run in parallel:
T077, T078, T079, T080 (extrude, revolve, loft, sweep)

# All pattern implementations can run in parallel:
T086, T087, T088 (linear, circular, mirror)
```

#### User Story 3 (Phase 5)
```bash
# All boolean tests can run in parallel:
T097-T107

# All boolean implementations can run in parallel:
T111, T112, T113 (union, subtract, intersect)
```

#### Polish Phase (Phase 6)
```bash
# Most polish tasks can run in parallel:
T125, T126, T127, T131, T132, T133
```

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Contract test for file.export operation in tests/contract/test_export_contract.py"
Task: "Test valid solid exports to STL with non-zero triangle data"
Task: "Test tessellation quality presets produce different triangle counts"
Task: "Test multi-solid export to single STL file"
Task: "Test error handling for invalid geometry and file write failures"

# Then launch all implementation files together:
Task: "Create src/cad_kernel/tessellation.py with TessellationConfig class"
Task: "REPLACE placeholder code in src/file_io/stl_handler.py"
Task: "Add file.export handler to src/agent_interface/cli.py"
```

---

## Parallel Example: User Story 2

```bash
# Launch all primitive implementations together:
Task: "Implement create_box() using BRepPrimAPI_MakeBox"
Task: "Implement create_cylinder() using BRepPrimAPI_MakeCylinder"
Task: "Implement create_sphere() using BRepPrimAPI_MakeSphere"
Task: "Implement create_cone() using BRepPrimAPI_MakeCone"

# Launch all creation operations together:
Task: "Implement extrude() using BRepPrimAPI_MakePrism"
Task: "Implement revolve() using BRepPrimAPI_MakeRevol"
Task: "Implement loft() using BRepOffsetAPI_ThruSections"
Task: "Implement sweep() using BRepOffsetAPI_MakePipe"

# Launch all pattern operations together:
Task: "Implement linear_pattern() using gp_Trsf"
Task: "Implement circular_pattern() using gp_Trsf rotation"
Task: "Implement mirror() using gp_Trsf SetMirror"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (8 tasks - includes system OCCT installation)
2. Complete Phase 2: Foundational (17 tasks - CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (21 tasks)
4. **STOP and VALIDATE**: Test User Story 1 independently
   - Create simple solid (extrude circle to cylinder)
   - Export to STL
   - Open in online viewer (https://www.viewstl.com/)
   - Verify real geometry is visible (NOT all zeros)
5. Deploy/demo if ready

**Total MVP tasks**: 46 tasks
**Estimated MVP value**: Users can export real 3D geometry for the first time - immediate validation that geometry kernel works

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready (25 tasks)
2. Add User Story 1 → Test independently → Deploy/Demo (MVP! - 46 total tasks)
   - **Value delivered**: Real STL export, viewable geometry
3. Add User Story 2 → Test independently → Deploy/Demo (98 total tasks)
   - **Value delivered**: Complete creation toolset (extrude, revolve, loft, sweep, primitives, patterns, mirror)
4. Add User Story 3 → Test independently → Deploy/Demo (126 total tasks)
   - **Value delivered**: Advanced modeling with boolean operations
5. Polish (138 total tasks) → Production ready

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (25 tasks)
2. Once Foundational is done:
   - **Developer A**: User Story 1 (21 tasks) - Export functionality
   - **Developer B**: User Story 2 (52 tasks) - Creation operations
   - **Developer C**: User Story 3 (28 tasks) - Boolean operations
3. Stories complete and integrate independently
4. All developers: Polish phase together (12 tasks)

---

## Notes

- [P] tasks = different files, no dependencies, can run in parallel
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing (TDD approach)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- **Constitution compliance**: No placeholder code, no mocks (use real pythonOCC, real database, real files)
- **Critical**: User Story 1 MUST replace placeholder code in stl_handler.py (constitution violation fix)
- All geometric properties must be validated with real calculations (BRepGProp)
- All exported STL files must contain actual geometry and open in external viewers
