"""Integration tests for file I/O operations.

Tests STL export and file round-trip functionality.
"""
import pytest
import os
import json
from src.cad_kernel.entity_manager import EntityManager
from src.persistence.database import Database
from src.operations.solid_modeling import SolidModeling
from src.file_io.stl_handler import export_stl
from src.file_io.json_handler import export_json, import_json


@pytest.fixture
def test_database(tmp_path):
    """Create test database."""
    db_path = str(tmp_path / "test_file_io.db")
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


def test_stl_export_tessellation(entity_manager, solid_modeling, tmp_path):
    """Test STL export with tessellation.

    Scenario:
    1. Create a box (10x10x10)
    2. Export to STL
    3. Verify file created
    4. Verify file size > 0
    5. Verify triangle count > 0
    6. Verify STL header format
    """
    workspace_id = "main"

    # Create box
    line1 = entity_manager.create_line([0, 0], [10, 0], workspace_id=workspace_id)
    line2 = entity_manager.create_line([10, 0], [10, 10], workspace_id=workspace_id)
    line3 = entity_manager.create_line([10, 10], [0, 10], workspace_id=workspace_id)
    line4 = entity_manager.create_line([0, 10], [0, 0], workspace_id=workspace_id)

    box = solid_modeling.extrude(
        entity_ids=[line1.entity_id, line2.entity_id, line3.entity_id, line4.entity_id],
        distance=10.0,
        workspace_id=workspace_id
    )

    # Export to STL
    output_path = str(tmp_path / "test_box.stl")
    solids = [box.to_dict()]
    result = export_stl(solids, output_path)

    # Verify file created
    assert os.path.exists(output_path), "STL file should be created"

    # Verify file size
    file_size = os.path.getsize(output_path)
    assert file_size > 0, "STL file should not be empty"
    assert file_size == result["file_size_bytes"], "Reported file size should match actual"

    # Verify triangle count
    assert result["triangle_count"] > 0, "Should have triangles"
    # Box should have 6 faces, each triangulated into at least 2 triangles = 12 minimum
    assert result["triangle_count"] >= 12, f"Box should have at least 12 triangles, got {result['triangle_count']}"

    # Verify STL format (read first line)
    with open(output_path, 'r') as f:
        first_line = f.readline().strip()
        assert first_line.startswith("solid"), "STL should start with 'solid' keyword"


