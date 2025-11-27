"""Primitive solid creation operations using Open CASCADE.

This module provides functions to create basic 3D primitives:
- Box (rectangular prism)
- Cylinder
- Sphere
- Cone
"""
import uuid
from datetime import datetime
from typing import Tuple, Optional

from OCC.Core.BRepPrimAPI import (
    BRepPrimAPI_MakeBox,
    BRepPrimAPI_MakeCylinder,
    BRepPrimAPI_MakeSphere,
    BRepPrimAPI_MakeCone
)
from OCC.Core.gp import gp_Pnt, gp_Ax2, gp_Dir, gp_DZ
from OCC.Core.TopoDS import TopoDS_Shape

from .geometry_engine import GeometryShape
from .properties import SolidProperties
from .exceptions import OperationFailedError, InvalidGeometryError


def create_box(
    width: float,
    depth: float,
    height: float,
    workspace_id: str,
    position: Optional[Tuple[float, float, float]] = None
) -> Tuple[GeometryShape, SolidProperties]:
    """Create a rectangular box primitive.

    Args:
        width: Box width (X dimension) in mm
        depth: Box depth (Y dimension) in mm
        height: Box height (Z dimension) in mm
        workspace_id: Workspace for this geometry
        position: Optional corner position (x, y, z). Default: origin (0, 0, 0)

    Returns:
        Tuple of (GeometryShape, SolidProperties)

    Raises:
        InvalidGeometryError: If dimensions are invalid (non-positive)
        OperationFailedError: If box creation fails
    """
    # Validate inputs
    if width <= 0 or depth <= 0 or height <= 0:
        raise InvalidGeometryError(
            f"Box dimensions must be positive (got width={width}, depth={depth}, height={height})"
        )

    try:
        # Create box at origin or specified position
        if position is None:
            # Simple box from origin
            maker = BRepPrimAPI_MakeBox(width, depth, height)
        else:
            # Box from specified corner point
            corner = gp_Pnt(position[0], position[1], position[2])
            maker = BRepPrimAPI_MakeBox(corner, width, depth, height)

        # Build the shape (required before IsDone check)
        maker.Build()

        if not maker.IsDone():
            raise OperationFailedError("Box creation failed - IsDone() returned False")

        shape = maker.Shape()

        # Wrap in GeometryShape
        geo_shape = GeometryShape.from_shape(shape, workspace_id, validate=True)

        # Compute properties
        entity_id = f"box_{uuid.uuid4().hex[:8]}"
        props = SolidProperties.compute_from_shape(entity_id, shape)

        # Verify expected volume
        expected_volume = width * depth * height
        if abs(props.volume - expected_volume) > 0.01:
            raise OperationFailedError(
                f"Box volume mismatch: expected {expected_volume:.2f}, got {props.volume:.2f}"
            )

        return geo_shape, props

    except (InvalidGeometryError, OperationFailedError):
        raise
    except Exception as e:
        raise OperationFailedError(f"Failed to create box: {e}")


def create_cylinder(
    radius: float,
    height: float,
    workspace_id: str,
    position: Optional[Tuple[float, float, float]] = None,
    direction: Optional[Tuple[float, float, float]] = None
) -> Tuple[GeometryShape, SolidProperties]:
    """Create a cylinder primitive.

    Args:
        radius: Cylinder radius in mm
        height: Cylinder height in mm
        workspace_id: Workspace for this geometry
        position: Optional base center position (x, y, z). Default: origin
        direction: Optional axis direction (x, y, z). Default: +Z (0, 0, 1)

    Returns:
        Tuple of (GeometryShape, SolidProperties)

    Raises:
        InvalidGeometryError: If radius or height are invalid
        OperationFailedError: If cylinder creation fails
    """
    # Validate inputs
    if radius <= 0:
        raise InvalidGeometryError(f"Cylinder radius must be positive (got {radius})")
    if height <= 0:
        raise InvalidGeometryError(f"Cylinder height must be positive (got {height})")

    try:
        # Setup coordinate system
        if position is None and direction is None:
            # Simple cylinder along Z axis from origin
            maker = BRepPrimAPI_MakeCylinder(radius, height)
        else:
            # Custom position and/or direction
            base_point = gp_Pnt(*(position or (0, 0, 0)))
            axis_dir = gp_Dir(*(direction or (0, 0, 1)))
            axis = gp_Ax2(base_point, axis_dir)
            maker = BRepPrimAPI_MakeCylinder(axis, radius, height)

        # Build the shape (required before IsDone check)
        maker.Build()

        if not maker.IsDone():
            raise OperationFailedError("Cylinder creation failed - IsDone() returned False")

        shape = maker.Shape()

        # Wrap in GeometryShape
        geo_shape = GeometryShape.from_shape(shape, workspace_id, validate=True)

        # Compute properties
        entity_id = f"cylinder_{uuid.uuid4().hex[:8]}"
        props = SolidProperties.compute_from_shape(entity_id, shape)

        # Verify expected volume (π * r² * h)
        import math
        expected_volume = math.pi * radius * radius * height
        if abs(props.volume - expected_volume) / expected_volume > 0.01:  # 1% tolerance
            raise OperationFailedError(
                f"Cylinder volume mismatch: expected {expected_volume:.2f}, got {props.volume:.2f}"
            )

        return geo_shape, props

    except (InvalidGeometryError, OperationFailedError):
        raise
    except Exception as e:
        raise OperationFailedError(f"Failed to create cylinder: {e}")


