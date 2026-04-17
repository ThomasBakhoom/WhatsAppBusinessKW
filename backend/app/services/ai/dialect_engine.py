"""Kuwaiti dialect AI engine - dialect detection, intent classification, sentiment analysis.

Uses Claude API for understanding Kuwaiti Arabic dialect and generating
culturally appropriate responses.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.ai_context import AIConversationContext

logger = structlog.get_logger()
settings = get_settings()

# System prompt for the Kuwaiti dialect AI
SYSTEM_PROMPT = """You are an AI assistant specialized in understanding Kuwaiti Arabic dialect (لهجة كويتية) and Gulf Arabic. You help businesses communicate with customers in Kuwait.

Your capabilities:
1. **Dialect Detection**: Identify whether text is in Kuwaiti dialect (كويتي), Gulf Arabic (خليجي), Modern Standard Arabic (فصحى), English, or mixed.
2. **Intent Classification**: Classify customer messages into: inquiry, purchase, support, complaint, greeting, scheduling, pricing, feedback, cancellation, other.
3. **Sentiment Analysis**: Detect sentiment as positive, negative, neutral, or mixed with a score from -1.0 to 1.0.
4. **Response Generation**: Generate culturally appropriate responses in the customer's dialect.

Key Kuwaiti dialect markers:
- "شلونك" (how are you) instead of "كيف حالك"
- "إي" (yes) instead of "نعم"
- "لا والله" (no, by God) as emphasis
- "حبيبي/حبيبتي" (my dear) as casual address
- "إنشاء الله" or "إن شاء الله" (God willing)
- "يا بعد قلبي" (dear to my heart)
- "وايد" (very/much) instead of "جداً"
- "شنو" (what) instead of "ماذا"
- "ليش" (why) instead of "لماذا"
- "هالحين" (now) instead of "الآن"

Always respond in JSON format when analyzing."""

ANALYSIS_PROMPT = """Analyze this customer message and return a JSON response:

Message: "{message}"
Direction: {direction}
Previous context: {context}

Return ONLY valid JSON with these fields:
{{
  "dialect": "kuwaiti" | "gulf" | "msa" | "english" | "mixed",
  "intent": "inquiry" | "purchase" | "support" | "complaint" | "greeting" | "scheduling" | "pricing" | "feedback" | "cancellation" | "other",
  "intent_confidence": 0.0-1.0,
  "sentiment": "positive" | "negative" | "neutral" | "mixed",
  "sentiment_score": -1.0 to 1.0,
  "topic": "brief topic description",
  "suggested_response": "natural response in the customer's dialect/language",
  "customer_insights": {{
    "needs": "what the customer needs",
    "urgency": "low" | "medium" | "high",
    "language_preference": "arabic" | "english" | "mixed"
  }}
}}"""


class DialectEngine:
    """AI engine for processing Kuwaiti dialect messages."""

    def __init__(self, db: AsyncSession, company_id: UUID):
        self.db = db
        self.company_id = company_id
        self.api_key = settings.anthropic_api_key

    async def analyze_message(
        self,
        conversation_id: UUID,
        message_content: str,
        direction: str = "inbound",
    ) -> dict[str, Any]:
        """Analyze a message using Claude API and update conversation context."""
        # Get existing context
        context = await self._get_or_create_context(conversation_id)
        context_summary = context.summary or "New conversation"

        if not self.api_key:
            # Use enhanced Kuwaiti NLP (100+ markers, code-switching, templates)
            from app.services.ai.kuwaiti_nlp import enhanced_analyze
            analysis = enhanced_analyze(message_content)
        else:
            # Call Claude API
            analysis = await self._call_claude(
                message_content, direction, context_summary
            )

        # Update context
        context.detected_dialect = analysis.get("dialect")
        context.current_intent = analysis.get("intent")
        context.intent_confidence = analysis.get("intent_confidence")
        context.sentiment = analysis.get("sentiment")
        context.sentiment_score = analysis.get("sentiment_score")
        context.topic = analysis.get("topic")
        context.suggested_response = analysis.get("suggested_response")
        context.customer_insights = analysis.get("customer_insights", {})

        # Append to context history
        history = list(context.context_history or [])
        history.append({
            "role": "customer" if direction == "inbound" else "agent",
            "content": message_content[:500],
            "analysis": {
                "intent": analysis.get("intent"),
                "sentiment": analysis.get("sentiment"),
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        # Keep last 20 messages in context
        context.context_history = history[-20:]

        # Update summary
        context.summary = f"Topic: {analysis.get('topic', 'unknown')}. " \
                          f"Intent: {analysis.get('intent', 'unknown')}. " \
                          f"Sentiment: {analysis.get('sentiment', 'unknown')}."

        await self.db.flush()

        logger.info(
            "ai_analysis_complete",
            conversation_id=str(conversation_id),
            dialect=analysis.get("dialect"),
            intent=analysis.get("intent"),
            sentiment=analysis.get("sentiment"),
        )

        return analysis

    async def get_context(self, conversation_id: UUID) -> AIConversationContext | None:
        """Get the AI context for a conversation."""
        result = await self.db.execute(
            select(AIConversationContext).where(
                AIConversationContext.conversation_id == conversation_id,
                AIConversationContext.company_id == self.company_id,
            )
        )
        return result.scalar_one_or_none()

    async def generate_response(
        self,
        conversation_id: UUID,
        agent_instructions: str | None = None,
    ) -> str | None:
        """Generate a suggested response for the agent."""
        context = await self.get_context(conversation_id)
        if not context:
            return None

        if not self.api_key:
            return context.suggested_response

        prompt = f"""Based on this conversation context, generate an appropriate response.

