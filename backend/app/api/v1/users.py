"""User management API - invite, list, update role, deactivate."""

from uuid import UUID
from fastapi import APIRouter, Query
from pydantic import EmailStr, Field
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictError, NotFoundError
from app.core.pagination import PaginatedResponse
from app.core.security import hash_password
from app.dependencies import AuthUser, TenantDbSession
from app.models.auth import Role, User, UserRole
from app.schemas.common import CamelModel, SuccessResponse

router = APIRouter()


class InviteUserRequest(CamelModel):
    email: EmailStr
    first_name: str = Field(..., min_length=1)
    last_name: str = ""
    role: str = Field(default="agent", pattern=r"^(admin|manager|agent)$")


class UserListItem(CamelModel):
    id: UUID
    email: str
    first_name: str
    last_name: str
    is_active: bool
    is_online: bool
    roles: list[str]
    created_at: str


class UpdateUserRequest(CamelModel):
    first_name: str | None = None
    last_name: str | None = None
    role: str | None = Field(default=None, pattern=r"^(admin|manager|agent)$")
    is_active: bool | None = None


@router.get("", response_model=list[UserListItem])
async def list_users(db: TenantDbSession, user: AuthUser):
    result = await db.execute(
        select(User).where(User.company_id == user.company_id)
        .options(selectinload(User.roles).selectinload(UserRole.role))
        .order_by(User.created_at)
    )
    return [
        UserListItem(
            id=u.id, email=u.email, first_name=u.first_name, last_name=u.last_name,
            is_active=u.is_active, is_online=u.is_online,
            roles=u.role_names, created_at=u.created_at.isoformat(),
        )
        for u in result.scalars().unique().all()
    ]


@router.post("/invite", response_model=UserListItem, status_code=201)
async def invite_user(data: InviteUserRequest, db: TenantDbSession, user: AuthUser):
    # Check duplicate
    existing = await db.execute(
        select(User).where(User.company_id == user.company_id, User.email == data.email)
    )
    if existing.scalar_one_or_none():
        raise ConflictError(f"User {data.email} already exists")

    # Create user with temp password
    import secrets
    temp_password = secrets.token_urlsafe(12)
    new_user = User(
        company_id=user.company_id, email=data.email,
        username=data.email.split("@")[0],
        password_hash=hash_password(temp_password),
        first_name=data.first_name, last_name=data.last_name,
    )
    db.add(new_user)
    await db.flush()

    # Assign role
    role_result = await db.execute(select(Role).where(Role.name == data.role))
    role = role_result.scalar_one_or_none()
    if role:
        db.add(UserRole(user_id=new_user.id, role_id=role.id))
    await db.commit()

    return UserListItem(
        id=new_user.id, email=new_user.email,
        first_name=new_user.first_name, last_name=new_user.last_name,
        is_active=True, is_online=False, roles=[data.role],
        created_at=new_user.created_at.isoformat(),
    )


@router.patch("/{user_id}", response_model=SuccessResponse)
async def update_user(user_id: UUID, data: UpdateUserRequest, db: TenantDbSession, user: AuthUser):
    result = await db.execute(
        select(User).where(User.company_id == user.company_id, User.id == user_id)
    )
    target = result.scalar_one_or_none()
    if not target:
        raise NotFoundError("User not found")

    if data.first_name is not None:
        target.first_name = data.first_name
    if data.last_name is not None:
        target.last_name = data.last_name
    if data.is_active is not None:
        target.is_active = data.is_active
    await db.commit()
    return SuccessResponse(message="User updated")


@router.delete("/{user_id}", response_model=SuccessResponse)
async def deactivate_user(user_id: UUID, db: TenantDbSession, user: AuthUser):
    result = await db.execute(
        select(User).where(User.company_id == user.company_id, User.id == user_id)
    )
    target = result.scalar_one_or_none()
    if not target:
        raise NotFoundError("User not found")
    target.is_active = False
    await db.commit()
    return SuccessResponse(message="User deactivated")
