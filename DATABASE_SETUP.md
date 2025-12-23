# Database Setup - Local Supabase for Parallel Agent Execution

This guide shows you how to set up the local Supabase (PostgreSQL) database for parallel multi-agent execution.

## Why Database Instead of Filesystem?

**Filesystem (old approach):**
- ✗ Only one agent can safely write at a time
- ✗ Race conditions with concurrent access
- ✗ No transactions or rollback
- ✗ Manual locking required

**Database (new approach):**
- ✓ Multiple agents can run in parallel
- ✓ ACID transactions with automatic rollback
- ✓ Built-in locking and concurrency control
- ✓ Real-time monitoring and logging
- ✓ Proper conflict resolution

## Prerequisites

- Docker and Docker Compose installed
- Python 3.9+ with pip

## Quick Start

### 1. Start the Database

```bash
# From project root
docker-compose up -d
```

This starts:
- PostgreSQL database (port 5432)
- PostgREST API (port 8000)
- Supabase Studio UI (port 3000)

### 2. Install Python Dependencies

```bash
cd humanoid_agents
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# The defaults should work for local development:
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/agentcad
SUPABASE_URL=http://localhost:8000
```

### 4. Initialize Database

```bash
python database/init_db.py
```

This will:
- Wait for PostgreSQL to be ready
- Create all tables and indexes
- Migrate any existing filesystem data
- Initialize default configuration

### 5. Verify Setup

**Option A: Use Supabase Studio (GUI)**
```bash
# Open in browser
http://localhost:3000
```

**Option B: Use psql (CLI)**
```bash
psql postgresql://postgres:postgres@localhost:5432/agentcad

# Run a test query
SELECT * FROM subsystems;
SELECT * FROM system_status;
```

**Option C: Use Python**
```python
from utils.shared_state import SharedState

state = SharedState()
statuses = state.get_all_subsystem_statuses()
print(statuses)
state.close()
```

## Database Schema

### Tables

1. **global_constraints** - Budget allocations and hard constraints
2. **subsystems** - Status of each subsystem (skeleton, actuation, etc.)
3. **subsystem_requirements** - Requirements for each subsystem (versioned)
4. **subsystem_interfaces** - Interfaces published by subsystems (versioned)
5. **subsystem_designs** - Detailed design data (versioned)
6. **conflicts** - Active and resolved conflicts
7. **agent_activity_logs** - Activity logging for monitoring
8. **agent_locks** - Resource locking for coordination

### Views

1. **system_status** - Current status of all subsystems with conflict counts

## Using the Database

### Basic Operations

```python
from utils.shared_state import SharedState

# Create connection
state = SharedState(execution_id="my-agent-123")

# Read global constraints
constraints = state.get_global_constraints()

# Update subsystem status
state.update_subsystem_status("skeleton", {
    "state": "complete",
    "current_mass_kg": 12.5,
    "current_cost_usd": 2400,
    "within_budget": True
})

# Get all subsystems
all_status = state.get_all_subsystem_statuses()

# Log activity
state.log_agent_activity("skeleton_agent", "design_complete", {
    "bones_designed": 6,
    "joints_designed": 10
})

# Close connection when done
state.close()
```

### Locking for Exclusive Access

```python
from utils.shared_state import SharedState

state = SharedState(execution_id="my-agent-123")

# Try to acquire lock
if state.acquire_lock("subsystem", "skeleton", "skeleton_agent"):
    try:
        # Do work with exclusive access
        status = state.get_subsystem_status("skeleton")
        # ... modify ...
        state.update_subsystem_status("skeleton", status)
    finally:
        # Always release lock
        state.release_lock("subsystem", "skeleton")
else:
    print("Resource is locked by another agent")

state.close()
```

### Conflict Management

