"""Seed script - populate default data for new deployments."""

import asyncio
import sys
sys.path.insert(0, ".")

from app.config import get_settings
from app.models.base import Base


async def seed():
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from app.models.payment import Plan
    from app.models.auth import Role
    from sqlalchemy import select

    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as db:
        # Seed roles
        for role_data in [
            {"name": "platform_admin", "display_name": "Platform Admin", "is_system": True},
            {"name": "owner", "display_name": "Owner", "is_system": True},
            {"name": "admin", "display_name": "Admin", "is_system": True},
            {"name": "manager", "display_name": "Manager", "is_system": True},
            {"name": "agent", "display_name": "Agent", "is_system": True},
        ]:
            existing = await db.execute(select(Role).where(Role.name == role_data["name"]))
            if not existing.scalar_one_or_none():
                db.add(Role(**role_data))
                print(f"  + Role: {role_data['name']}")

        # Seed plans
        for plan_data in [
            {"name": "starter", "display_name": "Starter", "description": "Perfect for small businesses",
             "price_monthly": 9.900, "price_yearly": 99.000,
             "max_contacts": 500, "max_conversations_per_month": 1000, "max_team_members": 3,
             "max_automations": 5, "max_pipelines": 1, "max_landing_pages": 3,
             "has_ai_features": False, "has_api_access": False, "sort_order": 0},
            {"name": "growth", "display_name": "Growth", "description": "For growing teams",
             "price_monthly": 29.900, "price_yearly": 299.000,
             "max_contacts": 5000, "max_conversations_per_month": 10000, "max_team_members": 10,
             "max_automations": 25, "max_pipelines": 3, "max_landing_pages": 10,
             "has_ai_features": True, "has_api_access": False, "sort_order": 1},
            {"name": "enterprise", "display_name": "Enterprise", "description": "Full power for large teams",
             "price_monthly": 79.900, "price_yearly": 799.000,
             "max_contacts": 50000, "max_conversations_per_month": 100000, "max_team_members": 50,
             "max_automations": 100, "max_pipelines": 10, "max_landing_pages": 50,
             "has_ai_features": True, "has_api_access": True, "sort_order": 2},
        ]:
            existing = await db.execute(select(Plan).where(Plan.name == plan_data["name"]))
            if not existing.scalar_one_or_none():
                db.add(Plan(**plan_data))
                print(f"  + Plan: {plan_data['name']} ({plan_data['price_monthly']} KWD/mo)")

        await db.commit()
        print("\nSeed complete!")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
