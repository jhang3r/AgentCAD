# How Claude Code Orchestrates the Humanoid Design System

This document explains how YOU (Claude Code) should orchestrate the multi-agent design system.

## Architecture

**NOT using**: Anthropic API calls (that's what `ai_agent_base.py` does - wrong!)
**USING**: Claude Code Task tool to spawn real AI subagents

## The Pattern

1. User asks you to start the design
2. You use orchestration helpers to check what needs to run
3. You spawn subagents using the Task tool with prompts from `agent_prompts/`
4. Subagents read/write to `shared_state/` filesystem
5. You monitor progress by reading `shared_state/`
6. You spawn more agents as needed based on state

## Example Session

```
User: "Start designing the humanoid robot"

Claude Code (you):
1. Read orchestration_helpers.py to understand state
2. Check if architect needed (read shared_state/constraints/global.json)
3. Spawn System Architect agent via Task tool
4. Wait for completion
5. Check results in shared_state/
6. Spawn subsystem agents in parallel
7. Monitor and iterate
```

## Step-by-Step: How to Spawn an Agent

### Step 1: Check What Needs to Run

```python
# Read the helper file
from humanoid_agents.orchestration_helpers import create_orchestrator

orch = create_orchestrator()

# Check what needs to run
if orch.should_spawn_architect():
    # Need to run architect
    pass

if orch.should_spawn_subsystem("skeleton"):
    # Need to run skeleton agent
    pass
```

### Step 2: Load Agent Prompt

```python
# Get the prompt
prompt = orch.get_agent_prompt("system_architect")
```

### Step 3: Spawn via Task Tool

```python
# In Claude Code, you would do:
Task(
    subagent_type="general-purpose",
    description="System Architect - allocate budgets",
    prompt=prompt
)
```

### Step 4: Monitor Results

After agent completes:

```python
# Check what it did
summary = orch.get_design_summary()
print(summary)

# Check if more agents needed
if orch.should_spawn_subsystem("skeleton"):
    # Spawn skeleton agent
    pass
```

## Important: Parallel Spawning

You can spawn multiple agents at once by calling Task multiple times in one message:

```python
# Spawn skeleton and actuation agents in parallel
skeleton_prompt = orch.get_agent_prompt("skeleton_designer")
actuation_prompt = orch.get_agent_prompt("actuation_designer")

# Call both in same message:
Task(subagent_type="general-purpose", description="Skeleton Designer", prompt=skeleton_prompt)
Task(subagent_type="general-purpose", description="Actuation Designer", prompt=actuation_prompt)
```

## Typical Flow

### Iteration 0: Initialize

```
You: Check if constraints exist
    -> No
You: Spawn System Architect
    -> Architect reads config/global_requirements.json
    -> Architect writes constraints/global.json
    -> Architect writes subsystems/*/requirements.json
    -> Architect finishes
You: Read results, report to user
```

### Iteration 1: Design Subsystems

```
You: Check what needs to run
    -> skeleton: not_started
    -> actuation: not_started
You: Spawn both in parallel
    -> Skeleton reads requirements, designs bones, writes outputs
    -> Actuation reads requirements, selects motors, writes outputs
    -> Both finish
You: Read results, report to user
```

### Iteration 2: Resolve Conflicts (if any)

```
You: Check conflicts
    -> Conflict: skeleton over mass budget
You: Spawn System Architect to resolve
    -> Architect reads conflict
    -> Architect adjusts budgets
    -> Architect marks conflict resolved
    -> Architect finishes
You: Spawn skeleton agent to redesign
    -> Skeleton reads new budget
    -> Skeleton redesigns lighter
    -> Skeleton finishes
You: Check results, report to user
```

## Key Differences from Traditional Approach

**Traditional** (what ai_agent_base.py does):
- Long-running Python processes
- Direct API calls to Anthropic
- Polling loops with sleep()
- Process management headaches

**Subagent Approach** (what you should use):
- Spawn agent when needed
- Agent does complete work
- Agent finishes (no long-running process)
- Communication via filesystem only
- You orchestrate, they execute

## Files You Should Use

✓ `orchestration_helpers.py` - Helper functions
✓ `agent_prompts/*.md` - Agent prompts for Task tool
✓ `shared_state/` - Communication filesystem

## Files You Should IGNORE/DEPRECATE

✗ `ai_agent_base.py` - Uses API directly
✗ `ai_skeleton_agent.py` - Uses API directly
✗ `orchestrator.py` - Standalone script (you ARE the orchestrator)
✗ `launch_agents.py` - Old process-based approach
✗ `base_agent.py` - Process-based approach

## Summary

**You (Claude Code) are the orchestrator.**

You don't call the Anthropic API yourself.
You spawn subagents using Task tool.
They communicate via shared_state/ filesystem.
You monitor and decide what to spawn next.

Simple!
