"""
Multi-Agent CAD Build Demo

Demonstrates multiple agents collaborating to build a simple box assembly.
You'll see each agent working on their specialized tasks.
"""

import os
import time
from pathlib import Path
from src.multi_agent.controller import Controller


def print_separator():
    print("\n" + "="*80 + "\n")


def main():
    print_separator()
    print("MULTI-AGENT CAD BUILD DEMO")
    print_separator()

    # Set up workspace directory
    workspace_dir = Path("data/workspaces/demo_build").absolute()
    if workspace_dir.exists():
        import shutil
        shutil.rmtree(workspace_dir)
    workspace_dir.mkdir(parents=True, exist_ok=True)

    os.environ["MULTI_AGENT_WORKSPACE_DIR"] = str(workspace_dir)

    # Create controller
    print("Creating Multi-Agent Controller...")
    controller = Controller(
        controller_id="demo_controller",
        max_concurrent_agents=6,
        workspace_dir=str(workspace_dir)
    )
    print(f"[OK] Controller created with {len(controller.role_templates)} role templates")
    print(f"   Available roles: {', '.join(controller.role_templates.keys())}")

    print_separator()
    print("BUILDING A BOX WITH LID")
    print_separator()

    # Step 1: Create Designer agent to create 2D geometry
    print("Step 1: Creating DESIGNER agent for 2D geometry...")
    designer = controller.create_agent(
        agent_id="designer_001",
        role_name="designer",
        workspace_id="box_design_ws"
    )
    print(f"[OK] Designer agent created: {designer.agent_id}")
    print(f"   Role: {designer.role.name}")
    print(f"   Workspace: {designer.workspace_id}")
    print(f"   Can perform: entity.create_point, entity.create_line, entity.create_circle")

    time.sleep(0.5)

    # Designer creates box base outline (4 corner points)
    print("\n[DESIGNER] Creating box base corner points...")
    points = []
    corners = [
        (0.0, 0.0, 0.0),
        (100.0, 0.0, 0.0),
        (100.0, 80.0, 0.0),
        (0.0, 80.0, 0.0)
    ]

    for i, (x, y, z) in enumerate(corners):
        result = controller.execute_operation(
            agent_id="designer_001",
            operation="entity.create_point",
            params={"x": x, "y": y, "z": z, "workspace_id": "box_design_ws"}
        )
        point_id = result.get("data", {}).get("entity_id")
        points.append(point_id)
        print(f"   [OK] Created corner point {i+1}: {point_id} at ({x}, {y}, {z})")

    # Designer creates a circle for the lid handle
    print("\n[DESIGNER] Creating lid handle (circle)...")
    circle_result = controller.execute_operation(
        agent_id="designer_001",
        operation="entity.create_circle",
        params={
            "center": {"x": 50.0, "y": 40.0, "z": 0.0},
            "radius": 10.0,
            "workspace_id": "box_design_ws"
        }
    )
    circle_id = circle_result.get("data", {}).get("entity_id")
    print(f"   [OK] Created circle: {circle_id} (radius=10.0)")

    print(f"\n[METRICS] Designer: {designer.operation_count} operations, {designer.success_count} successful")

    print_separator()

    # Step 2: Create Modeler agent for 3D operations
    print("Step 2: Creating MODELER agent for 3D extrusion...")
    modeler = controller.create_agent(
        agent_id="modeler_001",
        role_name="modeler",
        workspace_id="box_3d_ws"
    )
    print(f"[OK] Modeler agent created: {modeler.agent_id}")
    print(f"   Role: {modeler.role.name}")
    print(f"   Can perform: solid.extrude, solid.boolean")

    time.sleep(0.5)

    # Note: In a real scenario, we'd transfer geometry between workspaces
    # For this demo, we'll show the modeler creating their own circle to extrude
    print("\n[MODELER] Creating geometry for extrusion...")
    modeler_circle = controller.execute_operation(
        agent_id="modeler_001",
        operation="entity.create_circle",
        params={
            "center": {"x": 50.0, "y": 40.0, "z": 0.0},
            "radius": 15.0,
            "workspace_id": "box_3d_ws"
        }
    )
    modeler_circle_id = modeler_circle.get("data", {}).get("entity_id")
    print(f"   [OK] Created circle for extrusion: {modeler_circle_id}")

    print("\n[MODELER] Extruding circle to create 3D cylinder...")
    extrude_result = controller.execute_operation(
        agent_id="modeler_001",
        operation="solid.extrude",
        params={
            "entity_id": modeler_circle_id,
            "distance": 50.0,
            "workspace_id": "box_3d_ws"
        }
    )
    solid_id = extrude_result.get("data", {}).get("solid_id")
    print(f"   [OK] Extruded to create solid: {solid_id} (height=50.0)")

    print(f"\n[METRICS] Modeler: {modeler.operation_count} operations, {modeler.success_count} successful")

    print_separator()

    # Step 3: Create Validator agent
    print("Step 3: Creating VALIDATOR agent to check the design...")
    validator = controller.create_agent(
        agent_id="validator_001",
        role_name="validator",
        workspace_id="box_design_ws"
    )
    print(f"[OK] Validator agent created: {validator.agent_id}")
    print(f"   Role: {validator.role.name}")
    print(f"   Can perform: entity.list, entity.query, constraint.status")

    time.sleep(0.5)

    print("\n[VALIDATOR] Checking design workspace entities...")
    entities_result = controller.execute_operation(
        agent_id="validator_001",
        operation="entity.list",
        params={"workspace_id": "box_design_ws"}
    )
    entities = entities_result.get("data", {}).get("entities", [])
    print(f"   [OK] Found {len(entities)} entities in design workspace")
    for entity in entities:
        print(f"     - {entity.get('entity_type')}: {entity.get('entity_id')}")

    print(f"\n[METRICS] Validator: {validator.operation_count} operations")

    print_separator()

    # Step 4: Create Integrator agent
    print("Step 4: Creating INTEGRATOR agent for workspace management...")
    integrator = controller.create_agent(
        agent_id="integrator_001",
        role_name="integrator",
        workspace_id="final_assembly_ws"
    )
    print(f"[OK] Integrator agent created: {integrator.agent_id}")
    print(f"   Role: {integrator.role.name}")
    print(f"   Can perform: workspace.merge, workspace.status")

    print("\n[INTEGRATOR] Managing workspaces...")
    # List all workspaces
    print(f"   [OK] Coordinating workspaces:")
    print(f"     - Design workspace: box_design_ws")
    print(f"     - 3D workspace: box_3d_ws")
    print(f"     - Assembly workspace: final_assembly_ws")

    print_separator()

    # Summary
    print("BUILD SUMMARY")
    print_separator()
    print(f"Total Agents Created: {len(controller.agents)}")
    for agent_id, agent in controller.agents.items():
        print(f"\n[AGENT] {agent_id}")
        print(f"   Role: {agent.role.name}")
        print(f"   Workspace: {agent.workspace_id}")
        print(f"   Operations: {agent.operation_count}")
        print(f"   Success: {agent.success_count}")
        print(f"   Errors: {agent.error_count}")
        print(f"   Created entities: {len(agent.created_entities)}")

    print_separator()
    print("[OK] Multi-agent build demo completed!")
    print(f"Workspace directory: {workspace_dir}")
    print_separator()

    # Cleanup
    print("\nShutting down agents...")
    for agent_id in list(controller.agents.keys()):
        controller.shutdown_agent(agent_id)
    print("[OK] All agents shut down")


if __name__ == "__main__":
    main()
