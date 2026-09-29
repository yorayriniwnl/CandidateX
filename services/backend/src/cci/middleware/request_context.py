import time
import uuid
import contextvars
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

request_id_context_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")

class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        req_id = str(uuid.uuid4())
        token = request_id_context_var.set(req_id)
        
        start_time = time.perf_counter()
        
        try:
            response = await call_next(request)
        finally:
            request_id_context_var.reset(token)
            
        process_time = time.perf_counter() - start_time
        process_time_ms = int(process_time * 1000)
        
        response.headers["X-Request-ID"] = req_id
        response.headers["X-Response-Time"] = f"{process_time_ms}ms"
        
        return response
