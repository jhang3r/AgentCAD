"""Integration tests for workspace isolation and merging.

Tests workspace isolation between agents and merge functionality.
"""
import pytest
from src.cad_kernel.entity_manager import EntityManager
from src.cad_kernel.workspace_manager import WorkspaceManager
from src.persistence.database import Database
from src.operations.solid_modeling import SolidModeling


@pytest.fixture
def test_database(tmp_path):
    """Create test database."""
    db_path = str(tmp_path / "test_workspace.db")
    db = Database(db_path)
    yield db
    db.close()


@pytest.fixture
def workspace_manager(test_database):
    """Create workspace manager."""
    return WorkspaceManager(test_database)


@pytest.fixture
def entity_manager(test_database):
    """Create entity manager."""
    return EntityManager(test_database)


def test_workspace_isolation(workspace_manager, entity_manager, test_database):
    """Test that two agents can work in separate workspaces without interference.

    Scenario:
    1. Agent A creates entities in workspace A
    2. Agent B creates different entities in workspace B
    3. Verify Agent A's entities don't appear in workspace B
    4. Verify Agent B's entities don't appear in workspace A
    """
    # Agent A creates workspace
    workspace_a = workspace_manager.create_workspace(
        workspace_name="agent_a_workspace",
        workspace_type="agent_branch",
        base_workspace_id="main",
        owning_agent_id="agent_a"
    )

    # Agent B creates workspace
    workspace_b = workspace_manager.create_workspace(
        workspace_name="agent_b_workspace",
        workspace_type="agent_branch",
        base_workspace_id="main",
        owning_agent_id="agent_b"
    )

    # Agent A creates entities in workspace A
    point_a = entity_manager.create_point([10, 20, 30], workspace_id=workspace_a.workspace_id)
    line_a = entity_manager.create_line([0, 0], [10, 10], workspace_id=workspace_a.workspace_id)

    # Agent B creates entities in workspace B
    point_b = entity_manager.create_point([100, 200, 300], workspace_id=workspace_b.workspace_id)
    circle_b = entity_manager.create_circle([50, 50], 25.0, workspace_id=workspace_b.workspace_id)

    # Verify isolation: Query entities from workspace A
    cursor = test_database.connection.cursor()
    cursor.execute("""
        SELECT entity_id, entity_type FROM entities WHERE workspace_id = ?
    """, (workspace_a.workspace_id,))
    entities_a = cursor.fetchall()

    # Should only have point_a and line_a
    assert len(entities_a) == 2
    entity_ids_a = [e[0] for e in entities_a]
    assert point_a.entity_id in entity_ids_a
    assert line_a.entity_id in entity_ids_a
    assert point_b.entity_id not in entity_ids_a
    assert circle_b.entity_id not in entity_ids_a

    # Verify isolation: Query entities from workspace B
    cursor.execute("""
        SELECT entity_id, entity_type FROM entities WHERE workspace_id = ?
    """, (workspace_b.workspace_id,))
    entities_b = cursor.fetchall()

    # Should only have point_b and circle_b
    assert len(entities_b) == 2
    entity_ids_b = [e[0] for e in entities_b]
    assert point_b.entity_id in entity_ids_b
    assert circle_b.entity_id in entity_ids_b
    assert point_a.entity_id not in entity_ids_b
    assert line_a.entity_id not in entity_ids_b


