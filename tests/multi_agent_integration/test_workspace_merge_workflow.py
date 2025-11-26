"""
Integration test for workspace merge workflow.

Tests T015: Integration test for workspace merge workflow
- 3 modeler agents create components, integrator merges all workspaces via real CLI,
  verify all entities preserved

Constitution compliance:
- Uses real CLI subprocess calls for workspace operations
- Uses real workspaces and entities
- No mocks or stubs
"""

import pytest
import subprocess
import json
import os
from pathlib import Path


@pytest.fixture
def controller():
    """Create controller instance for testing."""
    from src.multi_agent.controller import Controller
    
    # Use temporary directory for workspaces (ABSOLUTE path)
    workspace_dir = (Path(__file__).parent.parent.parent / "data/workspaces/test_merge").absolute()
    if workspace_dir.exists():
        import shutil
        shutil.rmtree(workspace_dir)
    workspace_dir.mkdir(parents=True, exist_ok=True)

    controller = Controller(
        controller_id="test_controller_merge",
        max_concurrent_agents=10,
        workspace_dir=str(workspace_dir)
    )

    # Set env var for subprocess calls in test
    import os
    os.environ["MULTI_AGENT_WORKSPACE_DIR"] = str(workspace_dir)
    
    yield controller

    # Cleanup env var
    if "MULTI_AGENT_WORKSPACE_DIR" in os.environ:
        del os.environ["MULTI_AGENT_WORKSPACE_DIR"]

    # Cleanup
    agent_ids = list(controller.agents.keys())
    for agent_id in agent_ids:
        try:
            controller.shutdown_agent(agent_id)
        except:
            pass


@pytest.fixture
def cleanup_workspaces():
    """Cleanup test workspaces after test."""
    workspace_ids = []

    def register_workspace(ws_id):
        workspace_ids.append(ws_id)

    yield register_workspace

    for ws_id in workspace_ids:
        try:
            subprocess.run(
                ["python", "-m", "src.agent_interface.cli", "workspace.delete",
                 "--workspace_id", ws_id],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=Path(__file__).parent.parent.parent
            )
        except:
            pass


def test_workspace_merge_preserves_all_entities(controller, cleanup_workspaces):
    """
    Test T015: 3 modelers create components, integrator merges all workspaces,
    verify all entities preserved.

    Success criteria:
    - Each modeler creates entities in separate workspace
    - Integrator merges all 3 workspaces into main workspace
    - All entities from all workspaces present in merged workspace
    - No data loss during merge (SC-002: 100% merge success)
    - Merge completes in reasonable time (SC-004: <5s for 100 entities)
    """
    # Create 3 modeler agents with separate workspaces
    modeler_agents = []
    workspace_ids = []

    for i in range(3):
        workspace_id = f"ws_modeler_merge_{i}"
        workspace_ids.append(workspace_id)
        cleanup_workspaces(workspace_id)

        # Create workspace via CLI
        result = subprocess.run(
            ["python", "-m", "src.agent_interface.cli", "workspace.create",
             "--workspace_id", workspace_id],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=Path(__file__).parent.parent.parent,
            env=os.environ
        )
        assert result.returncode == 0, f"Failed to create workspace {workspace_id}"

        agent = controller.create_agent(
            agent_id=f"modeler_merge_{i}",
            role_name="modeler",
            workspace_id=workspace_id
        )
        modeler_agents.append(agent)

    # Each modeler creates different components
    components_per_agent = 3

    for idx, agent in enumerate(modeler_agents):
        # Create entities in this agent's workspace
        for j in range(components_per_agent):
            # Create a point
            result = controller.execute_operation(
                agent_id=agent.agent_id,
                operation="entity.create_point",
                params={
                    "x": float(idx * 100 + j * 10),
                    "y": float(idx * 100 + j * 10),
                    "z": 0.0,
                    "workspace_id": agent.workspace_id
                }
            )
            assert result.get("success") is True, f"Failed to create point in {agent.workspace_id}"

    # Verify each workspace has the correct number of entities
    entity_counts = {}
    for agent in modeler_agents:
        result = subprocess.run(
            ["python", "-m", "src.agent_interface.cli", "entity.list",
             "--workspace_id", agent.workspace_id],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=Path(__file__).parent.parent.parent,
            env=os.environ
        )
        assert result.returncode == 0

        response = json.loads(result.stdout)
        # Parse JSON-RPC 2.0 response: result.data.entities
        result_data = response.get("result", {}).get("data", {})
        entities = result_data.get("entities", [])
        entity_counts[agent.workspace_id] = len(entities)
        assert len(entities) == components_per_agent, (
            f"Workspace {agent.workspace_id} should have {components_per_agent} entities"
        )

    # Create main workspace for integration
    main_workspace_id = "ws_main_merge"
    cleanup_workspaces(main_workspace_id)

    result = subprocess.run(
        ["python", "-m", "src.agent_interface.cli", "workspace.create",
         "--workspace_id", main_workspace_id],
        capture_output=True,
        text=True,
        timeout=10,
        cwd=Path(__file__).parent.parent.parent,
        env=os.environ
    )
    assert result.returncode == 0

    # Create integrator agent
    integrator = controller.create_agent(
        agent_id="integrator_merge",
        role_name="integrator",
        workspace_id=main_workspace_id
    )

    # Integrator merges all 3 workspaces into main
    import time
    start_time = time.time()

    for source_ws in workspace_ids:
        merge_result = controller.execute_operation(
            agent_id=integrator.agent_id,
            operation="workspace.merge",
            params={
                "source_workspace": source_ws,
                "target_workspace": main_workspace_id
            }
        )
        assert merge_result.get("success") is True, (
            f"Failed to merge {source_ws} into {main_workspace_id}: {merge_result}"
        )

    end_time = time.time()
    merge_duration = end_time - start_time

    # Verify all entities preserved in main workspace
    result = subprocess.run(
        ["python", "-m", "src.agent_interface.cli", "entity.list",
         "--workspace_id", main_workspace_id],
        capture_output=True,
        text=True,
        timeout=10,
        cwd=Path(__file__).parent.parent.parent,
        env=os.environ
    )
    assert result.returncode == 0

    response = json.loads(result.stdout)
    # Parse JSON-RPC 2.0 response: result.data.entities
    result_data = response.get("result", {}).get("data", {})
    merged_entities = result_data.get("entities", [])
    total_expected_entities = 3 * components_per_agent  # 3 agents * 3 entities each = 9

    assert len(merged_entities) == total_expected_entities, (
        f"Main workspace should have {total_expected_entities} entities after merge, "
        f"found {len(merged_entities)}. Data loss detected!"
    )

    # Verify merge performance (SC-004: <5s for 100 entities, we have 9 entities)
    assert merge_duration < 5.0, (
        f"Merge took {merge_duration:.2f}s for {total_expected_entities} entities, "
        f"expected <5s (SC-004)"
    )

    # Verify integrator metrics
    assert integrator.success_count >= 3, "Integrator should have 3+ successful operations"
    assert integrator.error_count == 0, "Integrator should have no errors"


