"""Enhanced Kuwaiti dialect NLP engine - 100+ markers, code-switching, morphology.

Replaces the basic 6-marker fallback with a comprehensive rule engine
for environments without Claude API access.
"""

from typing import Any

# ═══════════════════════════════════════════════════════════════════════
# KUWAITI DIALECT MARKERS (100+ patterns)
# ═══════════════════════════════════════════════════════════════════════

KUWAITI_MARKERS = {
    # Greetings & Responses
    "شلونك", "شلونكم", "شلون", "هلا", "هلا والله", "يا هلا",
    "الله يسلمك", "مشكور", "تسلم", "يعطيك العافية", "الله يعافيك",
    "يا بعد قلبي", "يا بعد حيي", "يا بعد عمري", "حبيبي", "حبيبتي",
    # Pronouns & Demonstratives
    "شنو", "شنهو", "ليش", "وين", "هالحين", "ذحين", "إي", "لا والله",
    "جذي", "جي", "هالشكل", "هاك", "هاي", "هذيلا", "هذيله",
    # Intensifiers & Adverbs
    "وايد", "مرة", "بزاف", "أبد", "خوش", "زين", "ما شاء الله",
    "إن شاء الله", "إنشالله", "يالله", "خلاص", "بس", "يعني",
    "عاد", "بعدين", "توه", "توها", "لسه", "بالضبط",
    # Verbs (Kuwaiti conjugation patterns)
    "أبي", "أبغي", "تبي", "يبي", "نبي", "أروح", "تروح",
    "أسوي", "تسوي", "يسوي", "أدري", "تدري", "ما أدري",
    "أقدر", "ما أقدر", "لازم", "ما يحتاج", "خل", "خلنا",
    "طرش", "طرشلي", "طالع", "طالعة", "يطلع", "چا", "ييه",
    "اشتري", "شاري", "شريت", "بيع", "بعت",
    # Nouns (Kuwaiti-specific)
    "فلوس", "دراهم", "هدوم", "سيارة", "سيكل", "يهال", "عيال",
    "حريم", "رياييل", "ربع", "صاحب", "صاحبي", "بيت", "ديوانية",
    "غترة", "دشداشة", "بشت", "عقال", "مجبوس", "مچبوس",
    "طابون", "لقيمات", "جريش", "هريس", "رقاق",
    # Expressions
    "الله يبارك", "الله كريم", "ما عليك", "لا تشيل هم",
    "على كيفك", "عسى بس", "الحمد لله", "سبحان الله",
    "ما شاء الله عليك", "يزاك الله خير", "عساك على القوة",
    "مو كذا", "صح", "أكيد", "طبعا", "هيه",
    # Business/Commerce
    "كم السعر", "كم حقه", "كم يطلع", "بكم", "غالي",
    "رخيص", "خصم", "عرض", "توصيل", "فري", "مجاني",
}

KUWAITI_MARKER_SET = {m.lower() for m in KUWAITI_MARKERS}

# Gulf (non-Kuwaiti specific) markers
GULF_MARKERS = {
    "حياك", "حياكم", "يا زين", "ما قصرت", "تفضل",
    "حشا", "يا ربي", "خطير", "قوي", "زبون",
}

# ═══════════════════════════════════════════════════════════════════════
# CODE-SWITCHING DETECTION & PARSING
# ═══════════════════════════════════════════════════════════════════════

# Common English words embedded in Kuwaiti conversation
KUWAITI_ENGLISH_LOANWORDS = {
    "ok", "okay", "please", "thanks", "sorry", "hi", "hello", "bye",
    "delivery", "order", "online", "link", "offer", "sale", "discount",
    "size", "color", "brand", "model", "price", "free", "new",
    "account", "password", "email", "whatsapp", "instagram",
    "meeting", "appointment", "available", "confirm", "cancel",
    "location", "address", "shop", "mall", "parking",
}

# Transliterated Kuwaiti words (written in English letters)
KUWAITI_TRANSLITERATIONS = {
    "shlonik": "شلونك", "shlonkum": "شلونكم", "hala": "هلا",
    "wayed": "وايد", "inshallah": "إن شاء الله", "enshallah": "إن شاء الله",
    "mashallah": "ما شاء الله", "yallah": "يالله", "khalas": "خلاص",
    "habibi": "حبيبي", "habibti": "حبيبتي", "zain": "زين",
    "wallah": "والله", "abee": "أبي", "aby": "أبي",
    "sheno": "شنو", "laish": "ليش", "wain": "وين",
    "bas": "بس", "khosh": "خوش", "3adi": "عادي",
    "7abibi": "حبيبي", "ma3loom": "معلوم", "sa7": "صح",
    "9a7": "صح", "akeed": "أكيد", "mako": "ما كو",
}


