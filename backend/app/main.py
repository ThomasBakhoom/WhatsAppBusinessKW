from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from app.config import get_settings
from app.core.exceptions import AppException
from app.core.logging import setup_logging
from app.core.middleware import (
    RateLimitMiddleware,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
    TenantMiddleware,
    TimingMiddleware,
)
from app.core.observability import init_sentry
from app.core.redis import close_redis_pool

logger = structlog.get_logger()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown events."""
    # Startup
    setup_logging()
    init_sentry(settings)
    logger.info(
        "application_starting",
        app_name=settings.app_name,
        environment=settings.app_env,
        version=settings.app_version,
    )

    # Schema is owned by Alembic. Run `make migrate-docker` (or
    # `alembic upgrade head` inside the container) to apply migrations.
    # The previous behaviour of calling Base.metadata.create_all on startup
    # has been removed because it bypassed migrations and silently desynced
    # dev from prod (which does use migrations).

    # Start the WebSocket Redis pub/sub subscriber so broadcasts reach all pods.
    from app.websocket.manager import ws_manager
    await ws_manager.start()

    yield

    # Shutdown
    await ws_manager.stop()
    await close_redis_pool()
    logger.info("application_shutdown")


def create_app() -> FastAPI:
    """Application factory."""
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
    )

    # Middleware (order matters - first added = outermost / runs first on request)
    # Stack (request → app):
    #   CORS → RequestID → Timing → RateLimit → Tenant → Security → app
    # Rate-limit before tenant/auth so we can short-circuit floods cheaply.
    application.add_middleware(SecurityHeadersMiddleware)
    application.add_middleware(TenantMiddleware)
    application.add_middleware(RateLimitMiddleware)
    application.add_middleware(TimingMiddleware)
    application.add_middleware(RequestIDMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handlers
    @application.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return ORJSONResponse(
            status_code=exc.status_code,
            content={
                "type": "about:blank",
                "title": exc.message,
                "status": exc.status_code,
                "detail": exc.detail,
                "traceId": getattr(request.state, "request_id", None),
            },
        )

    # Include routers
    from app.api.router import api_router

    application.include_router(api_router, prefix="/v1")

    # Metrics endpoint
    from app.core.metrics import metrics
    from fastapi.responses import PlainTextResponse

    @application.get("/metrics")
    async def prometheus_metrics():
        return PlainTextResponse(metrics.format_prometheus(), media_type="text/plain")

    @application.get("/metrics/json")
    async def json_metrics():
        return metrics.get_all()

    # WebSocket endpoint
    from fastapi import WebSocket, WebSocketDisconnect, Query as WSQuery
    from app.websocket.manager import ws_manager
    from app.core.security import decode_token
    from uuid import UUID

    @application.websocket("/ws")
    async def websocket_endpoint(
        websocket: WebSocket,
        token: str = WSQuery(...),
    ):
        """WebSocket connection for real-time events."""
        try:
            payload = decode_token(token)
            if payload.get("type") != "access":
                await websocket.close(code=4001)
                return
            user_id = UUID(payload["sub"])
            company_id = UUID(payload["company_id"])
        except Exception:
            await websocket.close(code=4001)
            return

        await ws_manager.connect(websocket, company_id, user_id)
        try:
            while True:
                data = await websocket.receive_text()
                # Handle client events (typing indicators, etc.)
                if data == "ping":
                    await websocket.send_text('{"type":"pong"}')
        except WebSocketDisconnect:
            ws_manager.disconnect(websocket, company_id, user_id)

    # Health check endpoints
    @application.get("/health")
    async def health():
        return {"status": "healthy"}

    @application.get("/health/ready")
    async def health_ready():
        from app.core.database import engine
        from app.core.redis import get_redis

        checks = {}

        # Check database
        try:
            async with engine.connect() as conn:
                from sqlalchemy import text
                await conn.execute(text("SELECT 1"))
            checks["database"] = "ok"
        except Exception as e:
            checks["database"] = f"error: {e}"

        # Check Redis
        try:
            redis = await get_redis()
            await redis.ping()
            checks["redis"] = "ok"
        except Exception as e:
            checks["redis"] = f"error: {e}"

        all_ok = all(v == "ok" for v in checks.values())
        return ORJSONResponse(
            status_code=200 if all_ok else 503,
            content={"status": "ready" if all_ok else "degraded", "checks": checks},
        )

    return application


app = create_app()
