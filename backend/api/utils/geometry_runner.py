"""Run the geometry engine in a child process, so a hard kernel crash cannot take down the worker.

It runs the same CLI a developer would (`python -m geometry <file>`): exit code 0 means a JSON
result, exit code 1 means a JSON error. Anything else counts as a crash.
"""

import asyncio
import contextlib
import json
import sys
from pathlib import Path

from geometry.models import GeometryResult
from pydantic import ValidationError

from api.errors.quotes_errors import AnalysisCrashed, AnalysisFailed

DEFAULT_COMMAND = (sys.executable, "-m", "geometry")


async def analyze_in_subprocess(
    path: str | Path, timeout_seconds: float, command: tuple[str, ...] = DEFAULT_COMMAND
) -> GeometryResult:
    """Return the geometry result, or raise AnalysisFailed (bad file) / AnalysisCrashed."""
    process = await asyncio.create_subprocess_exec(
        *command,
        str(path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout_seconds)
    except TimeoutError:
        with contextlib.suppress(ProcessLookupError):
            process.kill()
        await process.wait()
        raise AnalysisCrashed(f"Analysis timed out after {timeout_seconds:g} s.") from None

    if process.returncode == 0:
        try:
            return GeometryResult.model_validate_json(stdout)
        except ValidationError:
            raise AnalysisCrashed("Analysis printed an unreadable result.") from None
    if process.returncode == 1:
        error = _parse_error(stdout)
        if error is not None:
            raise AnalysisFailed(*error)
    detail = stderr.decode(errors="replace").strip()[-200:]
    raise AnalysisCrashed(
        f"Analysis process exited with code {process.returncode}. {detail}".strip()
    )


def _parse_error(stdout: bytes) -> tuple[str, str] | None:
    try:
        error = json.loads(stdout)["error"]
        return str(error["code"]), str(error["message"])
    except (ValueError, KeyError, TypeError):
        return None
