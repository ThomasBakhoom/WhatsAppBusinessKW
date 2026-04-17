"""Unit tests for AI dialect engine fallback mode."""

import pytest
from app.services.ai.dialect_engine import DialectEngine


class TestDialectFallback:
    """Test the rule-based fallback engine (no API key needed)."""

    def _engine(self):
        # Create engine without DB/company for pure fallback testing
        return DialectEngine.__new__(DialectEngine)

    def test_detect_english(self):
        e = self._engine()
        result = e._fallback_analysis("Hello, I want to buy your product")
        assert result["dialect"] == "english"

    def test_detect_kuwaiti(self):
        e = self._engine()
        result = e._fallback_analysis("شلونكم يا حبايبي؟ أبي أعرف وايد عن المنتجات")
        assert result["dialect"] == "kuwaiti"

    def test_detect_msa(self):
        e = self._engine()
        result = e._fallback_analysis("مرحبا، أريد الاستفسار عن الأسعار")
        assert result["dialect"] == "msa"

    def test_detect_mixed(self):
        e = self._engine()
        result = e._fallback_analysis("Hi, أبي أسأل about the product")
        assert result["dialect"] == "mixed"

    def test_intent_pricing(self):
        e = self._engine()
        result = e._fallback_analysis("How much does it cost?")
        assert result["intent"] == "pricing"

    def test_intent_purchase(self):
        e = self._engine()
        result = e._fallback_analysis("I want to buy this product")
        assert result["intent"] == "purchase"

    def test_intent_support(self):
        e = self._engine()
        result = e._fallback_analysis("I have a problem with my order")
        assert result["intent"] == "support"

    def test_intent_greeting(self):
        e = self._engine()
        result = e._fallback_analysis("Hello!")
        assert result["intent"] == "greeting"

    def test_intent_greeting_arabic(self):
        e = self._engine()
        result = e._fallback_analysis("هلا شلونك")
        assert result["intent"] == "greeting"

    def test_sentiment_positive(self):
        e = self._engine()
        result = e._fallback_analysis("Thanks so much, great service!")
        assert result["sentiment"] == "positive"
        assert result["sentiment_score"] > 0

    def test_sentiment_negative(self):
        e = self._engine()
        result = e._fallback_analysis("This is really bad, I have a complaint")
        assert result["sentiment"] == "negative"
        assert result["sentiment_score"] < 0

    def test_sentiment_neutral(self):
        e = self._engine()
        result = e._fallback_analysis("Can you tell me your address?")
        assert result["sentiment"] == "neutral"

    def test_customer_insights_arabic(self):
        e = self._engine()
        result = e._fallback_analysis("أبي أعرف عن المنتجات حقتكم")
        assert result["customer_insights"]["language_preference"] == "arabic"

    def test_customer_insights_english(self):
        e = self._engine()
        result = e._fallback_analysis("What products do you have?")
        assert result["customer_insights"]["language_preference"] == "english"
