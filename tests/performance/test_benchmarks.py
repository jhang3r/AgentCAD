"""Performance benchmarks for CAD operations.

Ensures operations meet performance targets:
- Simple operations (point, line, circle): <100ms
- Complex operations (extrude, boolean): <1s
"""
import pytest
import time
from src.cad_kernel.entity_manager import EntityManager
from src.persistence.database import Database
from src.operations.solid_modeling import SolidModeling


@pytest.fixture
def test_database(tmp_path):
    """Create test database."""
    db_path = str(tmp_path / "test_perf.db")
    db = Database(db_path)
    yield db
    db.close()


@pytest.fixture
def entity_manager(test_database):
    """Create entity manager."""
    return EntityManager(test_database)


@pytest.fixture
def solid_modeling(entity_manager):
    """Create solid modeling operations."""
    return SolidModeling(entity_manager)


def test_point_creation_performance(entity_manager):
    """Test point creation is <100ms."""
    start = time.time()
    point = entity_manager.create_point([10, 20, 30], workspace_id="main")
    elapsed_ms = (time.time() - start) * 1000

    assert point is not None, "Point should be created"
    assert elapsed_ms < 100, f"Point creation should be <100ms, took {elapsed_ms:.2f}ms"
    print(f"Point creation: {elapsed_ms:.2f}ms (target: <100ms)")


def test_line_creation_performance(entity_manager):
    """Test line creation is <100ms."""
    start = time.time()
    line = entity_manager.create_line([0, 0], [10, 10], workspace_id="main")
    elapsed_ms = (time.time() - start) * 1000

    assert line is not None, "Line should be created"
    assert elapsed_ms < 100, f"Line creation should be <100ms, took {elapsed_ms:.2f}ms"
    print(f"Line creation: {elapsed_ms:.2f}ms (target: <100ms)")


def test_circle_creation_performance(entity_manager):
    """Test circle creation is <100ms."""
    start = time.time()
    circle = entity_manager.create_circle([5, 5], 3.0, workspace_id="main")
    elapsed_ms = (time.time() - start) * 1000

    assert circle is not None, "Circle should be created"
    assert elapsed_ms < 100, f"Circle creation should be <100ms, took {elapsed_ms:.2f}ms"
    print(f"Circle creation: {elapsed_ms:.2f}ms (target: <100ms)")


def test_extrude_performance(entity_manager, solid_modeling):
    """Test extrusion is <1s."""
    # Create square
    l1 = entity_manager.create_line([0, 0], [10, 0], workspace_id="main")
    l2 = entity_manager.create_line([10, 0], [10, 10], workspace_id="main")
    l3 = entity_manager.create_line([10, 10], [0, 10], workspace_id="main")
    l4 = entity_manager.create_line([0, 10], [0, 0], workspace_id="main")

    start = time.time()
    solid = solid_modeling.extrude(
        [l1.entity_id, l2.entity_id, l3.entity_id, l4.entity_id],
        10.0,
        workspace_id="main"
    )
    elapsed_ms = (time.time() - start) * 1000

    assert solid is not None, "Extrusion should succeed"
    assert elapsed_ms < 1000, f"Extrusion should be <1s, took {elapsed_ms:.2f}ms"
    print(f"Extrusion: {elapsed_ms:.2f}ms (target: <1000ms)")


def test_boolean_union_performance(entity_manager, solid_modeling):
    """Test boolean union is <1s."""
    # Create two boxes
    l1 = entity_manager.create_line([0, 0], [10, 0], workspace_id="main")
    l2 = entity_manager.create_line([10, 0], [10, 10], workspace_id="main")
    l3 = entity_manager.create_line([10, 10], [0, 10], workspace_id="main")
    l4 = entity_manager.create_line([0, 10], [0, 0], workspace_id="main")
    box1 = solid_modeling.extrude([l1.entity_id, l2.entity_id, l3.entity_id, l4.entity_id], 10.0, "main")

    l5 = entity_manager.create_line([5, 0], [15, 0], workspace_id="main")
    l6 = entity_manager.create_line([15, 0], [15, 10], workspace_id="main")
    l7 = entity_manager.create_line([15, 10], [5, 10], workspace_id="main")
    l8 = entity_manager.create_line([5, 10], [5, 0], workspace_id="main")
    box2 = solid_modeling.extrude([l5.entity_id, l6.entity_id, l7.entity_id, l8.entity_id], 10.0, "main")

    start = time.time()
    result = solid_modeling.boolean_union([box1.entity_id, box2.entity_id], "main")
    elapsed_ms = (time.time() - start) * 1000

    assert result is not None, "Boolean union should succeed"
    assert elapsed_ms < 1000, f"Boolean union should be <1s, took {elapsed_ms:.2f}ms"
    print(f"Boolean union: {elapsed_ms:.2f}ms (target: <1000ms)")


def test_batch_operations_performance(entity_manager):
    """Test creating 100 entities is reasonably fast."""
    start = time.time()

    for i in range(100):
        entity_manager.create_point([i, i * 2, i * 3], workspace_id="main")

    elapsed_ms = (time.time() - start) * 1000
    avg_per_entity = elapsed_ms / 100

    print(f"100 point creations: {elapsed_ms:.2f}ms total, {avg_per_entity:.2f}ms per point")
    assert avg_per_entity < 100, f"Average per entity should be <100ms, got {avg_per_entity:.2f}ms"
