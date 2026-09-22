"""Small request-boundary helpers shared by public API routers."""

import re
from uuid import uuid4


_REQUEST_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")


def set_request_id(request, response) -> str:
    """Echo a safe caller ID or create one, and always attach it to the response."""
    supplied = request.headers.get("X-Request-ID", "")
    existing = response.headers.get("X-Request-ID", "")
    request_id = (
        existing
        if _REQUEST_ID.fullmatch(existing)
        else supplied
        if _REQUEST_ID.fullmatch(supplied)
        else str(uuid4())
    )
    response.headers["X-Request-ID"] = request_id
    return request_id