```python
from utils.shared_state import SharedState

state = SharedState(execution_id="my-agent-123")

# Log a conflict
conflict_id = state.log_conflict(
    severity="high",
    source="actuation_agent",
    target="system_architect",
    description="Motor selection exceeds power budget by 200W",
    details={
        "current_power_w": 1000,
        "budget_w": 800,
        "overage_w": 200
    },
    priority=2,  # 1=critical, 2=high, 3=medium, 4=low
    blocks=["power_agent"]  # Which agents are blocked by this
)

# Get active conflicts for an agent
conflicts = state.get_active_conflicts("actuation_agent")

# Resolve a conflict
state.resolve_conflict(
    conflict_id=1,
    resolution="Reduced motor count from 30 to 24 DOF",
    resolved_by="actuation_agent"
)

state.close()
```

## Parallel Agent Execution

The database enables true parallel execution:

```python
# In Claude Code, spawn multiple agents in parallel:
Task(subagent_type="general-purpose", description="Skeleton Designer", prompt=skeleton_prompt)
Task(subagent_type="general-purpose", description="Actuation Designer", prompt=actuation_prompt)
Task(subagent_type="general-purpose", description="Power Designer", prompt=power_prompt)
```

All three agents can:
- Read shared state simultaneously
- Write to different subsystems safely
- Use locks when modifying shared resources
- Log conflicts without race conditions

## Monitoring

### View Real-Time Status

```bash
# Watch system status
watch -n 1 'psql postgresql://postgres:postgres@localhost:5432/agentcad -c "SELECT * FROM system_status;"'
```

### View Agent Activity

```python
from utils.shared_state import SharedState

state = SharedState()

# Get recent activity across all agents
activity = state.get_recent_activity(limit=20)
for entry in activity:
    print(f"[{entry['timestamp']}] {entry['agent_name']}: {entry['activity']}")

# Get activity for specific agent
skeleton_activity = state.get_recent_activity(agent_name="skeleton_agent")

state.close()
```

### Supabase Studio

Open http://localhost:3000 for a full database GUI:
- Browse tables and data
- Run custom SQL queries
- View realtime updates
- Monitor performance

## Stopping the Database

```bash
# Stop containers (data persists)
docker-compose stop

# Stop and remove containers (data persists in volume)
docker-compose down

# Stop and DELETE all data
docker-compose down -v
```

## Troubleshooting

### Database won't start

```bash
# Check logs
docker-compose logs db

# Ensure port 5432 is not in use
netstat -an | grep 5432
```

### Connection refused

```bash
# Wait for database to be fully ready
python database/init_db.py
```

### Migration issues

```bash
# Reset database completely
docker-compose down -v
docker-compose up -d
python database/init_db.py
```

### Lock timeouts

Locks automatically expire after 5 minutes. To manually clean:

```sql
-- Connect to database
psql postgresql://postgres:postgres@localhost:5432/agentcad

-- Clean expired locks
SELECT cleanup_expired_locks();

-- View current locks
SELECT * FROM agent_locks;

-- Force remove a specific lock
DELETE FROM agent_locks WHERE resource_name = 'skeleton';
```

## Performance Tuning

For production or heavy parallel workloads:

1. **Increase connection pool size:**
```python
# In shared_state.py, increase maxconn
self._pool = ThreadedConnectionPool(
    minconn=5,
    maxconn=50,  # Increase from 10
    dsn=self.db_url
)
```

2. **Add database indexes:**
```sql
-- For heavy conflict queries
CREATE INDEX idx_conflicts_source_target ON conflicts(source_agent, target_agent);

-- For activity log queries
CREATE INDEX idx_activity_execution ON agent_activity_logs(execution_id, timestamp DESC);
```

3. **Enable query logging:**
```yaml
# In docker-compose.yml, add to db service
environment:
  POSTGRES_LOG_STATEMENT: all
```

## Next Steps

- Read [CLAUDE_CODE_WORKFLOW.md](CLAUDE_CODE_WORKFLOW.md) for orchestration patterns
- See [IMPROVEMENTS_SUBAGENT_ARCHITECTURE.md](IMPROVEMENTS_SUBAGENT_ARCHITECTURE.md) for architecture details
- Check [humanoid_agents/README.md](humanoid_agents/README.md) for system overview
