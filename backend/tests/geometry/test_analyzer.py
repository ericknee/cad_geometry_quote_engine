import json
from pathlib import Path

import pytest
from geometry.analyzer import analyze_file
from geometry.cli import main
from geometry.errors import GeometryError, GeometryErrorCode

SAMPLES = Path(__file__).resolve().parents[3] / "samples"
BRACKET = SAMPLES / "vendra-bracket.STEP"
GEAR = SAMPLES / "vendra-gear.STEP"


def test_bracket_measurements():
    result = analyze_file(BRACKET)
    box = result.bounding_box_mm
    assert (box.length, box.width, box.height) == (90.0, 90.0, 41.0)
    assert result.volume_cm3 == pytest.approx(40.9604, abs=1e-3)
    assert result.features.holes_detected == 4
    assert result.source_units == "mm"


def test_gear_converts_inches_to_mm():
    result = analyze_file(GEAR)
    assert result.source_units == "inch"
    assert result.bounding_box_mm.length == pytest.approx(23.368, abs=1e-3)
    assert result.features.holes_detected == 1


def test_missing_file():
    with pytest.raises(GeometryError) as error:
        analyze_file(SAMPLES / "nope.step")
    assert error.value.code == GeometryErrorCode.FILE_NOT_FOUND


def test_unsupported_extension(tmp_path):
    path = tmp_path / "part.txt"
    path.write_text("x")
    with pytest.raises(GeometryError) as error:
        analyze_file(path)
    assert error.value.code == GeometryErrorCode.UNSUPPORTED_EXTENSION


def test_unreadable_step(tmp_path):
    path = tmp_path / "bad.step"
    path.write_text("this is not a STEP file")
    with pytest.raises(GeometryError) as error:
        analyze_file(path)
    assert error.value.code == GeometryErrorCode.UNREADABLE_STEP


def test_cli_prints_json(capsys):
    assert main([str(BRACKET)]) == 0
    assert json.loads(capsys.readouterr().out)["features"]["holes_detected"] == 4


@pytest.mark.parametrize("value", ["nan", "inf", "-1", "abc"])
def test_cli_rejects_bad_stock_allowance(value):
    with pytest.raises(SystemExit) as exit_info:
        main([str(BRACKET), "--stock-allowance", value])
    assert exit_info.value.code == 2


def test_cli_output_error_only_for_write(tmp_path, capsys):
    out = tmp_path / "missing-dir" / "out.json"
    assert main([str(BRACKET), "--out", str(out)]) == 1
    assert json.loads(capsys.readouterr().out)["error"]["code"] == "OUTPUT_ERROR"


def _block_with_cuts(*cuts: tuple[float, float, float, float]):
    """40x40x20 block; each cut is (x, y, radius, depth) drilled down from the top face."""
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder
    from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt

    shape = BRepPrimAPI_MakeBox(40, 40, 20).Shape()
    for x, y, radius, depth in cuts:
        axis = gp_Ax2(gp_Pnt(x, y, 20 - depth), gp_Dir(0, 0, 1))
        shape = BRepAlgoAPI_Cut(
            shape, BRepPrimAPI_MakeCylinder(axis, radius, depth).Shape()
        ).Shape()
    return shape


def test_counterbore_counts_as_one_hole():
    from geometry.features import extract_features

    plain = _block_with_cuts((20, 20, 3, 20))
    counterbored = _block_with_cuts((20, 20, 3, 20), (20, 20, 6, 5))
    assert extract_features(plain).holes_detected == 1
    assert extract_features(counterbored).holes_detected == 1


def test_separate_holes_still_count_separately():
    from geometry.features import extract_features

    two = _block_with_cuts((10, 20, 3, 20), (30, 20, 3, 20))
    assert extract_features(two).holes_detected == 2
