# Tasks: Multi-Agent CAD Collaboration Framework

**Input**: Design documents from `/specs/002-multi-agent-framework/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/, research.md, quickstart.md

**Tests**: Contract and integration tests are included per constitution requirements (Test Reality Principle - no mocks, real CLI subprocess calls)

**Organization**: Tasks grouped by user story to enable independent implementation and testing

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4, US5)
- All file paths are relative to repository root

## Path Conventions

Single project structure (from plan.md):
- Source: `src/multi_agent/`
- Tests: `tests/multi_agent_contract/`, `tests/multi_agent_integration/`, `tests/multi_agent_unit/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and module structure

- [X] T001 Create src/multi_agent/ module directory structure with __init__.py
- [X] T002 Create tests/multi_agent_contract/ directory for controller API contract tests
- [X] T003 Create tests/multi_agent_integration/ directory for integration tests with real CLI
- [X] T004 Create tests/multi_agent_unit/ directory for task decomposition unit tests

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete. These components are dependencies for ALL user stories.

- [X] T005 [P] Define RoleTemplate dataclass in src/multi_agent/roles.py with fields: name, description, allowed_operations, forbidden_operations, example_tasks
- [X] T006 [P] Define 6 predefined role templates in src/multi_agent/roles.py: designer, modeler, constraint_solver, validator, optimizer, integrator (load from contracts/role_templates.json)
- [X] T007 [P] Define Agent dataclass in src/multi_agent/controller.py with fields: agent_id, role, workspace_id, operation_count, success_count, error_count, created_entities, error_log, status, created_at, last_active
- [X] T008 Define Controller class skeleton in src/multi_agent/controller.py with __init__(controller_id, max_concurrent_agents) and empty method stubs
- [X] T009 Implement subprocess CLI invocation helper in src/multi_agent/controller.py: _execute_cli_command(operation, params) using subprocess.run() with capture_output=True, text=True, timeout=10
- [X] T010 Implement error parsing from CLI stderr in src/multi_agent/controller.py: _parse_cli_error(stderr) to extract error details

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Collaborative Assembly Design (Priority: P1) 🎯 MVP

**Goal**: Multiple agents (4+) work simultaneously on different components in isolated workspaces, then merge into final assembly with zero data loss and conflict detection

**Independent Test**: Create 3+ agents each creating different components in separate workspaces, merge workspaces via integrator agent, verify all components present with correct geometry and no conflicts

### Contract Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T011 [P] [US1] Contract test for create_agent() in tests/multi_agent_contract/test_agent_create.py - verify agent created with correct role and workspace via real CLI workspace.create subprocess call
- [X] T012 [P] [US1] Contract test for execute_operation() in tests/multi_agent_contract/test_agent_execute.py - verify operation executes via real CLI subprocess and updates agent metrics
- [X] T013 [P] [US1] Contract test for shutdown_agent() in tests/multi_agent_contract/test_agent_shutdown.py - verify agent status transitions to terminated

### Integration Tests for User Story 1

- [X] T014 [P] [US1] Integration test for concurrent agents in tests/multi_agent_integration/test_concurrent_agents.py - create 4 agents using ThreadPoolExecutor, each creates entities in separate workspace via real CLI, verify no interference or locking
- [X] T015 [P] [US1] Integration test for workspace merge workflow in tests/multi_agent_integration/test_workspace_merge_workflow.py - 3 modeler agents create components, integrator merges all workspaces via real CLI workspace.merge, verify all entities preserved
- [X] T016 [P] [US1] Integration test for merge conflict detection in tests/multi_agent_integration/test_merge_conflicts.py - 2 agents create overlapping entities, integrator detects conflicts via real CLI, applies resolution strategy

### Implementation for User Story 1

