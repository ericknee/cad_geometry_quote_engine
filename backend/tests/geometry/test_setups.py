from pathlib import Path

from geometry.analyzer import analyze_file
from geometry.features import extract_features
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder
from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt

SAMPLES = Path(__file__).resolve().parents[3] / "samples"


def _plate(*drills: tuple[tuple[float, float, float], tuple[float, float, float]]):
    """40x40x10 plate (thinnest axis = Z). Each drill is (start point, direction), r=2, through."""
    shape = BRepPrimAPI_MakeBox(40, 40, 10).Shape()
    for start, direction in drills:
        axis = gp_Ax2(gp_Pnt(*start), gp_Dir(*direction))
        shape = BRepAlgoAPI_Cut(shape, BRepPrimAPI_MakeCylinder(axis, 2, 40).Shape()).Shape()
    return shape


def test_plain_plate_needs_top_and_bottom():
    assert extract_features(_plate()).setups == 2


def test_hole_along_main_axis_adds_no_setup():
    plate = _plate(((20, 20, -5), (0, 0, 1)))
    assert extract_features(plate).setups == 2


def test_sideways_holes_add_one_setup_per_axis():
    one_axis = _plate(((-5, 10, 5), (1, 0, 0)), ((-5, 30, 5), (1, 0, 0)))
    two_axes = _plate(((-5, 10, 5), (1, 0, 0)), ((10, -5, 5), (0, 1, 0)))
    assert extract_features(one_axis).setups == 3
    assert extract_features(two_axes).setups == 4


def test_samples():
    assert analyze_file(SAMPLES / "vendra-gear.STEP").features.setups == 2
    assert analyze_file(SAMPLES / "vendra-bracket.STEP").features.setups == 4
