"""Errors the geometry engine can raise (FR-G6).

Same JSON shape as the rest of the project: {"error": {"code", "message"}}.
"""

from enum import StrEnum


class GeometryErrorCode(StrEnum):
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    UNSUPPORTED_EXTENSION = "UNSUPPORTED_EXTENSION"
    UNREADABLE_STEP = "UNREADABLE_STEP"
    NO_SOLIDS = "NO_SOLIDS"
    INVALID_SOLID = "INVALID_SOLID"


class GeometryError(Exception):
    def __init__(self, code: GeometryErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message

    def to_dict(self) -> dict[str, dict[str, str]]:
        return {"error": {"code": self.code.value, "message": self.message}}
