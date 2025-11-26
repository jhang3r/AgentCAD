"""Load testing for concurrent agent operations.

Tests system performance under load with multiple concurrent agents.
"""
import pytest
import multiprocessing
import time
import tempfile
import os
from pathlib import Path


def agent_workload(agent_id: str, db_path: str, operations_count: int) -> dict:
    """Workload for a single agent.

    Each agent performs a series of CAD operations.

    Args:
        agent_id: Unique agent identifier
        db_path: Path to shared database
        operations_count: Number of operations to perform

    Returns:
        Performance metrics for this agent
    """
    from src.cad_kernel.entity_manager import EntityManager
    from src.persistence.database import Database
    from src.operations.solid_modeling import SolidModeling

    # Connect to database
    db = Database(db_path)
    entity_manager = EntityManager(db)
    solid_ops = SolidModeling(entity_manager)

    workspace_id = f"agent_{agent_id}"

    start_time = time.time()
    operations_completed = 0
    errors = 0

    try:
        # Each agent creates points, lines, and a simple box
        for i in range(operations_count):
            try:
                # Create point
                entity_manager.create_point([i, i * 2, i * 3], workspace_id=workspace_id)

                # Create line
                entity_manager.create_line([i, i], [i + 10, i + 10], workspace_id=workspace_id)

                # Every 5 operations, create a box
                if i % 5 == 0:
                    l1 = entity_manager.create_line([i, i], [i + 10, i], workspace_id=workspace_id)
                    l2 = entity_manager.create_line([i + 10, i], [i + 10, i + 10], workspace_id=workspace_id)
                    l3 = entity_manager.create_line([i + 10, i + 10], [i, i + 10], workspace_id=workspace_id)
                    l4 = entity_manager.create_line([i, i + 10], [i, i], workspace_id=workspace_id)

                    solid_ops.extrude(
                        [l1.entity_id, l2.entity_id, l3.entity_id, l4.entity_id],
                        10.0,
                        workspace_id
                    )

                operations_completed += 1

            except Exception as e:
                errors += 1
                print(f"Agent {agent_id} error: {e}")

    finally:
        db.close()

    elapsed_time = time.time() - start_time

    return {
        "agent_id": agent_id,
        "operations_completed": operations_completed,
        "operations_target": operations_count,
        "errors": errors,
        "elapsed_seconds": elapsed_time,
        "ops_per_second": operations_completed / elapsed_time if elapsed_time > 0 else 0
    }


def test_concurrent_agents_load():
    """Test system with 10 concurrent agents.

    Each agent performs 20 operations in their own workspace.
    Verifies:
    - All agents can operate concurrently
    - No database locking issues
    - Reasonable performance under load
    """
    # Create temporary database
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "load_test.db")

        # Initialize database
        from src.persistence.database import Database
        db = Database(db_path)
        db.close()

        # Configuration
        num_agents = 10
        operations_per_agent = 20

        # Launch agents in parallel
        print(f"\nStarting load test: {num_agents} agents, {operations_per_agent} ops each")
        start_time = time.time()

        with multiprocessing.Pool(processes=num_agents) as pool:
            results = pool.starmap(
                agent_workload,
                [(str(i), db_path, operations_per_agent) for i in range(num_agents)]
            )

        total_elapsed = time.time() - start_time

        # Analyze results
        total_operations = sum(r["operations_completed"] for r in results)
        total_errors = sum(r["errors"] for r in results)
        avg_ops_per_second = sum(r["ops_per_second"] for r in results) / num_agents

        print(f"\nLoad Test Results:")
        print(f"  Total time: {total_elapsed:.2f}s")
        print(f"  Total operations: {total_operations}/{num_agents * operations_per_agent}")
        print(f"  Total errors: {total_errors}")
        print(f"  Avg ops/sec per agent: {avg_ops_per_second:.2f}")
        print(f"  Overall throughput: {total_operations / total_elapsed:.2f} ops/sec")

        # Verify all operations completed
        assert total_operations == num_agents * operations_per_agent, \
            f"Should complete all operations, got {total_operations}/{num_agents * operations_per_agent}"

        # Verify minimal errors
        assert total_errors == 0, f"Should have no errors, got {total_errors}"

        # Verify reasonable performance (at least 5 ops/sec per agent)
        assert avg_ops_per_second >= 5.0, \
            f"Each agent should achieve >=5 ops/sec, got {avg_ops_per_second:.2f}"

        # Individual agent performance
        for result in results:
            print(f"  Agent {result['agent_id']}: {result['operations_completed']} ops in "
                  f"{result['elapsed_seconds']:.2f}s ({result['ops_per_second']:.2f} ops/sec)")


def test_concurrent_workspace_operations():
    """Test multiple agents creating and listing workspaces concurrently.

    Verifies workspace isolation and no race conditions.
    """
    def agent_workspace_ops(agent_id: str, db_path: str) -> dict:
        """Each agent creates a workspace and lists all workspaces."""
        from src.cad_kernel.workspace_manager import WorkspaceManager
        from src.persistence.database import Database

        db = Database(db_path)
        ws_manager = WorkspaceManager(db)

        try:
            # Create workspace
            ws = ws_manager.create_workspace(
                workspace_name=f"agent_{agent_id}_workspace",
                workspace_type="agent_branch",
                base_workspace_id="main",
                owning_agent_id=f"agent_{agent_id}"
            )

            # List all workspaces
            all_workspaces = ws_manager.list_workspaces()

            return {
                "agent_id": agent_id,
                "workspace_created": ws.workspace_id,
                "total_workspaces_seen": len(all_workspaces),
                "success": True
            }

        except Exception as e:
            return {
                "agent_id": agent_id,
                "success": False,
                "error": str(e)
            }
        finally:
            db.close()

    # Create temporary database
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "workspace_load_test.db")

        # Initialize database
        from src.persistence.database import Database
        db = Database(db_path)
        db.close()

        # Run concurrent workspace operations
        num_agents = 10

        with multiprocessing.Pool(processes=num_agents) as pool:
            results = pool.starmap(
                agent_workspace_ops,
                [(str(i), db_path) for i in range(num_agents)]
            )

        # Verify all succeeded
        successes = sum(1 for r in results if r["success"])
        assert successes == num_agents, f"All agents should succeed, got {successes}/{num_agents}"

        # Verify each agent created a workspace
        workspaces_created = [r["workspace_created"] for r in results if r["success"]]
        assert len(workspaces_created) == num_agents, "Each agent should create a workspace"
        assert len(set(workspaces_created)) == num_agents, "All workspace IDs should be unique"

        print(f"\nConcurrent workspace test passed:")
        print(f"  {num_agents} agents created workspaces concurrently")
        print(f"  All workspace IDs unique: {len(set(workspaces_created)) == num_agents}")