def create_sphere(
    radius: float,
    workspace_id: str,
    center: Optional[Tuple[float, float, float]] = None
) -> Tuple[GeometryShape, SolidProperties]:
    """Create a sphere primitive.

    Args:
        radius: Sphere radius in mm
        workspace_id: Workspace for this geometry
        center: Optional center position (x, y, z). Default: origin

    Returns:
        Tuple of (GeometryShape, SolidProperties)

    Raises:
        InvalidGeometryError: If radius is invalid
        OperationFailedError: If sphere creation fails
    """
    # Validate inputs
    if radius <= 0:
        raise InvalidGeometryError(f"Sphere radius must be positive (got {radius})")

    try:
        # Create sphere
        if center is None:
            # Simple sphere at origin
            maker = BRepPrimAPI_MakeSphere(radius)
        else:
            # Sphere at specified center
            center_point = gp_Pnt(center[0], center[1], center[2])
            maker = BRepPrimAPI_MakeSphere(center_point, radius)

        # Build the shape (required before IsDone check)
        maker.Build()

        if not maker.IsDone():
            raise OperationFailedError("Sphere creation failed - IsDone() returned False")

        shape = maker.Shape()

        # Wrap in GeometryShape
        geo_shape = GeometryShape.from_shape(shape, workspace_id, validate=True)

        # Compute properties
        entity_id = f"sphere_{uuid.uuid4().hex[:8]}"
        props = SolidProperties.compute_from_shape(entity_id, shape)

        # Verify expected volume (4/3 * π * r³)
        import math
        expected_volume = (4.0 / 3.0) * math.pi * (radius ** 3)
        if abs(props.volume - expected_volume) / expected_volume > 0.01:  # 1% tolerance
            raise OperationFailedError(
                f"Sphere volume mismatch: expected {expected_volume:.2f}, got {props.volume:.2f}"
            )

        return geo_shape, props

    except (InvalidGeometryError, OperationFailedError):
        raise
    except Exception as e:
        raise OperationFailedError(f"Failed to create sphere: {e}")


def create_cone(
    radius1: float,
    radius2: float,
    height: float,
    workspace_id: str,
    position: Optional[Tuple[float, float, float]] = None,
    direction: Optional[Tuple[float, float, float]] = None
) -> Tuple[GeometryShape, SolidProperties]:
    """Create a cone or frustum primitive.

    Args:
        radius1: Bottom radius in mm
        radius2: Top radius in mm (use 0 for pointed cone)
        height: Cone height in mm
        workspace_id: Workspace for this geometry
        position: Optional base center position (x, y, z). Default: origin
        direction: Optional axis direction (x, y, z). Default: +Z

    Returns:
        Tuple of (GeometryShape, SolidProperties)

    Raises:
        InvalidGeometryError: If radii or height are invalid
        OperationFailedError: If cone creation fails
    """
    # Validate inputs
    if radius1 < 0 or radius2 < 0:
        raise InvalidGeometryError(
            f"Cone radii must be non-negative (got radius1={radius1}, radius2={radius2})"
        )
    if radius1 == 0 and radius2 == 0:
        raise InvalidGeometryError("At least one radius must be positive")
    if height <= 0:
        raise InvalidGeometryError(f"Cone height must be positive (got {height})")

    try:
        # Setup coordinate system
        if position is None and direction is None:
            # Simple cone along Z axis from origin
            maker = BRepPrimAPI_MakeCone(radius1, radius2, height)
        else:
            # Custom position and/or direction
            base_point = gp_Pnt(*(position or (0, 0, 0)))
            axis_dir = gp_Dir(*(direction or (0, 0, 1)))
            axis = gp_Ax2(base_point, axis_dir)
            maker = BRepPrimAPI_MakeCone(axis, radius1, radius2, height)

        # Build the shape (required before IsDone check)
        maker.Build()

        if not maker.IsDone():
            raise OperationFailedError("Cone creation failed - IsDone() returned False")

        shape = maker.Shape()

        # Wrap in GeometryShape
        geo_shape = GeometryShape.from_shape(shape, workspace_id, validate=True)

        # Compute properties
        entity_id = f"cone_{uuid.uuid4().hex[:8]}"
        props = SolidProperties.compute_from_shape(entity_id, shape)

        # Verify expected volume (1/3 * π * h * (r1² + r1*r2 + r2²))
        import math
        expected_volume = (1.0 / 3.0) * math.pi * height * (radius1**2 + radius1*radius2 + radius2**2)
        if abs(props.volume - expected_volume) / expected_volume > 0.01:  # 1% tolerance
            raise OperationFailedError(
                f"Cone volume mismatch: expected {expected_volume:.2f}, got {props.volume:.2f}"
            )

        return geo_shape, props

    except (InvalidGeometryError, OperationFailedError):
        raise
    except Exception as e:
        raise OperationFailedError(f"Failed to create cone: {e}")
