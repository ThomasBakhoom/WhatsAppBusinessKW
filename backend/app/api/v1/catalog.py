"""Product catalog API for WhatsApp Commerce."""

from decimal import Decimal
from uuid import UUID
from fastapi import APIRouter, Query
from pydantic import Field
from sqlalchemy import select, func
from app.dependencies import AuthUser, TenantDbSession
from app.models.catalog import Product, ProductCategory
from app.schemas.common import CamelModel, SuccessResponse
from app.core.exceptions import NotFoundError
from app.core.pagination import PaginatedResponse
from typing import Any

router = APIRouter()


class ProductCreate(CamelModel):
    name: str = Field(..., min_length=1, max_length=300)
    description: str | None = None
    price: Decimal = Field(default=Decimal("0.000"), ge=0)
    currency: str = "KWD"
    image_url: str | None = None
    sku: str | None = None
    category_id: UUID | None = None


class ProductResponse(CamelModel):
    id: UUID
    name: str
    description: str | None
    price: Decimal
    currency: str
    image_url: str | None
    sku: str | None
    is_active: bool
    stock_quantity: int | None
    category_id: UUID | None
    created_at: str


@router.get("/products")
async def list_products(db: TenantDbSession, user: AuthUser,
    limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0)):
    base = select(Product).where(Product.company_id == user.company_id, Product.is_active == True)
    count = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    result = await db.execute(base.order_by(Product.name).limit(limit).offset(offset))
    items = [
        ProductResponse(
            id=p.id, name=p.name, description=p.description, price=p.price,
            currency=p.currency, image_url=p.image_url, sku=p.sku,
            is_active=p.is_active, stock_quantity=p.stock_quantity,
            category_id=p.category_id, created_at=p.created_at.isoformat(),
        )
        for p in result.scalars().all()
    ]
    return PaginatedResponse.create(items=items, total=count, limit=limit, offset=offset)


@router.post("/products", response_model=ProductResponse, status_code=201)
async def create_product(data: ProductCreate, db: TenantDbSession, user: AuthUser):
    product = Product(
        company_id=user.company_id, name=data.name, description=data.description,
        price=data.price, currency=data.currency, image_url=data.image_url,
        sku=data.sku, category_id=data.category_id,
    )
    db.add(product)
    await db.commit()
    return ProductResponse(
        id=product.id, name=product.name, description=product.description,
        price=product.price, currency=product.currency, image_url=product.image_url,
        sku=product.sku, is_active=product.is_active, stock_quantity=product.stock_quantity,
        category_id=product.category_id, created_at=product.created_at.isoformat(),
    )


@router.delete("/products/{product_id}", response_model=SuccessResponse)
async def delete_product(product_id: UUID, db: TenantDbSession, user: AuthUser):
    result = await db.execute(
        select(Product).where(Product.company_id == user.company_id, Product.id == product_id)
    )
    p = result.scalar_one_or_none()
    if not p:
        raise NotFoundError("Product not found")
    p.is_active = False
    await db.commit()
    return SuccessResponse(message="Product removed")


@router.post("/sync-whatsapp", response_model=SuccessResponse)
async def sync_catalog_to_whatsapp(db: TenantDbSession, user: AuthUser):
    """Sync all products to WhatsApp Business Catalog via Meta Commerce Manager."""
    from app.services.whatsapp.catalog_sync import WhatsAppCatalogSync
    from app.models.company import Company

    company = await db.execute(select(Company).where(Company.id == user.company_id))
    co = company.scalar_one_or_none()
    catalog_id = co.settings.get("whatsapp_catalog_id", "") if co and co.settings else ""

    sync = WhatsAppCatalogSync(
        db, user.company_id,
        catalog_id=catalog_id,
        access_token=co.whatsapp_api_token_encrypted or "" if co else "",
    )
    result = await sync.sync_all_products()
    await db.commit()
    return SuccessResponse(
        message=f"Catalog sync: {result['created']} created, {result['updated']} updated, {result['failed']} failed"
    )


@router.post("/products/{product_id}/send")
async def send_product_message(product_id: UUID, conversation_id: UUID, db: TenantDbSession, user: AuthUser):
    """Send a single product message in a WhatsApp conversation."""
    from app.services.whatsapp.catalog_sync import WhatsAppCatalogSync

    result = await db.execute(
        select(Product).where(Product.company_id == user.company_id, Product.id == product_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise NotFoundError("Product not found")

    sync = WhatsAppCatalogSync(db, user.company_id)
    payload = sync.build_product_message(product)

    return {"message_type": "product", "payload": payload, "product_name": product.name}
