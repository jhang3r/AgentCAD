"""
Shared state management utilities for multi-agent humanoid design system.
Provides thread-safe read/write access to the shared filesystem database.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime
import threading

class SharedState:
    """Manages shared state between agents via filesystem JSON database."""

    def __init__(self, base_path: str = "./shared_state"):
        self.base_path = Path(base_path)
        self.lock = threading.RLock()

    def read_json(self, relative_path: str) -> Optional[Dict[str, Any]]:
        """Thread-safe read of JSON file."""
        full_path = self.base_path / relative_path

        with self.lock:
            if not full_path.exists():
                return None

            try:
                with open(full_path, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                print(f"Error reading {relative_path}: {e}")
                return None

    def write_json(self, relative_path: str, data: Dict[str, Any], timestamp: bool = True):
        """Thread-safe write of JSON file with optional timestamping."""
        full_path = self.base_path / relative_path

        if timestamp and isinstance(data, dict):
            data['timestamp'] = datetime.utcnow().isoformat()

        with self.lock:
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, 'w') as f:
                json.dump(data, f, indent=2)

    def get_global_constraints(self) -> Dict[str, Any]:
        """Get global design constraints."""
        return self.read_json("constraints/global.json") or {}

    def get_subsystem_status(self, subsystem: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific subsystem."""
        return self.read_json(f"subsystems/{subsystem}/status.json")

    def update_subsystem_status(self, subsystem: str, status: Dict[str, Any]):
        """Update status of a specific subsystem."""
        self.write_json(f"subsystems/{subsystem}/status.json", status)

    def get_subsystem_interfaces(self, subsystem: str) -> Optional[Dict[str, Any]]:
        """Get interface definitions published by a subsystem."""
        return self.read_json(f"subsystems/{subsystem}/interfaces.json")

    def update_subsystem_interfaces(self, subsystem: str, interfaces: Dict[str, Any]):
        """Update interface definitions for a subsystem."""
        self.write_json(f"subsystems/{subsystem}/interfaces.json", interfaces)

    def get_subsystem_requirements(self, subsystem: str) -> Optional[Dict[str, Any]]:
        """Get requirements consumed by a subsystem."""
        return self.read_json(f"subsystems/{subsystem}/requirements.json")

    def update_subsystem_requirements(self, subsystem: str, requirements: Dict[str, Any]):
        """Update requirements for a subsystem."""
        self.write_json(f"subsystems/{subsystem}/requirements.json", requirements)

    def log_conflict(self, severity: str, source: str, target: str, description: str, details: Dict[str, Any] = None):
        """Log a constraint conflict."""
        conflicts_data = self.read_json("conflicts/active.json") or {"conflicts": [], "resolved": [], "next_conflict_id": 1}

        conflict = {
            "id": conflicts_data["next_conflict_id"],
            "timestamp": datetime.utcnow().isoformat(),
            "severity": severity,  # "critical", "high", "medium", "low"
            "source_agent": source,
            "target_agent": target,
            "description": description,
            "details": details or {},
            "status": "open"
        }

        conflicts_data["conflicts"].append(conflict)
        conflicts_data["next_conflict_id"] += 1

        self.write_json("conflicts/active.json", conflicts_data, timestamp=False)
        return conflict["id"]

    def resolve_conflict(self, conflict_id: int, resolution: str):
        """Mark a conflict as resolved."""
        conflicts_data = self.read_json("conflicts/active.json")
        if not conflicts_data:
            return

        for conflict in conflicts_data["conflicts"]:
            if conflict["id"] == conflict_id:
                conflict["status"] = "resolved"
                conflict["resolution"] = resolution
                conflict["resolved_at"] = datetime.utcnow().isoformat()
                conflicts_data["resolved"].append(conflict)
                conflicts_data["conflicts"].remove(conflict)
                break

        self.write_json("conflicts/active.json", conflicts_data, timestamp=False)

    def get_active_conflicts(self, agent_name: Optional[str] = None) -> list:
        """Get all active conflicts, optionally filtered by agent."""
        conflicts_data = self.read_json("conflicts/active.json")
        if not conflicts_data:
            return []

        conflicts = conflicts_data.get("conflicts", [])

        if agent_name:
            conflicts = [c for c in conflicts if c["source_agent"] == agent_name or c["target_agent"] == agent_name]

        return conflicts

    def log_agent_activity(self, agent_name: str, activity: str, details: Dict[str, Any] = None):
        """Log agent activity for monitoring."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent": agent_name,
            "activity": activity,
            "details": details or {}
        }

        # Append to daily log file
        log_date = datetime.utcnow().strftime("%Y-%m-%d")
        log_file = f"logs/{log_date}.jsonl"

        full_path = self.base_path / log_file
        full_path.parent.mkdir(parents=True, exist_ok=True)

        with self.lock:
            with open(full_path, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