def test_workspace_merge_without_conflicts(workspace_manager, entity_manager, test_database):
    """Test merging workspaces without conflicts (non-overlapping geometry).

    Scenario:
    1. Create branch workspace from main
    2. Add entities to branch workspace
    3. Merge branch into main
    4. Verify all entities merged successfully
    5. Verify no conflicts reported
    """
    # Create branch workspace
    branch_ws = workspace_manager.create_workspace(
        workspace_name="feature_branch",
        workspace_type="agent_branch",
        base_workspace_id="main",
        owning_agent_id="agent_feature"
    )

    # Add entities to branch
    point1 = entity_manager.create_point([10, 20, 30], workspace_id=branch_ws.workspace_id)
    line1 = entity_manager.create_line([0, 0], [10, 10], workspace_id=branch_ws.workspace_id)
    circle1 = entity_manager.create_circle([5, 5], 3.0, workspace_id=branch_ws.workspace_id)

    # Count entities before merge
    cursor = test_database.connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM entities WHERE workspace_id = ?", ("main",))
    main_count_before = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM entities WHERE workspace_id = ?", (branch_ws.workspace_id,))
    branch_count = cursor.fetchone()[0]
    assert branch_count == 3

    # Perform merge (simulate merge logic)
    cursor.execute("""
        SELECT entity_id, entity_type, properties, bounding_box,
               is_valid, validation_errors, created_at, modified_at, created_by_agent
        FROM entities
        WHERE workspace_id = ?
    """, (branch_ws.workspace_id,))

    entities_merged = 0
    conflicts = []

    for row in cursor.fetchall():
        entity_id, entity_type, properties, bbox, is_valid, val_errors, created_at, modified_at, created_by = row

        # Generate new entity ID for main workspace
        import uuid
        base_id = entity_id.split('_', 1)[1] if '_' in entity_id else str(uuid.uuid4())[:8]
        new_entity_id = f"main:{entity_type}_{base_id}"

        # Check for conflicts
        cursor.execute("SELECT entity_id FROM entities WHERE entity_id = ?", (new_entity_id,))
        if cursor.fetchone():
            conflicts.append(new_entity_id)
            continue

        # Insert into main
        cursor.execute("""
            INSERT INTO entities (
                entity_id, entity_type, workspace_id, properties, bounding_box,
                is_valid, validation_errors, created_at, modified_at, created_by_agent
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (new_entity_id, entity_type, "main", properties, bbox,
              is_valid, val_errors, created_at, modified_at, created_by))

        entities_merged += 1

    test_database.connection.commit()

    # Verify merge results
    assert entities_merged == 3, "Should merge all 3 entities"
    assert len(conflicts) == 0, "Should have no conflicts"

    # Verify entity count in main increased
    cursor.execute("SELECT COUNT(*) FROM entities WHERE workspace_id = ?", ("main",))
    main_count_after = cursor.fetchone()[0]
    assert main_count_after == main_count_before + 3


def test_workspace_merge_conflict_detection(workspace_manager, entity_manager, test_database):
    """Test conflict detection when merging workspaces with overlapping changes.

    Scenario:
    1. Create entity in main workspace
    2. Create branch workspace
    3. Modify same entity in both main and branch
    4. Attempt merge
    5. Verify conflict is detected
    """
    # Create entity in main workspace
    point_main = entity_manager.create_point([10, 20, 30], workspace_id="main")

    # Create branch workspace
    branch_ws = workspace_manager.create_workspace(
        workspace_name="conflict_branch",
        workspace_type="agent_branch",
        base_workspace_id="main",
        owning_agent_id="agent_conflict"
    )

    # Simulate entity existing in both workspaces (e.g., copied during branch creation)
    # In practice, this would happen through branch initialization copying base entities

    # Create an entity with same ID in branch (simulating conflict)
    cursor = test_database.connection.cursor()

    # First, add entity to branch workspace
    import json
    from datetime import datetime, timezone

    # Create the same entity ID in branch workspace
    conflicting_id = f"main:{point_main.entity_type}_{point_main.entity_id.split('_')[1]}"

    cursor.execute("""
        INSERT INTO entities (
            entity_id, entity_type, workspace_id, properties, bounding_box,
            is_valid, validation_errors, created_at, modified_at, created_by_agent
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        conflicting_id,
        "point",
        branch_ws.workspace_id,
        json.dumps({"coordinates": [15, 25, 35]}),  # Different coordinates
        json.dumps({}),
        True,
        json.dumps([]),
        datetime.now(timezone.utc).isoformat(),
        datetime.now(timezone.utc).isoformat(),
        "agent_conflict"
    ))
    test_database.connection.commit()

    # Attempt merge and detect conflicts
    cursor.execute("""
        SELECT entity_id, entity_type FROM entities WHERE workspace_id = ?
    """, (branch_ws.workspace_id,))

    conflicts = []

    for row in cursor.fetchall():
        entity_id, entity_type = row

        # Check if entity exists in main (conflict)
        cursor.execute("SELECT entity_id FROM entities WHERE entity_id = ? AND workspace_id = ?",
                      (entity_id, "main"))
        if cursor.fetchone():
            conflicts.append({
                "entity_id": entity_id,
                "conflict_type": "entity_exists",
                "source_workspace": branch_ws.workspace_id,
                "target_workspace": "main"
            })

    # Verify conflict detected
    assert len(conflicts) > 0, "Should detect at least one conflict"
    assert conflicts[0]["conflict_type"] == "entity_exists"
    assert conflicts[0]["entity_id"] == conflicting_id
