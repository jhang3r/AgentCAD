"""
Helper functions for Claude Code to orchestrate subagents.
These are NOT standalone - they're called BY Claude Code.
"""

from pathlib import Path
import json
from typing import Dict, Any, List


class SubagentOrchestrator:
    """Helpers for Claude Code to manage subagents via Task tool."""

    def __init__(self, project_root: Path = None):
        if project_root is None:
            project_root = Path(__file__).parent
        self.project_root = project_root
        self.shared_state = project_root / "shared_state"
        self.prompts = project_root / "agent_prompts"

    def get_agent_prompt(self, agent_name: str) -> str:
        """Load an agent prompt for Task tool."""
        prompt_file = self.prompts / f"{agent_name}.md"
        if not prompt_file.exists():
            raise FileNotFoundError(f"Agent prompt not found: {prompt_file}")

        with open(prompt_file, 'r') as f:
            return f.read()

    def get_subsystem_status(self, subsystem: str) -> Dict[str, Any]:
        """Get current status of a subsystem."""
        status_file = self.shared_state / "subsystems" / subsystem / "status.json"
        if not status_file.exists():
            return {"state": "not_started"}

        with open(status_file, 'r') as f:
            return json.load(f)

    def get_all_subsystem_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all subsystems."""
        statuses = {}
        subsystems = ["skeleton", "actuation", "power", "sensing", "shell", "integration"]

        for subsystem in subsystems:
            statuses[subsystem] = self.get_subsystem_status(subsystem)

        return statuses

    def get_active_conflicts(self) -> List[Dict[str, Any]]:
        """Get all active conflicts."""
        conflicts_file = self.shared_state / "conflicts" / "active.json"
        if not conflicts_file.exists():
            return []

        with open(conflicts_file, 'r') as f:
            data = json.load(f)
            return data.get("conflicts", [])

    def get_global_totals(self) -> Dict[str, float]:
        """Calculate total mass and cost across all subsystems."""
        statuses = self.get_all_subsystem_statuses()

        total_mass = 0.0
        total_cost = 0.0

        for status in statuses.values():
            total_mass += status.get("current_mass_kg", 0.0)
            total_cost += status.get("current_cost_usd", 0.0)

        return {
            "total_mass_kg": total_mass,
            "total_cost_usd": total_cost
        }

    def should_spawn_architect(self) -> bool:
        """Determine if System Architect should run."""
        constraints_file = self.shared_state / "constraints" / "global.json"

        # Run if constraints don't exist
        if not constraints_file.exists():
            return True

        # Run if there are active conflicts
        if len(self.get_active_conflicts()) > 0:
            return True

        return False

    def should_spawn_subsystem(self, subsystem: str) -> bool:
        """Determine if a subsystem agent should run."""
        status = self.get_subsystem_status(subsystem)
        state = status.get("state", "not_started")

        # Run if not started
        if state == "not_started":
            return True

        # Don't run if complete
        if state == "complete":
            return False

        # Run if has conflicts
        conflicts = self.get_active_conflicts()
        has_conflict = any(
            subsystem in c.get("source_agent", "") or
            subsystem in c.get("target_agent", "")
            for c in conflicts
        )

        return has_conflict

    def get_design_summary(self) -> str:
        """Get human-readable summary of current design state."""
        statuses = self.get_all_subsystem_statuses()
        conflicts = self.get_active_conflicts()
        totals = self.get_global_totals()

        summary = "=== HUMANOID DESIGN STATUS ===\n\n"

        summary += "Subsystems:\n"
        for name, status in statuses.items():
            state = status.get("state", "not_started")
            mass = status.get("current_mass_kg", 0)
            cost = status.get("current_cost_usd", 0)
            summary += f"  {name:15s}: {state:15s} {mass:6.2f}kg  ${cost:8.2f}\n"

        summary += f"\nTotals:\n"
        summary += f"  Mass: {totals['total_mass_kg']:.2f} kg\n"
        summary += f"  Cost: ${totals['total_cost_usd']:.2f}\n"

        summary += f"\nActive Conflicts: {len(conflicts)}\n"
        for c in conflicts:
            summary += f"  [{c.get('severity')}] {c.get('description')}\n"

        return summary


def create_orchestrator():
    """Factory function for Claude Code to use."""
    return SubagentOrchestrator()
