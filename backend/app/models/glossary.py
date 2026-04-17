"""Custom business glossary for NLP enhancement."""

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TenantMixin, TimestampMixin, UUIDMixin


class GlossaryTerm(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """Client-specific business term for AI/NLP understanding."""

    __tablename__ = "glossary_terms"

    term: Mapped[str] = mapped_column(String(200), nullable=False)
    definition: Mapped[str | None] = mapped_column(Text, nullable=True)
    aliases: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="product")
    # Categories: product, service, promotion, location, other

    def __repr__(self) -> str:
        return f"<GlossaryTerm {self.term}>"
