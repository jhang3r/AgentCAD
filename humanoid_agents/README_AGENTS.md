# Humanoid Robot Multi-Agent System

True autonomous multi-agent system where I (Claude Code) spawn specialized agents using the Task tool. Each agent is a full Claude instance with reasoning, decision-making, and tool access.

## How It Works

When you say **"start the humanoid design system"**, I will:

1. **Spawn System Architect Agent** using Task tool
   - Reads global requirements
   - Decomposes into subsystem specs
   - Allocates budgets (mass, cost, power)
   - Writes requirements files

2. **Spawn Subsystem Agents in Parallel**
   - Skeleton Designer Agent
   - Actuation Designer Agent
   - Power Designer Agent (future)
   - Each reads its requirements and designs autonomously

3. **Monitor and Iterate**
   - Check shared_state for conflicts
   - Respawn architect to resolve conflicts
   - Respawn subsystem agents to iterate
   - Continue until convergence

## Agent Communication

All agents communicate through `humanoid_agents/shared_state/`:

```
shared_state/
├── constraints/global.json       # System architect writes budgets
├── subsystems/
│   ├── skeleton/
│   │   ├── requirements.json     # Architect writes, skeleton reads
│   │   ├── status.json           # Skeleton writes progress
│   │   ├── interfaces.json       # Skeleton publishes mounting points
│   │   └── geometry/             # Skeleton generates CAD files
│   └── actuation/
│       ├── requirements.json     # Architect writes torque specs
│       ├── status.json           # Actuation writes progress
│       └── interfaces.json       # Actuation publishes power needs
└── conflicts/active.json         # Agents report conflicts
```

## To Start

Just tell me: **"Launch the humanoid design agents"**

I'll spawn them using the Task tool and orchestrate their collaboration!
