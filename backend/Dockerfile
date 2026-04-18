# Stage 1: Builder - install dependencies
FROM python:3.11-slim AS builder

WORKDIR /build

COPY pyproject.toml .

# Extract dependencies from pyproject.toml and install them
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --prefix=/install \
    fastapi[standard] uvicorn[standard] python-multipart \
    "sqlalchemy[asyncio]" asyncpg alembic \
    pydantic pydantic-settings email-validator \
    "python-jose[cryptography]" "passlib[bcrypt]" "bcrypt<4.1" \
    "redis[hiredis]" "celery[redis]" \
    httpx structlog boto3 phonenumbers cryptography \
    python-dateutil orjson \
    "sentry-sdk[fastapi]"

# Stage 2: Production
FROM python:3.11-slim AS production

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY . .

# Create non-root user
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
