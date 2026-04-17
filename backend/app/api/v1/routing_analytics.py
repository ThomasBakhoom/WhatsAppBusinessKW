"""Routing and localization analytics endpoints."""

from fastapi import APIRouter, Query
from sqlalchemy import func, select
from app.dependencies import AuthUser, TenantDbSession
from app.models.routing_decision import RoutingDecision
from app.models.ai_context import AIConversationContext

router = APIRouter()


@router.get("/routing")
async def get_routing_analytics(db: TenantDbSession, user: AuthUser):
    """Routing continuity analytics - same-agent rate, method distribution."""
    total = await db.execute(
        select(func.count()).select_from(RoutingDecision).where(RoutingDecision.company_id == user.company_id)
    )
    total_count = total.scalar_one()

    # By method
    method_result = await db.execute(
        select(RoutingDecision.routing_method, func.count())
        .where(RoutingDecision.company_id == user.company_id)
        .group_by(RoutingDecision.routing_method)
    )
    methods = {r[0]: r[1] for r in method_result.all()}

    # Same-agent rate
    same_agent = methods.get("relationship", 0)
    same_agent_rate = round(same_agent / max(total_count, 1) * 100, 1)

    return {
        "total_routing_decisions": total_count,
        "same_agent_rate": same_agent_rate,
        "method_distribution": methods,
        "avg_score": None,
    }


@router.get("/localization")
async def get_localization_analytics(db: TenantDbSession, user: AuthUser):
    """NLP localization effectiveness - dialect distribution, confidence, code-switching."""
    # Dialect distribution
    dialect_result = await db.execute(
        select(AIConversationContext.detected_dialect, func.count())
        .where(AIConversationContext.company_id == user.company_id, AIConversationContext.detected_dialect.isnot(None))
        .group_by(AIConversationContext.detected_dialect)
    )
    dialects = {r[0]: r[1] for r in dialect_result.all()}

    # Average intent confidence
    conf_result = await db.execute(
        select(func.avg(AIConversationContext.intent_confidence))
        .where(AIConversationContext.company_id == user.company_id, AIConversationContext.intent_confidence.isnot(None))
    )
    avg_confidence = conf_result.scalar_one()

    # Sentiment distribution
    sent_result = await db.execute(
        select(AIConversationContext.sentiment, func.count())
        .where(AIConversationContext.company_id == user.company_id, AIConversationContext.sentiment.isnot(None))
        .group_by(AIConversationContext.sentiment)
    )
    sentiments = {r[0]: r[1] for r in sent_result.all()}

    total = sum(dialects.values()) or 1
    kuwaiti_pct = round(dialects.get("kuwaiti", 0) / total * 100, 1)

    return {
        "dialect_distribution": dialects,
        "kuwaiti_dialect_percentage": kuwaiti_pct,
        "avg_intent_confidence": round(float(avg_confidence), 3) if avg_confidence else None,
        "sentiment_distribution": sentiments,
        "total_analyzed": total,
    }
