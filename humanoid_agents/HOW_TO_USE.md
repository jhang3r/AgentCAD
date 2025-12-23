# How to Use the Humanoid Multi-Agent Design System

## What This Is

A true multi-agent system where **I (Claude Code) spawn independent agent instances** using the Task tool. Each agent is a full Claude AI that:
- Reads requirements from shared state
- Makes autonomous engineering decisions
- Generates designs (dimensions, materials, costs)
- Publishes interfaces for other agents
- Detects and reports conflicts

## Quick Start

### Step 1: Initialize

Tell me: **"Launch the System Architect agent"**

I will spawn an agent using the Task tool with the prompt from `agent_prompts/system_architect.md`. The agent will:
- Read `config/global_requirements.json`
- Allocate budgets to subsystems
- Write requirements files for skeleton and actuation
- Report when ready for subsystem agents

### Step 2: Launch Designers

Tell me: **"Launch the Skeleton and Actuation agents in parallel"**

I'll spawn both agents simultaneously using the Task tool. They will:
- **Skeleton**: Design bones, joints, bearings → publish mounting interfaces
- **Actuation**: Select motors, design transmissions → publish power requirements

### Step 3: Monitor

Tell me: **"Check the design progress"**

I'll read `shared_state/subsystems/*/status.json` and show you:
- What state each agent is in
- Current mass and cost
- Whether budgets are met
- Active conflicts

### Step 4: Iterate

If there are conflicts:

Tell me: **"Respawn the Architect to resolve conflicts"**

The architect will read conflicts and:
- Adjust budgets
- Request design changes
- Mark conflicts as resolved

Then: **"Respawn the Skeleton agent to iterate"**

The agent will redesign based on new constraints.

## Detailed Commands

### Spawning Agents

**System Architect**: "Launch the System Architect"
- Initializes system, allocates budgets
- Use this first, or to resolve conflicts

**Skeleton Designer**: "Launch the Skeleton Designer"
- Designs complete skeletal structure
- Publishes mounting interfaces

**Actuation Designer**: "Launch the Actuation Designer"
- Selects motors and transmissions
- Publishes power requirements

**Parallel Launch**: "Launch Skeleton and Actuation in parallel"
- Spawns both at once for efficiency

### Monitoring

**Check Status**: "Show me the design status"
- I'll read all status.json files

**Check Conflicts**: "Are there any conflicts?"
- I'll read conflicts/active.json

**Check Budget**: "What's the total mass and cost?"
- I'll sum all subsystem values

**Show Interfaces**: "Show the skeleton interfaces"
- I'll read skeleton interfaces.json

## File Structure

```
humanoid_agents/
├── config/
│   └── global_requirements.json    # Top-level specs (you can edit)
├── shared_state/                   # Agent communication
│   ├── constraints/
│   │   └── global.json             # Architect writes budgets
│   ├── subsystems/
│   │   ├── skeleton/
│   │   │   ├── requirements.json   # Architect → Skeleton
│   │   │   ├── status.json         # Skeleton reports progress
│   │   │   ├── interfaces.json     # Skeleton → Actuation
│   │   │   └── design.json         # Complete bone/joint specs
│   │   └── actuation/
│   │       ├── requirements.json   # Architect → Actuation
│   │       ├── status.json         # Actuation reports progress
│   │       ├── interfaces.json     # Actuation → Power
│   │       └── design.json         # Motor/transmission specs
│   └── conflicts/
│       └── active.json             # All agents can write here
└── agent_prompts/                  # Prompts for Task tool
    ├── system_architect.md
    ├── skeleton_designer.md
    └── actuation_designer.md
```

## Example Session

```
You: "Launch the System Architect agent"

Me: [Spawns agent via Task tool]
Agent: Reads config, writes budgets, creates requirements files
Agent: Reports "System initialized, ready for subsystem agents"

You: "Launch Skeleton and Actuation agents in parallel"

Me: [Spawns both agents via Task tool in one message]
Skeleton Agent: Designs bones, calculates mass, publishes mounting points
Actuation Agent: Selects motors, checks fitment, publishes power needs

You: "Check the status"

Me: [Reads status files]
- Skeleton: complete, 12.5kg / 15kg, $2400 / $3000
- Actuation: complete, 11.2kg / 12kg, $5800 / $6000
- Total: 23.7kg / 45kg, $8200 / $15000
- Conflicts: 0

You: "Perfect! Export the designs"

Me: [Reads design.json files and formats them for you]
```

## Agents Are Truly Autonomous!

Each agent:
- **Decides** what bearing sizes to use
- **Calculates** exact bone dimensions
- **Selects** specific motor models
- **Optimizes** for mass and cost
- **Detects** when budgets are exceeded
- **Reports** status without being asked

They're not scripts - they're AI engineers!

## Ready to Start?

Just say: **"Launch the System Architect agent"**
