"""Domain errors for quotes. Services raise these; routers map them to status codes."""

from http import HTTPStatus


class QuoteError(Exception):
    """Base class: a stable machine-readable code, a readable message, and an HTTP status."""

    code = "QUOTE_ERROR"
    http_status = HTTPStatus.BAD_REQUEST

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class QuoteNotFound(QuoteError):
    code = "QUOTE_NOT_FOUND"
    http_status = HTTPStatus.NOT_FOUND


class InvalidFile(QuoteError):
    """Wrong extension, empty file, or over the size limit."""

    code = "INVALID_FILE"
    http_status = HTTPStatus.UNPROCESSABLE_ENTITY


class InvalidQuantity(QuoteError):
    code = "INVALID_QUANTITY"
    http_status = HTTPStatus.UNPROCESSABLE_ENTITY


class InvalidStatusTransition(QuoteError):
    code = "INVALID_STATUS_TRANSITION"
    http_status = HTTPStatus.UNPROCESSABLE_ENTITY


class StatusConflict(QuoteError):
    """The quote's status changed between reading it and updating it (e.g. the worker finished)."""

    code = "STATUS_CONFLICT"
    http_status = HTTPStatus.CONFLICT


class JobError(Exception):
    """Base class for what can go wrong while a worker analyzes a file. Never sent over HTTP."""


class AnalysisFailed(JobError):
    """The geometry engine rejected the file (corrupt, no solids...). Retrying cannot help."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class AnalysisCrashed(JobError):
    """The analysis process died, timed out or printed nonsense. Possibly a one-off, so retried."""
