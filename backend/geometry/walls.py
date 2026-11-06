"""Thin wall count.

A wall is two roughly parallel faces facing away from each other with material between them. It is
"thin" when that material is less than THIN_WALL_MM thick.

How: from sample points on every face, a short ray goes into the material along the inward normal.
If it meets a roughly parallel opposite face within THIN_WALL_MM, those two faces form a thin pair.
Pairs that share a face are one wall, so the count is the number of connected groups of thin pairs
(CAD often splits one surface into several faces, and a wall made of those would otherwise be
counted several times).

- Wedges (gear tooth tips, chamfers) are skipped: their thickness shrinks to 0 at the tip, so they
  would count as thin wherever we sampled.
- Speed: a ray is only tested against faces whose bounding box touches its short segment, and
  cones (the slowest surface to intersect) are skipped unless the segment can reach them. The gear
  takes about 0.1 s.
- Samples per face start at 3x3 and shrink as the face count grows (3x3 up to 555 faces, then 2x2,
  then 1x1 above 1,250), to keep the total number of rays near RAY_BUDGET.

Limits: samples can miss a very small thin feature, and fewer samples on large parts make that
more likely. On the gear, 2x2 samples miss its thin wall (count 0); 3x3 and above find it, except
that 4x4 finds 2 (a group's links can depend on where the samples fall). The per-ray face check is
a plain loop over all faces, so time still grows with faces squared, just with a small constant;
parts above MAX_FACES_FOR_THIN_WALLS faces skip the check and report 0 thin walls.
"""

import math

from OCP.Bnd import Bnd_Box
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepClass import BRepClass_FaceClassifier
from OCP.BRepGProp import BRepGProp_Face
from OCP.BRepTools import BRepTools
from OCP.GeomAbs import GeomAbs_Cone
from OCP.gp import gp_Dir, gp_Lin, gp_Pnt, gp_Pnt2d, gp_Vec
from OCP.IntCurvesFace import IntCurvesFace_Intersector
from OCP.TopAbs import TopAbs_FACE, TopAbs_IN
from OCP.TopoDS import TopoDS, TopoDS_Face, TopoDS_Shape

from geometry.topology import unique_subshapes

# A wall thinner than this counts as thin (assumption; stated in the README and REPORT).
THIN_WALL_MM = 3.0

START_SAMPLES_PER_AXIS = 3  # per face, for small parts
RAY_BUDGET = 5000  # total rays; more faces means fewer samples per face (never below 1x1)
# Above this many faces the check is skipped (count 0): every ray scans all face boxes, so time
# grows with faces squared and a very detailed part could exceed the analysis timeout.
MAX_FACES_FOR_THIN_WALLS = 3000

_PARALLEL_COS = 0.94  # hit face must point back within ~20 degrees to count as the other side
_RAY_START_MM = 1e-4  # skip the face the ray starts on
_BOX_MARGIN_MM = 1e-3
_TOLERANCE = 1e-6

Box = tuple[float, float, float, float, float, float]
# Cone as (apex-side origin, axis, base radius, sin, cos of the half angle): see _cone_distance.
ConeShape = tuple[tuple[float, float, float], tuple[float, float, float], float, float, float]


def samples_per_axis(face_count: int) -> int:
    """Samples along each side of a face: 3 for small parts, down to 1 for very detailed ones."""
    affordable = int(math.sqrt(RAY_BUDGET / max(face_count, 1)))
    return max(1, min(START_SAMPLES_PER_AXIS, affordable))


