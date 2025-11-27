"""Pattern and mirror operations for duplicating geometry.

Implements linear pattern, circular pattern, and mirror operations using Open CASCADE.
"""
import math
import uuid
from typing import Tuple, List

from OCC.Core.TopoDS import TopoDS_Shape
from OCC.Core.gp import gp_Trsf, gp_Vec, gp_Ax1, gp_Pnt, gp_Dir, gp_Pln
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform

from .geometry_engine import GeometryShape
from .properties import SolidProperties
from .exceptions import InvalidGeometryError, OperationFailedError


def linear_pattern(
    base_shape: TopoDS_Shape,
    direction: Tuple[float, float, float],
    spacing: float,
    count: int,
    workspace_id: str
) -> List[Tuple[GeometryShape, SolidProperties]]:
    """Create a linear pattern of copies along a direction vector.

    Args:
        base_shape: Base shape to pattern
        direction: Direction vector (dx, dy, dz) - will be normalized
        spacing: Distance between copies in mm
        count: Number of copies to create (including original)
        workspace_id: Workspace for this geometry

    Returns:
        List of (GeometryShape, SolidProperties) tuples for each copy

    Raises:
        InvalidGeometryError: If parameters are invalid
        OperationFailedError: If pattern operation fails
    """
    # Validate inputs
    if count <= 0:
        raise InvalidGeometryError(f"Pattern count must be positive (got {count})")

    if spacing <= 0:
        raise InvalidGeometryError(f"Pattern spacing must be positive (got {spacing})")

    # Normalize direction vector
    dx, dy, dz = direction
    mag = math.sqrt(dx*dx + dy*dy + dz*dz)
    if mag < 1e-10:
        raise InvalidGeometryError("Direction vector cannot be zero")

    dx, dy, dz = dx/mag, dy/mag, dz/mag

    results = []

    try:
        for i in range(count):
            # Calculate translation distance
            offset = spacing * i

            # Create transformation (translation)
            trsf = gp_Trsf()
            translation_vec = gp_Vec(dx * offset, dy * offset, dz * offset)
            trsf.SetTranslation(translation_vec)

            # Apply transformation to create copy
            transformer = BRepBuilderAPI_Transform(base_shape, trsf, True)  # True = copy
            transformer.Build()

            if not transformer.IsDone():
                raise OperationFailedError(f"Pattern copy {i+1} failed - IsDone() returned False")

            shape = transformer.Shape()

            # Wrap in GeometryShape
            geo_shape = GeometryShape.from_shape(shape, workspace_id, validate=True)

            # Compute properties
            entity_id = f"linear_pattern_{i}_{uuid.uuid4().hex[:8]}"
            props = SolidProperties.compute_from_shape(entity_id, shape)

            results.append((geo_shape, props))

        return results

    except (InvalidGeometryError, OperationFailedError):
        raise
    except Exception as e:
        raise OperationFailedError(f"Linear pattern failed: {e}")


