"""Mesh generation and tessellation for 3D shapes."""
from typing import Optional, List, Tuple
from dataclasses import dataclass

from OCC.Core.TopoDS import TopoDS_Shape
from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopAbs import TopAbs_FACE
from OCC.Core.BRep import BRep_Tool
from OCC.Core.TopLoc import TopLoc_Location
from OCC.Core.gp import gp_Pnt

from .exceptions import TessellationError


@dataclass
class TessellationConfig:
    """Configuration for mesh generation quality.

    Attributes:
        linear_deflection: Maximum distance between mesh and surface (mm)
        angular_deflection: Maximum angular deviation (radians)
        relative: Whether deflection is relative to shape size
        name: Config name (preview, standard, high_quality)
    """
    linear_deflection: float
    angular_deflection: float
    relative: bool = False
    name: str = "custom"

    @classmethod
    def preview(cls) -> "TessellationConfig":
        """Quick preview quality (fast, low detail)."""
        return cls(
            linear_deflection=1.0,
            angular_deflection=1.0,
            relative=False,
            name="preview"
        )

    @classmethod
    def standard(cls) -> "TessellationConfig":
        """Standard quality (balanced, default)."""
        return cls(
            linear_deflection=0.1,
            angular_deflection=0.5,
            relative=False,
            name="standard"
        )

    @classmethod
    def high_quality(cls) -> "TessellationConfig":
        """High quality (slow, detailed)."""
        return cls(
            linear_deflection=0.01,
            angular_deflection=0.1,
            relative=False,
            name="high_quality"
        )

    @classmethod
    def from_name(cls, name: str) -> "TessellationConfig":
        """Get config by preset name.

        Args:
            name: Preset name (preview, standard, high_quality)

        Returns:
            TessellationConfig instance

        Raises:
            ValueError: If name is not recognized
        """
        configs = {
            "preview": cls.preview,
            "standard": cls.standard,
            "high_quality": cls.high_quality
        }

        if name not in configs:
            raise ValueError(
                f"Unknown tessellation config: {name}. "
                f"Valid options: {', '.join(configs.keys())}"
            )

        return configs[name]()


@dataclass
class Triangle:
    """Single triangle in a mesh.

    Attributes:
        normal: Normal vector [x, y, z]
        vertices: Three vertices, each [x, y, z]
    """
    normal: Tuple[float, float, float]
    vertices: Tuple[
        Tuple[float, float, float],
        Tuple[float, float, float],
        Tuple[float, float, float]
    ]


class MeshGenerator:
    """Generate triangulated meshes from Open CASCADE shapes."""

    @staticmethod
    def tessellate_shape(
        shape: TopoDS_Shape,
        config: Optional[TessellationConfig] = None
    ) -> List[Triangle]:
        """Generate triangular mesh from shape.

        Args:
            shape: TopoDS_Shape to tessellate
            config: Tessellation quality config (default: standard)

        Returns:
            List of Triangle objects

        Raises:
            TessellationError: If mesh generation fails
        """
        if config is None:
            config = TessellationConfig.standard()

        try:
            # Generate mesh using BRepMesh_IncrementalMesh
            mesh = BRepMesh_IncrementalMesh(
                shape,
                config.linear_deflection,
                config.relative,
                config.angular_deflection
            )
            mesh.Perform()

            if not mesh.IsDone():
                raise TessellationError("Mesh generation failed - IsDone() returned False")

            # Extract triangles from all faces
            triangles = []
            face_explorer = TopExp_Explorer(shape, TopAbs_FACE)

            while face_explorer.More():
                face = face_explorer.Current()
                triangles.extend(MeshGenerator._extract_face_triangles(face))
                face_explorer.Next()

            if not triangles:
                raise TessellationError("No triangles generated - shape may be invalid")

            return triangles

        except TessellationError:
            raise
        except Exception as e:
            raise TessellationError(f"Tessellation failed: {e}")

    @staticmethod
    def _extract_face_triangles(face) -> List[Triangle]:
        """Extract triangles from a single face.

        Args:
            face: TopoDS_Shape representing a face

        Returns:
            List of Triangle objects for this face
        """
        triangles = []

        try:
            # Get location and triangulation directly from face
            # (TopExp_Explorer already returns shapes in the correct type)
            location = TopLoc_Location()
            triangulation = BRep_Tool.Triangulation(face, location)

            if triangulation is None:
                return []

            # Get transformation
            transform = location.Transformation()

            # Extract triangles
            num_triangles = triangulation.NbTriangles()

            for i in range(1, num_triangles + 1):
                triangle = triangulation.Triangle(i)

                # Get vertex indices (1-based in OCCT)
                n1, n2, n3 = triangle.Get()

                # Get vertex coordinates
                p1 = triangulation.Node(n1).Transformed(transform)
                p2 = triangulation.Node(n2).Transformed(transform)
                p3 = triangulation.Node(n3).Transformed(transform)

                # Calculate normal from vertices (cross product)
                normal = MeshGenerator._calculate_normal(p1, p2, p3)

                # Create triangle
                tri = Triangle(
                    normal=normal,
                    vertices=(
                        (p1.X(), p1.Y(), p1.Z()),
                        (p2.X(), p2.Y(), p2.Z()),
                        (p3.X(), p3.Y(), p3.Z())
                    )
                )
                triangles.append(tri)

        except Exception as e:
            # If face triangulation fails, continue with other faces
            pass

        return triangles

    @staticmethod
    def _calculate_normal(
        p1: gp_Pnt,
        p2: gp_Pnt,
        p3: gp_Pnt
    ) -> Tuple[float, float, float]:
        """Calculate triangle normal using cross product.

        Args:
            p1, p2, p3: Triangle vertices

        Returns:
            Normalized normal vector (x, y, z)
        """
        # Calculate edge vectors
        v1_x = p2.X() - p1.X()
        v1_y = p2.Y() - p1.Y()
        v1_z = p2.Z() - p1.Z()

        v2_x = p3.X() - p1.X()
        v2_y = p3.Y() - p1.Y()
        v2_z = p3.Z() - p1.Z()

        # Cross product
        normal_x = v1_y * v2_z - v1_z * v2_y
        normal_y = v1_z * v2_x - v1_x * v2_z
        normal_z = v1_x * v2_y - v1_y * v2_x

        # Normalize
        magnitude = (normal_x**2 + normal_y**2 + normal_z**2)**0.5

        if magnitude < 1e-10:
            # Degenerate triangle, return default normal
            return (0.0, 0.0, 1.0)

        return (
            normal_x / magnitude,
            normal_y / magnitude,
            normal_z / magnitude
        )
