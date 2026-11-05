"""Complexity-related counts and ratios."""

from dataclasses import dataclass

from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cylinder
from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE
from OCP.TopoDS import TopoDS, TopoDS_Shape

from geometry.holes import find_hole_axes
from geometry.setups import count_setups
from geometry.topology import unique_subshapes


@dataclass(frozen=True)
class SolidFeatures:
    face_count: int
    edge_count: int
    cylindrical_faces: int
    holes_detected: int
    setups: int


def extract_features(solid: TopoDS_Shape) -> SolidFeatures:
    faces = [TopoDS.Face(f) for f in unique_subshapes(solid, TopAbs_FACE)]
    adaptors = [(f, BRepAdaptor_Surface(f)) for f in faces]
    cylinders = [(f, a) for f, a in adaptors if a.GetType() == GeomAbs_Cylinder]
    hole_axes = find_hole_axes(solid, cylinders)
    return SolidFeatures(
        face_count=len(faces),
        edge_count=len(unique_subshapes(solid, TopAbs_EDGE)),
        cylindrical_faces=len(cylinders),
        holes_detected=len(hole_axes),
        setups=count_setups(solid, hole_axes),
    )


def merge_features(parts: list[SolidFeatures]) -> SolidFeatures:
    """Counts add up across solids."""
    return SolidFeatures(
        face_count=sum(p.face_count for p in parts),
        edge_count=sum(p.edge_count for p in parts),
        cylindrical_faces=sum(p.cylindrical_faces for p in parts),
        holes_detected=sum(p.holes_detected for p in parts),
        setups=sum(p.setups for p in parts),
    )


def sa_to_volume_ratio(surface_area_cm2: float, volume_cm3: float) -> float:
    return surface_area_cm2 / volume_cm3


def material_removal_ratio(volume_cm3: float, stock_volume_cm3: float) -> float:
    """Share of the raw block that gets cut away: 0 = nothing, 1 = everything."""
    return min(1.0, max(0.0, 1 - volume_cm3 / stock_volume_cm3))
