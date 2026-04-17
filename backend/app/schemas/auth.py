"""Auth-related Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import CamelModel


# --- Request schemas ---

class RegisterRequest(BaseModel):
    company_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8, max_length=128)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


# --- Response schemas ---

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(CamelModel):
    id: UUID
    email: str
    username: str
    first_name: str
    last_name: str
    avatar_url: str | None = None
    is_active: bool
    is_verified: bool
    roles: list[str] = []
    company_id: UUID
    created_at: datetime
    updated_at: datetime


class RegisterResponse(BaseModel):
    user: UserResponse
    tokens: TokenResponse


class MeResponse(CamelModel):
    user: UserResponse
    company: "CompanyBriefResponse"


class CompanyBriefResponse(CamelModel):
    id: UUID
    name: str
    slug: str
    logo_url: str | None = None
