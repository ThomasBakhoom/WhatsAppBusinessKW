"""Seed demo data — creates a sample company with realistic Kuwait CRM data.

Run: cd backend && python -m scripts.seed_demo

Creates:
  * Demo company "Al-Baraka Trading" with owner@albaraka.kw / Demo123!
  * 5 system roles (if missing)
  * 3 pricing plans (if missing)
  * 10 contacts with Kuwaiti names + phone numbers
  * 1 sales pipeline with 4 stages + 5 deals
  * 3 tags
  * 5 conversations with sample messages

Idempotent: skips creation if the demo company already exists.
"""

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

sys.path.insert(0, ".")


CONTACTS = [
    {"phone": "+96599001001", "first_name": "Abdullah", "last_name": "Al-Mutairi", "email": "abdullah@example.kw"},
    {"phone": "+96599001002", "first_name": "Fatima", "last_name": "Al-Sabah", "email": "fatima@example.kw"},
    {"phone": "+96599001003", "first_name": "Mohammed", "last_name": "Al-Rashidi", "email": "mohammed@example.kw"},
    {"phone": "+96599001004", "first_name": "Noura", "last_name": "Al-Kandari", "email": "noura@example.kw"},
    {"phone": "+96599001005", "first_name": "Yousef", "last_name": "Al-Enezi", "email": "yousef@example.kw"},
    {"phone": "+96599001006", "first_name": "Maryam", "last_name": "Al-Shammari", "email": "maryam@example.kw"},
    {"phone": "+96599001007", "first_name": "Khalid", "last_name": "Al-Hajri", "email": "khalid@example.kw"},
    {"phone": "+96599001008", "first_name": "Sara", "last_name": "Al-Dosari", "email": "sara@example.kw"},
    {"phone": "+96599001009", "first_name": "Omar", "last_name": "Al-Azmi", "email": "omar@example.kw"},
    {"phone": "+96599001010", "first_name": "Lulwa", "last_name": "Al-Failakawi", "email": "lulwa@example.kw"},
]

STAGES = [
    {"name": "New Lead", "color": "#3B82F6", "is_won": False, "is_lost": False},
    {"name": "Proposal Sent", "color": "#F59E0B", "is_won": False, "is_lost": False},
    {"name": "Negotiation", "color": "#8B5CF6", "is_won": False, "is_lost": False},
    {"name": "Won", "color": "#10B981", "is_won": True, "is_lost": False},
]

TAGS = [
    {"name": "VIP", "color": "#EF4444"},
    {"name": "WhatsApp Active", "color": "#10B981"},
    {"name": "Needs Follow-up", "color": "#F59E0B"},
]


