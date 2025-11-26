"""Agent journey test: Multi-agent workspace collaboration.

Tests a realistic scenario where two agents collaborate using workspace branching and merging.
"""
import pytest
from src.cad_kernel.entity_manager import EntityManager
from src.cad_kernel.workspace_manager import WorkspaceManager
from src.persistence.database import Database
from src.operations.solid_modeling import SolidModeling


@pytest.fixture
def test_database(tmp_path):
    """Create test database."""
    db_path = str(tmp_path / "test_collaboration.db")
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


@pytest.fixture
def solid_modeling(entity_manager):
    """Create solid modeling operations."""
    return SolidModeling(entity_manager)


def test_two_agents_collaborate_with_merge(workspace_manager, entity_manager, solid_modeling, test_database):
    """Journey: Two agents collaborate on a design with workspace branching and merging.

    Scenario:
    1. Agent A creates a branch workspace and designs the base (a platform)
    2. Agent B creates a separate branch and designs a column
    3. Both agents merge their work into main workspace
    4. Verify final design contains both parts
    5. Verify no conflicts occurred

    This tests the complete workflow of:
    - Workspace creation
    - Isolated design work
    - Merging contributions
    - Collaborative CAD design
    """
    # === Phase 1: Agent A creates base platform ===

    # Agent A creates workspace
    workspace_a = workspace_manager.create_workspace(
        workspace_name="agent_a_platform",
        workspace_type="agent_branch",
        base_workspace_id="main",
        owning_agent_id="agent_a"
    )

    assert workspace_a is not None, "Agent A workspace should be created"
    assert workspace_a.workspace_type == "agent_branch", "Should be a branch workspace"

    # Agent A designs a platform (20x20x2 box)
    # Create square outline
    l1 = entity_manager.create_line([0, 0], [20, 0], workspace_id=workspace_a.workspace_id)
    l2 = entity_manager.create_line([20, 0], [20, 20], workspace_id=workspace_a.workspace_id)
    l3 = entity_manager.create_line([20, 20], [0, 20], workspace_id=workspace_a.workspace_id)
    l4 = entity_manager.create_line([0, 20], [0, 0], workspace_id=workspace_a.workspace_id)

    # Extrude to create platform
    platform = solid_modeling.extrude(
        entity_ids=[l1.entity_id, l2.entity_id, l3.entity_id, l4.entity_id],
        distance=2.0,
        workspace_id=workspace_a.workspace_id
    )

    # Verify platform created
    assert platform is not None, "Platform should be created"
    assert platform.entity_type == "solid", "Platform should be a solid"
    expected_volume = 20.0 * 20.0 * 2.0  # 800
    assert abs(platform.volume - expected_volume) < 1.0, f"Platform volume should be ~{expected_volume}, got {platform.volume}"

    # === Phase 2: Agent B creates column ===

    # Agent B creates workspace
    workspace_b = workspace_manager.create_workspace(
        workspace_name="agent_b_column",
        workspace_type="agent_branch",
        base_workspace_id="main",
        owning_agent_id="agent_b"
    )

    assert workspace_b is not None, "Agent B workspace should be created"

    # Agent B designs a column (4x4x10 box centered on platform)
    # Create column outline (centered at 10, 10)
    col1 = entity_manager.create_line([8, 8], [12, 8], workspace_id=workspace_b.workspace_id)
    col2 = entity_manager.create_line([12, 8], [12, 12], workspace_id=workspace_b.workspace_id)
    col3 = entity_manager.create_line([12, 12], [8, 12], workspace_id=workspace_b.workspace_id)
    col4 = entity_manager.create_line([8, 12], [8, 8], workspace_id=workspace_b.workspace_id)

    # Extrude to create column
    column = solid_modeling.extrude(
        entity_ids=[col1.entity_id, col2.entity_id, col3.entity_id, col4.entity_id],
        distance=10.0,
        workspace_id=workspace_b.workspace_id
    )

    # Verify column created
    assert column is not None, "Column should be created"
    expected_column_volume = 4.0 * 4.0 * 10.0  # 160
    assert abs(column.volume - expected_column_volume) < 1.0, f"Column volume should be ~{expected_column_volume}, got {column.volume}"

    # === Phase 3: Merge Agent A's work into main ===

    # Count entities in main before merge
    cursor = test_database.connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM entities WHERE workspace_id = ?", ("main",))
    main_count_before = cursor.fetchone()[0]

    # Perform merge from workspace A to main
    cursor.execute("""
        SELECT entity_id, entity_type, properties, bounding_box,
               is_valid, validation_errors, created_at, modified_at, created_by_agent
        FROM entities
        WHERE workspace_id = ?
    """, (workspace_a.workspace_id,))

    entities_merged_a = 0
    conflicts_a = []

    for row in cursor.fetchall():
        entity_id, entity_type, properties, bbox, is_valid, val_errors, created_at, modified_at, created_by = row

        # Generate new entity ID for main
        import uuid
        base_id = entity_id.split('_', 1)[1] if '_' in entity_id else str(uuid.uuid4())[:8]
        new_entity_id = f"main:{entity_type}_{base_id}"

        # Check for conflicts
        cursor.execute("SELECT entity_id FROM entities WHERE entity_id = ?", (new_entity_id,))
        if cursor.fetchone():
            conflicts_a.append(new_entity_id)
            continue

        # Insert into main
        cursor.execute("""
            INSERT INTO entities (
                entity_id, entity_type, workspace_id, properties, bounding_box,
                is_valid, validation_errors, created_at, modified_at, created_by_agent
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (new_entity_id, entity_type, "main", properties, bbox,
              is_valid, val_errors, created_at, modified_at, created_by))

        entities_merged_a += 1

    test_database.connection.commit()

    # Verify Agent A's merge
    assert len(conflicts_a) == 0, f"Agent A merge should have no conflicts, got {len(conflicts_a)}"
    assert entities_merged_a == 5, f"Should merge 5 entities (4 lines + 1 solid), got {entities_merged_a}"

    # Update workspace status
    workspace_manager.update_branch_status(workspace_a.workspace_id, "merged")

    # === Phase 4: Merge Agent B's work into main ===

    # Perform merge from workspace B to main
    cursor.execute("""
        SELECT entity_id, entity_type, properties, bounding_box,
               is_valid, validation_errors, created_at, modified_at, created_by_agent
        FROM entities
        WHERE workspace_id = ?
    """, (workspace_b.workspace_id,))

    entities_merged_b = 0
    conflicts_b = []

    for row in cursor.fetchall():
        entity_id, entity_type, properties, bbox, is_valid, val_errors, created_at, modified_at, created_by = row

        # Generate new entity ID for main
        base_id = entity_id.split('_', 1)[1] if '_' in entity_id else str(uuid.uuid4())[:8]
        new_entity_id = f"main:{entity_type}_{base_id}"

        # Check for conflicts
        cursor.execute("SELECT entity_id FROM entities WHERE entity_id = ?", (new_entity_id,))
        if cursor.fetchone():
            conflicts_b.append(new_entity_id)
            continue

        # Insert into main
        cursor.execute("""
            INSERT INTO entities (
                entity_id, entity_type, workspace_id, properties, bounding_box,
                is_valid, validation_errors, created_at, modified_at, created_by_agent
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (new_entity_id, entity_type, "main", properties, bbox,
              is_valid, val_errors, created_at, modified_at, created_by))

        entities_merged_b += 1

    test_database.connection.commit()

    # Verify Agent B's merge
    assert len(conflicts_b) == 0, f"Agent B merge should have no conflicts, got {len(conflicts_b)}"
    assert entities_merged_b == 5, f"Should merge 5 entities (4 lines + 1 solid), got {entities_merged_b}"

    # Update workspace status
    workspace_manager.update_branch_status(workspace_b.workspace_id, "merged")

    # === Phase 5: Verify final state ===

    # Count total entities in main
    cursor.execute("SELECT COUNT(*) FROM entities WHERE workspace_id = ?", ("main",))
    main_count_after = cursor.fetchone()[0]

    expected_total = main_count_before + entities_merged_a + entities_merged_b
    assert main_count_after == expected_total, f"Main should have {expected_total} entities, got {main_count_after}"

    # Verify both solids exist in main
    cursor.execute("""
        SELECT entity_id, entity_type
        FROM entities
        WHERE workspace_id = ? AND entity_type = ?
    """, ("main", "solid"))

    solids_in_main = cursor.fetchall()
    assert len(solids_in_main) == 2, f"Main should have 2 solids (platform + column), got {len(solids_in_main)}"

    # Verify workspace statuses
    ws_a_status = workspace_manager.get_workspace(workspace_a.workspace_id)
    assert ws_a_status.branch_status == "merged", "Agent A workspace should be marked as merged"

    ws_b_status = workspace_manager.get_workspace(workspace_b.workspace_id)
    assert ws_b_status.branch_status == "merged", "Agent B workspace should be marked as merged"

    print(f"[PASS] Collaborative design complete:")
    print(f"  - Agent A contributed platform (volume: {platform.volume:.2f})")
    print(f"  - Agent B contributed column (volume: {column.volume:.2f})")
    print(f"  - Total entities in main: {main_count_after}")
    print(f"  - No conflicts during merge")
