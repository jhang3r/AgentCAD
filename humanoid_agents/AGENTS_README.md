# Humanoid Robot Multi-Agent System - Skills-Based

This is a **true multi-agent system** where each agent is a full Claude AI instance with reasoning capabilities, spawned as Skills.

## Architecture

```
You (in Claude Code)
    │
    ├─> humanoid-architect-agent     (System coordinator)
    │
    ├─> humanoid-skeleton-agent      (Structural design)
    │
    ├─> humanoid-actuation-agent     (Motors & transmissions)
    │
    ├─> humanoid-power-agent         (Batteries & wiring) [TODO]
    │
    └─> [other agents...]
```

## Available Agent Skills

### 1. `humanoid-architect-agent`
**System Architect** - Top-level coordinator
- Decomposes requirements into subsystem specs
- Allocates mass/cost/power budgets
- Monitors all subsystems
- Resolves conflicts
- Validates integration

### 2. `humanoid-skeleton-agent`
**Skeleton Designer** - Structural engineer
- Designs bones (femur, tibia, humerus, etc.)
- Designs joint housings and bearings
- Calculates structural loads
- Publishes mounting interfaces
- Uses `modeling-agent` to generate CAD geometry

### 3. `humanoid-actuation-agent`
**Actuation Designer** - Motor specialist
- Selects motors for each joint
- Designs transmissions (gears/belts)
- Designs motor mounts
- Calculates power requirements
- Checks fitment and clearances

## How to Use

### Step 1: Initialize the System

I'll spawn the System Architect first to set up requirements:

```
Please spawn: humanoid-architect-agent
```

The architect will:
- Read `config/global_requirements.json`
- Create budget allocations in `constraints/global.json`
- Write requirements for each subsystem
- Report initial status

### Step 2: Spawn Subsystem Agents

Once the architect has initialized, spawn the subsystem agents **in parallel**:

```
Please spawn: humanoid-skeleton-agent, humanoid-actuation-agent
```

Each agent will:
- Read its requirements
- Make autonomous design decisions
- Generate CAD geometry (using `modeling-agent`)
- Publish interfaces for other agents
- Report conflicts if budgets exceeded

### Step 3: Iterate

Agents communicate through the shared filesystem. When conflicts occur:

1. Agent reports conflict to `shared_state/conflicts/active.json`
2. Respawn the architect: `humanoid-architect-agent`
3. Architect resolves conflict (adjusts budgets, requests changes)
4. Respawn affected agents to iterate

### Step 4: Monitor Progress

Check `shared_state/subsystems/*/status.json` to see progress:

```json
{
  "state": "designing",
  "iteration": 3,
  "current_mass_kg": 12.5,
  "current_cost_usd": 2400,
  "bones_designed": 6,
  "joints_designed": 10
}
```

### Step 5: Integration

When all agents reach "complete" state, spawn:

```
humanoid-integration-agent  [TODO - not yet created]
```

This will assemble all STEP files and generate the final BOM.

## Shared State Structure

```
humanoid_agents/
├── shared_state/
│   ├── constraints/
│   │   └── global.json              # Budgets, limits
│   ├── subsystems/
│   │   ├── skeleton/
│   │   │   ├── requirements.json    # Joints, loads
│   │   │   ├── status.json          # Progress
│   │   │   ├── interfaces.json      # Mounting points
│   │   │   ├── design.json          # Complete spec
│   │   │   └── geometry/
│   │   │       ├── femur_r.step
│   │   │       └── ...
│   │   ├── actuation/
│   │   │   ├── requirements.json    # Torques, speeds
│   │   │   ├── status.json
│   │   │   ├── interfaces.json      # Motor specs, power
│   │   │   └── geometry/
│   │   └── ...
│   ├── conflicts/
│   │   └── active.json              # Current conflicts
│   └── logs/
│       └── 2025-11-30.jsonl         # Activity log
└── config/
    └── global_requirements.json     # Top-level specs
```

## Example Workflow

```
You: "Start designing a humanoid robot"

Step 1: Spawn the architect
> humanoid-architect-agent

[Architect initializes system, writes requirements]

Step 2: Spawn subsystem designers in parallel
> humanoid-skeleton-agent
> humanoid-actuation-agent

[Agents design autonomously, publish interfaces]

Step 3: Check for conflicts
> Read: shared_state/conflicts/active.json

[Conflict found: "Skeleton mass exceeded budget by 2.5kg"]

Step 4: Respawn architect to resolve
> humanoid-architect-agent

[Architect adjusts budgets or requests design changes]

Step 5: Respawn skeleton agent to iterate
> humanoid-skeleton-agent

[Agent redesigns with new constraints]

Repeat until convergence!
```

## Agent Communication Pattern

```
Skeleton Agent:
  1. Reads: subsystems/skeleton/requirements.json
  2. Designs bones with dimensions
  3. Writes: subsystems/skeleton/status.json (mass, cost)
  4. Writes: subsystems/skeleton/interfaces.json (mounting points)

Actuation Agent:
  1. Reads: subsystems/skeleton/interfaces.json (mounting points)
  2. Selects motors that fit
  3. Writes: subsystems/actuation/status.json (power requirements)
  4. Writes: subsystems/actuation/interfaces.json (power draw)

Architect:
  1. Reads: ALL subsystems/*/status.json
  2. Validates budgets (sum of all masses ≤ 45kg)
  3. Reads: conflicts/active.json
  4. Resolves or escalates conflicts
  5. Updates: constraints/global.json
```

## Real AI Agents!

Each agent is a full Claude instance that:
- **Reasons** about design trade-offs
- **Makes decisions** autonomously (motor selection, dimensions, materials)
- **Uses tools** (Read, Write, modeling-agent for CAD)
- **Detects conflicts** and proposes solutions
- **Iterates** based on feedback from other agents

This is NOT hard-coded logic - these are real AI agents collaborating!

## Next Steps

1. Spawn `humanoid-architect-agent` to initialize
2. Spawn `humanoid-skeleton-agent` to start designing
3. Spawn `humanoid-actuation-agent` in parallel
4. Monitor `shared_state/` and iterate
5. Create more agent skills (power, sensing, shell, integration)

Ready to start? Just tell me:
**"Spawn: humanoid-architect-agent"**