def detect_code_switching(text: str) -> dict[str, Any]:
    """Analyze code-switching patterns in a message."""
    words = text.split()
    arabic_words = []
    english_words = []
    transliterated = []

    for word in words:
        clean = word.strip(".,!?()[]{}\"'؟،؛").lower()
        if not clean:
            continue

        # Check transliterations first
        if clean in KUWAITI_TRANSLITERATIONS:
            transliterated.append(clean)
            continue

        # Check if Arabic script
        has_arabic = any("\u0600" <= c <= "\u06FF" for c in clean)
        has_latin = any("a" <= c <= "z" for c in clean)

        if has_arabic and not has_latin:
            arabic_words.append(clean)
        elif has_latin and not has_arabic:
            english_words.append(clean)
        elif has_arabic and has_latin:
            # Mixed-script word (rare but possible)
            arabic_words.append(clean)

    total = len(arabic_words) + len(english_words) + len(transliterated)
    if total == 0:
        return {"is_code_switched": False, "pattern": "empty", "arabic_ratio": 0, "english_ratio": 0}

    arabic_ratio = (len(arabic_words) + len(transliterated)) / total
    english_ratio = len(english_words) / total

    is_code_switched = (arabic_ratio > 0.1 and english_ratio > 0.1) or len(transliterated) > 0

    if arabic_ratio > 0.8:
        pattern = "arabic_dominant"
    elif english_ratio > 0.8:
        pattern = "english_dominant"
    elif arabic_ratio > english_ratio:
        pattern = "arabic_primary_english_mixed"
    else:
        pattern = "english_primary_arabic_mixed"

    return {
        "is_code_switched": is_code_switched,
        "pattern": pattern,
        "arabic_ratio": round(arabic_ratio, 2),
        "english_ratio": round(english_ratio, 2),
        "arabic_words": len(arabic_words),
        "english_words": len(english_words),
        "transliterated_words": len(transliterated),
        "transliterations_found": [
            {"original": t, "arabic": KUWAITI_TRANSLITERATIONS[t]}
            for t in transliterated
        ],
    }


# ═══════════════════════════════════════════════════════════════════════
# ENHANCED INTENT CLASSIFICATION
# ═══════════════════════════════════════════════════════════════════════

INTENT_PATTERNS = {
    "pricing": {
        "ar": ["كم", "سعر", "بكم", "كم حقه", "كم يطلع", "غالي", "رخيص", "خصم", "عرض", "تخفيض", "كوبون"],
        "en": ["price", "cost", "how much", "discount", "offer", "sale", "deal", "coupon", "promo"],
    },
    "purchase": {
        "ar": ["أبي", "أبغي", "شراء", "اشتري", "أطلب", "طلب", "أخذ", "بشتري", "أبي أشتري", "حق"],
        "en": ["buy", "purchase", "order", "want", "get", "add to cart", "checkout", "pay"],
    },
    "support": {
        "ar": ["مساعدة", "مشكلة", "ما يشتغل", "خربان", "عطلان", "ما وصل", "تأخر", "رجعوا", "استبدال", "ترجيع"],
        "en": ["help", "problem", "issue", "broken", "not working", "return", "refund", "exchange", "complaint"],
    },
    "greeting": {
        "ar": ["هلا", "شلون", "شلونك", "مرحبا", "السلام", "سلام", "أهلا", "صباح الخير", "مساء الخير"],
        "en": ["hi", "hello", "hey", "good morning", "good evening", "howdy"],
    },
    "inquiry": {
        "ar": ["أبي أعرف", "استفسار", "سؤال", "معلومات", "تفاصيل", "شنو", "وين", "متى", "كيف"],
        "en": ["info", "information", "details", "tell me", "what", "where", "when", "how", "interested"],
    },
    "scheduling": {
        "ar": ["موعد", "حجز", "أحجز", "متى فاضي", "وقت", "جدول", "بكرا", "اليوم", "الحين"],
        "en": ["appointment", "schedule", "book", "reserve", "available", "time", "tomorrow", "today"],
    },
    "shipping": {
        "ar": ["وين طلبي", "شحن", "توصيل", "وصل", "تتبع", "تراكنق", "شحنة", "الطلب حقي"],
        "en": ["shipping", "delivery", "track", "tracking", "where is my order", "package", "arrived"],
    },
    "complaint": {
        "ar": ["شكوى", "زعلان", "مو راضي", "سيء", "أسوأ", "خدمة سيئة", "ما عجبني", "محد رد علي"],
        "en": ["complaint", "angry", "unhappy", "worst", "terrible", "bad service", "never again"],
    },
    "feedback": {
        "ar": ["شكرا", "ممتاز", "حلو", "عجبني", "أحسن", "رائع", "الله يعطيكم العافية"],
        "en": ["thank", "thanks", "great", "excellent", "amazing", "love it", "perfect", "awesome"],
    },
    "cancellation": {
        "ar": ["إلغاء", "ألغي", "ما أبي", "لا أبي", "رجعوا فلوسي", "استرجاع"],
        "en": ["cancel", "cancellation", "refund", "unsubscribe", "stop", "remove"],
    },
}


