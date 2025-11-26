# Multi-Agent System Constitution

<!--
SYNC IMPACT REPORT
==================
Version change: [INITIAL] → 1.0.0
Modified principles: N/A (initial version)
Added sections:
  - Core Principles (8 principles)
  - Development Constraints
  - Testing Requirements
  - Task Completion Standards
  - Development Workflow
  - Governance
Removed sections: N/A (initial version)
Templates requiring updates:
  ✅ plan-template.md (reviewed - Constitution Check section present)
  ✅ spec-template.md (reviewed - aligns with principles)
  ✅ tasks-template.md (reviewed - aligns with principles)
  ✅ agent-file-template.md (exists but not modified)
  ✅ checklist-template.md (exists but not modified)
Follow-up TODOs:
  - Monitor AI agent compliance with no-mocks principle during implementation
  - Validate hot reload system integration once development begins
  - Establish documentation retrieval workflow before project begins in earnest
Ratification date: 2025-11-24 (project initialization)
-->

## Core Principles

### I. Multi-Agent Architecture Enforcement

The system MUST utilize all available agents in the multi-agent system for their designated purposes. No single agent should operate in isolation when other specialized agents can contribute to the task. Every feature implementation MUST involve coordination across planning, specification, task generation, and implementation agents as defined by the system architecture.

**Rationale**: Multi-agent coordination distributes complexity, enables parallel work, and leverages specialized capabilities. Single-agent shortcuts lead to brittle solutions and missed architectural benefits.

### II. No Mocks, Stubs, Proxies, Placeholders, Dummy Code, or Incomplete Implementations

Code MUST contain ZERO mocks, stubs, proxies, test doubles, placeholder implementations, dummy implementations, skeleton code, TODO comments, FIXME comments, or any form of simulated/incomplete functionality.

**If you cannot implement it fully, DO NOT COMMIT IT. No exceptions.**

Every function, class, and module MUST be fully implemented with real, working code that performs its stated purpose. Tests MUST exercise actual implementations against real dependencies (databases, file systems, APIs) or containerized equivalents.

**ABSOLUTELY FORBIDDEN** - ANY of these results in immediate deletion:
- Comments: "placeholder", "TODO", "FIXME", "stub", "dummy", "mock", "fake", "skeleton", "not implemented", "will implement later", "real implementation", "in real impl"
- Dummy/fake data that doesn't reflect actual behavior
- Functions that return zeros, hardcoded values, or empty results instead of doing real work
- Any code admitting it's incomplete or simulated

**Rationale**: Placeholders are LIES. They create false confidence and hide the fact that features don't work. If it's not ready, don't commit it.

**Enforcement**:
- CI/CD MUST fail on keywords: `placeholder`, `TODO`, `FIXME`, `dummy`, `stub`, `mock`, `fake`, `skeleton`, `@skip`, `@ignore`, `not implemented`, `real impl`
- AI agents MUST refuse to generate any placeholder/mock/stub patterns
- ANY violation = immediate revert

### III. Verifiable Task Completion Only

A task is marked "completed" ONLY when it contains 100% actual, verifiable, working code that:
1. Compiles/runs without errors
2. Passes all tests (if tests exist for this feature)
3. Is fully integrated with dependent systems (no mocked interfaces)
4. Contains zero TODOs, FIXMEs, or placeholder comments
5. Is deployable to a runtime environment

Tasks that are "90% done" or "works except for X" remain IN PROGRESS until ALL criteria are met.

**Rationale**: Partial completion creates technical debt, obscures true project status, and allows quality erosion. Binary completion standards maintain velocity visibility and prevent scope creep.

**Enforcement**:
- Task tracking systems MUST validate completion criteria before allowing status change
- AI agents MUST NOT mark tasks complete if ANY criterion is unmet
- Code review checklists MUST verify all completion criteria

### IV. Test Reality Principle

Tests MUST test what actually needs to be tested: real user journeys, real error conditions, real integration points, and real performance characteristics. Tests MUST NOT test mocked behavior, theoretical edge cases that cannot occur, or implementation details that users never interact with.

Every test MUST answer: "If this test passes, what USER-VISIBLE behavior am I confident works?"

**Rationale**: Tests that validate mocks or internal implementation details provide false security. Tests must validate contracts, behaviors, and integration points that affect users.

**Application**:
- Prioritize contract tests (API boundaries, CLI contracts, data schemas)
- Prioritize integration tests (database writes/reads, file I/O, API calls)
- Unit tests are acceptable for complex algorithms, but MUST NOT mock dependencies
- Avoid: testing getters/setters, testing that mocks return mocked values, testing private methods

