"""Custom exceptions for geometry kernel operations."""


class GeometryKernelError(Exception):
    """Base exception for all geometry kernel errors."""
    pass


class InvalidGeometryError(GeometryKernelError):
    """Raised when geometry validation fails.

    Examples:
    - Invalid BRep data
    - Non-manifold geometry
    - Self-intersecting surfaces
    - Open solids when closed expected
    """
    pass


class OperationFailedError(GeometryKernelError):
    """Raised when a geometry operation fails to execute.

    Examples:
    - Boolean operation fails (e.g., non-overlapping solids)
    - Extrusion fails (e.g., invalid distance)
    - Tessellation fails (e.g., degenerate geometry)
    """
    pass


class TessellationError(GeometryKernelError):
    """Raised when mesh generation fails.

    Examples:
    - Invalid tessellation parameters
    - Mesh generation timeout
    - Memory allocation failure
    """
    pass


class ShapeSerializationError(GeometryKernelError):
    """Raised when BRep serialization/deserialization fails.

    Examples:
    - Corrupt BRep data
    - Incompatible OCCT version
    - Encoding/decoding errors
    """
    pass


class PropertyComputationError(GeometryKernelError):
    """Raised when geometric property computation fails.

    Examples:
    - Volume calculation fails
    - Center of mass undefined
    - Invalid solid for property computation
    """
    pass
