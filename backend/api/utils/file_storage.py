"""Save an uploaded STEP file to disk: checks it, hashes it, never loads it whole into memory."""

import asyncio
import hashlib
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from api.errors.quotes_errors import InvalidFile

ALLOWED_EXTENSIONS = (".step", ".stp")
# Every STEP file starts with this line. A cheap check that catches renamed non-STEP files; real
# corruption is still decided by the geometry engine.
STEP_SIGNATURE = b"ISO-10303-21"
_UTF8_BOM = b"\xef\xbb\xbf"
_CHUNK_BYTES = 1024 * 1024
_MAX_NAME_LENGTH = 200


class Upload(Protocol):
    """The part of FastAPI's UploadFile we use (a protocol so tests need no web layer)."""

    filename: str | None

    async def read(self, size: int = -1) -> bytes: ...


@dataclass(frozen=True)
class StoredFile:
    file_name: str  # sanitized original name, for display only
    file_path: str  # absolute path of the stored copy
    file_hash: str  # SHA-256 hex


def sanitize_file_name(name: str | None) -> str:
    """Keep only the last path part and drop control characters. The stored copy never uses
    this name (it is a random id), so this only protects what we show and log."""
    # Browsers send a bare name, but a client can send "..\\..\\evil.step". Split on both slashes.
    base = re.split(r"[\\/]", name or "")[-1]
    base = re.sub(r"[\x00-\x1f\x7f]", "", base).strip()
    return base[:_MAX_NAME_LENGTH]


def _check_extension(file_name: str) -> None:
    if not file_name.lower().endswith(ALLOWED_EXTENSIONS):
        raise InvalidFile("Only .step or .stp files are accepted.")


def _check_signature(first_bytes: bytes) -> None:
    head = first_bytes.removeprefix(_UTF8_BOM).lstrip()
    if not head.startswith(STEP_SIGNATURE):
        raise InvalidFile("The file does not look like a STEP file (missing ISO-10303-21 header).")


async def save_upload(upload: Upload, upload_dir: Path, max_bytes: int) -> StoredFile:
    """Check the name, stream the file to `upload_dir/<random id>.step` while hashing it, and
    refuse it if it is empty, too large or not STEP. Nothing is left on disk on failure."""
    file_name = sanitize_file_name(upload.filename)
    _check_extension(file_name)

    upload_dir.mkdir(parents=True, exist_ok=True)
    path = (upload_dir / f"{uuid.uuid4().hex}.step").resolve()
    digest = hashlib.sha256()
    size = 0
    try:
        with path.open("wb") as out:
            while chunk := await upload.read(_CHUNK_BYTES):
                if size == 0:
                    _check_signature(chunk)
                size += len(chunk)
                if size > max_bytes:
                    raise InvalidFile(f"The file is larger than {max_bytes // (1024 * 1024)} MB.")
                digest.update(chunk)
                await asyncio.to_thread(out.write, chunk)
        if size == 0:
            raise InvalidFile("The file is empty.")
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return StoredFile(file_name=file_name, file_path=str(path), file_hash=digest.hexdigest())


def delete_file(path: str | Path) -> None:
    """Remove a stored file, e.g. when the database insert that followed failed."""
    Path(path).unlink(missing_ok=True)
