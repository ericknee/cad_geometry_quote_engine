"""Estimate setups: how many times the part must be clamped on a 3-axis machine.

A 3-axis machine only reaches features facing its tool, so each side that needs work is a clamping.

Rule:
- Main axis = the part's thinnest direction. Its two sides (top, bottom) each count as a setup
  if they have a flat face pointing straight along that axis.
- Side walls are free: the tool cuts the outline during the top and bottom setups.
- Holes along either of the other two axes need their own setup, once per axis.
- Always at least 1.

Limits: ignores angled faces and angled holes; ties for thinnest pick the first axis.
"""

from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Plane
from OCP.TopAbs import TopAbs_FACE, TopAbs_REVERSED
from OCP.TopoDS import TopoDS, TopoDS_Shape

from geometry.measures import bounding_corners
from geometry.topology import unique_subshapes

Vec = tuple[float, float, float]

_ALIGNED = 0.999  # |cos| of the angle to an axis above which a direction counts as along it


def count_setups(solid: TopoDS_Shape, hole_axes: list[Vec]) -> int:
    low, high = bounding_corners(solid)
    sizes = [hi - lo for lo, hi in zip(low, high, strict=True)]
    main = sizes.index(min(sizes))

    sides = _flat_face_sides(solid, main)
    sideways = {
        axis
        for direction in hole_axes
        for axis in range(3)
        if axis != main and abs(direction[axis]) >= _ALIGNED
    }
    return max(1, len(sides) + len(sideways))


def _flat_face_sides(solid: TopoDS_Shape, axis: int) -> set[int]:
    """Which sides (+1 / -1) of `axis` have a flat face pointing straight out along it."""
    sides: set[int] = set()
    for shape in unique_subshapes(solid, TopAbs_FACE):
        face = TopoDS.Face(shape)
        surface = BRepAdaptor_Surface(face)
        if surface.GetType() != GeomAbs_Plane:
            continue
        direction = surface.Plane().Axis().Direction()
        component = (direction.X(), direction.Y(), direction.Z())[axis]
        # Face orientation says whether the plane's own direction points into or out of the solid.
        if face.Orientation() == TopAbs_REVERSED:
            component = -component
        if abs(component) >= _ALIGNED:
            sides.add(1 if component > 0 else -1)
    return sides