- [X] T017 [US1] Implement Controller.create_agent(agent_id, role_name, workspace_id) in src/multi_agent/controller.py - create workspace via CLI subprocess, create Agent instance, add to self.agents dict, return agent
- [X] T018 [US1] Implement Controller.execute_operation(agent_id, operation, params) in src/multi_agent/controller.py - lookup agent, call _execute_cli_command() subprocess, update agent metrics (operation_count, success_count/error_count, last_active), return result
- [X] T019 [US1] Implement Controller.shutdown_agent(agent_id) in src/multi_agent/controller.py - set agent status to terminated, remove from agents dict, cleanup message queue
- [X] T020 [US1] Implement concurrent agent execution in src/multi_agent/controller.py - initialize ThreadPoolExecutor in __init__, provide _execute_concurrent(agents, operations) helper using executor.submit()
- [X] T021 [US1] Add agent metrics tracking in src/multi_agent/controller.py - update operation_count, success_count, error_count, created_entities list in execute_operation()
- [X] T022 [US1] Add error logging in src/multi_agent/controller.py - append to agent.error_log when operation fails, capture stderr from CLI subprocess

**Checkpoint**: At this point, User Story 1 should be fully functional - 4+ agents can work simultaneously, create components, and merge workspaces. Test independently before proceeding.

---

## Phase 4: User Story 2 - Role-Based Agent Specialization (Priority: P2)

**Goal**: Agents assigned specialized roles (designer, modeler, validator, optimizer, integrator, constraint_solver) with enforced capabilities - designer cannot extrude, validator cannot modify, etc.

**Independent Test**: Assign different roles to agents, verify allowed operations succeed and forbidden operations blocked with RoleViolationError citing specific constraint

### Contract Tests for User Story 2

- [X] T023 [P] [US2] Contract test for role enforcement in tests/multi_agent_contract/test_role_enforcement.py - designer agent executes entity.create_line (succeeds), then solid.extrude (blocked with error)
- [X] T024 [P] [US2] Contract test for validator role in tests/multi_agent_contract/test_role_enforcement.py - validator executes entity.query (succeeds), then entity.create_point (blocked)
- [X] T025 [P] [US2] Contract test for integrator role in tests/multi_agent_contract/test_role_enforcement.py - integrator executes workspace.merge (succeeds), then solid.boolean (blocked)

### Integration Tests for User Story 2

- [X] T026 [US2] Integration test for role constraint enforcement across 6 roles in tests/multi_agent_integration/test_role_constraints.py - create agent for each role, test allowed and forbidden operations via real CLI, verify 100% enforcement

### Implementation for User Story 2

- [X] T027 [US2] Implement role validation in Controller.execute_operation() in src/multi_agent/controller.py - check if operation in agent.role.allowed_operations before CLI subprocess call
- [X] T028 [US2] Implement RoleViolationError exception in src/multi_agent/roles.py - include agent_id, role_name, operation, error message
- [X] T029 [US2] Add forbidden operations check in Controller.execute_operation() in src/multi_agent/controller.py - raise RoleViolationError if operation in agent.role.forbidden_operations
- [X] T030 [US2] Add role violation logging in src/multi_agent/controller.py - log all role violations with agent_id, role, attempted operation for audit trail

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently - agents collaborate AND role constraints enforced 100% of the time

---

## Phase 5: User Story 3 - Automatic Task Decomposition and Coordination (Priority: P3)

**Goal**: Controller receives high-level design goal ("create box assembly with lid"), decomposes into specific tasks (create base, create lid, integrate), assigns to agents based on role matching, coordinates execution with dependency handling

**Independent Test**: Provide goal description, verify controller identifies correct subtasks, assigns to appropriate role types (modeler for solids, integrator for merge), executes in correct sequence, achieves design goal

### Contract Tests for User Story 3

- [X] T031 [P] [US3] Contract test for decompose_task() in tests/multi_agent_contract/test_task_decomposition.py - pass "create box assembly with lid", verify returns TaskAssignment list with create_base, create_lid, integrate tasks
- [X] T032 [P] [US3] Contract test for assign_task() in tests/multi_agent_contract/test_task_assignment.py - assign task to agent, verify agent role matches task.required_operations
- [X] T033 [P] [US3] Contract test for task dependencies in tests/multi_agent_contract/test_task_assignment.py - verify tasks execute in correct order respecting dependencies

