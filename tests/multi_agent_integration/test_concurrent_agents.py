"""
Integration test for concurrent agents working simultaneously.

Tests T014: Integration test for concurrent agents in tests/multi_agent_integration/test_concurrent_agents.py
- create 4 agents using ThreadPoolExecutor, each creates entities in separate workspace via real CLI,
  verify no interference or locking

Constitution compliance:
- Uses real CLI subprocess calls (subprocess.run)
- Uses real workspaces via JSON-RPC CLI
- No mocks or stubs
"""

import pytest
import subprocess
import json
import time
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


@pytest.fixture
def controller():
    """Create controller instance for testing."""
    from src.multi_agent.controller import Controller

    # Use temporary directory for workspaces (ABSOLUTE path)
    workspace_dir = (Path(__file__).parent.parent.parent / "data/workspaces/test_concurrent").absolute()
    if workspace_dir.exists():
        import shutil
        shutil.rmtree(workspace_dir)
    workspace_dir.mkdir(parents=True, exist_ok=True)

    controller = Controller(
        controller_id="test_controller_concurrent",
        max_concurrent_agents=10,
        workspace_dir=str(workspace_dir)
    )

    # Set env var for subprocess calls in test
    os.environ["MULTI_AGENT_WORKSPACE_DIR"] = str(workspace_dir)

    yield controller

    # Cleanup env var
    if "MULTI_AGENT_WORKSPACE_DIR" in os.environ:
        del os.environ["MULTI_AGENT_WORKSPACE_DIR"]

    # Cleanup: shutdown all agents
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

    # Cleanup all registered workspaces
    for ws_id in workspace_ids:
        try:
            result = subprocess.run(
                ["python", "-m", "src.agent_interface.cli", "workspace.delete",
                 "--workspace_id", ws_id],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=Path(__file__).parent.parent.parent,
                env=os.environ
            )
        except:
            pass


def test_concurrent_agents_no_interference(controller, cleanup_workspaces):
    """
    Test T014: 4 agents work simultaneously in separate workspaces without interference.

    Success criteria:
    - All 4 agents create entities successfully
    - No locking or blocking between agents
    - Each workspace contains only its agent's entities
    - All operations complete within reasonable time
    """
    # Create 4 agents with separate workspaces
    num_agents = 4
    agents = []

    for i in range(num_agents):
        agent_id = f"concurrent_agent_{i}"
        workspace_id = f"ws_concurrent_{i}"
        cleanup_workspaces(workspace_id)

        # Create workspace via CLI first
        result = subprocess.run(
            ["python", "-m", "src.agent_interface.cli", "workspace.create",
             "--workspace_id", workspace_id],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=Path(__file__).parent.parent.parent,
            env=os.environ
        )
        assert result.returncode == 0, f"Failed to create workspace {workspace_id}: {result.stderr}"

        # Create agent
        agent = controller.create_agent(
            agent_id=agent_id,
            role_name="modeler",
            workspace_id=workspace_id
        )
        agents.append(agent)

    # Define work function for each agent
    def agent_work(agent, entity_count=5):
        """Each agent creates multiple entities in its workspace."""
        results = []
        for j in range(entity_count):
            # Create a point entity
            result = controller.execute_operation(
                agent_id=agent.agent_id,
                operation="entity.create_point",
                params={
                    "x": float(j * 10),
                    "y": float(j * 10),
                    "z": 0.0,
                    "workspace_id": agent.workspace_id
                }
            )
            results.append(result)
        return results

    # Execute all agents concurrently using ThreadPoolExecutor
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=num_agents) as executor:
        futures = {executor.submit(agent_work, agent): agent for agent in agents}

        agent_results = {}
        for future in as_completed(futures):
            agent = futures[future]
            try:
                results = future.result(timeout=30)
                agent_results[agent.agent_id] = results
            except Exception as e:
                pytest.fail(f"Agent {agent.agent_id} failed: {str(e)}")

    end_time = time.time()
    execution_time = end_time - start_time

    # Verify all agents completed successfully
    assert len(agent_results) == num_agents, "Not all agents completed"

    # Verify each agent created 5 entities
    for agent_id, results in agent_results.items():
        assert len(results) == 5, f"Agent {agent_id} didn't create 5 entities"
        for result in results:
            assert result.get("success") is True, f"Agent {agent_id} operation failed"

    # Verify no interference: each workspace should have exactly 5 entities
    for agent in agents:
        # Query entities in workspace via CLI
        result = subprocess.run(
            ["python", "-m", "src.agent_interface.cli", "entity.list",
             "--workspace_id", agent.workspace_id],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=Path(__file__).parent.parent.parent,
            env=os.environ
        )
        assert result.returncode == 0, f"Failed to list entities in {agent.workspace_id}"

        # Parse JSON response (find line starting with '{')
        response_line = None
        for line in result.stdout.strip().split('\n'):
            if line.startswith('{'):
                response_line = line
                break
        assert response_line is not None, f"No JSON response found in stdout: {result.stdout}"

        response = json.loads(response_line)
        # Parse JSON-RPC 2.0 response: result.data.entities
        result_data = response.get("result", {}).get("data", {})
        entity_count = len(result_data.get("entities", []))
        assert entity_count == 5, (
            f"Workspace {agent.workspace_id} should have 5 entities, found {entity_count}. "
            f"This indicates interference from other agents."
        )

    # Verify reasonable execution time (concurrent should be faster than sequential)
    # 4 agents * 5 operations each = 20 operations total
    # If sequential, this would take much longer; concurrent should complete in reasonable time
    assert execution_time < 20.0, (
        f"Concurrent execution took {execution_time:.2f}s, expected <20s. "
        f"May indicate blocking or serialization."
    )

    # Verify agent metrics were updated correctly
    for agent in agents:
        assert agent.operation_count >= 5, f"Agent {agent.agent_id} operation_count should be >=5"
        assert agent.success_count >= 5, f"Agent {agent.agent_id} success_count should be >=5"
        assert agent.error_count == 0, f"Agent {agent.agent_id} should have no errors"


def test_concurrent_agents_high_load(controller, cleanup_workspaces):
    """
    Additional test: 10 agents working concurrently (stress test).

    Verifies success criteria SC-006: 10 agents in parallel, operations remain fast.
    """
    num_agents = 10
    agents = []

    for i in range(num_agents):
        agent_id = f"stress_agent_{i}"
        workspace_id = f"ws_stress_{i}"
        cleanup_workspaces(workspace_id)

        # Create workspace
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

        agent = controller.create_agent(
            agent_id=agent_id,
            role_name="designer",
            workspace_id=workspace_id
        )
        agents.append(agent)

    # Each agent creates 3 entities
    def agent_work(agent):
        results = []
        for j in range(3):
            result = controller.execute_operation(
                agent_id=agent.agent_id,
                operation="entity.create_point",
                params={"x": float(j), "y": float(j), "z": 0.0, "workspace_id": agent.workspace_id}
            )
            results.append(result)
        return results

    start_time = time.time()

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(agent_work, agent): agent for agent in agents}

        for future in as_completed(futures):
            agent = futures[future]
            try:
                results = future.result(timeout=30)
                assert all(r.get("success") for r in results)
            except Exception as e:
                pytest.fail(f"Agent {agent.agent_id} failed: {str(e)}")

    end_time = time.time()
    execution_time = end_time - start_time

    # Verify execution time is reasonable for 10 concurrent agents
    assert execution_time < 30.0, f"10 agents took {execution_time:.2f}s, expected <30s"

    # Verify all agents completed successfully
    for agent in agents:
        assert agent.success_count >= 3
        assert agent.error_count == 0