def test_file_roundtrip_validation(entity_manager, solid_modeling, tmp_path):
    """Test file round-trip: Create → Export JSON → Import → Verify.

    Scenario:
    1. Create entities (points, lines, circle, box)
    2. Export to JSON
    3. Clear database
    4. Import from JSON
    5. Verify all entities restored correctly
    6. Verify properties preserved
    """
    workspace_id = "main"

    # Step 1: Create entities
    point1 = entity_manager.create_point([10, 20, 30], workspace_id=workspace_id)
    line1 = entity_manager.create_line([0, 0], [10, 10], workspace_id=workspace_id)
    circle1 = entity_manager.create_circle([5, 5], 3.0, workspace_id=workspace_id)

    # Create a box
    l1 = entity_manager.create_line([0, 0], [10, 0], workspace_id=workspace_id)
    l2 = entity_manager.create_line([10, 0], [10, 10], workspace_id=workspace_id)
    l3 = entity_manager.create_line([10, 10], [0, 10], workspace_id=workspace_id)
    l4 = entity_manager.create_line([0, 10], [0, 0], workspace_id=workspace_id)
    box = solid_modeling.extrude(
        [l1.entity_id, l2.entity_id, l3.entity_id, l4.entity_id],
        10.0,
        workspace_id
    )

    # Record original data
    original_entities = {
        "point": point1.to_dict(),
        "line": line1.to_dict(),
        "circle": circle1.to_dict(),
        "box": box.to_dict()
    }

    # Step 2: Export to JSON
    json_path = str(tmp_path / "test_export.json")

    # Query all entities from database for export
    cursor = entity_manager.database.connection.cursor()
    cursor.execute("""
        SELECT entity_id, entity_type, workspace_id, properties, bounding_box,
               is_valid, validation_errors, created_at, modified_at, created_by_agent
        FROM entities
        WHERE workspace_id = ?
    """, (workspace_id,))

    entities_to_export = []
    for row in cursor.fetchall():
        entity_dict = dict(row)
        entity_dict["properties"] = json.loads(entity_dict["properties"]) if entity_dict["properties"] else {}
        entity_dict["bounding_box"] = json.loads(entity_dict["bounding_box"]) if entity_dict["bounding_box"] else {}
        entity_dict["validation_errors"] = json.loads(entity_dict["validation_errors"]) if entity_dict["validation_errors"] else []
        entity_dict["is_valid"] = bool(entity_dict["is_valid"])

        # Spread properties for consistency
        if entity_dict["entity_type"] == "solid":
            props = entity_dict["properties"]
            entity_dict.update(props)
            del entity_dict["properties"]

        entities_to_export.append(entity_dict)

    result = export_json(entities_to_export, json_path)

    # Verify export
    assert os.path.exists(json_path), "JSON file should be created"
    assert result["entity_count"] == 8, "Should export 8 entities (3 initial + 4 for box + 1 box solid)"

    # Step 3: Clear database (delete entities)
    cursor.execute("DELETE FROM entities WHERE workspace_id = ?", (workspace_id,))
    entity_manager.database.connection.commit()

    # Verify cleared
    cursor.execute("SELECT COUNT(*) FROM entities WHERE workspace_id = ?", (workspace_id,))
    assert cursor.fetchone()[0] == 0, "Database should be empty"

    # Step 4: Import from JSON
    import_result = import_json(json_path)

    # Step 5: Re-insert imported entities into database
    for entity_data in import_result["entities"]:
        # Convert back to database format
        entity_type = entity_data["entity_type"]
        entity_id = entity_data["entity_id"]

        # For solids, nest properties back
        if entity_type == "solid":
            properties = {
                "volume": entity_data.get("volume"),
                "surface_area": entity_data.get("surface_area"),
                "center_of_mass": entity_data.get("center_of_mass"),
                "topology": entity_data.get("topology")
            }
        else:
            # Extract entity-specific properties
            if entity_type == "point":
                properties = {"coordinates": entity_data.get("coordinates")}
            elif entity_type == "line":
                properties = {
                    "start": entity_data.get("start"),
                    "end": entity_data.get("end"),
                    "length": entity_data.get("length")
                }
            elif entity_type == "circle":
                properties = {
                    "center": entity_data.get("center"),
                    "radius": entity_data.get("radius"),
                    "circumference": entity_data.get("circumference"),
                    "area": entity_data.get("area")
                }
            else:
                properties = {}

        cursor.execute("""
            INSERT INTO entities (
                entity_id, entity_type, workspace_id, properties, bounding_box,
                is_valid, validation_errors, created_at, modified_at, created_by_agent
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entity_id,
            entity_type,
            entity_data.get("workspace_id", workspace_id),
            json.dumps(properties),
            json.dumps(entity_data.get("bounding_box", {})),
            entity_data.get("is_valid", True),
            json.dumps(entity_data.get("validation_errors", [])),
            entity_data.get("created_at"),
            entity_data.get("modified_at"),
            entity_data.get("created_by_agent", "default_agent")
        ))

    entity_manager.database.connection.commit()

    # Step 6: Verify restoration
    cursor.execute("SELECT COUNT(*) FROM entities WHERE workspace_id = ?", (workspace_id,))
    count = cursor.fetchone()[0]
    assert count == 8, f"Should restore 8 entities, got {count}"

    # Verify specific entities
    cursor.execute("""
        SELECT entity_id, entity_type, properties
        FROM entities
        WHERE entity_id = ? AND workspace_id = ?
    """, (point1.entity_id, workspace_id))

    point_row = cursor.fetchone()
    assert point_row is not None, "Point should be restored"
    restored_point_props = json.loads(point_row[2])
    assert restored_point_props["coordinates"] == [10, 20, 30], "Point coordinates should be preserved"

    # Verify box solid
    cursor.execute("""
        SELECT entity_type, properties
        FROM entities
        WHERE entity_id = ? AND workspace_id = ?
    """, (box.entity_id, workspace_id))

    box_row = cursor.fetchone()
    assert box_row is not None, "Box solid should be restored"
    assert box_row[0] == "solid", "Entity type should be solid"
    restored_box_props = json.loads(box_row[1])
    assert "volume" in restored_box_props, "Box should have volume property"
    # Volume should be preserved (10x10x10 = 1000)
    assert abs(restored_box_props["volume"] - 1000.0) < 0.1, "Box volume should be preserved"


def test_json_export_format_validation(entity_manager, tmp_path):
    """Test JSON export format is valid and complete.

    Verifies:
    1. Valid JSON syntax
    2. Required fields present
    3. Metadata included
    """
    workspace_id = "main"

    # Create simple entities
    point = entity_manager.create_point([1, 2, 3], workspace_id=workspace_id)
    line = entity_manager.create_line([0, 0], [5, 5], workspace_id=workspace_id)

    # Query entities
    cursor = entity_manager.database.connection.cursor()
    cursor.execute("""
        SELECT entity_id, entity_type, workspace_id, properties, bounding_box,
               is_valid, validation_errors, created_at, modified_at, created_by_agent
        FROM entities
        WHERE workspace_id = ?
    """, (workspace_id,))

    entities = []
    for row in cursor.fetchall():
        entity_dict = dict(row)
        entity_dict["properties"] = json.loads(entity_dict["properties"]) if entity_dict["properties"] else {}
        entity_dict["bounding_box"] = json.loads(entity_dict["bounding_box"]) if entity_dict["bounding_box"] else {}
        entity_dict["validation_errors"] = json.loads(entity_dict["validation_errors"]) if entity_dict["validation_errors"] else []
        entity_dict["is_valid"] = bool(entity_dict["is_valid"])

        # Spread properties
        props = entity_dict.pop("properties")
        entity_dict.update(props)

        entities.append(entity_dict)

    # Export
    json_path = str(tmp_path / "format_test.json")
    result = export_json(entities, json_path)

    # Verify file is valid JSON
    with open(json_path, 'r') as f:
        data = json.load(f)

    # Verify structure
    assert "entities" in data, "Should have entities key"
    assert "metadata" in data, "Should have metadata key"
    assert isinstance(data["entities"], list), "Entities should be a list"
    assert len(data["entities"]) == 2, "Should have 2 entities"

    # Verify entity fields
    for entity in data["entities"]:
        assert "entity_id" in entity, "Entity should have entity_id"
        assert "entity_type" in entity, "Entity should have entity_type"
        assert "workspace_id" in entity, "Entity should have workspace_id"