### Integration Tests for User Story 3

- [X] T034 [US3] Integration test for task decomposition workflow in tests/multi_agent_integration/test_task_decomposition_workflow.py - decompose "box assembly", create agents, assign tasks, execute workflow, verify final design via real CLI entity.list

### Unit Tests for User Story 3

- [X] T035 [P] [US3] Unit test for task decomposition patterns in tests/multi_agent_unit/test_task_decomposition.py - test decompose logic for box assembly, bracket creation, cylinder patterns using real role definitions (no mocks)

### Implementation for User Story 3

- [X] T036 [P] [US3] Define TaskAssignment dataclass in src/multi_agent/task_decomposer.py with fields: task_id, agent_id, description, required_operations, dependencies, success_criteria, status, assigned_at, completed_at, result
- [X] T037 [US3] Implement task decomposition rules in src/multi_agent/task_decomposer.py - decompose_goal(goal_description, context) returns List[TaskAssignment] for common patterns (box, bracket, cylinder)
- [X] T038 [US3] Implement Controller.decompose_task(goal_description, context) in src/multi_agent/controller.py - call task_decomposer.decompose_goal(), return task list
- [X] T039 [US3] Implement Controller.assign_task(task_id, agent_id) in src/multi_agent/controller.py - validate agent role matches task.required_operations, set task.agent_id, update task.status to pending
- [X] T040 [US3] Implement dependency resolution in src/multi_agent/task_decomposer.py - _resolve_dependencies(tasks) returns execution order respecting task.dependencies
- [X] T041 [US3] Implement task execution coordination in src/multi_agent/controller.py - execute_tasks(task_assignments) respects dependencies, uses ThreadPoolExecutor for parallel tasks, tracks completion

**Checkpoint**: All user stories 1, 2, and 3 should now be independently functional - agents collaborate, roles enforced, and controller decomposes goals automatically

---

## Phase 6: User Story 4 - Agent-to-Agent Communication and Coordination (Priority: P4)

**Goal**: Agents send direct messages (request, response, broadcast, error) to each other for validation requests, feedback loops, status updates beyond shared workspace entities

**Independent Test**: Agent A sends validation request to Agent B, Agent B validates component via entity.query and responds with feedback, Agent A receives response and acts on it, verify message delivery <100ms latency

### Contract Tests for User Story 4

- [X] T042 [P] [US4] Contract test for send_message() in tests/multi_agent_contract/test_messaging.py - agent sends request message, verify message queued with correct structure
- [X] T043 [P] [US4] Contract test for get_messages() in tests/multi_agent_contract/test_messaging.py - agent retrieves messages from queue, verify messages returned and marked read
- [X] T044 [P] [US4] Contract test for broadcast messages in tests/multi_agent_contract/test_messaging.py - agent broadcasts status update, verify all agents receive message

### Integration Tests for User Story 4

- [X] T045 [US4] Integration test for agent messaging feedback loop in tests/multi_agent_integration/test_messaging_feedback.py - designer creates component, sends validation request to validator, validator queries via real CLI, responds with feedback, designer revises based on feedback

### Implementation for User Story 4

- [X] T046 [P] [US4] Define AgentMessage dataclass in src/multi_agent/messaging.py with fields: message_id, from_agent_id, to_agent_id, message_type, content, timestamp, read
- [X] T047 [US4] Implement message queue initialization in Controller.__init__() in src/multi_agent/controller.py - create queue.Queue() for each agent in self.message_queues dict
- [X] T048 [US4] Implement Controller.send_message(from_agent_id, to_agent_id, message_type, content) in src/multi_agent/controller.py - create AgentMessage, put in target agent's queue (or all queues if broadcast)
- [X] T049 [US4] Implement Controller.get_messages(agent_id, mark_read=True) in src/multi_agent/controller.py - retrieve all messages from agent's queue, optionally mark as read, return List[AgentMessage]
- [X] T050 [US4] Implement message type validation in src/multi_agent/messaging.py - validate_message_content(message_type, content) checks structure matches contracts/message_schemas.json
- [X] T051 [US4] Add message latency tracking in src/multi_agent/controller.py - record send and receive timestamps, log if latency exceeds 100ms threshold