def classify_intent(text: str) -> tuple[str, float]:
    """Classify intent from text with confidence score."""
    lower = text.lower()
    scores: dict[str, float] = {}

    for intent, patterns in INTENT_PATTERNS.items():
        score = 0.0
        for kw in patterns["ar"]:
            if kw in lower:
                score += 1.5  # Arabic keywords weighted higher for Kuwait
        for kw in patterns["en"]:
            if kw in lower:
                score += 1.0
        # Check transliterations
        for translit, arabic in KUWAITI_TRANSLITERATIONS.items():
            if translit in lower and arabic in [kw for kw in patterns["ar"]]:
                score += 1.5
        scores[intent] = score

    if not scores or max(scores.values()) == 0:
        return "other", 0.3

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    confidence = min(scores[best] / max(total, 1) + 0.3, 0.95)
    return best, round(confidence, 2)


# ═══════════════════════════════════════════════════════════════════════
# ENHANCED DIALECT DETECTION
# ═══════════════════════════════════════════════════════════════════════

def detect_dialect(text: str) -> tuple[str, float]:
    """Detect dialect with higher accuracy using 100+ markers."""
    lower = text.lower()
    words = set(lower.split())

    # Count Arabic characters
    arabic_chars = sum(1 for c in text if "\u0600" <= c <= "\u06FF")
    total_chars = max(len(text.replace(" ", "")), 1)
    arabic_ratio = arabic_chars / total_chars

    # Check Kuwaiti markers (both in-text and word-level)
    kuwaiti_hits = 0
    for marker in KUWAITI_MARKER_SET:
        if marker in lower:
            kuwaiti_hits += 1

    # Check transliterations
    translit_hits = sum(1 for t in KUWAITI_TRANSLITERATIONS if t in lower)

    # Check Gulf markers
    gulf_hits = sum(1 for m in GULF_MARKERS if m in lower)

    # Code-switching analysis
    cs = detect_code_switching(text)

    # Decision logic
    if kuwaiti_hits >= 2 or (kuwaiti_hits >= 1 and arabic_ratio > 0.3):
        return "kuwaiti", min(0.5 + kuwaiti_hits * 0.1, 0.95)
    elif translit_hits >= 2:
        return "kuwaiti", min(0.5 + translit_hits * 0.1, 0.90)
    elif translit_hits >= 1 and cs["is_code_switched"]:
        return "kuwaiti", 0.65
    elif gulf_hits >= 1 and arabic_ratio > 0.3:
        return "gulf", min(0.5 + gulf_hits * 0.1, 0.85)
    elif cs["is_code_switched"]:
        return "mixed", 0.70
    elif arabic_ratio > 0.5:
        return "msa", 0.60
    elif arabic_ratio > 0.1:
        return "mixed", 0.55
    else:
        return "english", 0.80


# ═══════════════════════════════════════════════════════════════════════
# ENHANCED SENTIMENT
# ═══════════════════════════════════════════════════════════════════════

POSITIVE_WORDS = {
    "ar": ["شكرا", "ممتاز", "حلو", "زين", "خوش", "عجبني", "رائع", "جميل",
           "أحسن", "الله يعطيك العافية", "يزاك الله خير", "مشكور", "تسلم",
           "ما قصرت", "الله يبارك", "حبيت", "حبيته", "واو", "بالضبط"],
    "en": ["thank", "thanks", "great", "excellent", "amazing", "love", "perfect",
           "awesome", "wonderful", "good", "nice", "happy", "satisfied", "best", "fantastic"],
}

