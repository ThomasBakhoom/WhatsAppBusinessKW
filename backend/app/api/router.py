"""Master API router - all v1 routes (31 modules)."""

from fastapi import APIRouter

from app.api.v1 import (
    auth, contacts, tags, custom_fields, conversations, webhooks,
    automations, ai, pipelines, payments, shipping, landing_pages,
    analytics, compliance, campaigns, chatbots, users, media, export,
    channels, templates, catalog, surveys, qrcode,
    glossary, timeline, routing_analytics, instagram_webhooks,
    platform,
)

api_router = APIRouter()

# Auth
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])

# CRM
api_router.include_router(contacts.router, prefix="/contacts", tags=["Contacts"])
api_router.include_router(tags.router, prefix="/tags", tags=["Tags"])
api_router.include_router(custom_fields.router, prefix="/custom-fields", tags=["Custom Fields"])
api_router.include_router(timeline.router, prefix="/timeline", tags=["Contact Timeline"])

# Messaging
api_router.include_router(conversations.router, prefix="/conversations", tags=["Conversations"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
api_router.include_router(instagram_webhooks.router, prefix="/webhooks", tags=["Instagram Webhooks"])
api_router.include_router(templates.router, prefix="/templates", tags=["Templates"])

# Automation & AI
api_router.include_router(automations.router, prefix="/automations", tags=["Automations"])
api_router.include_router(chatbots.router, prefix="/chatbots", tags=["Chatbot Flows"])
api_router.include_router(ai.router, prefix="/ai", tags=["AI Engine"])
api_router.include_router(glossary.router, prefix="/glossary", tags=["Business Glossary"])

# Sales
api_router.include_router(pipelines.router, prefix="/pipelines", tags=["Pipelines"])

# Marketing
api_router.include_router(campaigns.router, prefix="/campaigns", tags=["Campaigns"])
api_router.include_router(landing_pages.router, prefix="/landing-pages", tags=["Landing Pages"])

# Commerce
api_router.include_router(catalog.router, prefix="/catalog", tags=["Product Catalog"])

# Payments & Shipping
api_router.include_router(payments.router, prefix="/payments", tags=["Payments"])
api_router.include_router(shipping.router, prefix="/shipping", tags=["Shipping"])

# Analytics & Compliance
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(routing_analytics.router, prefix="/analytics", tags=["Routing & Localization Analytics"])
api_router.include_router(compliance.router, prefix="/compliance", tags=["Compliance"])
api_router.include_router(surveys.router, prefix="/surveys", tags=["Surveys & CSAT"])

# Platform Admin (cross-tenant)
api_router.include_router(platform.router, prefix="/platform", tags=["Platform Admin"])

# Admin & Tools
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(channels.router, prefix="/channels", tags=["Channels"])
api_router.include_router(media.router, prefix="/media", tags=["Media"])
api_router.include_router(export.router, prefix="/export", tags=["Export"])
api_router.include_router(qrcode.router, prefix="/qr", tags=["QR Codes"])
