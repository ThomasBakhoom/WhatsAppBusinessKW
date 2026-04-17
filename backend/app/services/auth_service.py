"""Authentication service - handles registration, login, token refresh."""

import re
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.core.database import set_tenant_context
from app.core.exceptions import ConflictError, NotFoundError, UnauthorizedError
from app.core.security import (
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    decode_password_reset_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.audit import AuditLog
from app.models.auth import Role, User, UserRole
from app.models.company import Company
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
)

logger = structlog.get_logger()
settings = get_settings()


def _slugify(name: str) -> str:
    """Convert a company name to a URL-friendly slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug[:100]


class AuthService:
    def __init__(
        self,
        db: AsyncSession,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ):
        self.db = db
        self.ip_address = ip_address
        self.user_agent = user_agent

    async def register(self, data: RegisterRequest) -> RegisterResponse:
        """Register a new company and owner user."""
        # Check if email already exists
        existing = await self.db.execute(
            select(User).where(User.email == data.email)
        )
        if existing.scalar_one_or_none():
            raise ConflictError(f"User with email '{data.email}' already exists")

        # Create company
        slug = _slugify(data.company_name)
        existing_company = await self.db.execute(
            select(Company).where(Company.slug == slug)
        )
        if existing_company.scalar_one_or_none():
            slug = f"{slug}-{str(__import__('uuid').uuid4())[:8]}"

        company = Company(
            name=data.company_name,
            slug=slug,
        )
        self.db.add(company)
        await self.db.flush()  # Get company.id

        # IMPORTANT: from this point on, we INSERT into RLS-protected tables
        # (users, audit_logs, etc.). Set the tenant GUC for the rest of this
        # transaction so the policies' WITH CHECK clauses pass and the rows
        # are visible to subsequent queries inside this request.
        await set_tenant_context(self.db, company.id)

        # Ensure the "owner" role exists (roles is NOT tenant-scoped)
        owner_role = await self._get_or_create_role("owner")

        # Create user
        user = User(
            company_id=company.id,
            email=data.email,
            username=data.username,
            password_hash=hash_password(data.password),
            first_name=data.first_name,
            last_name=data.last_name,
            is_active=True,
        )
        self.db.add(user)
        await self.db.flush()

        # Assign owner role
        user_role = UserRole(user_id=user.id, role_id=owner_role.id)
        self.db.add(user_role)
        await self.db.flush()

        # Generate tokens
        tokens = self._create_tokens(user.id, company.id, ["owner"])

        # Audit trail
        await self._audit(
            company_id=company.id,
            action="company.registered",
            description=f"New company '{company.name}' registered with owner {user.email}",
            user_id=user.id,
            user_email=user.email,
            resource_type="company",
            resource_id=str(company.id),
        )
        await self._audit(
            company_id=company.id,
            action="user.registered",
            description=f"User {user.email} registered as company owner",
            user_id=user.id,
            user_email=user.email,
            resource_type="user",
            resource_id=str(user.id),
        )

        logger.info("user_registered", user_id=str(user.id), company_id=str(company.id))

        return RegisterResponse(
            user=UserResponse(
                id=user.id,
                email=user.email,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                is_active=user.is_active,
                is_verified=user.is_verified,
                roles=["owner"],
                company_id=company.id,
                created_at=user.created_at,
                updated_at=user.updated_at,
            ),
            tokens=tokens,
        )

    async def login(self, data: LoginRequest) -> TokenResponse:
        """Authenticate a user and return tokens.

        `users` is intentionally NOT under RLS (see migration
        359ca78ab254) so this email lookup works without a tenant
        context. Once we know the user's company, we set the tenant GUC so
        subsequent writes (audit_logs, last_login) pass RLS.
        """
        result = await self.db.execute(
            select(User)
            .where(User.email == data.email)
            .options(selectinload(User.roles).selectinload(UserRole.role))
        )
        user = result.scalar_one_or_none()

        if not user or not verify_password(data.password, user.password_hash):
            # Failed login: only audit if we identified a user (we need
            # company_id to set tenant context for the audit_logs INSERT).
            if user is not None:
                await set_tenant_context(self.db, user.company_id)
                await self._audit(
                    company_id=user.company_id,
                    action="user.login_failed",
                    description=f"Failed login attempt for {data.email}",
                    user_email=data.email,
                )
            logger.warning("login_failed", email=data.email)
            raise UnauthorizedError("Invalid email or password")

        # Authenticated. Set tenant context for the rest of the request.
        await set_tenant_context(self.db, user.company_id)

        if not user.is_active:
            await self._audit(
                company_id=user.company_id,
                action="user.login_denied",
                description=f"Login denied for deactivated user {data.email}",
                user_id=user.id,
                user_email=data.email,
            )
            raise UnauthorizedError("Account is deactivated")

        # Get user roles
        role_names = []
        for ur in user.roles:
            if ur.role:
                role_names.append(ur.role.name)

        tokens = self._create_tokens(user.id, user.company_id, role_names)

        # Update last login
        from datetime import datetime, timezone
        user.last_login_at = datetime.now(timezone.utc)

        await self._audit(
            company_id=user.company_id,
            action="user.login",
            description=f"User {user.email} logged in",
            user_id=user.id,
            user_email=user.email,
            resource_type="user",
            resource_id=str(user.id),
        )

        logger.info("user_logged_in", user_id=str(user.id))

        return tokens

    async def refresh_tokens(self, refresh_token: str) -> TokenResponse:
        """Refresh access and refresh tokens."""
        try:
            payload = decode_token(refresh_token)
        except ValueError:
            raise UnauthorizedError("Invalid refresh token")

        if payload.get("type") != "refresh":
            raise UnauthorizedError("Invalid token type")

        user_id = UUID(payload["sub"])
        result = await self.db.execute(
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.roles).selectinload(UserRole.role))
        )
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            raise UnauthorizedError("User not found or deactivated")

        # Set tenant context before writing the audit row.
        await set_tenant_context(self.db, user.company_id)

        role_names = [ur.role.name for ur in user.roles if ur.role]
        tokens = self._create_tokens(user.id, user.company_id, role_names)

        await self._audit(
            company_id=user.company_id,
            action="user.token_refreshed",
            description=f"Token refreshed for {user.email}",
            user_id=user.id,
            user_email=user.email,
            resource_type="user",
            resource_id=str(user.id),
        )
        return tokens

    def _create_tokens(
        self, user_id: UUID, company_id: UUID, roles: list[str]
    ) -> TokenResponse:
        """Create access and refresh token pair."""
        access_token = create_access_token(user_id, company_id, roles)
        refresh_token = create_refresh_token(user_id)
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.jwt_access_token_expire_minutes * 60,
        )

    async def _audit(
        self,
        *,
        company_id: UUID,
        action: str,
        description: str,
        user_id: UUID | None = None,
        user_email: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        changes: dict | None = None,
    ) -> None:
        """Write an audit log entry. Best-effort: never fails the caller."""
        try:
            entry = AuditLog(
                company_id=company_id,
                user_id=user_id,
                user_email=user_email,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                description=description,
                changes=changes,
                ip_address=self.ip_address,
                user_agent=self.user_agent,
            )
            self.db.add(entry)
            await self.db.flush()
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("audit_log_failed", action=action, error=str(exc))

    async def request_password_reset(
        self, data: ForgotPasswordRequest, reset_base_url: str
    ) -> None:
        """Issue a password-reset token and email it to the user.

        SECURITY: we deliberately return the same outcome regardless of
        whether the email exists, so this endpoint can't be used to enumerate
        accounts. An audit entry is recorded for real hits; failed lookups
        are logged at DEBUG but NOT audited (there's no tenant to attribute).
        """
        result = await self.db.execute(
            select(User).where(User.email == data.email)
        )
        user = result.scalar_one_or_none()

        if user is None or not user.is_active:
            logger.info("password_reset_unknown_email", email=data.email)
            return

        token = create_password_reset_token(user.id, user.email)
        reset_link = f"{reset_base_url.rstrip('/')}?token={token}"

        # Email send is best-effort; surface failure as a warning but don't
        # leak it to the caller (doing so would enable account enumeration).
        try:
            from app.services.email_service import EmailService

            await EmailService().send_password_reset(user.email, reset_link)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("password_reset_email_failed", error=str(exc))

        # Attribute the audit under the target user's tenant.
        await set_tenant_context(self.db, user.company_id)
        await self._audit(
            company_id=user.company_id,
            action="user.password_reset_requested",
            description=f"Password reset requested for {user.email}",
            user_id=user.id,
            user_email=user.email,
            resource_type="user",
            resource_id=str(user.id),
        )

    async def reset_password(self, data: ResetPasswordRequest) -> None:
        """Consume a reset token and set a new password.

        Tokens are single-use in spirit: once the password changes, the old
        token still verifies (it's stateless JWT) but the new password
        invalidates any attacker-observed login path. For stricter behaviour,
        store a password-hash digest in the JWT and reject if it no longer
        matches the stored hash — left as a follow-up.
        """
        try:
            payload = decode_password_reset_token(data.token)
        except ValueError as exc:
            raise UnauthorizedError(f"Invalid reset token: {exc}") from exc

        user_id = UUID(payload["sub"])
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None or not user.is_active:
            raise UnauthorizedError("User not found or deactivated")

        # Email must match the token's embedded email — catches the edge
        # case where a user's email was changed after the token was issued.
        token_email = payload.get("email")
        if token_email and token_email != user.email:
            raise UnauthorizedError("Token does not match current user email")

        user.password_hash = hash_password(data.new_password)

        await set_tenant_context(self.db, user.company_id)
        await self._audit(
            company_id=user.company_id,
            action="user.password_reset",
            description=f"Password reset for {user.email}",
            user_id=user.id,
            user_email=user.email,
            resource_type="user",
            resource_id=str(user.id),
        )

    async def change_password(
        self, user_id: UUID, data: ChangePasswordRequest
    ) -> None:
        """Change password for an authenticated user. Requires current password.

        Separate from `reset_password` which is token-based (for users who've
        lost access). This path verifies the CURRENT password before rotating,
        making it safe to expose to an authenticated session without involving
        email.
        """
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None or not user.is_active:
            raise UnauthorizedError("User not found or deactivated")

        if not verify_password(data.current_password, user.password_hash):
            # Audit the failed attempt — this is a real security signal.
            await set_tenant_context(self.db, user.company_id)
            await self._audit(
                company_id=user.company_id,
                action="user.password_change_failed",
                description=f"Failed password change for {user.email} (bad current password)",
                user_id=user.id,
                user_email=user.email,
            )
            raise UnauthorizedError("Current password is incorrect")

        if data.current_password == data.new_password:
            raise UnauthorizedError("New password must differ from current password")

        user.password_hash = hash_password(data.new_password)

        await set_tenant_context(self.db, user.company_id)
        await self._audit(
            company_id=user.company_id,
            action="user.password_changed",
            description=f"Password changed for {user.email}",
            user_id=user.id,
            user_email=user.email,
            resource_type="user",
            resource_id=str(user.id),
        )

    async def _get_or_create_role(self, name: str) -> Role:
        """Get an existing role or create it."""
        result = await self.db.execute(select(Role).where(Role.name == name))
        role = result.scalar_one_or_none()
        if role:
            return role

        # Import here to avoid circular
        from app.core.permissions import ROLE_PERMISSIONS

        perms = ROLE_PERMISSIONS.get(name, [])
        role = Role(
            name=name,
            display_name=name.replace("_", " ").title(),
            permissions=[p.value for p in perms],
            is_system=True,
        )
        self.db.add(role)
        await self.db.flush()
        return role
