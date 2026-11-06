from pathlib import Path

from geometry.analyzer import analyze_file
from geometry.walls import count_thin_walls, samples_per_axis
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.gp import gp_Pnt, gp_Trsf

SAMPLES = Path(__file__).resolve().parents[3] / "samples"


def _box(x, y, z):
    return BRepPrimAPI_MakeBox(x, y, z).Shape()


def test_thick_block_has_no_thin_walls():
    assert count_thin_walls(_box(30.0, 20.0, 10.0)) == 0


def test_thin_plate_is_one_thin_wall():
    # Top and bottom are 2 mm apart: one wall. The 20 and 30 mm sides are far apart.
    assert count_thin_walls(_box(30.0, 20.0, 2.0)) == 1


def test_threshold_is_a_parameter():
    assert count_thin_walls(_box(30.0, 20.0, 2.0), thin_mm=1.5) == 0


def test_hollow_box_has_six_thin_walls():
    inner = BRepPrimAPI_MakeBox(26.0, 26.0, 26.0).Shape()
    move = gp_Trsf()
    move.SetTranslation(gp_Pnt(0, 0, 0), gp_Pnt(2, 2, 2))
    shell = BRepAlgoAPI_Cut(_box(30.0, 30.0, 30.0), BRepBuilderAPI_Transform(inner, move).Shape())
    assert count_thin_walls(shell.Shape()) == 6  # 2 mm shell on each of 6 sides


def test_sample_parts():
    # Gear: one thin wall (2.7 mm). Wedge-shaped tooth tips are ignored.
    assert analyze_file(SAMPLES / "vendra-gear.STEP").features.thin_wall_count == 1
    assert analyze_file(SAMPLES / "vendra-bracket.STEP").features.thin_wall_count == 0


def test_samples_shrink_as_faces_grow():
    assert samples_per_axis(99) == 3  # the gear
    assert samples_per_axis(555) == 3
    assert samples_per_axis(556) == 2
    assert samples_per_axis(1251) == 1
    assert samples_per_axis(100_000) == 1
