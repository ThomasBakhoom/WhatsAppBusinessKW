"""Promote a user to platform_admin.

Usage:
    python -m scripts.promote_platform_admin <email>

Example:
    python -m scripts.promote_platform_admin thomasbakhoom@gmail.com

The user must already exist (register through the normal flow first).
The script:
  1. Ensures the `platform_admin` role exists
  2. Replaces any existing roles with `platform_admin`
  3. Prints the result

Idempotent — safe to run multiple times.
"""

import asyncio
import sys


async def promote(email: str):
    from sqlalchemy import delete, select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.config import get_settings
    from app.core.permissions import ROLE_PERMISSIONS
    from app.models.auth import Role, User, UserRole

    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as db:
        # 1. Find the user
        user_result = await db.execute(select(User).where(User.email == email))
        user = user_result.scalar_one_or_none()
        if not user:
            print(f"ERROR: No user found with email {email}")
            print("Register them first via POST /v1/auth/register")
            await engine.dispose()
            sys.exit(1)

        print(f"Found user: {user.email} (id={user.id}, company_id={user.company_id})")

        # 2. Ensure platform_admin role exists
        role_result = await db.execute(select(Role).where(Role.name == "platform_admin"))
        role = role_result.scalar_one_or_none()
        if not role:
            perms = ROLE_PERMISSIONS.get("platform_admin", [])
            role = Role(
                name="platform_admin",
                display_name="Platform Admin",
                description="Cross-tenant operator",
                permissions=[p.value for p in perms],
                is_system=True,
            )
            db.add(role)
            await db.flush()
            print(f"Created platform_admin role (id={role.id})")
        else:
            print(f"Found existing platform_admin role (id={role.id})")

        # 3. Clear existing roles for this user, then assign platform_admin
        await db.execute(delete(UserRole).where(UserRole.user_id == user.id))
        db.add(UserRole(user_id=user.id, role_id=role.id))
        await db.commit()

        print(f"\n{user.email} is now a PLATFORM_ADMIN.")
        print("Login via the normal flow to get a JWT with the platform_admin role.")
        print("Access /v1/platform/* endpoints and the /platform UI section.")

    await engine.dispose()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.promote_platform_admin <email>")
        sys.exit(1)
    asyncio.run(promote(sys.argv[1]))
