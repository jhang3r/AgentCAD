"""Boolean operations for combining and modifying 3D solids.

Implements union, subtract, and intersect operations using Open CASCADE.
"""
import uuid
from typing import Tuple

from OCC.Core.TopoDS import TopoDS_Shape
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Fuse, BRepAlgoAPI_Cut, BRepAlgoAPI_Common
from OCC.Core.BRepCheck import BRepCheck_Analyzer

from .geometry_engine import GeometryShape
from .properties import SolidProperties
from .exceptions import InvalidGeometryError, OperationFailedError


def validate_solid(shape: TopoDS_Shape, entity_id: str) -> None:
    """Validate that a shape is a valid solid.

    Args:
        shape: Shape to validate
        entity_id: Entity ID for error messages

    Raises:
        InvalidGeometryError: If shape is not a valid solid
    """
    analyzer = BRepCheck_Analyzer(shape)
    if not analyzer.IsValid():
        raise InvalidGeometryError(
            f"Invalid geometry for {entity_id}: Shape failed validation"
        )


def union(
    solid1_shape: TopoDS_Shape,
    solid2_shape: TopoDS_Shape,
    workspace_id: str,
    solid1_id: str = "solid1",
    solid2_id: str = "solid2"
) -> Tuple[GeometryShape, SolidProperties]:
    """Perform boolean union (A ∪ B) on two solids.

    Creates a new solid representing the combined volume of both input solids.

    Args:
        solid1_shape: First solid shape
        solid2_shape: Second solid shape
        workspace_id: Workspace for the result
        solid1_id: ID of first solid (for error messages)
        solid2_id: ID of second solid (for error messages)

    Returns:
        Tuple of (GeometryShape, SolidProperties) for the result

    Raises:
        InvalidGeometryError: If either input is invalid
        OperationFailedError: If union operation fails
    """
    # Validate inputs
    validate_solid(solid1_shape, solid1_id)
    validate_solid(solid2_shape, solid2_id)

    try:
        # Create union (fuse) operation
        fuse = BRepAlgoAPI_Fuse(solid1_shape, solid2_shape)

        # Build the result
        fuse.Build()

        if not fuse.IsDone():
            raise OperationFailedError("Boolean union failed - IsDone() returned False")

        # Get result shape
        result_shape = fuse.Shape()

        # Validate result
        validate_solid(result_shape, "union_result")

        # Wrap in GeometryShape
        geo_shape = GeometryShape.from_shape(result_shape, workspace_id, validate=True)

        # Compute properties
        entity_id = f"union_{uuid.uuid4().hex[:8]}"
        props = SolidProperties.compute_from_shape(entity_id, result_shape)

        return geo_shape, props

    except (InvalidGeometryError, OperationFailedError):
        raise
    except Exception as e:
        raise OperationFailedError(f"Boolean union failed: {e}")


def subtract(
    base_shape: TopoDS_Shape,
    tool_shape: TopoDS_Shape,
    workspace_id: str,
    base_id: str = "base",
    tool_id: str = "tool"
) -> Tuple[GeometryShape, SolidProperties]:
    """Perform boolean subtraction (A - B) to remove tool from base.

    Creates a new solid with the tool's volume removed from the base solid.

    Args:
        base_shape: Base solid to subtract from
        tool_shape: Tool solid to subtract
        workspace_id: Workspace for the result
        base_id: ID of base solid (for error messages)
        tool_id: ID of tool solid (for error messages)

    Returns:
        Tuple of (GeometryShape, SolidProperties) for the result

    Raises:
        InvalidGeometryError: If either input is invalid
        OperationFailedError: If subtract operation fails
    """
    # Validate inputs
    validate_solid(base_shape, base_id)
    validate_solid(tool_shape, tool_id)

    try:
        # Create cut (subtraction) operation
        cut = BRepAlgoAPI_Cut(base_shape, tool_shape)

        # Build the result
        cut.Build()

        if not cut.IsDone():
            raise OperationFailedError("Boolean subtract failed - IsDone() returned False")

        # Get result shape
        result_shape = cut.Shape()

        # Validate result
        validate_solid(result_shape, "subtract_result")

        # Wrap in GeometryShape
        geo_shape = GeometryShape.from_shape(result_shape, workspace_id, validate=True)

        # Compute properties
        entity_id = f"subtract_{uuid.uuid4().hex[:8]}"
        props = SolidProperties.compute_from_shape(entity_id, result_shape)

        return geo_shape, props

    except (InvalidGeometryError, OperationFailedError):
        raise
    except Exception as e:
        raise OperationFailedError(f"Boolean subtract failed: {e}")


def intersect(
    solid1_shape: TopoDS_Shape,
    solid2_shape: TopoDS_Shape,
    workspace_id: str,
    solid1_id: str = "solid1",
    solid2_id: str = "solid2"
) -> Tuple[GeometryShape, SolidProperties]:
    """Perform boolean intersection (A ∩ B) to find overlapping volume.

    Creates a new solid from only the overlapping volume of both input solids.

    Args:
        solid1_shape: First solid shape
        solid2_shape: Second solid shape
        workspace_id: Workspace for the result
        solid1_id: ID of first solid (for error messages)
        solid2_id: ID of second solid (for error messages)

    Returns:
        Tuple of (GeometryShape, SolidProperties) for the result

    Raises:
        InvalidGeometryError: If either input is invalid
        OperationFailedError: If intersect operation fails or solids don't overlap
    """
    # Validate inputs
    validate_solid(solid1_shape, solid1_id)
    validate_solid(solid2_shape, solid2_id)

    try:
        # Create common (intersection) operation
        common = BRepAlgoAPI_Common(solid1_shape, solid2_shape)

        # Build the result
        common.Build()

        if not common.IsDone():
            raise OperationFailedError("Boolean intersect failed - IsDone() returned False")

        # Get result shape
        result_shape = common.Shape()

        # Validate result - if solids don't overlap, result may be empty or invalid
        analyzer = BRepCheck_Analyzer(result_shape)
        if not analyzer.IsValid():
            raise OperationFailedError(
                f"Boolean intersect failed: Solids do not overlap or result is invalid. "
                f"Check that {solid1_id} and {solid2_id} actually intersect."
            )

        # Wrap in GeometryShape
        geo_shape = GeometryShape.from_shape(result_shape, workspace_id, validate=True)

        # Compute properties
        entity_id = f"intersect_{uuid.uuid4().hex[:8]}"
        props = SolidProperties.compute_from_shape(entity_id, result_shape)

        # Additional check: if volume is near zero, operation likely failed
        if props.volume < 0.01:  # Less than 0.01 cubic mm
            raise OperationFailedError(
                f"Boolean intersect failed: Solids do not overlap (result volume ~0). "
                f"Verify that {solid1_id} and {solid2_id} actually intersect."
            )

        return geo_shape, props

    except (InvalidGeometryError, OperationFailedError):
        raise
    except Exception as e:
        raise OperationFailedError(f"Boolean intersect failed: {e}")