NEGATIVE_WORDS = {
    "ar": ["سيء", "سيئة", "أسوأ", "خربان", "عطلان", "زعلان", "مو راضي",
           "شكوى", "مشكلة", "ما عجبني", "محد رد", "تأخر", "غالي بزيادة",
           "نصب", "غش", "كذب", "ما يستاهل"],
    "en": ["bad", "terrible", "worst", "angry", "unhappy", "disappointed",
           "complaint", "problem", "issue", "horrible", "never", "hate", "scam", "fraud"],
}


def analyze_sentiment(text: str) -> tuple[str, float]:
    """Analyze sentiment with Kuwaiti-aware word lists."""
    lower = text.lower()
    pos = sum(1 for w in POSITIVE_WORDS["ar"] if w in lower) * 1.5
    pos += sum(1 for w in POSITIVE_WORDS["en"] if w in lower)
    neg = sum(1 for w in NEGATIVE_WORDS["ar"] if w in lower) * 1.5
    neg += sum(1 for w in NEGATIVE_WORDS["en"] if w in lower)

    if pos > neg + 1:
        return "positive", round(min(pos / (pos + neg + 1), 0.9), 2)
    elif neg > pos + 1:
        return "negative", round(-min(neg / (pos + neg + 1), 0.9), 2)
    elif pos > 0 and neg > 0:
        return "mixed", round((pos - neg) / (pos + neg + 1), 2)
    else:
        return "neutral", 0.0


# ═══════════════════════════════════════════════════════════════════════
# KUWAITI DIALECT RESPONSE TEMPLATES
# ═══════════════════════════════════════════════════════════════════════

RESPONSE_TEMPLATES = {
    "greeting": [
        "هلا والله! شلون أقدر أساعدك اليوم؟",
        "أهلين وسهلين! تفضل شنو تبي؟",
        "هلا فيك! كيف أقدر أخدمك؟",
    ],
    "pricing": [
        "تبي تعرف الأسعار؟ خلني أوريك التفاصيل",
        "إي أكيد! خلني أطرشلك الأسعار",
    ],
    "purchase": [
        "إن شاء الله! خلني أساعدك بالطلب",
        "ممتاز! تبي أسويلك الطلب الحين؟",
    ],
    "support": [
        "ما عليك هم، خلني أساعدك بالمشكلة",
        "إن شاء الله نحلها! شنو بالضبط المشكلة؟",
    ],
    "shipping": [
        "خلني أشيك على الطلب حقك",
        "إن شاء الله وصل! خلني أتابع لك",
    ],
    "feedback": [
        "الله يبارك فيك! نحن في خدمتك دايما",
        "يزاك الله خير! رأيك يهمنا وايد",
    ],
    "default": [
        "تفضل! كيف أقدر أساعدك؟",
        "هلا! شنو تبي؟",
    ],
}


def get_dialect_response(intent: str) -> str:
    """Get a culturally appropriate Kuwaiti dialect response template."""
    import random
    templates = RESPONSE_TEMPLATES.get(intent, RESPONSE_TEMPLATES["default"])
    return random.choice(templates)


# ═══════════════════════════════════════════════════════════════════════
# UNIFIED ANALYSIS FUNCTION
# ═══════════════════════════════════════════════════════════════════════

def enhanced_analyze(text: str) -> dict[str, Any]:
    """Full NLP analysis with enhanced Kuwaiti dialect support."""
    dialect, dialect_conf = detect_dialect(text)
    intent, intent_conf = classify_intent(text)
    sentiment, sentiment_score = analyze_sentiment(text)
    code_switch = detect_code_switching(text)
    suggested = get_dialect_response(intent) if dialect in ("kuwaiti", "gulf", "mixed") else None

    return {
        "dialect": dialect,
        "dialect_confidence": dialect_conf,
        "intent": intent,
        "intent_confidence": intent_conf,
        "sentiment": sentiment,
        "sentiment_score": sentiment_score,
        "topic": intent,
        "suggested_response": suggested,
        "code_switching": code_switch,
        "customer_insights": {
            "needs": intent,
            "urgency": "high" if intent in ("support", "complaint", "cancellation") else "medium",
            "language_preference": "arabic" if code_switch["arabic_ratio"] > 0.5 else "english" if code_switch["english_ratio"] > 0.8 else "mixed",
        },
    }