def test_workspace_merge_with_complex_entities(controller, cleanup_workspaces):
    """
    Additional test: Merge workspaces containing different entity types.

    Verifies that merge handles points, lines, circles correctly.
    """
    # Create 2 agents with different entity types
    workspace_ids = []

    for i in range(2):
        workspace_id = f"ws_complex_merge_{i}"
        workspace_ids.append(workspace_id)
        cleanup_workspaces(workspace_id)

        result = subprocess.run(
            ["python", "-m", "src.agent_interface.cli", "workspace.create",
             "--workspace_id", workspace_id],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=Path(__file__).parent.parent.parent,
            env=os.environ
        )
        assert result.returncode == 0

    # Agent 1: designer creating 2D geometry
    designer = controller.create_agent(
        agent_id="designer_complex",
        role_name="designer",
        workspace_id=workspace_ids[0]
    )

    # Create a line
    result = controller.execute_operation(
        agent_id=designer.agent_id,
        operation="entity.create_line",
        params={
            "start": {"x": 0.0, "y": 0.0, "z": 0.0},
            "end": {"x": 100.0, "y": 0.0, "z": 0.0},
            "workspace_id": workspace_ids[0]
        }
    )
    assert result.get("success") is True

    # Create a circle
    result = controller.execute_operation(
        agent_id=designer.agent_id,
        operation="entity.create_circle",
        params={
            "center": {"x": 50.0, "y": 50.0, "z": 0.0},
            "radius": 25.0,
            "workspace_id": workspace_ids[0]
        }
    )
    assert result.get("success") is True

    # Agent 2: modeler creating points
    modeler = controller.create_agent(
        agent_id="modeler_complex",
        role_name="modeler",
        workspace_id=workspace_ids[1]
    )

    for i in range(2):
        result = controller.execute_operation(
            agent_id=modeler.agent_id,
            operation="entity.create_point",
            params={"x": float(i*50), "y": float(i*50), "z": 0.0, "workspace_id": workspace_ids[1]}
        )
        assert result.get("success") is True

    # Create main workspace and integrator
    main_workspace_id = "ws_main_complex"
    cleanup_workspaces(main_workspace_id)

    result = subprocess.run(
        ["python", "-m", "src.agent_interface.cli", "workspace.create",
         "--workspace_id", main_workspace_id],
        capture_output=True,
        text=True,
        timeout=10,
        cwd=Path(__file__).parent.parent.parent,
        env=os.environ
    )
    assert result.returncode == 0

    integrator = controller.create_agent(
        agent_id="integrator_complex",
        role_name="integrator",
        workspace_id=main_workspace_id
    )

    # Merge both workspaces
    for source_ws in workspace_ids:
        result = controller.execute_operation(
            agent_id=integrator.agent_id,
            operation="workspace.merge",
            params={
                "source_workspace": source_ws,
                "target_workspace": main_workspace_id
            }
        )
        assert result.get("success") is True

    # Verify all 4 entities (2 from designer, 2 from modeler) are in main workspace
    result = subprocess.run(
        ["python", "-m", "src.agent_interface.cli", "entity.list",
         "--workspace_id", main_workspace_id],
        capture_output=True,
        text=True,
        timeout=10,
        cwd=Path(__file__).parent.parent.parent,
        env=os.environ
    )
    assert result.returncode == 0

    response = json.loads(result.stdout)
    # Parse JSON-RPC 2.0 response: result.data.entities
    result_data = response.get("result", {}).get("data", {})
    merged_entities = result_data.get("entities", [])
    assert len(merged_entities) == 4, f"Expected 4 entities in merged workspace, found {len(merged_entities)}"
