import time
import uuid

import structlog
from fastapi import Request, Response
from fastapi.responses import ORJSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.exceptions import RateLimitError

logger = structlog.get_logger()


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Adds a unique request ID to each request for tracing."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class TimingMiddleware(BaseHTTPMiddleware):
    """Measures request processing time and records metrics."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        from app.core.metrics import metrics, normalize_path

        start_time = time.perf_counter()
        response = await call_next(request)
        process_time = time.perf_counter() - start_time
        response.headers["X-Process-Time"] = f"{process_time:.4f}"

        # Record metrics with a NORMALIZED path label. Using the raw path
        # produces one label value per UUID in the URL, which blows up
        # Prometheus series count. `normalize_path` collapses
        # /v1/contacts/<uuid> → /v1/contacts/:id so we keep useful route
        # granularity without unbounded cardinality.
        method = request.method
        status = response.status_code
        route = normalize_path(request.url.path)
        metrics.inc(
            "http_requests_total",
            labels={"method": method, "status": str(status), "route": route},
        )
        metrics.observe(
            "http_request_duration_seconds",
            process_time,
            labels={"method": method, "route": route},
        )

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds security headers to all responses."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )
        return response


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Extracts tenant (company_id) from JWT and sets it on request state.
    The actual RLS SET LOCAL is done at the database session level.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # company_id is set by the auth dependency, not middleware
        # This middleware only provides a fallback for public routes
        if not hasattr(request.state, "company_id"):
            request.state.company_id = None
        response = await call_next(request)
        return response


# Per-route limit table. Keys are matched as path PREFIXES; the longest match
# wins. (limit, window_seconds). Tighter on auth endpoints to slow brute force
# and credential-stuffing.
RATE_LIMITS: tuple[tuple[str, int, int], ...] = (
    # path_prefix,                       requests, window_seconds
    ("/v1/auth/login",                       10,    60),   # 10/min/IP
    ("/v1/auth/register",                     5,    60),   # 5/min/IP
    ("/v1/auth/refresh",                     30,    60),
    ("/v1/auth/forgot-password",              3,    60),   # strict — email send + enum defence
    ("/v1/auth/reset-password",              10,    60),
    ("/v1/auth/change-password",             10,    60),   # throttle to slow guess-the-current-password
    ("/v1/payments/tap-webhook",            120,    60),   # webhooks: bursty but capped
    ("/v1/webhooks/whatsapp",               300,    60),   # WhatsApp can burst
    ("/v1/webhooks/instagram",              120,    60),
    ("/v1/",                                300,    60),   # default for /v1/*
)


def _match_limit(path: str) -> tuple[int, int] | None:
    """Return (limit, window_seconds) for the longest-matching prefix."""
    best: tuple[str, int, int] | None = None
    for prefix, limit, window in RATE_LIMITS:
        if path.startswith(prefix):
            if best is None or len(prefix) > len(best[0]):
                best = (prefix, limit, window)
    return (best[1], best[2]) if best else None


def _client_key(request: Request) -> str:
    """Build the per-client bucket key.

    Authenticated requests keyed by user_id (set by the auth dependency on
    request.state); anonymous requests keyed by best-effort client IP, which
    honors X-Forwarded-For when behind a proxy.
    """
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"u:{user_id}"
    xff = request.headers.get("x-forwarded-for")
    if xff:
        ip = xff.split(",")[0].strip()
    else:
        ip = request.client.host if request.client else "unknown"
    return f"ip:{ip}"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limiter, fronted by Redis.

    Rules from `RATE_LIMITS`. Adds standard `X-RateLimit-*` headers on every
    response, returns 429 + RFC-7231 `Retry-After` when the bucket is full.

    The middleware degrades open: if Redis is unavailable, requests pass and
    we log a warning rather than breaking the API. This is the safer default
    for a CRM where availability matters more than perfect rate accounting.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip non-versioned routes (health, metrics, docs).
        path = request.url.path
        match = _match_limit(path)
        if match is None:
            return await call_next(request)

        limit, window = match
        bucket = f"rl:{path[: path.find('/', 4)] if path.startswith('/v1/') else path}:{_client_key(request)}"

        try:
            from app.core.rate_limiter import RateLimiter
            from app.core.redis import get_redis

            redis = await get_redis()
            limiter = RateLimiter(redis)
            info = await limiter.check(bucket, limit=limit, window_seconds=window)
        except RateLimitError as exc:
            retry_after = window
            return ORJSONResponse(
                status_code=429,
                content={
                    "type": "about:blank",
                    "title": "Too Many Requests",
                    "status": 429,
                    "detail": str(exc),
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Window": str(window),
                },
            )
        except Exception as exc:  # pragma: no cover - defensive
            # Redis down, key collision, etc. Don't break the request — log and pass.
            logger.warning("rate_limit_check_failed", error=str(exc), path=path)
            return await call_next(request)

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(info["reset"])
        response.headers["X-RateLimit-Window"] = str(window)
        return response