def count_thin_walls(solid: TopoDS_Shape, thin_mm: float = THIN_WALL_MM) -> int:
    faces = [TopoDS.Face(shape) for shape in unique_subshapes(solid, TopAbs_FACE)]
    if len(faces) > MAX_FACES_FOR_THIN_WALLS:
        return 0
    boxes = [_box(face) for face in faces]
    cones = {i: shape for i, face in enumerate(faces) if (shape := _cone_shape(face))}
    intersectors: dict[int, IntCurvesFace_Intersector] = {}
    samples = samples_per_axis(len(faces))

    # Union-find over faces: thin pairs join their two faces into one wall.
    parent = list(range(len(faces)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    in_thin_pair: set[int] = set()
    for index, face in enumerate(faces):
        for other in _thin_partners(face, faces, boxes, cones, intersectors, samples, thin_mm):
            in_thin_pair.update((index, other))
            parent[find(index)] = find(other)

    return len({find(i) for i in in_thin_pair})


def _box(face: TopoDS_Face) -> Box:
    box = Bnd_Box()
    BRepBndLib.Add_s(face, box)
    return (
        box.GetXMin(),
        box.GetYMin(),
        box.GetZMin(),
        box.GetXMax(),
        box.GetYMax(),
        box.GetZMax(),
    )


def _thin_partners(face, faces, boxes, cones, intersectors, samples: int, thin_mm: float):
    """Indexes of faces met by a sample ray from `face` through less than `thin_mm` of material."""
    u_min, u_max, v_min, v_max = BRepTools.UVBounds_s(face)
    properties = BRepGProp_Face(face)
    for i in range(samples):
        for j in range(samples):
            u = u_min + (u_max - u_min) * (i + 0.5) / samples
            v = v_min + (v_max - v_min) * (j + 0.5) / samples
            partner = _partner_at(
                face, properties, faces, boxes, cones, intersectors, u, v, thin_mm
            )
            if partner is not None:
                yield partner


def _partner_at(
    face, properties, faces, boxes, cones, intersectors, u: float, v: float, thin_mm: float
):
    # Trimmed faces: the UV box can include points outside the face.
    if BRepClass_FaceClassifier(face, gp_Pnt2d(u, v), _TOLERANCE).State() != TopAbs_IN:
        return None
    point, normal = gp_Pnt(), gp_Vec()
    properties.Normal(u, v, point, normal)  # points out of the material
    if normal.Magnitude() < 1e-12:
        return None
    inward = gp_Dir(-normal.X(), -normal.Y(), -normal.Z())

    hit = _nearest_hit(point, inward, faces, boxes, cones, intersectors, thin_mm)
    if hit is None:
        return None
    far_index, far_u, far_v = hit
    far_point, far_normal = gp_Pnt(), gp_Vec()
    BRepGProp_Face(faces[far_index]).Normal(far_u, far_v, far_point, far_normal)
    if far_normal.Magnitude() < 1e-12:
        return None
    cosine = normal.Dot(far_normal) / (normal.Magnitude() * far_normal.Magnitude())
    return far_index if cosine <= -_PARALLEL_COS else None


def _nearest_hit(point, direction, faces, boxes, cones, intersectors, thin_mm: float):
    """(face index, u, v) of the first face the ray meets within `thin_mm`, or None."""
    start = (point.X(), point.Y(), point.Z())
    end = (
        start[0] + direction.X() * thin_mm,
        start[1] + direction.Y() * thin_mm,
        start[2] + direction.Z() * thin_mm,
    )
    low = tuple(min(a, b) - _BOX_MARGIN_MM for a, b in zip(start, end, strict=True))
    high = tuple(max(a, b) + _BOX_MARGIN_MM for a, b in zip(start, end, strict=True))
    line = gp_Lin(point, direction)

    best = None  # (distance, face index, u, v)
    for index, (x0, y0, z0, x1, y1, z1) in enumerate(boxes):
        # Skip faces whose bounding box does not touch the ray's short segment.
        if x1 < low[0] or x0 > high[0] or y1 < low[1] or y0 > high[1]:
            continue
        if z1 < low[2] or z0 > high[2]:
            continue
        # Exact intersection with a cone is slow (about 1000x a plane), so first check cheaply
        # whether the segment can reach the cone at all.
        if index in cones and not _cone_may_be_hit(start, direction, cones[index], thin_mm):
            continue
        intersector = intersectors.get(index)
        if intersector is None:
            intersector = intersectors[index] = IntCurvesFace_Intersector(faces[index], _TOLERANCE)
        intersector.Perform(line, _RAY_START_MM, thin_mm)
        if not intersector.IsDone():
            continue
        for k in range(1, intersector.NbPnt() + 1):
            distance = intersector.WParameter(k)
            if best is None or distance < best[0]:
                best = (distance, index, intersector.UParameter(k), intersector.VParameter(k))
    return None if best is None else best[1:]


def _cone_shape(face: TopoDS_Face) -> ConeShape | None:
    surface = BRepAdaptor_Surface(face)
    if surface.GetType() != GeomAbs_Cone:
        return None
    cone = surface.Cone()
    origin, axis = cone.Location(), cone.Axis().Direction()
    angle = cone.SemiAngle()
    return (
        (origin.X(), origin.Y(), origin.Z()),
        (axis.X(), axis.Y(), axis.Z()),
        cone.RefRadius(),
        math.sin(angle),
        math.cos(angle),
    )


def _cone_may_be_hit(start, direction, cone: ConeShape, max_mm: float) -> bool:
    """False if the ray segment cannot cross the cone's infinite surface (so not the face either).

    Along the cone axis (z) and out from it (r), the surface is r cos(a) = R cos(a) + z sin(a)
    (R = base radius, a = half angle). Putting the ray point start + t x direction into that
    equation, squared, gives a quadratic in t; we only need to know if it has a root in the
    segment. Squaring also admits the mirror cone, which only makes the test more cautious.
    """
    origin, axis, base_radius, sin, cos = cone
    offset = tuple(p - o for p, o in zip(start, origin, strict=True))
    d = (direction.X(), direction.Y(), direction.Z())
    z0 = sum(a * b for a, b in zip(offset, axis, strict=True))
    dz = sum(a * b for a, b in zip(d, axis, strict=True))
    along = sum(a * b for a, b in zip(offset, d, strict=True))
    radial_sq = sum(c * c for c in offset) - z0 * z0  # r squared at t = 0

    k = base_radius * cos + z0 * sin
    m = sin * dz
    a2 = cos * cos * (1.0 - dz * dz) - m * m
    b1 = cos * cos * 2.0 * (along - z0 * dz) - 2.0 * k * m
    c0 = cos * cos * radial_sq - k * k

    low, high = _RAY_START_MM - _BOX_MARGIN_MM, max_mm + _BOX_MARGIN_MM

    def f(t: float) -> float:
        return (a2 * t + b1) * t + c0

    if f(low) * f(high) <= 0:
        return True
    if abs(a2) < 1e-12:
        return False  # linear and no sign change inside the segment
    vertex = -b1 / (2.0 * a2)
    return low <= vertex <= high and f(vertex) * a2 <= 0 and b1 * b1 - 4.0 * a2 * c0 >= 0
