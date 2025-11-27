"""Creation operations for generating 3D solids from 2D profiles.

Implements extrude, revolve, loft, and sweep operations using Open CASCADE.
"""
import math
import uuid
from typing import Tuple, List, Optional

from OCC.Core.TopoDS import TopoDS_Shape, TopoDS_Wire, TopoDS_Face
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeRevol
from OCC.Core.BRepOffsetAPI import BRepOffsetAPI_ThruSections
from OCC.Core.BRepOffsetAPI import BRepOffsetAPI_MakePipe
from OCC.Core.gp import gp_Vec, gp_Ax1, gp_Pnt, gp_Dir
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeWire, BRepBuilderAPI_MakeFace

from .geometry_engine import GeometryShape
from .properties import SolidProperties
from .exceptions import InvalidGeometryError, OperationFailedError


def extrude_profile(
    profile_shape: TopoDS_Shape,
    direction: Tuple[float, float, float],
    distance: float,
    workspace_id: str
) -> Tuple[GeometryShape, SolidProperties]:
    """Extrude a 2D profile along a direction vector to create a 3D solid.

    Args:
        profile_shape: 2D profile to extrude (wire or face)
        direction: Direction vector (dx, dy, dz) - will be normalized
        distance: Extrusion distance in mm (must be positive)
        workspace_id: Workspace for this geometry

    Returns:
        Tuple of (GeometryShape, SolidProperties)

    Raises:
        InvalidGeometryError: If profile or parameters are invalid
        OperationFailedError: If extrusion fails
    """
    # Validate inputs
    if distance <= 0:
        raise InvalidGeometryError(f"Extrusion distance must be positive (got {distance})")

    # Normalize direction vector
    dx, dy, dz = direction
    mag = math.sqrt(dx*dx + dy*dy + dz*dz)
    if mag < 1e-10:
        raise InvalidGeometryError("Direction vector cannot be zero")

    dx, dy, dz = dx/mag, dy/mag, dz/mag

    try:
        # Create extrusion vector
        extrusion_vec = gp_Vec(dx * distance, dy * distance, dz * distance)

        # Create prism (extrusion)
        maker = BRepPrimAPI_MakePrism(profile_shape, extrusion_vec)
        maker.Build()

        if not maker.IsDone():
            raise OperationFailedError("Extrusion failed - IsDone() returned False")

        shape = maker.Shape()

        # Wrap in GeometryShape
        geo_shape = GeometryShape.from_shape(shape, workspace_id, validate=True)

        # Compute properties
        entity_id = f"extrude_{uuid.uuid4().hex[:8]}"
        props = SolidProperties.compute_from_shape(entity_id, shape)

        return geo_shape, props

    except (InvalidGeometryError, OperationFailedError):
        raise
    except Exception as e:
        raise OperationFailedError(f"Extrusion failed: {e}")


def revolve_profile(
    profile_shape: TopoDS_Shape,
    axis_point: Tuple[float, float, float],
    axis_direction: Tuple[float, float, float],
    angle: float,
    workspace_id: str
) -> Tuple[GeometryShape, SolidProperties]:
    """Revolve a 2D profile around an axis to create a 3D solid of revolution.

    Args:
        profile_shape: 2D profile to revolve (wire or face)
        axis_point: Point on rotation axis (px, py, pz)
        axis_direction: Axis direction vector (dx, dy, dz) - will be normalized
        angle: Rotation angle in degrees (0-360)
        workspace_id: Workspace for this geometry

    Returns:
        Tuple of (GeometryShape, SolidProperties)

    Raises:
        InvalidGeometryError: If profile or parameters are invalid
        OperationFailedError: If revolve operation fails
    """
    # Validate inputs
    if angle <= 0 or angle > 360:
        raise InvalidGeometryError(f"Revolve angle must be in range (0, 360] (got {angle})")

    # Normalize axis direction
    dx, dy, dz = axis_direction
    mag = math.sqrt(dx*dx + dy*dy + dz*dz)
    if mag < 1e-10:
        raise InvalidGeometryError("Axis direction vector cannot be zero")

    dx, dy, dz = dx/mag, dy/mag, dz/mag

    try:
        # Create axis of revolution
        axis_pnt = gp_Pnt(axis_point[0], axis_point[1], axis_point[2])
        axis_dir = gp_Dir(dx, dy, dz)
        axis = gp_Ax1(axis_pnt, axis_dir)

        # Convert angle to radians
        angle_rad = math.radians(angle)

        # Create revolution
        maker = BRepPrimAPI_MakeRevol(profile_shape, axis, angle_rad)
        maker.Build()

        if not maker.IsDone():
            raise OperationFailedError("Revolve operation failed - IsDone() returned False")

        shape = maker.Shape()

        # Wrap in GeometryShape
        geo_shape = GeometryShape.from_shape(shape, workspace_id, validate=True)

        # Compute properties
        entity_id = f"revolve_{uuid.uuid4().hex[:8]}"
        props = SolidProperties.compute_from_shape(entity_id, shape)

        return geo_shape, props

    except (InvalidGeometryError, OperationFailedError):
        raise
    except Exception as e:
        raise OperationFailedError(f"Revolve operation failed: {e}")