**Checkpoint**: All user stories 1-4 should now be independently functional - agents collaborate, roles enforced, goals decomposed, and agents communicate directly

---

## Phase 7: User Story 5 - Agent Learning and Performance Tracking (Priority: P5)

**Goal**: System tracks agent performance (success rate, error rate trends, task completion time, learning progress), agents query metrics to identify improvement areas

**Independent Test**: Agent performs 20+ operations across multiple tasks, query metrics, verify success rate calculated correctly, error rate trend identified (improving/stable/degrading), average operation time computed, learning status determined

### Integration Tests for User Story 5

- [X] T052 [US5] Integration test for agent metrics calculation in tests/multi_agent_integration/test_agent_metrics.py - agent executes 20 operations (mix of success/failure via real CLI), query metrics, verify success_rate, error_rate_trend, average_operation_time match actual with <1% variance

### Implementation for User Story 5

- [X] T053 [US5] Implement Controller.get_agent_metrics(agent_id) in src/multi_agent/controller.py - calculate success_rate (success_count / operation_count), error_rate_trend (improving/stable/degrading), average_operation_time, learning_status
- [X] T054 [US5] Implement error rate trend calculation in src/multi_agent/controller.py - _calculate_error_trend(agent) analyzes recent errors vs earlier errors, returns "improving", "stable", or "degrading"
- [X] T055 [US5] Implement operation timing tracking in Controller.execute_operation() in src/multi_agent/controller.py - record start and end time for each operation, store in agent operation history
- [X] T056 [US5] Implement learning status determination in src/multi_agent/controller.py - _determine_learning_status(agent) based on error trend and success rate, returns "improving", "stable", or "needs_attention"

**Checkpoint**: All user stories 1-5 should now be independently functional and complete

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Collaborative scenarios, workflow execution, CLI, documentation - improvements that affect multiple user stories

- [ ] T057 [P] Define CollaborativeScenario dataclass in src/multi_agent/controller.py with fields: scenario_name, description, agent_assignments, workflow_pattern, task_sequence, success_criteria, estimated_duration
- [ ] T058 [P] Define WorkflowExecution dataclass in src/multi_agent/controller.py with fields: workflow_id, scenario_name, task_assignments, execution_state, completion_percentage, agent_failures, started_at, completed_at, metrics
- [ ] T059 [P] Load 3 predefined collaborative scenarios in src/multi_agent/controller.py - assembly_design, design_review_loop, parallel_component_creation (from design artifacts)
- [ ] T060 Implement Controller.execute_workflow(scenario_name, agent_overrides) in src/multi_agent/controller.py - load scenario, create agents per agent_assignments, execute task_sequence, track progress in WorkflowExecution, handle failures
- [ ] T061 Implement Controller.get_workflow_status(workflow_id) in src/multi_agent/controller.py - return WorkflowExecution with current state, completion percentage, failures
- [ ] T062 [P] Create multi-agent CLI interface in src/multi_agent/cli.py - commands: controller.create, agent.create, agent.execute, agent.metrics, workflow.execute, workflow.status
- [ ] T063 [P] Integration test for collaborative scenarios in tests/multi_agent_integration/test_collaborative_scenarios.py - execute all 3 scenarios via real CLI, verify success criteria met (SC-008)
- [ ] T064 [P] Add comprehensive logging throughout src/multi_agent/ modules - log agent creation, operation execution, role violations, messaging, task decomposition, workflow progress
- [ ] T065 [P] Validate quickstart.md examples in tests/multi_agent_integration/test_quickstart_validation.py - run all 8 quickstart examples as integration tests with real CLI subprocess calls
- [ ] T066 [P] Performance optimization in src/multi_agent/controller.py - verify controller overhead <15% vs single-agent operation (SC success criteria)
- [ ] T067 Code cleanup and refactoring across src/multi_agent/ - ensure no TODOs, FIXMEs, placeholders, mocks, or stubs remain (constitution enforcement)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phases 3-7)**: All depend on Foundational phase completion
  - User stories CAN proceed in parallel if team capacity allows
  - Or sequentially in priority order: US1 (P1) → US2 (P2) → US3 (P3) → US4 (P4) → US5 (P5)