### V. Documentation-Driven Development

Before implementing any feature involving third-party libraries, frameworks, or tools, the AI agent MUST:
1. Retrieve and review the official documentation for those tools
2. Verify syntax, API contracts, and usage patterns against current versions
3. Cite documentation sources in code comments for non-obvious patterns
4. Flag any assumptions that lack documentation support

**Rationale**: Hallucinated APIs, outdated syntax, and assumed behaviors cause implementation failures. Documentation grounding reduces rework and ensures compatibility.

**Enforcement**:
- AI agents MUST use web search or documentation retrieval tools before generating code
- Code reviews MUST verify that tool usage matches official documentation
- Unknown/undocumented patterns MUST be flagged for human verification

### VI. Live Error Reporting

All development environments MUST pipe errors, warnings, and logs directly to the AI agent's working context. The AI agent MUST NEVER ask the user "What error did you get?" - errors must be automatically visible.

**Implementation Requirements**:
- Hot reload system with error streaming to AI terminal
- Compiler errors, linter warnings, test failures routed to agent context
- Runtime exceptions captured and surfaced immediately
- Build system failures interrupt agent workflow with full error context

**Rationale**: Asynchronous error reporting wastes time, breaks flow, and forces context switching. Immediate error visibility enables rapid iteration.

### VII. Library-First Architecture

Every feature starts as a standalone library with:
- Clear, single purpose (no "utility" or organizational-only libraries)
- Self-contained implementation (minimal external dependencies)
- Independent test suite
- Documented contracts (inputs, outputs, side effects)
- CLI interface for standalone execution

**Rationale**: Libraries enforce modularity, enable reuse, simplify testing, and force clear API design. Monolithic architectures obscure dependencies and hinder parallel development.

### VIII. Owned 3D CAD System

The project MUST build and maintain its own 3D CAD system rather than depending on third-party CAD tools. This ensures:
- Full control over geometry representation and manipulation
- Ability to optimize for specific domain requirements
- No licensing restrictions or vendor lock-in
- Direct integration with other system components
- Custom export formats and rendering pipelines

**Rationale**: Third-party CAD systems impose constraints on geometry handling, interoperability, and extensibility. Ownership enables domain-specific optimizations and removes external dependencies for critical functionality.

**Scope**: This principle applies to core geometry kernel, solid modeling operations, constraint solving, and rendering - NOT to file format support for interoperability (STEP, STL, DXF import/export are acceptable).

## Development Constraints

### Forbidden Patterns

The following patterns are EXPLICITLY FORBIDDEN and MUST be rejected in code review:

1. **Mock objects** in any form
2. **Stub implementations**
3. **Placeholder/dummy/fake implementations**
4. **TODO/FIXME comments**
5. **@skip, @ignore decorators**
6. **Skeleton/incomplete code**
7. **Comments admitting code doesn't work** ("placeholder", "real impl", "will implement", etc.)
8. **Hardcoded/zero returns** instead of actual operations
9. **Any code that lies about what it does**

### Required Patterns

1. **Real implementations**: Every function has actual logic
2. **Real dependencies**: Tests use actual databases, file systems, APIs (containerized if needed)
3. **Contract tests**: Validate API boundaries with real requests/responses
4. **Integration tests**: Validate cross-service communication
5. **Error handling**: Real error paths, not generic catch-all handlers
6. **Observability**: Structured logging at integration points
7. **Documentation**: Inline citations for non-obvious tool usage

## Testing Requirements

### Test Categories (In Priority Order)

1. **Contract Tests** (HIGHEST PRIORITY)
   - Test API boundaries (REST endpoints, CLI arguments, function signatures)
   - Validate request/response schemas
   - Ensure backward compatibility
   - MUST use real HTTP requests, real CLI invocations, real function calls

2. **Integration Tests** (HIGH PRIORITY)
   - Test cross-service communication
   - Test database writes and reads (real database, not in-memory)
   - Test file I/O with real file system
   - Test external API calls (use test instances, not mocks)

3. **Unit Tests** (LOWER PRIORITY)
   - Only for complex algorithms or business logic
   - MUST NOT mock dependencies - use real instances
   - Acceptable: testing pure functions, calculations, transformations
   - Avoid: testing getters/setters, testing private methods

### Test Execution Standards

