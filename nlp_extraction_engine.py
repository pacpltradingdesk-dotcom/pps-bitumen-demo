"""
nlp_extraction_engine.py — NLP Entity Extraction Engine
========================================================
spaCy NER + HuggingFace sentiment analysis with regex fallbacks.
Works with ZERO new packages (falls back to regex-based extraction).
"""
from __future__ import annotations

import re
import logging
from typing import Optional

LOG = logging.getLogger("nlp_extraction")

# ── Optional dependency detection ────────────────────────────────────────────
_HAS_SPACY = False
_HAS_TRANSFORMERS = False
_spacy_nlp = None  # lazy loaded
_sentiment_pipeline = None  # lazy loaded
_zeroshot_pipeline = None  # lazy loaded

try:
    import spacy
    _HAS_SPACY = True
except Exception:
    pass

try:
    from transformers import pipeline as hf_pipeline
    _HAS_TRANSFORMERS = True
except Exception:
    pass


# ── Indian states and major cities for regex fallback ────────────────────────

_INDIAN_STATES = {
    "andhra pradesh", "arunachal pradesh", "assam", "bihar", "chhattisgarh",
    "goa", "gujarat", "haryana", "himachal pradesh", "jharkhand", "karnataka",
    "kerala", "madhya pradesh", "maharashtra", "manipur", "meghalaya",
    "mizoram", "nagaland", "odisha", "punjab", "rajasthan", "sikkim",
    "tamil nadu", "telangana", "tripura", "uttar pradesh", "uttarakhand",
    "west bengal", "delhi", "jammu and kashmir", "ladakh",
    "andaman and nicobar", "chandigarh", "dadra and nagar haveli",
    "daman and diu", "lakshadweep", "puducherry",
}

_MAJOR_CITIES = {
    "mumbai", "delhi", "bangalore", "bengaluru", "hyderabad", "ahmedabad",
    "chennai", "kolkata", "pune", "jaipur", "lucknow", "kanpur", "nagpur",
    "indore", "thane", "bhopal", "visakhapatnam", "vizag", "patna",
    "vadodara", "ghaziabad", "ludhiana", "agra", "nashik", "faridabad",
    "meerut", "rajkot", "varanasi", "srinagar", "aurangabad", "dhanbad",
    "amritsar", "allahabad", "ranchi", "howrah", "coimbatore", "jabalpur",
    "gwalior", "vijayawada", "jodhpur", "madurai", "raipur", "kochi",
    "chandigarh", "dehradun", "guwahati", "solapur", "hubli", "tiruchirappalli",
    "bareilly", "moradabad", "mysore", "tiruppur", "gurgaon", "noida",
    "kandla", "mangalore", "surat", "baroda",
}

_WORK_TYPES = {
    "highway", "expressway", "road", "bridge", "flyover", "overpass",
    "tunnel", "bypass", "widening", "resurfacing", "bitumen", "asphalt",
    "tar", "paving", "construction", "rehabilitation", "maintenance",
    "national highway", "state highway", "rural road", "pmgsy",
    "nhai", "nhidcl", "pwd", "morth", "bro",
}

_POSITIVE_KEYWORDS = {
    "approved", "sanctioned", "commence", "inaugurated", "completed",
    "awarded", "launched", "opened", "progress", "ahead of schedule",
    "on track", "increased", "growth", "boost", "expansion",
}

_NEGATIVE_KEYWORDS = {
    "delayed", "suspended", "cancelled", "stalled", "halted",
    "rejected", "failed", "collapse", "accident", "protest",
    "slow", "behind schedule", "cost overrun", "scam", "corruption",
}


# ═══════════════════════════════════════════════════════════════════════════════
# STATUS
# ═══════════════════════════════════════════════════════════════════════════════

