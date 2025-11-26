"""JSON format import/export for CAD entities.

JSON is a simple interchange format that preserves all entity properties.
"""
import json
from pathlib import Path
from typing import Any


def export_json(entities: list[dict[str, Any]], file_path: str) -> dict[str, Any]:
    """Export entities to JSON format.

    Args:
        entities: List of entity dictionaries
        file_path: Output file path

    Returns:
        Export report with statistics
    """
    output_path = Path(file_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Create export data structure
    export_data = {
        "format_version": "1.0",
        "entity_count": len(entities),
        "entities": entities
    }

    # Write to file
    with open(output_path, 'w') as f:
        json.dump(export_data, f, indent=2)

    file_size = output_path.stat().st_size

    return {
        "file_path": str(output_path),
        "format": "json",
        "entity_count": len(entities),
        "file_size": file_size,
        "data_loss": False,
        "warnings": []
    }


def import_json(file_path: str) -> dict[str, Any]:
    """Import entities from JSON format.

    Args:
        file_path: Input file path

    Returns:
        Import report with entities and statistics
    """
    input_path = Path(file_path)

    if not input_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Read file
    with open(input_path, 'r') as f:
        import_data = json.load(f)

    if "entities" not in import_data:
        raise ValueError("Invalid JSON format: missing 'entities' field")

    entities = import_data["entities"]

    return {
        "file_path": str(input_path),
        "format": "json",
        "entity_count": len(entities),
        "entities": entities,
        "warnings": [],
        "errors": []
    }
