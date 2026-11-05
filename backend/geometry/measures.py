"""Size measurements: bounding box, volume, surface area, stock volume."""

from dataclasses import dataclass

from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.TopoDS import TopoDS_Shape

# Extra material added on each side of the part to get the raw stock block (PRD FR-P1).
DEFAULT_STOCK_ALLOWANCE_MM = 3.0

Point = tuple[float, float, float]


@dataclass(frozen=True)
class SolidMeasures:
    """Raw measurements of one solid. Corners are kept (not just sizes) so solids can be merged."""

    min_corner_mm: Point
    max_corner_mm: Point
    volume_cm3: float
    surface_area_cm2: float


def bounding_corners(solid: TopoDS_Shape) -> tuple[Point, Point]:
    """Opposite corners of the tight axis-aligned box around the solid."""
    # AddOptimal gives the tight box. The default adds padding and would overstate the size.
    box = Bnd_Box()
    BRepBndLib.AddOptimal_s(solid, box, False, False)
    low, high = box.CornerMin(), box.CornerMax()
    return (low.X(), low.Y(), low.Z()), (high.X(), high.Y(), high.Z())


def measure_solid(solid: TopoDS_Shape) -> SolidMeasures:
    low, high = bounding_corners(solid)

    volume = GProp_GProps()
    BRepGProp.VolumeProperties_s(solid, volume)
    area = GProp_GProps()
    BRepGProp.SurfaceProperties_s(solid, area)

    return SolidMeasures(
        min_corner_mm=low,
        max_corner_mm=high,
        # abs(): a solid with reversed orientation reports negative volume.
        volume_cm3=abs(volume.Mass()) / 1000,  # mm³ -> cm³
        surface_area_cm2=area.Mass() / 100,  # mm² -> cm²
    )


def merge_measures(parts: list[SolidMeasures]) -> SolidMeasures:
    """Combine solids: one box around all of them, volumes and areas added."""
    return SolidMeasures(
        min_corner_mm=tuple(min(p.min_corner_mm[i] for p in parts) for i in range(3)),
        max_corner_mm=tuple(max(p.max_corner_mm[i] for p in parts) for i in range(3)),
        volume_cm3=sum(p.volume_cm3 for p in parts),
        surface_area_cm2=sum(p.surface_area_cm2 for p in parts),
    )


def box_dimensions(measures: SolidMeasures) -> tuple[float, float, float]:
    """Box sides sorted longest to shortest: (length, width, height)."""
    corners = zip(measures.min_corner_mm, measures.max_corner_mm, strict=True)
    sides = (high - low for low, high in corners)
    length, width, height = sorted(sides, reverse=True)
    return length, width, height


def stock_volume_cm3(
    dimensions_mm: tuple[float, float, float], allowance_mm: float = DEFAULT_STOCK_ALLOWANCE_MM
) -> float:
    """Volume of the raw block: the box grown by `allowance_mm` on every side."""
    length, width, height = (side + 2 * allowance_mm for side in dimensions_mm)
    return length * width * height / 1000
