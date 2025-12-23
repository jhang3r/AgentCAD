# Humanoid Robot Multi-Agent Design System

Autonomous multi-agent system for designing complete humanoid robots from scratch. Agents work in parallel to design subsystems, resolve conflicts, and produce manufacturable CAD models.

## Architecture

### Agent Hierarchy

```
System Architect (Top-level coordinator)
├── Skeleton Agent (Bones, joints, structure)
├── Actuation Agent (Motors, transmissions)
├── Power Agent (Batteries, distribution) [TODO]
├── Sensing Agent (IMUs, encoders, cameras) [TODO]
├── Shell Agent (Exterior panels, aesthetics) [TODO]
└── Integration Agent (Assembly, BOM) [TODO]
```

### Design Philosophy

- **Fully Autonomous**: Agents design without human intervention
- **Constraint-Based**: Continuous validation of mass, cost, power budgets
- **Conflict Resolution**: Automatic negotiation between subsystems
- **Real Geometry**: Not just planning - actual CAD models (OOCCT integration)

## Current Status

**Implemented:**
- ✓ System Architect agent
- ✓ Skeleton subsystem agent
- ✓ Actuation subsystem agent
- ✓ Shared state filesystem database
- ✓ Conflict detection and logging
- ✓ Real-time monitoring dashboard
- ✓ Multi-agent launcher

**In Progress:**
- ⚙ OOCCT geometry generation integration
- ⚙ Power subsystem agent
- ⚙ Sensing subsystem agent

**Planned:**
- ○ Shell subsystem agent
- ○ Integration agent
- ○ FEA structural validation
- ○ Kinematics validation
- ○ Manufacturing validation (DFM)
- ○ STEP export for Fusion360

## Quick Start

### Installation

```bash
cd humanoid_agents
pip install -r requirements.txt  # (will be created)
```

### Running the System

**Option 1: Launch all agents** (recommended)
```bash
python launch_agents.py
```

**Option 2: Run agents individually** (for debugging)
```bash
# Terminal 1
python agents/system_architect.py

# Terminal 2
python agents/skeleton_agent.py

# Terminal 3
python agents/actuation_agent.py
```

### Monitoring

In a separate terminal:
```bash
python monitor.py
```

Optional: Specify refresh rate in seconds
```bash
python monitor.py 1.0  # Refresh every 1 second
```

## How It Works

### 1. Initialization
- System Architect reads global requirements from `config/global_requirements.json`
- Decomposes into subsystem requirements
- Writes requirements to `shared_state/subsystems/{name}/requirements.json`

### 2. Design Phase
Each subsystem agent:
1. Reads its requirements
2. Generates design (bones, motors, etc.)
3. Validates against constraints
4. Publishes interfaces for other agents
5. Checks for conflicts
6. Iterates

### 3. Conflict Resolution
When conflicts occur:
- Agent logs conflict to `shared_state/conflicts/active.json`
- System Architect attempts automatic resolution
- Agents adjust designs in response
- Process continues until convergence

### 4. Integration
- All subsystems reach "complete" state
- Integration agent assembles STEP files
- Generates BOM, assembly instructions
- Exports for manufacturing

## Shared State Structure

```
shared_state/
├── constraints/
│   └── global.json          # Global mass, cost, performance limits
├── subsystems/
│   ├── skeleton/
│   │   ├── status.json       # Current state, mass, cost
│   │   ├── interfaces.json   # Published mounting points, envelopes
│   │   ├── requirements.json # Joint specs, loads
│   │   └── geometry.step     # CAD model [TODO]
│   ├── actuation/
│   │   ├── status.json
│   │   ├── interfaces.json   # Motor specs, power requirements
│   │   └── ...
│   └── ...
├── conflicts/
│   └── active.json           # Unresolved conflicts
└── logs/
    └── YYYY-MM-DD.jsonl      # Activity logs
```

## Configuration

Edit `config/global_requirements.json` to change robot specifications:

```json
{
  "physical": {
    "height_m": 1.75,          // Total height
    "mass_kg_max": 45.0,       // Maximum mass
    "degrees_of_freedom": 30   // Total DOF
  },
  "performance": {
    "walking_speed_ms": 1.5,   // Target walking speed
    "payload_capacity_kg": 5.0,
    "battery_life_hours": 4.0
  },
  "constraints": {
    "cost_usd_max": 15000,     // Maximum total cost
    "material_primary": "aluminum_6061"
  }
}
```

## Adding New Agents

1. Create new agent file: `agents/your_agent.py`
2. Inherit from `BaseAgent`
3. Implement `run_iteration()` method
4. Use `SharedState` for communication
5. Add to `launch_agents.py`

Example skeleton:
```python
from base_agent import BaseAgent

class YourAgent(BaseAgent):
    def __init__(self, shared_state_path="./shared_state"):
        super().__init__("YourAgent", "subsystem", shared_state_path)
        self.state = "initializing"

    def run_iteration(self):
        if self.state == "initializing":
            requirements = self.shared_state.get_subsystem_requirements("your_subsystem")
            # ... initialize
            self.state = "designing"

        elif self.state == "designing":
            # ... design logic
            self.publish_interfaces()
            self.check_constraints()

        self.update_status()
```

## Integration with OOCCT (Next Steps)

The system is designed to integrate with Open CASCADE for real geometry generation:

1. **Install OOCCT**: `conda install -c conda-forge pythonocc-core`
2. **Geometry generation**: Agents will use `geometry/generators.py` to create STEP files
3. **Export**: Each subsystem writes `geometry.step` to its shared_state directory
4. **Validation**: Interference checking, mass properties extraction

Example (planned):
```python
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeCylinder
from OCC.Core.gp import gp_Ax2, gp_Pnt, gp_Dir

# Generate bone as hollow cylinder
bone = BRepPrimAPI_MakeCylinder(radius, length).Shape()
# Export to STEP
write_step_file(bone, "shared_state/subsystems/skeleton/femur.step")
```

## Monitoring Dashboard

The monitor displays:
- **Subsystem Status**: State, mass, cost, progress bar
- **Active Conflicts**: Severity, description, involved agents
- **Recent Activity**: Last 5 agent actions
- **Global Constraints**: Total mass/cost vs. budgets

## Human Interaction

The system runs autonomously, but humans can:
- **Stop agents**: Ctrl+C on launcher
- **Inject constraints**: Edit `shared_state/constraints/global.json`
- **Force redesign**: Delete subsystem status files
- **Review logs**: Check `shared_state/logs/`
- **Review conflicts**: Check `shared_state/conflicts/active.json`

## Next Development Priorities

1. **OOCCT Integration** - Generate real STEP geometry
2. **Power Agent** - Battery sizing, wiring design
3. **Kinematics Validator** - Check reachability, singularities
4. **Structural Validator** - FEA using CalculiX
5. **Manufacturing Agent** - DFM checks, toolpath generation

## License

MIT

## Contributing

This is a research/experimental system. Contributions welcome!
