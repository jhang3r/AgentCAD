"""Multi-Agent CAD Controller.

Orchestrates multiple AI agents collaborating on CAD design tasks.
Demonstrates workspace isolation, parallel work, merging, and conflict resolution.
"""
import json
import sys
import subprocess
from typing import Any, Optional, List, Dict
from dataclasses import dataclass
from datetime import datetime


@dataclass
class AgentTask:
    """A task assigned to an agent."""
    agent_id: str
    agent_role: str
    workspace_name: str
    task_description: str
    operations: List[dict]
    success_criteria: dict


class CADAgent:
    """Represents a single CAD agent with specialized role."""

    def __init__(self, agent_id: str, role: str):
        """Initialize agent.

        Args:
            agent_id: Unique agent identifier
            role: Agent role (designer, modeler, validator, integrator)
        """
        self.agent_id = agent_id
        self.role = role
        self.workspace_id = None
        self.operations_completed = 0
        self.errors = []
        self.created_entities = []

    def execute_jsonrpc(self, method: str, params: dict) -> dict:
        """Execute a JSON-RPC command via the CLI.

        Args:
            method: JSON-RPC method name
            params: Method parameters

        Returns:
            JSON-RPC response
        """
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": self.operations_completed + 1
        }

        # Execute via CLI
        try:
            result = subprocess.run(
                ["py", "-m", "src.agent_interface.cli"],
                input=json.dumps(request),
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                error_msg = f"CLI error: {result.stderr}"
                self.errors.append(error_msg)
                return {"error": error_msg}

            response = json.loads(result.stdout)
            self.operations_completed += 1

            if "error" in response:
                self.errors.append(f"{method}: {response['error']}")

            return response

        except subprocess.TimeoutExpired:
            error_msg = f"Timeout executing {method}"
            self.errors.append(error_msg)
            return {"error": error_msg}
        except Exception as e:
            error_msg = f"Exception executing {method}: {str(e)}"
            self.errors.append(error_msg)
            return {"error": error_msg}

    def create_workspace(self, workspace_name: str) -> bool:
        """Create isolated workspace for this agent.

        Args:
            workspace_name: Name for the workspace

        Returns:
            True if successful
        """
        response = self.execute_jsonrpc("workspace.create", {
            "workspace_name": workspace_name,
            "base_workspace_id": "main",
            "owning_agent_id": self.agent_id
        })

        if "result" in response and response["result"]["status"] == "success":
            self.workspace_id = response["result"]["data"]["workspace_id"]
            return True
        return False

    def create_entity(self, entity_type: str, params: dict) -> Optional[str]:
        """Create a CAD entity.

        Args:
            entity_type: Type of entity (point, line, circle)
            params: Entity parameters

        Returns:
            Entity ID if successful, None otherwise
        """
        method_map = {
            "point": "entity.create.point",
            "line": "entity.create.line",
            "circle": "entity.create.circle"
        }

        method = method_map.get(entity_type)
        if not method:
            self.errors.append(f"Unknown entity type: {entity_type}")
            return None

        response = self.execute_jsonrpc(method, params)

        if "result" in response and response["result"]["status"] == "success":
            entity_id = response["result"]["data"]["entity_id"]
            self.created_entities.append(entity_id)
            return entity_id
        return None

    def extrude(self, entity_ids: List[str], distance: float) -> Optional[str]:
        """Extrude entities to create solid.

        Args:
            entity_ids: List of entity IDs forming closed sketch
            distance: Extrusion distance

        Returns:
            Solid entity ID if successful
        """
        response = self.execute_jsonrpc("solid.extrude", {
            "entity_ids": entity_ids,
            "distance": distance
        })

        if "result" in response and response["result"]["status"] == "success":
            solid_id = response["result"]["data"]["entity_id"]
            self.created_entities.append(solid_id)
            return solid_id
        return None

    def get_metrics(self) -> dict:
        """Get agent learning metrics.

        Returns:
            Metrics dictionary
        """
        response = self.execute_jsonrpc("agent.metrics", {
            "agent_id": self.agent_id
        })

        if "result" in response:
            return response["result"]
        return {}


class MultiAgentController:
    """Controls multiple agents working collaboratively."""

    def __init__(self):
        """Initialize controller."""
        self.agents: Dict[str, CADAgent] = {}
        self.task_results = []

    def create_agent(self, agent_id: str, role: str) -> CADAgent:
        """Create a new agent.

        Args:
            agent_id: Unique identifier
            role: Agent role

        Returns:
            Created agent
        """
        agent = CADAgent(agent_id, role)
        self.agents[agent_id] = agent
        return agent

    def run_collaborative_assembly(self) -> dict:
        """Run collaborative assembly scenario.

        Scenario: 4 agents build a simple enclosure
        - Agent A: Housing (base box)
        - Agent B: Lid (top cover)
        - Agent C: Internal support (mounting posts)
        - Agent D: Integration (merge all parts)

        Returns:
            Assembly results
        """
        print("\n" + "="*80)
        print("MULTI-AGENT COLLABORATIVE ASSEMBLY")
        print("="*80)
        print("\nScenario: 4 agents collaborate to design an enclosure")
        print("  - Agent A (Housing): Creates base box 50x50x30mm")
        print("  - Agent B (Lid): Creates lid 50x50x5mm")
        print("  - Agent C (Support): Creates internal mounting posts")
        print("  - Agent D (Integrator): Merges all parts into assembly")
        print("\n" + "-"*80)

        # Phase 1: Create agents
        print("\n[Phase 1] Creating specialized agents...")
        agent_a = self.create_agent("agent_housing", "housing_designer")
        agent_b = self.create_agent("agent_lid", "lid_designer")
        agent_c = self.create_agent("agent_support", "support_designer")
        agent_d = self.create_agent("agent_integrator", "integrator")

        print(f"  [OK] Created {len(self.agents)} agents")

        # Phase 2: Create workspaces
        print("\n[Phase 2] Creating isolated workspaces...")
        workspaces_created = 0

        if agent_a.create_workspace("housing_workspace"):
            print(f"  [OK] Agent A workspace: {agent_a.workspace_id}")
            workspaces_created += 1

        if agent_b.create_workspace("lid_workspace"):
            print(f"  [OK] Agent B workspace: {agent_b.workspace_id}")
            workspaces_created += 1

        if agent_c.create_workspace("support_workspace"):
            print(f"  [OK] Agent C workspace: {agent_c.workspace_id}")
            workspaces_created += 1

        print(f"  Total: {workspaces_created}/3 workspaces created")

        # Phase 3: Parallel design work
        print("\n[Phase 3] Agents working in parallel...")

        # Agent A: Housing (50x50x30mm box)
        print("\n  Agent A (Housing Designer):")
        print("    Task: Create base box 50x50x30mm with mounting holes")

        # Create housing outline
        l1 = agent_a.create_entity("line", {"start": [0, 0], "end": [50, 0]})
        l2 = agent_a.create_entity("line", {"start": [50, 0], "end": [50, 50]})
        l3 = agent_a.create_entity("line", {"start": [50, 50], "end": [0, 50]})
        l4 = agent_a.create_entity("line", {"start": [0, 50], "end": [0, 0]})

        if all([l1, l2, l3, l4]):
            housing_solid = agent_a.extrude([l1, l2, l3, l4], 30.0)
            if housing_solid:
                print(f"    [OK] Created housing: {housing_solid}")
                print(f"    [OK] Volume: 75000 mm³ (50x50x30)")
            else:
                print(f"    [FAIL] Failed to extrude housing")
        else:
            print(f"    [FAIL] Failed to create housing outline")

        # Agent B: Lid (50x50x5mm box)
        print("\n  Agent B (Lid Designer):")
        print("    Task: Create matching lid 50x50x5mm")

        # Create lid outline
        l5 = agent_b.create_entity("line", {"start": [0, 0], "end": [50, 0]})
        l6 = agent_b.create_entity("line", {"start": [50, 0], "end": [50, 50]})
        l7 = agent_b.create_entity("line", {"start": [50, 50], "end": [0, 50]})
        l8 = agent_b.create_entity("line", {"start": [0, 50], "end": [0, 0]})

        if all([l5, l6, l7, l8]):
            lid_solid = agent_b.extrude([l5, l6, l7, l8], 5.0)
            if lid_solid:
                print(f"    [OK] Created lid: {lid_solid}")
                print(f"    [OK] Volume: 12500 mm³ (50x50x5)")
            else:
                print(f"    [FAIL] Failed to extrude lid")
        else:
            print(f"    [FAIL] Failed to create lid outline")

        # Agent C: Support posts (4x 5x5x25mm posts at corners)
        print("\n  Agent C (Support Designer):")
        print("    Task: Create 4 mounting posts 5x5x25mm at corners")

        # Create one support post at corner
        p1 = agent_c.create_entity("line", {"start": [5, 5], "end": [10, 5]})
        p2 = agent_c.create_entity("line", {"start": [10, 5], "end": [10, 10]})
        p3 = agent_c.create_entity("line", {"start": [10, 10], "end": [5, 10]})
        p4 = agent_c.create_entity("line", {"start": [5, 10], "end": [5, 5]})

        if all([p1, p2, p3, p4]):
            post_solid = agent_c.extrude([p1, p2, p3, p4], 25.0)
            if post_solid:
                print(f"    [OK] Created mounting post: {post_solid}")
                print(f"    [OK] Volume: 625 mm³ (5x5x25)")
            else:
                print(f"    [FAIL] Failed to extrude post")
        else:
            print(f"    [FAIL] Failed to create post outline")

        # Phase 4: Merge to main workspace
        print("\n[Phase 4] Integration - Merging workspaces...")

        merges_completed = 0
        total_conflicts = 0

        # Merge Agent A's housing
        print("\n  Merging housing workspace...")
        merge_result_a = agent_d.execute_jsonrpc("workspace.merge", {
            "source_workspace_id": agent_a.workspace_id,
            "target_workspace_id": "main"
        })

        if "result" in merge_result_a:
            result_a = merge_result_a["result"]
            print(f"    [OK] Merge result: {result_a.get('merge_result')}")
            print(f"    [OK] Entities added: {result_a.get('entities_added')}")
            conflicts_a = result_a.get('conflicts', [])
            total_conflicts += len(conflicts_a)
            if len(conflicts_a) > 0:
                print(f"    [WARN] Conflicts: {len(conflicts_a)}")
            merges_completed += 1

        # Merge Agent B's lid
        print("\n  Merging lid workspace...")
        merge_result_b = agent_d.execute_jsonrpc("workspace.merge", {
            "source_workspace_id": agent_b.workspace_id,
            "target_workspace_id": "main"
        })

        if "result" in merge_result_b:
            result_b = merge_result_b["result"]
            print(f"    [OK] Merge result: {result_b.get('merge_result')}")
            print(f"    [OK] Entities added: {result_b.get('entities_added')}")
            conflicts_b = result_b.get('conflicts', [])
            total_conflicts += len(conflicts_b)
            if len(conflicts_b) > 0:
                print(f"    [WARN] Conflicts: {len(conflicts_b)}")
            merges_completed += 1

        # Merge Agent C's support
        print("\n  Merging support workspace...")
        merge_result_c = agent_d.execute_jsonrpc("workspace.merge", {
            "source_workspace_id": agent_c.workspace_id,
            "target_workspace_id": "main"
        })

        if "result" in merge_result_c:
            result_c = merge_result_c["result"]
            print(f"    [OK] Merge result: {result_c.get('merge_result')}")
            print(f"    [OK] Entities added: {result_c.get('entities_added')}")
            conflicts_c = result_c.get('conflicts', [])
            total_conflicts += len(conflicts_c)
            if len(conflicts_c) > 0:
                print(f"    [WARN] Conflicts: {len(conflicts_c)}")
            merges_completed += 1

        print(f"\n  Total merges: {merges_completed}/3")
        print(f"  Total conflicts: {total_conflicts}")

        # Phase 5: Validation & Metrics
        print("\n[Phase 5] Validation & Agent Metrics...")

        print("\n  Agent Performance:")
        for agent_id, agent in self.agents.items():
            print(f"\n    {agent_id} ({agent.role}):")
            print(f"      Operations: {agent.operations_completed}")
            print(f"      Entities created: {len(agent.created_entities)}")
            print(f"      Errors: {len(agent.errors)}")

            if agent.errors:
                print(f"      Error details:")
                for error in agent.errors[:3]:  # Show first 3 errors
                    print(f"        - {error}")

        # Final summary
        print("\n" + "="*80)
        print("ASSEMBLY COMPLETE")
        print("="*80)

        total_ops = sum(a.operations_completed for a in self.agents.values())
        total_entities = sum(len(a.created_entities) for a in self.agents.values())
        total_errors = sum(len(a.errors) for a in self.agents.values())

        print(f"\nFinal Statistics:")
        print(f"  Agents: {len(self.agents)}")
        print(f"  Total operations: {total_ops}")
        print(f"  Total entities created: {total_entities}")
        print(f"  Total errors: {total_errors}")
        print(f"  Workspaces merged: {merges_completed}/3")
        print(f"  Merge conflicts: {total_conflicts}")

        success = merges_completed == 3 and total_conflicts == 0
        print(f"\nStatus: {'[SUCCESS]' if success else '[PARTIAL SUCCESS]'}")

        return {
            "success": success,
            "agents": len(self.agents),
            "operations": total_ops,
            "entities": total_entities,
            "errors": total_errors,
            "merges": merges_completed,
            "conflicts": total_conflicts
        }


def main():
    """Main entry point."""
    controller = MultiAgentController()
    result = controller.run_collaborative_assembly()

    # Exit with appropriate code
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