def get_nlp_status() -> dict:
    """Returns which NLP libraries/models are available."""
    spacy_model = False
    if _HAS_SPACY:
        try:
            spacy.load("en_core_web_sm")
            spacy_model = True
        except Exception:
            pass

    return {
        "spacy_available": _HAS_SPACY,
        "spacy_model_loaded": spacy_model,
        "transformers_available": _HAS_TRANSFORMERS,
        "active_engine": "spacy" if spacy_model else "regex",
        "install_hints": {
            "spacy": "pip install spacy && python -m spacy download en_core_web_sm",
            "transformers": "pip install transformers torch",
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
# ENTITY EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════

def _get_spacy_nlp():
    """Lazy load spaCy model (cached after first load)."""
    global _spacy_nlp
    if _spacy_nlp is None and _HAS_SPACY:
        try:
            _spacy_nlp = spacy.load("en_core_web_sm")
        except Exception:
            pass
    return _spacy_nlp


def extract_entities(text: str) -> dict:
    """
    Extract named entities from text.
    Primary: spaCy NER. Fallback: regex patterns.
    Returns: {"states", "cities", "orgs", "amounts", "dates", "work_types", "engine"}
    """
    if not text or not text.strip():
        return {"states": [], "cities": [], "orgs": [], "amounts": [],
                "dates": [], "work_types": [], "engine": "none"}

    nlp = _get_spacy_nlp()
    if nlp is not None:
        return _extract_spacy(text, nlp)
    return _extract_regex(text)


def _extract_spacy(text: str, nlp) -> dict:
    """Extract entities using spaCy NER."""
    doc = nlp(text[:10000])  # limit to 10K chars

    states, cities, orgs, amounts, dates = [], [], [], [], []

    for ent in doc.ents:
        label = ent.label_
        val = ent.text.strip()
        if label == "GPE":
            val_lower = val.lower()
            if val_lower in _INDIAN_STATES:
                states.append(val)
            elif val_lower in _MAJOR_CITIES:
                cities.append(val)
            else:
                # Check partial match
                for s in _INDIAN_STATES:
                    if val_lower in s or s in val_lower:
                        states.append(val)
                        break
                else:
                    cities.append(val)
        elif label == "ORG":
            orgs.append(val)
        elif label == "MONEY":
            amounts.append(val)
        elif label == "DATE":
            dates.append(val)

    # Also extract work types via regex (spaCy doesn't have this label)
    work_types = _extract_work_types_regex(text)

    # Also try regex for Indian states that spaCy might miss
    regex_states = _extract_states_regex(text)
    for s in regex_states:
        if s not in states:
            states.append(s)

    return {
        "states": list(set(states)),
        "cities": list(set(cities)),
        "orgs": list(set(orgs)),
        "amounts": list(set(amounts)),
        "dates": list(set(dates)),
        "work_types": list(set(work_types)),
        "engine": "spacy",
    }


def _extract_regex(text: str) -> dict:
    """Regex-based entity extraction (always available)."""
    text_lower = text.lower()

    states = _extract_states_regex(text)
    cities = _extract_cities_regex(text)
    orgs = _extract_orgs_regex(text)
    amounts = _extract_amounts_regex(text)
    dates = _extract_dates_regex(text)
    work_types = _extract_work_types_regex(text)

    return {
        "states": states,
        "cities": cities,
        "orgs": orgs,
        "amounts": amounts,
        "dates": dates,
        "work_types": work_types,
        "engine": "regex",
    }


def _extract_states_regex(text: str) -> list:
    text_lower = text.lower()
    found = []
    for state in _INDIAN_STATES:
        if state in text_lower:
            found.append(state.title())
    return list(set(found))


def _extract_cities_regex(text: str) -> list:
    text_lower = text.lower()
    found = []
    for city in _MAJOR_CITIES:
        if city in text_lower:
            found.append(city.title())
    return list(set(found))


def _extract_orgs_regex(text: str) -> list:
    patterns = [
        r'\b(NHAI|NHIDCL|MoRTH|BRO|PWD|PMGSY)\b',
        r'\b(L&T|Larsen|Tata|Adani|GMR|IRB|Dilip Buildcon|Ashoka Buildcon)\b',
        r'\b(IOCL|BPCL|HPCL|CPCL|ONGC|GAIL)\b',
        r'\b(NITI Aayog|Ministry of Road|Ministry of Finance)\b',
    ]
    found = []
    for pat in patterns:
        found.extend(re.findall(pat, text, re.IGNORECASE))
    return list(set(found))


def _extract_amounts_regex(text: str) -> list:
    patterns = [
        r'(?:Rs\.?|INR|₹)\s*[\d,]+(?:\.\d+)?\s*(?:crore|lakh|cr|lac|billion|million)?',
        r'\$\s*[\d,]+(?:\.\d+)?\s*(?:billion|million|bn|mn)?',
        r'[\d,]+(?:\.\d+)?\s*(?:crore|lakh|cr|billion|million)\b',
    ]
    found = []
    for pat in patterns:
        found.extend(re.findall(pat, text, re.IGNORECASE))
    return list(set(found))


def _extract_dates_regex(text: str) -> list:
    patterns = [
        r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b',
        r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b',
        r'\b(?:FY|fy)\s*\d{2,4}(?:-\d{2,4})?\b',
        r'\bQ[1-4]\s*(?:FY)?\s*\d{2,4}\b',
    ]
    found = []
    for pat in patterns:
        found.extend(re.findall(pat, text, re.IGNORECASE))
    return list(set(found))


def _extract_work_types_regex(text: str) -> list:
    text_lower = text.lower()
    found = []
    for wt in _WORK_TYPES:
        if wt in text_lower:
            found.append(wt.title())
    return list(set(found))


# ═══════════════════════════════════════════════════════════════════════════════
# SENTIMENT ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

def analyze_sentiment(text: str, domain: str = "general") -> dict:
    """
    Sentiment analysis on text.
    Primary (financial): FinBERT → DistilBERT → keyword.
    Primary (general): DistilBERT → keyword.
    Returns: {"sentiment", "score", "engine"}
    """
    if not text or not text.strip():
        return {"sentiment": "neutral", "score": 0.5, "engine": "none"}

    # Tier 0: FinBERT for financial domain
    if domain == "financial":
        try:
            from finbert_engine import analyze_financial_sentiment
            result = analyze_financial_sentiment(text)
            if result.get("engine") == "finbert":
                return result
        except Exception:
            pass

    if _HAS_TRANSFORMERS:
        try:
            return _sentiment_transformers(text)
        except Exception as e:
            LOG.debug("Transformer sentiment failed: %s", e)

    return _sentiment_keywords(text)


def _sentiment_transformers(text: str) -> dict:
    """HuggingFace sentiment analysis."""
    global _sentiment_pipeline
    if _sentiment_pipeline is None:
        _sentiment_pipeline = hf_pipeline(
            "sentiment-analysis",
            model="distilbert-base-uncased-finetuned-sst-2-english",
            truncation=True,
            max_length=512,
        )
    result = _sentiment_pipeline(text[:512])[0]
    label = result["label"].lower()
    score = float(result["score"])
    sentiment = "positive" if label == "positive" else "negative"
    if score < 0.6:
        sentiment = "neutral"
    return {"sentiment": sentiment, "score": round(score, 3), "engine": "transformers"}


def _sentiment_keywords(text: str) -> dict:
    """Keyword-based sentiment analysis (always available)."""
    text_lower = text.lower()
    pos_count = sum(1 for kw in _POSITIVE_KEYWORDS if kw in text_lower)
    neg_count = sum(1 for kw in _NEGATIVE_KEYWORDS if kw in text_lower)
    total = pos_count + neg_count
    if total == 0:
        return {"sentiment": "neutral", "score": 0.5, "engine": "keyword"}
    ratio = pos_count / total
    if ratio > 0.6:
        sentiment = "positive"
    elif ratio < 0.4:
        sentiment = "negative"
    else:
        sentiment = "neutral"
    return {"sentiment": sentiment, "score": round(ratio, 3), "engine": "keyword"}


# ═══════════════════════════════════════════════════════════════════════════════
# NEWS CLASSIFICATION
# ═══════════════════════════════════════════════════════════════════════════════

def classify_news(text: str) -> dict:
    """
    Classify news article category.
    Primary: HuggingFace zero-shot. Fallback: keyword matching.
    Returns: {"category", "confidence", "engine"}
    """
    if not text or not text.strip():
        return {"category": "other", "confidence": 0.0, "engine": "none"}

    if _HAS_TRANSFORMERS:
        try:
            return _classify_zeroshot(text)
        except Exception as e:
            LOG.debug("Zero-shot classification failed: %s", e)

    return _classify_keywords(text)


def _classify_zeroshot(text: str) -> dict:
    """HuggingFace zero-shot classification."""
    global _zeroshot_pipeline
    if _zeroshot_pipeline is None:
        _zeroshot_pipeline = hf_pipeline(
            "zero-shot-classification",
            model="facebook/bart-large-mnli",
            truncation=True,
        )
    labels = ["infrastructure", "market", "policy", "weather", "trade"]
    result = _zeroshot_pipeline(text[:512], candidate_labels=labels)
    return {
        "category": result["labels"][0],
        "confidence": round(float(result["scores"][0]), 3),
        "engine": "transformers",
    }


def _classify_keywords(text: str) -> dict:
    """Keyword-based classification (always available)."""
    text_lower = text.lower()
    scores = {
        "infrastructure": 0,
        "market": 0,
        "policy": 0,
        "weather": 0,
        "trade": 0,
    }
    infra_kw = ["highway", "road", "bridge", "expressway", "nhai", "construction", "tender", "project"]
    market_kw = ["price", "crude", "brent", "opec", "refinery", "bitumen", "oil", "barrel"]
    policy_kw = ["government", "ministry", "budget", "policy", "regulation", "gst", "tax", "subsidy"]
    weather_kw = ["monsoon", "rain", "flood", "cyclone", "weather", "temperature", "storm"]
    trade_kw = ["import", "export", "trade", "customs", "tariff", "shipment", "cargo", "port"]

    for kw in infra_kw:
        if kw in text_lower:
            scores["infrastructure"] += 1
    for kw in market_kw:
        if kw in text_lower:
            scores["market"] += 1
    for kw in policy_kw:
        if kw in text_lower:
            scores["policy"] += 1
    for kw in weather_kw:
        if kw in text_lower:
            scores["weather"] += 1
    for kw in trade_kw:
        if kw in text_lower:
            scores["trade"] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    conf = scores[best] / total if total > 0 else 0
    return {"category": best if total > 0 else "other", "confidence": round(conf, 3), "engine": "keyword"}


# ═══════════════════════════════════════════════════════════════════════════════
# TENDER INFO EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════

def extract_tender_info(text: str) -> dict:
    """
    Extract structured tender data from text.
    Returns: {"org", "work_type", "location", "amount", "deadline", "engine"}
    """
    entities = extract_entities(text)
    amounts = _extract_amounts_regex(text)
    dates = _extract_dates_regex(text)

    return {
        "org": entities["orgs"][0] if entities["orgs"] else "",
        "work_type": entities["work_types"][0] if entities["work_types"] else "",
        "location": (entities["states"][0] if entities["states"]
                     else (entities["cities"][0] if entities["cities"] else "")),
        "amount": amounts[0] if amounts else "",
        "deadline": dates[0] if dates else "",
        "engine": entities["engine"],
    }
