"""STEP format export for CAD solids.

STEP (Standard for the Exchange of Product Data) is an ISO standard (ISO 10303)
for representing and exchanging product manufacturing information. It preserves
exact geometry unlike mesh formats (STL, OBJ).
"""
from pathlib import Path
from typing import List, Any, Dict

from OCC.Core.TopoDS import TopoDS_Shape
from OCC.Core.STEPControl import STEPControl_Writer, STEPControl_AsIs
from OCC.Core.IFSelect import IFSelect_RetDone
from OCC.Core.Interface import Interface_Static


def export_step(
    shapes: List[TopoDS_Shape],
    file_path: str,
    schema: str = "AP214"
) -> Dict[str, Any]:
    """Export Open CASCADE shapes to STEP format.

    STEP preserves exact geometry (BRep representation) unlike mesh formats.
    This is the preferred format for CAD-to-CAD data exchange.

    Args:
        shapes: List of TopoDS_Shape objects to export
        file_path: Output file path (.step or .stp)
        schema: STEP schema (AP203, AP214, AP242) - default AP214

    Returns:
        Export report dictionary with statistics

    Raises:
        RuntimeError: If STEP export fails
    """
    output_path = Path(file_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Ensure proper extension
    if output_path.suffix.lower() not in ['.step', '.stp']:
        output_path = output_path.with_suffix('.step')

    # Initialize STEP writer
    writer = STEPControl_Writer()

    # Set STEP schema (AP203, AP214, AP242)
    # AP214: Automotive design (most common)
    # AP203: Configuration controlled 3D design
    # AP242: Managed model based 3D engineering (latest)
    Interface_Static.SetCVal("write.step.schema", schema)

    # Set unit to millimeters
    Interface_Static.SetCVal("write.step.unit", "MM")

    # Set product name
    Interface_Static.SetCVal("write.step.product.name", "CAD_Export")

    # Transfer shapes to STEP writer
    shape_count = 0
    for shape in shapes:
        # Transfer shape (keep topology as-is)
        status = writer.Transfer(shape, STEPControl_AsIs)
        if status == IFSelect_RetDone:
            shape_count += 1
        else:
            raise RuntimeError(f"Failed to transfer shape {shape_count + 1} to STEP writer")

    if shape_count == 0:
        raise RuntimeError("No shapes were successfully transferred to STEP writer")

    # Write STEP file
    write_status = writer.Write(str(output_path))

    if write_status != IFSelect_RetDone:
        raise RuntimeError(f"STEP write failed with status: {write_status}")

    # Get file statistics
    file_size = output_path.stat().st_size

    return {
        "file_path": str(output_path.absolute()),
        "format": "step",
        "schema": schema,
        "entity_count": shape_count,
        "file_size": file_size,
        "data_loss": False,  # STEP preserves exact geometry
        "notes": [
            f"STEP format preserves exact BRep geometry (schema: {schema})",
            "Compatible with most CAD software (SolidWorks, CATIA, NX, etc.)",
            "Recommended for CAD-to-CAD data exchange"
        ]
    }


def get_supported_schemas() -> List[str]:
    """Get list of supported STEP schemas.

    Returns:
        List of schema names
    """
    return ["AP203", "AP214", "AP242"]