def loft_profiles(
    profile_shapes: List[TopoDS_Shape],
    is_solid: bool,
    is_ruled: bool,
    workspace_id: str
) -> Tuple[GeometryShape, SolidProperties]:
    """Loft between multiple 2D profiles to create a 3D solid.

    Args:
        profile_shapes: List of 2D profiles (wires or edges) to loft between
        is_solid: Create a solid (True) or surface shell (False)
        is_ruled: Use ruled surface (True) or smooth interpolation (False)
        workspace_id: Workspace for this geometry

    Returns:
        Tuple of (GeometryShape, SolidProperties)

    Raises:
        InvalidGeometryError: If profiles are invalid or incompatible
        OperationFailedError: If loft operation fails
    """
    # Validate inputs
    if len(profile_shapes) < 2:
        raise InvalidGeometryError(f"Loft requires at least 2 profiles (got {len(profile_shapes)})")

    try:
        # Create loft generator
        loft_maker = BRepOffsetAPI_ThruSections(is_solid, is_ruled)

        # Add each profile wire to the loft
        for profile_shape in profile_shapes:
            # OCCT requires wires for lofting
            # If we have an edge or other shape, try to convert to wire
            try:
                # Assume profile_shape is already a wire
                loft_maker.AddWire(profile_shape)
            except Exception:
                # If not a wire, try to create one
                # For now, just pass the shape directly
                # (May need more sophisticated wire extraction)
                loft_maker.AddWire(profile_shape)

        # Build the loft
        loft_maker.Build()

        if not loft_maker.IsDone():
            raise OperationFailedError("Loft operation failed - IsDone() returned False")

        shape = loft_maker.Shape()

        # Wrap in GeometryShape
        geo_shape = GeometryShape.from_shape(shape, workspace_id, validate=True)

        # Compute properties
        entity_id = f"loft_{uuid.uuid4().hex[:8]}"
        props = SolidProperties.compute_from_shape(entity_id, shape)

        return geo_shape, props

    except (InvalidGeometryError, OperationFailedError):
        raise
    except Exception as e:
        raise OperationFailedError(f"Loft operation failed: {e}")


def sweep_profile_along_path(
    profile_shape: TopoDS_Shape,
    path_shape: TopoDS_Shape,
    workspace_id: str
) -> Tuple[GeometryShape, SolidProperties]:
    """Sweep a 2D profile along a path curve to create a 3D solid.

    Args:
        profile_shape: 2D profile to sweep (wire or face)
        path_shape: Path curve to sweep along (wire or edge)
        workspace_id: Workspace for this geometry

    Returns:
        Tuple of (GeometryShape, SolidProperties)

    Raises:
        InvalidGeometryError: If profile or path are invalid
        OperationFailedError: If sweep operation fails
    """
    try:
        # Create pipe (sweep) operation
        maker = BRepOffsetAPI_MakePipe(path_shape, profile_shape)
        maker.Build()

        if not maker.IsDone():
            raise OperationFailedError("Sweep operation failed - IsDone() returned False")

        shape = maker.Shape()

        # Wrap in GeometryShape
        geo_shape = GeometryShape.from_shape(shape, workspace_id, validate=True)

        # Compute properties
        entity_id = f"sweep_{uuid.uuid4().hex[:8]}"
        props = SolidProperties.compute_from_shape(entity_id, shape)

        return geo_shape, props

    except (InvalidGeometryError, OperationFailedError):
        raise
    except Exception as e:
        raise OperationFailedError(f"Sweep operation failed: {e}")
