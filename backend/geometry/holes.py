"""Hole detection.

Rule: group cylinder faces that share an axis and radius, keep only hole walls, and call a group
a hole when its faces together cover at least HOLE_MIN_ARC_DEG of the circle.

- Grouping: CAD often splits one hole into several faces (two 180° halves), so counting
  faces would double count.
- Hole wall vs outside surface: a convex hub or boss is also a full cylinder, so the arc alone
  is not enough. We test a point just outside the wall: material there means a hole wall.
- 270°: keeps holes partly cut away by another feature. Drops fillets, scallops and
  half-round slot ends (180°).
"""

import math

from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.BRepTools import BRepTools
from OCP.gp import gp_Pnt
from OCP.TopAbs import TopAbs_IN
from OCP.TopoDS import TopoDS_Face, TopoDS_Shape

HOLE_MIN_ARC_DEG = 270.0
_PROBE_OFFSET_MM = 0.01
_TOLERANCE_MM = 1e-6
_DECIMALS = 3  # rounding used to match axes and radii that differ only by float noise

Vec = tuple[float, float, float]
GroupKey = tuple[Vec, Vec, float]


def count_holes(solid: TopoDS_Shape, cylinder_faces: list[TopoDS_Face]) -> int:
    classifier = BRepClass3d_SolidClassifier(solid)
    arc_by_group: dict[GroupKey, float] = {}
    for face in cylinder_faces:
        surface = BRepAdaptor_Surface(face)
        u_min, u_max, v_min, v_max = BRepTools.UVBounds_s(face)
        if not _is_hole_wall(classifier, surface, (u_min + u_max) / 2, (v_min + v_max) / 2):
            continue
        key = _group_key(surface)
        arc_by_group[key] = arc_by_group.get(key, 0.0) + math.degrees(u_max - u_min)
    return sum(1 for arc in arc_by_group.values() if arc >= HOLE_MIN_ARC_DEG)


def _axis(surface: BRepAdaptor_Surface) -> tuple[Vec, Vec]:
    axis = surface.Cylinder().Axis()
    origin, direction = axis.Location(), axis.Direction()
    return (origin.X(), origin.Y(), origin.Z()), (direction.X(), direction.Y(), direction.Z())


def _dot(a: Vec, b: Vec) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


def _is_hole_wall(
    classifier: BRepClass3d_SolidClassifier, surface: BRepAdaptor_Surface, u: float, v: float
) -> bool:
    """True if there is material just outside the cylinder wall, i.e. the wall faces a void."""
    origin, direction = _axis(surface)
    point = surface.Value(u, v)
    p = (point.X(), point.Y(), point.Z())
    along = _dot(tuple(p[i] - origin[i] for i in range(3)), direction)
    radial = tuple(p[i] - origin[i] - direction[i] * along for i in range(3))
    length = math.sqrt(_dot(radial, radial))
    probe = tuple(p[i] + radial[i] / length * _PROBE_OFFSET_MM for i in range(3))
    classifier.Perform(gp_Pnt(*probe), _TOLERANCE_MM)
    return classifier.State() == TopAbs_IN


def _group_key(surface: BRepAdaptor_Surface) -> GroupKey:
    """Identify a cylinder by axis line and radius, ignoring axis direction sign."""
    origin, direction = _axis(surface)
    # Flip so the first non-zero component is positive: opposite directions are the same axis.
    first = next((c for c in direction if abs(c) > 1e-9), 1.0)
    if first < 0:
        direction = (-direction[0], -direction[1], -direction[2])
    # Closest point of the axis line to the world origin: the same for any point on that line.
    shift = _dot(origin, direction)
    foot = tuple(origin[i] - direction[i] * shift for i in range(3))
    # "+ 0.0" turns -0.0 into 0.0 so equal keys compare equal.
    return (
        tuple(round(c, _DECIMALS) + 0.0 for c in direction),
        tuple(round(c, _DECIMALS) + 0.0 for c in foot),
        round(surface.Cylinder().Radius(), _DECIMALS),
    )
