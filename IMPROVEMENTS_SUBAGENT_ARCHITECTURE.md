# Improvements for Subagent Architecture

This document outlines improvements specifically for the Claude Code Task tool subagent architecture.

## Critical Changes Needed

### 1. **Remove/Deprecate API-Based Code** (HIGHEST PRIORITY)

**Problem**: You have two competing architectures in the codebase.

**Files that should be REMOVED or moved to `deprecated/`**:
- `humanoid_agents/agents/ai_agent_base.py` (243 lines) - Uses Anthropic API directly
- `humanoid_agents/agents/ai_skeleton_agent.py` (378 lines) - Uses Anthropic API directly
- `humanoid_agents/launch_agents.py` - Launches processes, not subagents
- `humanoid_agents/orchestrator.py` - Standalone script (Claude Code IS the orchestrator)
- `humanoid_agents/agents/base_agent.py` - Process-based with sleep loops

**Why**: These files use the Anthropic API directly and create long-running processes. You want Claude Code to spawn subagents via the Task tool instead.

**Action**:
```bash
mkdir humanoid_agents/deprecated
mv humanoid_agents/agents/ai_*.py humanoid_agents/deprecated/
mv humanoid_agents/launch_agents.py humanoid_agents/deprecated/
mv humanoid_agents/orchestrator.py humanoid_agents/deprecated/
mv humanoid_agents/agents/base_agent.py humanoid_agents/deprecated/
```

**Keep**:
- `agent_prompts/*.md` - These ARE what you want (prompts for Task tool)
- `utils/shared_state.py` - Still needed for filesystem communication
- `config/` - Configuration files
- `shared_state/` - The communication filesystem

---

### 2. **Fix Agent Prompts** (HIGH PRIORITY)

**Current Issues**:
- Hardcoded absolute Windows paths
- Don't clearly state when to finish
- Don't emphasize single-execution completion
- Missing error handling guidance

**Required Changes for ALL agent prompts**:

#### a) Remove hardcoded paths
```markdown
❌ BAD:
`C:\Users\jrdnh\Documents\AgentCAD\humanoid_agents\shared_state\`

✓ GOOD:
All paths are relative to: `humanoid_agents/shared_state/`
```

#### b) Add clear completion criteria
```markdown
## Success Criteria - When You're Done

You MUST complete ALL of these before finishing:
- ✓ Read all required inputs
- ✓ Perform calculations
- ✓ Write all output files
- ✓ Report final status
```

#### c) Emphasize single execution
```markdown
**IMPORTANT**: You are a spawned subagent. Complete your entire design
in ONE execution. Don't wait for iterations - do the full design now,
write all files, and finish.
```

#### d) Add error handling
```markdown
## If Files Don't Exist

If `requirements.json` doesn't exist:
- Report error clearly
- Suggest running System Architect first
- Exit gracefully

If `constraints.json` doesn't exist:
- Use default budgets: 15kg mass, $3000 cost
- Log warning
- Continue with defaults
```

**Files to update**:
- `agent_prompts/system_architect.md` ✓ (needs same fixes)
- `agent_prompts/skeleton_designer.md` ✓ (partially done)
- `agent_prompts/actuation_designer.md` ✓ (needs same fixes)

---

### 3. **Improve Shared State Structure** (MEDIUM PRIORITY)

**Current**: Plain JSON files with no validation

**Improvements Needed**:

#### a) Add JSON schemas
Create `humanoid_agents/schemas/` directory:

```json
// schemas/subsystem_status.schema.json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["state", "current_mass_kg", "current_cost_usd"],
  "properties": {
    "state": {
      "type": "string",
      "enum": ["not_started", "initializing", "designing", "validating", "complete"]
    },
    "current_mass_kg": {"type": "number", "minimum": 0},
    "current_cost_usd": {"type": "number", "minimum": 0},
    "iteration": {"type": "integer", "minimum": 1},
    "within_budget": {"type": "boolean"}
  }
}
```

#### b) Update agent prompts to validate
```markdown
After writing status.json, validate it against the schema to ensure correctness.
```

#### c) Add initialization templates
Create `humanoid_agents/templates/` with default structures:

```json
// templates/empty_conflicts.json
{
  "conflicts": [],
  "resolved": [],
  "next_conflict_id": 1
}
```

**Why**: Prevents agents from creating malformed JSON that breaks other agents.

---

### 4. **Improve orchestration_helpers.py** (MEDIUM PRIORITY)

**Current state**: Basic functionality (just created)

**Needed additions**:

#### a) Add validation helpers
```python
def validate_shared_state_structure(self) -> List[str]:
    """Check if shared_state has correct directory structure."""
    issues = []
    required_dirs = [
        "constraints",
        "subsystems/skeleton",
        "subsystems/actuation",
        "conflicts",
        "logs"
    ]
    for dir_path in required_dirs:
        full_path = self.shared_state / dir_path
        if not full_path.exists():
            issues.append(f"Missing directory: {dir_path}")
    return issues
```

#### b) Add initialization helpers
```python
def initialize_shared_state(self):
    """Create necessary directories and template files."""
    # Create directories
    (self.shared_state / "constraints").mkdir(parents=True, exist_ok=True)
    (self.shared_state / "conflicts").mkdir(parents=True, exist_ok=True)
    (self.shared_state / "logs").mkdir(parents=True, exist_ok=True)

    # Create empty conflicts file if doesn't exist
    conflicts_file = self.shared_state / "conflicts" / "active.json"
    if not conflicts_file.exists():
        with open(conflicts_file, 'w') as f:
            json.dump({"conflicts": [], "resolved": [], "next_conflict_id": 1}, f)
```

