import hashlib
import io
from pathlib import Path

import pytest
from api.errors.quotes_errors import InvalidFile
from api.utils.file_storage import delete_file, sanitize_file_name, save_upload

STEP = b"ISO-10303-21;\nHEADER;\nENDSEC;\nEND-ISO-10303-21;\n"


class FakeUpload:
    def __init__(self, filename: str | None, content: bytes) -> None:
        self.filename = filename
        self._stream = io.BytesIO(content)

    async def read(self, size: int = -1) -> bytes:
        return self._stream.read(size)


async def test_saves_file_and_hash(tmp_path):
    stored = await save_upload(FakeUpload("part.STEP", STEP), tmp_path, max_bytes=1000)
    assert stored.file_name == "part.STEP"
    assert stored.file_hash == hashlib.sha256(STEP).hexdigest()
    saved = Path(stored.file_path)
    assert saved.read_bytes() == STEP
    assert saved.suffix == ".step"
    assert saved.parent == tmp_path.resolve()


async def test_accepts_stp_and_byte_order_mark(tmp_path):
    await save_upload(FakeUpload("part.stp", b"\xef\xbb\xbf  " + STEP), tmp_path, max_bytes=1000)


@pytest.mark.parametrize("name", ["part.txt", "part", "part.step.exe", "", None])
async def test_rejects_wrong_extension(tmp_path, name):
    with pytest.raises(InvalidFile):
        await save_upload(FakeUpload(name, STEP), tmp_path, max_bytes=1000)
    assert list(tmp_path.iterdir()) == []


async def test_rejects_empty_file(tmp_path):
    with pytest.raises(InvalidFile, match="empty"):
        await save_upload(FakeUpload("a.step", b""), tmp_path, max_bytes=1000)
    assert list(tmp_path.iterdir()) == []


async def test_rejects_non_step_content(tmp_path):
    with pytest.raises(InvalidFile, match="STEP"):
        await save_upload(FakeUpload("a.step", b"hello world"), tmp_path, max_bytes=1000)
    assert list(tmp_path.iterdir()) == []


async def test_rejects_oversize_and_leaves_nothing(tmp_path):
    with pytest.raises(InvalidFile, match="larger"):
        await save_upload(FakeUpload("a.step", STEP), tmp_path, max_bytes=10)
    assert list(tmp_path.iterdir()) == []


async def test_creates_missing_upload_folder(tmp_path):
    target = tmp_path / "nested" / "uploads"
    await save_upload(FakeUpload("a.step", STEP), target, max_bytes=1000)
    assert len(list(target.iterdir())) == 1


async def test_two_uploads_never_share_a_path(tmp_path):
    first = await save_upload(FakeUpload("a.step", STEP), tmp_path, max_bytes=1000)
    second = await save_upload(FakeUpload("a.step", STEP), tmp_path, max_bytes=1000)
    assert first.file_path != second.file_path


@pytest.mark.parametrize(
    ("raw", "clean"),
    [
        ("part.step", "part.step"),
        ("..\\..\\evil.step", "evil.step"),
        ("/etc/passwd.step", "passwd.step"),
        ("a\x00b\nc.step", "abc.step"),
        (None, ""),
    ],
)
def test_sanitize_file_name(raw, clean):
    assert sanitize_file_name(raw) == clean


def test_delete_file_ignores_missing(tmp_path):
    delete_file(tmp_path / "nope.step")
