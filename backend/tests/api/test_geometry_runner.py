import sys
from pathlib import Path

import pytest
from api.errors.quotes_errors import AnalysisCrashed, AnalysisFailed
from api.utils.geometry_runner import analyze_in_subprocess

GEAR = Path(__file__).resolve().parents[3] / "samples" / "vendra-gear.STEP"


def _python(code: str) -> tuple[str, ...]:
    """A stand-in for the geometry CLI that runs `code` instead."""
    return (sys.executable, "-c", code)


async def test_real_file_is_analyzed_in_a_child_process():
    result = await analyze_in_subprocess(GEAR, timeout_seconds=60)
    assert result.file == "vendra-gear.STEP"
    assert result.features.setups == 2


async def test_bad_file_raises_analysis_failed_with_the_engine_error(tmp_path):
    junk = tmp_path / "junk.step"
    junk.write_text("not a step file")
    with pytest.raises(AnalysisFailed) as caught:
        await analyze_in_subprocess(junk, timeout_seconds=60)
    assert caught.value.code == "UNREADABLE_STEP"


async def test_hard_crash_is_reported_as_crashed():
    with pytest.raises(AnalysisCrashed, match="code 139"):
        await analyze_in_subprocess(GEAR, 30, command=_python("import os; os._exit(139)"))


async def test_timeout_kills_the_process_and_is_reported_as_crashed():
    with pytest.raises(AnalysisCrashed, match="timed out"):
        await analyze_in_subprocess(GEAR, 0.5, command=_python("import time; time.sleep(30)"))


async def test_success_exit_with_garbage_output_is_a_crash():
    with pytest.raises(AnalysisCrashed, match="unreadable"):
        await analyze_in_subprocess(GEAR, 30, command=_python("print('hello')"))


async def test_error_exit_without_json_is_a_crash_not_a_bad_file():
    code = "import sys; print('oops'); sys.exit(1)"
    with pytest.raises(AnalysisCrashed):
        await analyze_in_subprocess(GEAR, 30, command=_python(code))