- **Polish (Phase 8)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories ✅
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Enhances US1 but independently testable ✅
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Uses US1 agents/controller but independently testable ✅
- **User Story 4 (P4)**: Can start after Foundational (Phase 2) - Adds messaging to US1 agents but independently testable ✅
- **User Story 5 (P5)**: Can start after Foundational (Phase 2) - Uses US1 metrics tracking but independently testable ✅

**All user stories are designed for independent implementation and testing**

### Within Each User Story

1. Contract tests FIRST → ensure they FAIL before implementation
2. Integration tests → ensure they FAIL before implementation
3. Unit tests (if any) → ensure they FAIL before implementation
4. Implementation → make tests PASS
5. Verify story independently → checkpoint before next story

### Parallel Opportunities

- **Phase 1 (Setup)**: All 4 tasks can run in parallel [T001-T004]
- **Phase 2 (Foundational)**: T005, T006, T007 can run in parallel (different components)
- **Phase 3 (US1)**:
  - Contract tests can run in parallel: T011, T012, T013
  - Integration tests can run in parallel: T014, T015, T016
- **Phase 4 (US2)**: Contract tests can run in parallel: T023, T024, T025
- **Phase 5 (US3)**:
  - Contract tests can run in parallel: T031, T032, T033
  - Unit tests can run in parallel: T035
  - T036 and T037 can run in parallel (different files)
- **Phase 6 (US4)**:
  - Contract tests can run in parallel: T042, T043, T044
  - T046 and T047 can run in parallel (different concerns)
- **Phase 8 (Polish)**: T057, T058, T059, T062, T063, T064, T065, T066, T067 can all run in parallel (different files/concerns)

**If multiple developers**: After Foundational phase, US1-US5 can be developed in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Launch all contract tests for User Story 1 together:
Task T011: "Contract test for create_agent() in tests/multi_agent_contract/test_agent_create.py"
Task T012: "Contract test for execute_operation() in tests/multi_agent_contract/test_agent_execute.py"
Task T013: "Contract test for shutdown_agent() in tests/multi_agent_contract/test_agent_shutdown.py"

# Launch all integration tests for User Story 1 together:
Task T014: "Integration test for concurrent agents in tests/multi_agent_integration/test_concurrent_agents.py"
Task T015: "Integration test for workspace merge in tests/multi_agent_integration/test_workspace_merge_workflow.py"
Task T016: "Integration test for merge conflicts in tests/multi_agent_integration/test_merge_conflicts.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T004)
2. Complete Phase 2: Foundational (T005-T010) - CRITICAL, blocks everything
3. Complete Phase 3: User Story 1 (T011-T022)
4. **STOP and VALIDATE**: Test User Story 1 independently
   - 4+ agents create components simultaneously
   - Workspace merge with zero data loss
   - Conflict detection working
5. Deploy/demo MVP if ready

**Estimated MVP task count**: 22 tasks (Setup + Foundational + US1)

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → **Deploy/Demo (MVP!)** ✅
3. Add User Story 2 → Test independently → Deploy/Demo (MVP + Role enforcement)
4. Add User Story 3 → Test independently → Deploy/Demo (MVP + Task decomposition)
5. Add User Story 4 → Test independently → Deploy/Demo (MVP + Messaging)
6. Add User Story 5 → Test independently → Deploy/Demo (Complete feature)
7. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done (after T010):
   - **Developer A**: User Story 1 (T011-T022)
   - **Developer B**: User Story 2 (T023-T030)
   - **Developer C**: User Story 3 (T031-T041)
   - **Developer D**: User Story 4 (T042-T051)
   - **Developer E**: User Story 5 (T052-T056)