#### c) Add better status reporting
```python
def get_next_actions(self) -> List[str]:
    """Determine what agents should be spawned next."""
    actions = []

    if self.should_spawn_architect():
        actions.append("spawn_architect")

    for subsystem in ["skeleton", "actuation", "power"]:
        if self.should_spawn_subsystem(subsystem):
            actions.append(f"spawn_{subsystem}")

    return actions
```

---

### 5. **Better Conflict Management** (MEDIUM PRIORITY)

**Current**: Simple JSON append

**Improvements**:

#### a) Add conflict priorities
```json
{
  "id": 1,
  "priority": 1,  // 1=critical, 2=high, 3=medium, 4=low
  "severity": "critical",
  "blocks": ["actuation"],  // Which agents are blocked
  "created_at": "2025-01-15T10:30:00Z",
  "must_resolve_before_proceeding": true
}
```

#### b) Update agent prompts to respect priorities
```markdown
## Checking Conflicts

Before starting, read `conflicts/active.json`.

If there are conflicts with priority=1 (critical) that block you:
- Don't proceed with design
- Report that you're blocked
- Suggest System Architect should resolve first
```

---

### 6. **Add State Visualization** (LOW PRIORITY)

Create a simple status viewer that Claude Code can run:

```python
# humanoid_agents/view_status.py
from orchestration_helpers import create_orchestrator

def main():
    orch = create_orchestrator()
    print(orch.get_design_summary())

    next_actions = orch.get_next_actions()
    print("\nRecommended next actions:")
    for action in next_actions:
        print(f"  - {action}")

if __name__ == "__main__":
    main()
```

**Usage by Claude Code**:
```bash
python humanoid_agents/view_status.py
```

---

### 7. **Documentation Updates** (MEDIUM PRIORITY)

**Files to update**:

#### a) Main README.md
- Remove references to `launch_agents.py` process approach
- Add section "How This Works with Claude Code"
- Update quick start to just say "Ask Claude Code to start the design"

#### b) Consolidate documentation
**Current**: 4 README files (confusing!)
- README.md
- AGENTS_README.md
- README_AGENTS.md
- HOW_TO_USE.md

**Proposed structure**:
```
README.md           -> Main overview, architecture, quick start
docs/
  ARCHITECTURE.md   -> Detailed architecture explanation
  AGENT_GUIDE.md    -> Writing new agents
  CLAUDE_CODE.md    -> How Claude Code orchestrates (the new one I created)
```

---

### 8. **Testing Strategy** (LOW PRIORITY but important)

**Challenge**: Testing subagent interactions is hard

**Approach**:

#### a) Test shared state utilities
```python
# tests/test_shared_state.py
def test_read_write_json():
    state = SharedState("./test_shared_state")
    state.write_json("test.json", {"foo": "bar"})
    data = state.read_json("test.json")
    assert data["foo"] == "bar"
```

#### b) Test orchestration helpers
```python
# tests/test_orchestration.py
def test_should_spawn_architect_no_constraints():
    orch = SubagentOrchestrator(test_path)
    assert orch.should_spawn_architect() == True
```

#### c) Mock agent prompts
```python
# tests/test_agent_prompts.py
def test_all_prompts_load():
    orch = SubagentOrchestrator()
    for agent in ["system_architect", "skeleton_designer", "actuation_designer"]:
        prompt = orch.get_agent_prompt(agent)
        assert len(prompt) > 0
        assert "IMPORTANT" in prompt  # Check for completion emphasis
```

---

## Summary of Priority Actions

### Do Immediately:
1. ✓ Create `orchestration_helpers.py` (DONE)
2. ✓ Create `CLAUDE_CODE_WORKFLOW.md` (DONE)
3. ✓ Update `skeleton_designer.md` prompt (DONE)
4. Move API-based files to `deprecated/`
5. Update remaining agent prompts (system_architect, actuation_designer)

### Do Soon:
6. Add JSON schemas for validation
7. Add initialization helpers to orchestration_helpers.py
8. Consolidate documentation (merge 4 READMEs)
9. Add state validation checks

### Do Later:
10. Add comprehensive testing
11. Add state visualization tools
12. Improve conflict management with priorities
13. Add CI/CD for shared state validation

---

## Key Architectural Principles

1. **Subagents are one-shot**: They complete their task and finish, not long-running
2. **Communication is filesystem-only**: No API calls, no message queues
3. **Claude Code is the orchestrator**: Not a Python script
4. **State is the source of truth**: shared_state/ contains everything
5. **Agents are autonomous**: They make engineering decisions, not just follow scripts

---

## What Success Looks Like

User: "Design a humanoid robot"

Claude Code (you):
```
1. Check shared_state/ (nothing exists)
2. Spawn System Architect
   -> Architect creates budgets and requirements
3. Check results
4. Spawn Skeleton + Actuation in parallel
   -> Both complete designs
5. Check for conflicts
6. If conflicts, spawn Architect to resolve
7. Iterate until complete
8. Report final design to user
```

**No Python processes, no API management, just pure orchestration!**
