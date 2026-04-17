"""AI engine API endpoints."""

from uuid import UUID

from fastapi import APIRouter

from app.dependencies import AuthUser, TenantDbSession
from app.schemas.ai import (
    AIAnalyzeRequest,
    AIAnalyzeResponse,
    AIContextResponse,
)
from app.services.ai.dialect_engine import DialectEngine

router = APIRouter()


@router.post("/analyze", response_model=AIAnalyzeResponse)
async def analyze_message(
    data: AIAnalyzeRequest,
    db: TenantDbSession,
    user: AuthUser,
):
    """Analyze a message for dialect, intent, and sentiment."""
    engine = DialectEngine(db, user.company_id)
    result = await engine.analyze_message(
        data.conversation_id, data.message_content, data.message_direction
    )
    # get_db dependency auto-commits after endpoint returns
    return AIAnalyzeResponse(**result)


@router.get("/context/{conversation_id}", response_model=AIContextResponse | None)
async def get_ai_context(
    conversation_id: UUID,
    db: TenantDbSession,
    user: AuthUser,
):
    """Get the AI context for a conversation."""
    engine = DialectEngine(db, user.company_id)
    ctx = await engine.get_context(conversation_id)
    if not ctx:
        return None
    return AIContextResponse(
        id=ctx.id,
        conversation_id=ctx.conversation_id,
        detected_dialect=ctx.detected_dialect,
        current_intent=ctx.current_intent,
        intent_confidence=ctx.intent_confidence,
        sentiment=ctx.sentiment,
        sentiment_score=ctx.sentiment_score,
        topic=ctx.topic,
        summary=ctx.summary,
        suggested_response=ctx.suggested_response,
        customer_insights=ctx.customer_insights,
        created_at=ctx.created_at,
        updated_at=ctx.updated_at,
    )


@router.post("/suggest/{conversation_id}")
async def suggest_response(
    conversation_id: UUID,
    db: TenantDbSession,
    user: AuthUser,
    instructions: str | None = None,
):
    """Generate a suggested response for a conversation."""
    engine = DialectEngine(db, user.company_id)
    response = await engine.generate_response(conversation_id, instructions)
    await db.commit()
    return {"suggested_response": response}
