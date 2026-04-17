"""WhatsApp Commerce/Catalog models."""

from decimal import Decimal
from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TenantMixin, TimestampMixin, UUIDMixin
import uuid


class ProductCategory(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "product_categories"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    def __repr__(self) -> str:
        return f"<ProductCategory {self.name}>"


class Product(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "products"

    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_categories.id", ondelete="SET NULL"), nullable=True,
    )
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), default="KWD")
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    sku: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    stock_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    whatsapp_catalog_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    extra_data: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")

    def __repr__(self) -> str:
        return f"<Product {self.name}>"