def circular_pattern(
    base_shape: TopoDS_Shape,
    axis_point: Tuple[float, float, float],
    axis_direction: Tuple[float, float, float],
    count: int,
    angle: float,
    workspace_id: str
) -> List[Tuple[GeometryShape, SolidProperties]]:
    """Create a circular pattern of copies around an axis.

    Args:
        base_shape: Base shape to pattern
        axis_point: Point on rotation axis (px, py, pz)
        axis_direction: Axis direction vector (dx, dy, dz) - will be normalized
        count: Number of copies to create (including original)
        angle: Total angle to distribute copies over (degrees, 0-360)
        workspace_id: Workspace for this geometry

    Returns:
        List of (GeometryShape, SolidProperties) tuples for each copy

    Raises:
        InvalidGeometryError: If parameters are invalid
        OperationFailedError: If pattern operation fails
    """
    # Validate inputs
    if count <= 0:
        raise InvalidGeometryError(f"Pattern count must be positive (got {count})")

    if angle <= 0 or angle > 360:
        raise InvalidGeometryError(f"Pattern angle must be in range (0, 360] (got {angle})")

    # Normalize axis direction
    dx, dy, dz = axis_direction
    mag = math.sqrt(dx*dx + dy*dy + dz*dz)
    if mag < 1e-10:
        raise InvalidGeometryError("Axis direction vector cannot be zero")

    dx, dy, dz = dx/mag, dy/mag, dz/mag

    results = []

    try:
        # Calculate angular spacing between copies
        angular_spacing_deg = angle / max(count - 1, 1)  # Distribute over total angle

        # Create axis of rotation
        axis_pnt = gp_Pnt(axis_point[0], axis_point[1], axis_point[2])
        axis_dir = gp_Dir(dx, dy, dz)
        axis = gp_Ax1(axis_pnt, axis_dir)

        for i in range(count):
            # Calculate rotation angle for this copy
            rotation_angle_deg = angular_spacing_deg * i
            rotation_angle_rad = math.radians(rotation_angle_deg)

            # Create transformation (rotation)
            trsf = gp_Trsf()
            trsf.SetRotation(axis, rotation_angle_rad)

            # Apply transformation to create copy
            transformer = BRepBuilderAPI_Transform(base_shape, trsf, True)  # True = copy
            transformer.Build()

            if not transformer.IsDone():
                raise OperationFailedError(f"Pattern copy {i+1} failed - IsDone() returned False")

            shape = transformer.Shape()

            # Wrap in GeometryShape
            geo_shape = GeometryShape.from_shape(shape, workspace_id, validate=True)

            # Compute properties
            entity_id = f"circular_pattern_{i}_{uuid.uuid4().hex[:8]}"
            props = SolidProperties.compute_from_shape(entity_id, shape)

            results.append((geo_shape, props))

        return results

    except (InvalidGeometryError, OperationFailedError):
        raise
    except Exception as e:
        raise OperationFailedError(f"Circular pattern failed: {e}")


def mirror_shape(
    base_shape: TopoDS_Shape,
    mirror_plane_point: Tuple[float, float, float],
    mirror_plane_normal: Tuple[float, float, float],
    workspace_id: str
) -> Tuple[GeometryShape, SolidProperties]:
    """Create a mirrored copy of a shape across a plane.

    Args:
        base_shape: Base shape to mirror
        mirror_plane_point: Point on mirror plane (px, py, pz)
        mirror_plane_normal: Plane normal vector (nx, ny, nz) - will be normalized
        workspace_id: Workspace for this geometry

    Returns:
        Tuple of (GeometryShape, SolidProperties) for mirrored copy

    Raises:
        InvalidGeometryError: If parameters are invalid
        OperationFailedError: If mirror operation fails
    """
    # Normalize plane normal
    nx, ny, nz = mirror_plane_normal
    mag = math.sqrt(nx*nx + ny*ny + nz*nz)
    if mag < 1e-10:
        raise InvalidGeometryError("Mirror plane normal vector cannot be zero")

    nx, ny, nz = nx/mag, ny/mag, nz/mag

    try:
        # Create mirror plane
        plane_pnt = gp_Pnt(mirror_plane_point[0], mirror_plane_point[1], mirror_plane_point[2])
        plane_dir = gp_Dir(nx, ny, nz)
        mirror_plane = gp_Pln(plane_pnt, plane_dir)

        # Create transformation (mirror)
        trsf = gp_Trsf()
        trsf.SetMirror(mirror_plane.Axis())

        # Apply transformation to create mirrored copy
        transformer = BRepBuilderAPI_Transform(base_shape, trsf, True)  # True = copy
        transformer.Build()

        if not transformer.IsDone():
            raise OperationFailedError("Mirror operation failed - IsDone() returned False")

        shape = transformer.Shape()

        # Wrap in GeometryShape
        geo_shape = GeometryShape.from_shape(shape, workspace_id, validate=True)

        # Compute properties
        entity_id = f"mirror_{uuid.uuid4().hex[:8]}"
        props = SolidProperties.compute_from_shape(entity_id, shape)

        return geo_shape, props

    except (InvalidGeometryError, OperationFailedError):
        raise
    except Exception as e:
        raise OperationFailedError(f"Mirror operation failed: {e}")
