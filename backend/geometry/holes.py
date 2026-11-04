"""Hole detection.

Rule: group cylinder faces that share an axis and radius, keep only hole walls, and call a group
a hole when its faces together cover at least HOLE_MIN_ARC_DEG of the circle.

- Counterbores: coaxial cylinders of different radius that touch end to end are one hole.
- Grouping: CAD often splits one hole into several faces (two 180° halves), so counting
  faces would double count.
- Hole wall vs outside surface: a convex hub or boss is also a full cylinder, so the arc alone
  is not enough. We test a point just outside the wall: material there means a hole wall.
- 270°: keeps holes partly cut away by another feature. Drops fillets, scallops and
  half-round slot ends (180°).
"""

import math
from dataclasses import dataclass

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
_TOUCH_MM = 1e-3  # coaxial cylinders whose axial spans are this close count as touching

Vec = tuple[float, float, float]
AxisKey = tuple[Vec, Vec]
GroupKey = tuple[Vec, Vec, float]


@dataclass
class _Group:
    arc_deg: float = 0.0
    lo: float = math.inf  # axial span along the normalized axis direction
    hi: float = -math.inf


def count_holes(
    solid: TopoDS_Shape, cylinders: list[tuple[TopoDS_Face, BRepAdaptor_Surface]]
) -> int:
    classifier = BRepClass3d_SolidClassifier(solid)
    # Future improvement: groups are keyed by axis line and radius only, so two same-size blind
    # holes drilled from opposite faces along one axis merge into one group (and one hole).
    # Splitting by axial span or face adjacency would fix that.
    groups: dict[GroupKey, _Group] = {}
    for face, surface in cylinders:
        u_min, u_max, v_min, v_max = BRepTools.UVBounds_s(face)
        if not _is_hole_wall(classifier, surface, (u_min + u_max) / 2, (v_min + v_max) / 2):
            continue
        group = groups.setdefault(_group_key(surface), _Group())
        group.arc_deg += math.degrees(u_max - u_min)
        lo, hi = _axial_span(surface, v_min, v_max)
        group.lo, group.hi = min(group.lo, lo), max(group.hi, hi)
    return _count_stacks(groups)


def _count_stacks(groups: dict[GroupKey, _Group]) -> int:
    """Count holes: a counterbore is several coaxial cylinders of different radius that touch
    end to end, so those stacks count once."""
    spans_by_axis: dict[AxisKey, list[tuple[float, float]]] = {}
    for (direction, foot, _radius), group in groups.items():
        if group.arc_deg >= HOLE_MIN_ARC_DEG:
            spans_by_axis.setdefault((direction, foot), []).append((group.lo, group.hi))
    holes = 0
    for spans in spans_by_axis.values():
        spans.sort()
        holes += 1
        reach = spans[0][1]
        for lo, hi in spans[1:]:
            if lo > reach + _TOUCH_MM:
                holes += 1
            reach = max(reach, hi)
    return holes


def _normalized_direction(direction: Vec) -> Vec:
    """Flip so the first non-zero component is positive: opposite directions are the same axis."""
    first = next((c for c in direction if abs(c) > 1e-9), 1.0)
    return (-direction[0], -direction[1], -direction[2]) if first < 0 else direction


def _axial_span(surface: BRepAdaptor_Surface, v_min: float, v_max: float) -> tuple[float, float]:
    """Where the face sits along the (normalized) axis, in mm. For a cylinder, v is the distance
    along its own axis from its origin."""
    origin, own = _axis(surface)
    normalized = _normalized_direction(own)
    sign = _dot(own, normalized)  # +1 or -1
    start = _dot(origin, normalized)
    a, b = start + sign * v_min, start + sign * v_max
    return min(a, b), max(a, b)


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
    direction = _normalized_direction(direction)
    # Closest point of the axis line to the world origin: the same for any point on that line.
    shift = _dot(origin, direction)
    foot = tuple(origin[i] - direction[i] * shift for i in range(3))
    # "+ 0.0" turns -0.0 into 0.0 so equal keys compare equal.
    return (
        tuple(round(c, _DECIMALS) + 0.0 for c in direction),
        tuple(round(c, _DECIMALS) + 0.0 for c in foot),
        round(surface.Cylinder().Radius(), _DECIMALS),
    )
