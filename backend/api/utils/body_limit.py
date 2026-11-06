"""Reject oversized request bodies from the Content-Length header, before reading any of them."""

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

# Room for the multipart framing and the form fields around the file itself.
OVERHEAD_BYTES = 64 * 1024


class BodyLimitMiddleware:
    """Answer 413 when the declared body size is over `max_bytes` (plus multipart overhead).

    This is a cheap, early guard, not complete protection:
    - A client can omit or falsify Content-Length, so `save_upload` still enforces the real
      size while writing the file.
    - Starlette buffers a multipart body before the route runs, so a client that lies about
      the length can still make the server accept the whole body first.
    Production hardening: put an nginx reverse proxy in front with `client_max_body_size`
    set to MAX_UPLOAD_MB (and do not publish the API port), so oversized bodies are cut off
    before they reach this app.
    """

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self._app = app
        self._limit = max_bytes + OVERHEAD_BYTES
        self._max_mb = max_bytes // (1024 * 1024)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and self._declared_length(scope) > self._limit:
            response = JSONResponse(
                status_code=413,
                content={
                    "error": {
                        "code": "FILE_TOO_LARGE",
                        "message": f"The request is larger than the {self._max_mb} MB limit.",
                    }
                },
            )
            await response(scope, receive, send)
            return
        await self._app(scope, receive, send)

    @staticmethod
    def _declared_length(scope: Scope) -> int:
        for name, value in scope["headers"]:
            if name == b"content-length":
                try:
                    return int(value)
                except ValueError:
                    return 0  # malformed: let the server and the route deal with it
        return 0
