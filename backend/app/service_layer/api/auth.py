"""轻量 API Key 认证 + 内存限流"""

from __future__ import annotations

import time
from collections import defaultdict

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_bearer = HTTPBearer(auto_error=False)


async def verify_api_key(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> bool:
    settings = request.app.state.container.settings
    if not settings.api_key:
        return True
    if not credentials or credentials.credentials != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True


class InMemoryRateLimiter:
    def __init__(self, max_requests: int, window_seconds: int = 60):
        self._max = max_requests
        self._window = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    def is_limited(self, key: str) -> bool:
        now = time.time()
        cutoff = now - self._window
        self._requests[key] = [t for t in self._requests[key] if t > cutoff]
        if len(self._requests[key]) >= self._max:
            return True
        self._requests[key].append(now)
        return False


async def rate_limit_middleware(request: Request, call_next):
    settings = request.app.state.container.settings
    limit = settings.rate_limit_per_minute
    if limit <= 0:
        return await call_next(request)

    limiter: InMemoryRateLimiter = request.app.state.rate_limiter
    client_ip = request.client.host if request.client else "unknown"
    if limiter.is_limited(client_ip):
        raise HTTPException(status_code=429, detail="Too many requests")
    return await call_next(request)