async def seed_demo():
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.config import get_settings
    from app.core.database import set_tenant_context
    from app.core.security import hash_password
    from app.models.auth import Role, User, UserRole
    from app.models.company import Company
    from app.models.contact import Contact, ContactTag, Tag
    from app.models.conversation import Conversation
    from app.models.message import Message
    from app.models.pipeline import Deal, Pipeline, PipelineStage

    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as db:
        # Check if demo company exists
        existing = await db.execute(
            select(Company).where(Company.slug == "al-baraka-trading")
        )
        if existing.scalar_one_or_none():
            print("Demo company already exists. Skipping.")
            await engine.dispose()
            return

        # Run the base seed first (roles + plans)
        from scripts.seed import seed
        await seed()

        # Create demo company
        company = Company(name="Al-Baraka Trading", slug="al-baraka-trading")
        db.add(company)
        await db.flush()
        company_id = company.id
        print(f"\n+ Company: {company.name} (id={company_id})")

        # Set tenant context for RLS
        await set_tenant_context(db, company_id)

        # Create owner user
        owner_role = (await db.execute(select(Role).where(Role.name == "owner"))).scalar_one()
        user = User(
            company_id=company_id,
            email="owner@albaraka.kw",
            username="owner",
            password_hash=hash_password("Demo123!"),
            first_name="Ahmad",
            last_name="Al-Baraka",
            is_active=True,
        )
        db.add(user)
        await db.flush()
        db.add(UserRole(user_id=user.id, role_id=owner_role.id))
        print(f"  + User: {user.email} (password: Demo123!)")

        # Create tags
        tag_map = {}
        for t in TAGS:
            tag = Tag(company_id=company_id, name=t["name"], color=t["color"])
            db.add(tag)
            await db.flush()
            tag_map[t["name"]] = tag.id
            print(f"  + Tag: {t['name']}")

        # Create contacts
        contact_ids = []
        for i, c in enumerate(CONTACTS):
            contact = Contact(
                company_id=company_id,
                phone=c["phone"],
                email=c["email"],
                first_name=c["first_name"],
                last_name=c["last_name"],
                source="whatsapp",
                status="active",
                opt_in_whatsapp=True,
            )
            db.add(contact)
            await db.flush()
            contact_ids.append(contact.id)
            # Tag first 3 as VIP
            if i < 3:
                db.add(ContactTag(contact_id=contact.id, tag_id=tag_map["VIP"]))
            # Tag all as WhatsApp Active
            db.add(ContactTag(contact_id=contact.id, tag_id=tag_map["WhatsApp Active"]))
            print(f"  + Contact: {c['first_name']} {c['last_name']} ({c['phone']})")

        # Create pipeline + stages
        pipeline = Pipeline(company_id=company_id, name="Sales Pipeline", is_default=True)
        db.add(pipeline)
        await db.flush()
        stage_ids = []
        for i, s in enumerate(STAGES):
            stage = PipelineStage(
                pipeline_id=pipeline.id,
                name=s["name"],
                color=s["color"],
                sort_order=i,
                is_won=s["is_won"],
                is_lost=s["is_lost"],
            )
            db.add(stage)
            await db.flush()
            stage_ids.append(stage.id)
        print(f"  + Pipeline: {pipeline.name} ({len(STAGES)} stages)")

        # Create deals
        now = datetime.now(timezone.utc)
        deals = [
            {"title": "Office Furniture Supply", "value": "2500.000", "stage": 0, "contact": 0},
            {"title": "IT Infrastructure Upgrade", "value": "15000.000", "stage": 1, "contact": 1},
            {"title": "Annual Maintenance Contract", "value": "5000.000", "stage": 2, "contact": 2},
            {"title": "Marketing Materials Print", "value": "800.000", "stage": 0, "contact": 4},
            {"title": "Security System Install", "value": "7500.000", "stage": 3, "contact": 3},
        ]
        for d in deals:
            deal = Deal(
                company_id=company_id,
                pipeline_id=pipeline.id,
                stage_id=stage_ids[d["stage"]],
                contact_id=contact_ids[d["contact"]],
                title=d["title"],
                value=Decimal(d["value"]),
                currency="KWD",
                status="won" if d["stage"] == 3 else "open",
                assigned_to_user_id=user.id,
                expected_close_date=now + timedelta(days=30),
            )
            db.add(deal)
            print(f"  + Deal: {d['title']} ({d['value']} KWD)")

        # Create conversations with messages
        messages = [
            ("Hello! I'm interested in your office furniture catalog", "inbound"),
            ("Welcome! We have a great selection. What are you looking for?", "outbound"),
            ("I need 20 desks and chairs for our new office", "inbound"),
        ]
        for ci in range(5):
            conv = Conversation(
                company_id=company_id,
                contact_id=contact_ids[ci],
                status="open" if ci < 3 else "closed",
                channel="whatsapp",
                assigned_to_user_id=user.id,
                last_message_at=now - timedelta(hours=ci),
                last_message_preview=messages[0][0] if ci == 0 else f"Sample message from {CONTACTS[ci]['first_name']}",
                unread_count=1 if ci < 3 else 0,
            )
            db.add(conv)
            await db.flush()
            for j, (content, direction) in enumerate(messages):
                msg = Message(
                    company_id=company_id,
                    conversation_id=conv.id,
                    direction=direction,
                    sender_type="contact" if direction == "inbound" else "agent",
                    sender_id=user.id if direction == "outbound" else None,
                    message_type="text",
                    content=content,
                    delivery_status="delivered",
                )
                db.add(msg)
            print(f"  + Conversation with {CONTACTS[ci]['first_name']} ({len(messages)} msgs)")

        await db.commit()
        print(f"\nDemo seed complete! Login: owner@albaraka.kw / Demo123!")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_demo())
