"""Schemas for landing pages."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.schemas.common import CamelModel


class BlockContent(CamelModel):
    type: str  # hero, text, image, features, cta, testimonial, faq, form, divider
    content: dict[str, Any] = Field(default_factory=dict)
    settings: dict[str, Any] = Field(default_factory=dict)


class LandingPageCreate(CamelModel):
    title: str = Field(..., min_length=1, max_length=300)
    slug: str = Field(..., min_length=1, max_length=200, pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")
    description: str | None = None
    blocks: list[BlockContent] = Field(default_factory=list)
    settings: dict[str, Any] = Field(default_factory=dict)
    whatsapp_number: str | None = None
    whatsapp_message: str | None = None
    meta_title: str | None = None
    meta_description: str | None = None
    og_image_url: str | None = None
    template: str | None = None


class LandingPageUpdate(CamelModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    slug: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    blocks: list[BlockContent] | None = None
    settings: dict[str, Any] | None = None
    whatsapp_number: str | None = None
    whatsapp_message: str | None = None
    meta_title: str | None = None
    meta_description: str | None = None
    og_image_url: str | None = None


class LandingPageResponse(CamelModel):
    id: UUID
    title: str
    slug: str
    description: str | None = None
    status: str
    published_at: datetime | None = None
    blocks: list[dict[str, Any]]
    settings: dict[str, Any]
    whatsapp_number: str | None = None
    whatsapp_message: str | None = None
    visit_count: int
    conversion_count: int
    meta_title: str | None = None
    meta_description: str | None = None
    og_image_url: str | None = None
    template: str | None = None
    company_id: UUID
    created_at: datetime
    updated_at: datetime


class LandingPageListItem(CamelModel):
    id: UUID
    title: str
    slug: str
    status: str
    visit_count: int
    conversion_count: int
    published_at: datetime | None = None
    created_at: datetime


class PublishRequest(CamelModel):
    pass  # No body needed


class PageAnalytics(CamelModel):
    page_id: UUID
    title: str
    slug: str
    visit_count: int
    conversion_count: int
    conversion_rate: float
