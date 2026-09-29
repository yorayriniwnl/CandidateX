import time
from typing import Callable, Any
from fastapi import Request, HTTPException, status
from cci.config import settings

# In-memory store for rate limiting (Upgrade path: Use Redis)
# Dictionary mapping route_key to list of timestamps
_RATE_LIMIT_STORE: dict[str, list[float]] = {}

def reset_rate_limits() -> None:
    """Clears in-memory rate limit store (useful for tests and maintenance)."""
    _RATE_LIMIT_STORE.clear()

def rate_limit(max_requests: int, window_seconds: int = 60) -> Callable:
    async def dependency(request: Request) -> None:
        if not getattr(settings, "RATE_LIMIT_ENABLED", True):
            return

        client_ip = request.headers.get("X-Forwarded-For")
        if not client_ip:
            client_ip = request.client.host if request.client else "unknown"
            
        path = request.url.path if hasattr(request, "url") else "default"
        method = request.method if hasattr(request, "method") else "GET"
        store_key = f"{client_ip}:{method}:{path}"
        current_time = time.time()
        
        # Clean up old entries and check limit
        if store_key not in _RATE_LIMIT_STORE:
            _RATE_LIMIT_STORE[store_key] = []
            
        # Filter out timestamps older than the window
        _RATE_LIMIT_STORE[store_key] = [
            t for t in _RATE_LIMIT_STORE[store_key] 
            if current_time - t < window_seconds
        ]
        
        if len(_RATE_LIMIT_STORE[store_key]) >= max_requests:
            oldest_request = _RATE_LIMIT_STORE[store_key][0]
            retry_after = max(1, int(window_seconds - (current_time - oldest_request)))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests",
                headers={"Retry-After": str(retry_after)},
            )
            
        _RATE_LIMIT_STORE[store_key].append(current_time)

    return dependency