Dialect: {context.detected_dialect}
Intent: {context.current_intent}
Sentiment: {context.sentiment}
Topic: {context.topic}
Summary: {context.summary}

Recent messages:
{self._format_history(context.context_history)}

{f'Agent instructions: {agent_instructions}' if agent_instructions else ''}

Generate a natural, culturally appropriate response in the customer's language/dialect.
Return ONLY the response text, no JSON."""

        try:
            response = await self._raw_claude_call(prompt)
            context.suggested_response = response
            await self.db.flush()
            return response
        except Exception as e:
            logger.error("ai_response_gen_failed", error=str(e))
            return context.suggested_response

    # ── Private ───────────────────────────────────────────────────────────────

    async def _get_or_create_context(
        self, conversation_id: UUID
    ) -> AIConversationContext:
        result = await self.db.execute(
            select(AIConversationContext).where(
                AIConversationContext.conversation_id == conversation_id,
                AIConversationContext.company_id == self.company_id,
            )
        )
        ctx = result.scalar_one_or_none()
        if not ctx:
            ctx = AIConversationContext(
                company_id=self.company_id,
                conversation_id=conversation_id,
            )
            self.db.add(ctx)
            await self.db.flush()
        return ctx

    async def _call_claude(
        self, message: str, direction: str, context: str
    ) -> dict[str, Any]:
        """Call Claude API for message analysis."""
        import json

        prompt = ANALYSIS_PROMPT.format(
            message=message,
            direction=direction,
            context=context,
        )

        try:
            raw = await self._raw_claude_call(prompt)
            # Extract JSON from response
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("ai_json_parse_failed", raw_response=raw[:200])
            return self._fallback_analysis(message)
        except Exception as e:
            logger.error("ai_api_call_failed", error=str(e))
            return self._fallback_analysis(message)

    async def _raw_claude_call(self, prompt: str) -> str:
        """Make a raw call to the Claude API."""
        from app.config import get_settings

        api_url = get_settings().anthropic_api_url.rstrip("/")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{api_url}/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 1024,
                    "system": SYSTEM_PROMPT,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["content"][0]["text"]

    def _fallback_analysis(self, message: str) -> dict[str, Any]:
        """Rule-based fallback when Claude API is unavailable."""
        # Simple heuristics
        arabic_chars = sum(1 for c in message if "\u0600" <= c <= "\u06FF")
        total_chars = max(len(message.replace(" ", "")), 1)
        arabic_ratio = arabic_chars / total_chars

        # Dialect detection
        kuwaiti_markers = ["شلون", "وايد", "شنو", "ليش", "هالحين", "إي"]
        has_kuwaiti = any(m in message for m in kuwaiti_markers)

        if arabic_ratio > 0.5:
            dialect = "kuwaiti" if has_kuwaiti else "msa"
        elif arabic_ratio > 0.1:
            dialect = "mixed"
        else:
            dialect = "english"

        # Intent detection. Order matters: stronger signals win, and a
        # problem/complaint ALWAYS beats a purchase signal even when "order"
        # appears in the message ("problem with my order" is support, not
        # buying intent).
        intent = "other"
        lower = message.lower()
        if any(w in lower for w in ["price", "كم", "سعر", "cost", "how much"]):
            intent = "pricing"
        elif any(w in lower for w in ["help", "مساعدة", "problem", "مشكلة", "issue", "broken", "doesn't work"]):
            intent = "support"
        elif any(w in lower for w in ["buy", "شراء", "أبي", "أبغي", "purchase", "order"]):
            intent = "purchase"
        elif any(w in lower for w in ["hi", "hello", "مرحبا", "السلام", "هلا", "شلون"]):
            intent = "greeting"
        elif any(w in lower for w in ["interested", "مهتم", "info", "معلومات"]):
            intent = "inquiry"

        # Sentiment
        positive_words = ["شكرا", "thanks", "great", "حلو", "ممتاز", "good", "love", "interested"]
        negative_words = ["bad", "سيء", "problem", "مشكلة", "complaint", "شكوى", "angry"]

        pos = sum(1 for w in positive_words if w in lower)
        neg = sum(1 for w in negative_words if w in lower)

        if pos > neg:
            sentiment, score = "positive", 0.5
        elif neg > pos:
            sentiment, score = "negative", -0.5
        else:
            sentiment, score = "neutral", 0.0

        return {
            "dialect": dialect,
            "intent": intent,
            "intent_confidence": 0.6,
            "sentiment": sentiment,
            "sentiment_score": score,
            "topic": intent,
            "suggested_response": None,
            "customer_insights": {
                "needs": "unknown",
                "urgency": "medium",
                "language_preference": "arabic" if arabic_ratio > 0.5 else "english",
            },
        }

    def _format_history(self, history: list) -> str:
        lines = []
        for entry in (history or [])[-5:]:
            role = entry.get("role", "?")
            content = entry.get("content", "")[:100]
            lines.append(f"[{role}]: {content}")
        return "\n".join(lines) if lines else "No history"