- All tests MUST pass before marking a task complete
- Tests MUST run in CI/CD pipeline on every commit
- Flaky tests MUST be fixed or deleted (no @retry decorators to mask issues)
- Test coverage is NOT a goal - test coverage of REAL behavior is the goal
- If a test requires mocks to pass, the test is testing the wrong thing

## Task Completion Standards

A task transitions to "completed" status ONLY when ALL of the following are true:

1. ✅ **Code compiles/executes**: No syntax errors, type errors, or runtime crashes
2. ✅ **Tests pass**: All relevant tests pass (or tests explicitly not required for this feature)
3. ✅ **No mocks/stubs/todos**: Zero placeholder code, comments, or test doubles
4. ✅ **Integrated**: Code is connected to real dependencies (databases, APIs, services)
5. ✅ **Deployable**: Code can be deployed to a runtime environment
6. ✅ **Documented**: Non-obvious patterns cite documentation sources
7. ✅ **Observable**: Errors/logs are captured and visible to monitoring systems

If ANY criterion is unmet, the task remains IN PROGRESS.

### Task Verification Checklist

Before marking a task complete, verify:

```bash
# No forbidden keywords
grep -r "TODO\|FIXME\|mock\|stub\|proxy\|@skip\|@ignore" src/ tests/

# Tests pass
./run_tests.sh

# Code compiles
./build.sh

# Integration points work
./integration_check.sh

# Errors are visible
./error_reporting_check.sh
```

## Development Workflow

### Feature Development Process

1. **Specification Phase** (via /speckit.specify)
   - Define user stories with acceptance criteria
   - Identify functional requirements
   - Document success criteria
   - NO implementation details yet

2. **Planning Phase** (via /speckit.plan)
   - Research technical approach (documentation review MANDATORY)
   - Design data models and contracts
   - Verify constitution compliance
   - Identify integration points

3. **Task Generation Phase** (via /speckit.tasks)
   - Break down into granular, verifiable tasks
   - Each task must have clear completion criteria
   - Group by user story for independent delivery
   - Mark parallel opportunities

4. **Implementation Phase** (via /speckit.implement)
   - Multi-agent execution: planning, coding, testing agents coordinate
   - Write tests FIRST (if tests required)
   - Implement with real code (no mocks/stubs)
   - Verify completion criteria before marking complete
   - Errors visible in real-time to AI agent

5. **Validation Phase**
   - All tests pass
   - Manual smoke test of user journeys
   - Error reporting functional
   - Documentation up to date

### Hot Reload & Error Reporting Integration

Development environments MUST implement:

1. **File Watcher**: Detects changes to source files
2. **Auto-Rebuild**: Recompiles/reloads on change
3. **Error Stream**: Pipes compiler/runtime errors to AI agent context
4. **Test Re-Run**: Automatically re-runs relevant tests on change
5. **Status Display**: Shows build/test status in AI terminal

The AI agent MUST receive errors automatically - no human intermediary.

## Governance

### Amendment Process

1. Constitution changes require:
   - Documented rationale (why is this change needed?)
   - Impact analysis (what breaks? what improves?)
   - Migration plan (how do existing features comply?)
   - Approval from project lead

2. Version bumping rules:
   - **MAJOR (X.0.0)**: Removing or redefining core principles (backward incompatible)
   - **MINOR (X.Y.0)**: Adding new principles or expanding guidance
   - **PATCH (X.Y.Z)**: Clarifications, typo fixes, non-semantic changes

### Compliance Review

- All PRs MUST verify compliance with this constitution
- Code reviews MUST explicitly check for forbidden patterns
- CI/CD pipeline MUST enforce no-mocks policy (grep checks)
- Task completions MUST meet all completion criteria
- Complexity introduced MUST be justified against principles

### Constitution Authority

This constitution supersedes:
- Individual preferences
- "Common practices" that violate principles
- External style guides that conflict with these rules
- AI agent default behaviors that suggest forbidden patterns

When in doubt, the constitution is the final authority.

### AI Agent Compliance

AI agents operating in this project MUST:
- Read and internalize this constitution before generating code
- Reject suggestions to create mocks, stubs, or placeholders
- Refuse to mark tasks complete unless all criteria met
- Retrieve documentation before using unfamiliar tools
- Surface errors immediately (never ask user for error text)
- Coordinate with other agents per multi-agent architecture

Human operators MUST:
- Provide agents with access to this constitution
- Configure hot reload and error streaming
- Reject agent output that violates principles
- Update constitution when patterns emerge that need codification

---

**Version**: 1.1.0 | **Ratified**: 2025-11-24 | **Last Amended**: 2025-11-26