3. Stories complete and integrate independently
4. Converge on Phase 8 (Polish) together

---

## Success Criteria Mapping

Each task maps to specific success criteria from spec.md:

- **SC-001** (4+ agents simultaneously): T014, T020
- **SC-002** (100% merge success): T015
- **SC-003** (Role constraints 100% enforced): T023-T030
- **SC-004** (Workspace merge <5s): T015 (verify performance)
- **SC-005** (Conflict detection 100%): T016
- **SC-006** (10 agents in parallel): T014, T020
- **SC-007** (Metrics accuracy <1% variance): T052-T056
- **SC-008** (3 collaborative scenarios succeed): T063
- **SC-009** (Task decomposition 80% accuracy): T031-T041
- **SC-010** (Messaging <100ms latency): T042-T051
- **SC-011** (Graceful agent failure handling): T060, T061
- **SC-012** (Decomposition <2s): T037, T038

---

## Constitution Compliance

All tasks comply with `.specify/memory/constitution.md`:

- ✅ **No Mocks/Stubs**: All tests use real CLI subprocess calls (subprocess.run()), real queue.Queue, real database via JSON-RPC
- ✅ **Verifiable Completion**: Each task has clear completion criteria (tests pass, operations work via real CLI, metrics match actual)
- ✅ **Test Reality**: Contract tests test real controller API, integration tests test real CLI subprocess invocations, unit tests use real role definitions
- ✅ **Documentation-Driven**: research.md decisions guide implementation (subprocess.run, ThreadPoolExecutor, queue.Queue patterns)
- ✅ **Multi-Agent Architecture**: All user stories require coordination across agents
- ✅ **Library-First**: All code in src/multi_agent/ module
- ✅ **3D CAD Ownership**: Uses existing owned CAD system via JSON-RPC CLI

---

## Notes

- **[P] tasks** = different files, no dependencies, can run in parallel
- **[Story] label** maps task to specific user story for traceability
- **All tests use real CLI subprocess calls** - NO mocks, stubs, or proxies allowed
- **Each user story independently completable and testable** - can stop after any story
- **Verify tests FAIL before implementing** - TDD approach ensures tests are valid
- **Commit after each task or logical group** - small, incremental progress
- **Stop at any checkpoint** to validate story independently before proceeding
- **Constitution enforcement**: Grep for forbidden keywords before marking any task complete:
  ```bash
  grep -r "TODO\|FIXME\|mock\|stub\|proxy\|@skip\|@ignore" src/multi_agent/ tests/multi_agent_*
  ```

---

## Total Task Summary

- **Phase 1 (Setup)**: 4 tasks
- **Phase 2 (Foundational)**: 6 tasks (BLOCKS all user stories)
- **Phase 3 (US1 - Collaborative Assembly)**: 12 tasks (6 tests + 6 implementation)
- **Phase 4 (US2 - Role Specialization)**: 8 tasks (4 tests + 4 implementation)
- **Phase 5 (US3 - Task Decomposition)**: 11 tasks (5 tests + 6 implementation)
- **Phase 6 (US4 - Messaging)**: 10 tasks (4 tests + 6 implementation)
- **Phase 7 (US5 - Performance Tracking)**: 5 tasks (1 test + 4 implementation)
- **Phase 8 (Polish)**: 11 tasks

**Total**: 67 tasks

**MVP (US1 only)**: 22 tasks (Setup + Foundational + US1)
**US1 + US2**: 30 tasks
**US1 + US2 + US3**: 41 tasks

**Parallel opportunities**: 35 tasks marked [P] can run in parallel with other tasks in same phase
