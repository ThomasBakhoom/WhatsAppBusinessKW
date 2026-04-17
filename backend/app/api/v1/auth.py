"""Authentication API endpoints."""

from fastapi import APIRouter, Request

from app.dependencies import AuthUser, DbSession, TenantDbSession
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    RegisterResponse,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
    MeResponse,
    CompanyBriefResponse,
)
from app.schemas.common import SuccessResponse
from app.services.auth_service import AuthService

router = APIRouter()


def _client_context(request: Request) -> tuple[str | None, str | None]:
    """Best-effort extraction of client IP and user-agent for audit logging."""
    # Respect X-Forwarded-For (first entry is the real client when behind a proxy)
    xff = request.headers.get("x-forwarded-for")
    if xff:
        ip = xff.split(",")[0].strip() or None
    else:
        ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    return ip, ua


@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register(data: RegisterRequest, request: Request, db: DbSession):
    """Register a new company and owner account."""
    ip, ua = _client_context(request)
    service = AuthService(db, ip_address=ip, user_agent=ua)
    return await service.register(data)


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, request: Request, db: DbSession):
    """Authenticate and get access/refresh tokens."""
    ip, ua = _client_context(request)
    service = AuthService(db, ip_address=ip, user_agent=ua)
    return await service.login(data)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(data: RefreshTokenRequest, request: Request, db: DbSession):
    """Refresh access token using a refresh token."""
    ip, ua = _client_context(request)
    service = AuthService(db, ip_address=ip, user_agent=ua)
    return await service.refresh_tokens(data.refresh_token)


@router.post("/forgot-password", response_model=SuccessResponse)
async def forgot_password(
    data: ForgotPasswordRequest, request: Request, db: DbSession
):
    """Request a password-reset email.

    Always returns 200 with the same message regardless of whether the email
    exists — this prevents account enumeration via timing/response differences.
    """
    ip, ua = _client_context(request)
    service = AuthService(db, ip_address=ip, user_agent=ua)
    # Base URL for the reset page. Prefer the frontend origin from settings;
    # the frontend appends `?token=<jwt>` and calls /reset-password.
    from app.config import get_settings

    settings = get_settings()
    frontend_origin = settings.cors_origins[0] if settings.cors_origins else ""
    reset_base_url = f"{frontend_origin.rstrip('/')}/reset-password"

    await service.request_password_reset(data, reset_base_url=reset_base_url)
    return SuccessResponse(
        message="If an account exists for that email, a reset link has been sent."
    )


@router.post("/reset-password", response_model=SuccessResponse)
async def reset_password(data: ResetPasswordRequest, request: Request, db: DbSession):
    """Consume a password-reset token and set a new password."""
    ip, ua = _client_context(request)
    service = AuthService(db, ip_address=ip, user_agent=ua)
    await service.reset_password(data)
    return SuccessResponse(message="Password updated")


@router.post("/change-password", response_model=SuccessResponse)
async def change_password(
    data: ChangePasswordRequest,
    request: Request,
    db: DbSession,
    current_user: AuthUser,
):
    """Change password for the authenticated user. Requires the current password."""
    ip, ua = _client_context(request)
    service = AuthService(db, ip_address=ip, user_agent=ua)
    await service.change_password(current_user.user_id, data)
    return SuccessResponse(message="Password updated")


@router.get("/me", response_model=MeResponse)
async def get_current_user_profile(current_user: AuthUser, db: TenantDbSession):
    """Get the current authenticated user's profile."""
    from sqlalchemy import select
    from app.models.auth import User
    from app.models.company import Company

    result = await db.execute(select(User).where(User.id == current_user.user_id))
    user = result.scalar_one()

    result = await db.execute(select(Company).where(Company.id == current_user.company_id))
    company = result.scalar_one()

    return MeResponse(
        user=UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            avatar_url=user.avatar_url,
            is_active=user.is_active,
            is_verified=user.is_verified,
            roles=current_user.roles,
            company_id=user.company_id,
            created_at=user.created_at,
            updated_at=user.updated_at,
        ),
        company=CompanyBriefResponse(
            id=company.id,
            name=company.name,
            slug=company.slug,
            logo_url=company.logo_url,
        ),
    )
