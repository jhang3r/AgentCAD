"""
Multi-Agent CAD Collaboration Framework

Enables multiple AI agents to work simultaneously on CAD design tasks with role-based
specialization, workspace isolation, and coordinated execution.

Core components:
- Controller: Orchestrates multiple agents, manages task assignment
- Roles: Defines agent capabilities and constraints
- Messaging: Agent-to-agent communication
- Task Decomposer: High-level goal decomposition

All CAD operations executed via JSON-RPC CLI subprocess calls to the existing
CAD environment (001-cad-environment).
"""

__version__ = "0.1.0"

__all__ = ["Controller", "RoleTemplate", "Agent"]
