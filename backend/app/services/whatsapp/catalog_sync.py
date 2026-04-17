"""WhatsApp Commerce Catalog sync - push products to Meta Commerce Manager.

Syncs local Product models to WhatsApp Business Catalog via Graph API,
enabling in-chat product browsing and ordering.
"""

from typing import Any
from uuid import UUID

import httpx
import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import Product

logger = structlog.get_logger()

GRAPH_API = "https://graph.facebook.com/v19.0"


class WhatsAppCatalogSync:
    """Sync products to/from Meta Commerce Manager for WhatsApp Catalog."""

    def __init__(self, db: AsyncSession, company_id: UUID,
                 catalog_id: str = "", access_token: str = ""):
        self.db = db
        self.company_id = company_id
        self.catalog_id = catalog_id
        self.access_token = access_token

    async def sync_all_products(self) -> dict[str, Any]:
        """Push all active products to WhatsApp Business Catalog."""
        result = await self.db.execute(
            select(Product).where(
                Product.company_id == self.company_id,
                Product.is_active == True,
            )
        )
        products = result.scalars().all()

        created = updated = failed = 0

        for product in products:
            try:
                if product.whatsapp_catalog_id:
                    # Update existing
                    success = await self._update_product(product)
                    if success:
                        updated += 1
                    else:
                        failed += 1
                else:
                    # Create new
                    wa_id = await self._create_product(product)
                    if wa_id:
                        product.whatsapp_catalog_id = wa_id
                        created += 1
                    else:
                        failed += 1
            except Exception as e:
                logger.error("catalog_sync_product_failed", product_id=str(product.id), error=str(e))
                failed += 1

        await self.db.flush()
        logger.info("catalog_sync_complete", created=created, updated=updated, failed=failed)

        return {"created": created, "updated": updated, "failed": failed, "total": len(products)}

    async def _create_product(self, product: Product) -> str | None:
        """Create a product in Meta Commerce Manager catalog."""
        if not self.access_token or not self.catalog_id:
            # Mock for development
            mock_id = f"wa_product_{product.id.hex[:12]}"
            logger.info("catalog_create_mock", product=product.name, wa_id=mock_id)
            return mock_id

        payload = {
            "name": product.name,
            "description": product.description or product.name,
            "price": int(float(product.price) * 1000),  # Price in milliunits
            "currency": product.currency,
            "availability": "in stock" if (product.stock_quantity is None or product.stock_quantity > 0) else "out of stock",
            "retailer_id": product.sku or str(product.id),
        }
        if product.image_url:
            payload["image_url"] = product.image_url

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{GRAPH_API}/{self.catalog_id}/products",
                json=payload,
                params={"access_token": self.access_token},
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("id", "")
            else:
                logger.error("catalog_create_failed", status=resp.status_code, body=resp.text[:200])
                return None

    async def _update_product(self, product: Product) -> bool:
        """Update an existing product in Meta catalog."""
        if not self.access_token:
            logger.info("catalog_update_mock", product=product.name)
            return True

        payload = {
            "name": product.name,
            "description": product.description or product.name,
            "price": int(float(product.price) * 1000),
            "currency": product.currency,
            "availability": "in stock" if (product.stock_quantity is None or product.stock_quantity > 0) else "out of stock",
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{GRAPH_API}/{product.whatsapp_catalog_id}",
                json=payload,
                params={"access_token": self.access_token},
            )
            return resp.status_code == 200

    async def delete_product(self, product_id: UUID) -> bool:
        """Remove a product from Meta catalog."""
        result = await self.db.execute(
            select(Product).where(Product.id == product_id, Product.company_id == self.company_id)
        )
        product = result.scalar_one_or_none()
        if not product or not product.whatsapp_catalog_id:
            return False

        if self.access_token:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.delete(
                    f"{GRAPH_API}/{product.whatsapp_catalog_id}",
                    params={"access_token": self.access_token},
                )
                if resp.status_code != 200:
                    return False

        product.whatsapp_catalog_id = None
        await self.db.flush()
        return True

    def build_product_message(self, product: Product) -> dict[str, Any]:
        """Build a WhatsApp single-product message payload."""
        return {
            "type": "product",
            "action": {
                "catalog_id": self.catalog_id,
                "product_retailer_id": product.sku or str(product.id),
            },
        }

    def build_product_list_message(
        self, products: list[Product], header: str = "Our Products", body: str = "Browse our catalog:"
    ) -> dict[str, Any]:
        """Build a WhatsApp multi-product message payload."""
        sections = [{
            "title": "Products",
            "product_items": [
                {"product_retailer_id": p.sku or str(p.id)}
                for p in products[:30]  # WhatsApp max 30 products per message
            ],
        }]

        return {
            "type": "product_list",
            "header": {"type": "text", "text": header},
            "body": {"text": body},
            "action": {
                "catalog_id": self.catalog_id,
                "sections": sections,
            },
        }
