"""
finbert_engine.py — Financial-Domain Sentiment Analysis
========================================================
FinBERT (ProsusAI/finbert) for financial text sentiment.
Fallback: DistilBERT (nlp_extraction_engine) → keyword-based.
"""
from __future__ import annotations

import logging
from typing import Optional

LOG = logging.getLogger("finbert_engine")

# ── Optional dependency detection ────────────────────────────────────────────
_HAS_TRANSFORMERS = False
_HAS_TORCH = False
_finbert_pipeline = None

try:
    import transformers
    _HAS_TRANSFORMERS = True
except Exception:
    pass

try:
    import torch
    _HAS_TORCH = True
except Exception:
    pass

_HAS_VADER = False
_vader_analyzer = None

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    _HAS_VADER = True
except ImportError:
    pass


# ═══════════════════════════════════════════════════════════════════════════════
# STATUS
# ═══════════════════════════════════════════════════════════════════════════════

def get_finbert_status() -> dict:
    """Returns FinBERT model availability and active tier."""
    if _HAS_TRANSFORMERS and _HAS_TORCH:
        active = "finbert"
    elif _HAS_VADER:
        active = "vader"
    else:
        active = "keyword"
    return {
        "transformers_available": _HAS_TRANSFORMERS,
        "torch_available": _HAS_TORCH,
        "vader_available": _HAS_VADER,
        "finbert_ready": _HAS_TRANSFORMERS and _HAS_TORCH,
        "active_engine": active,
        "tier_chain": "FinBERT → DistilBERT → VADER → Keyword",
        "install_hints": {
            "transformers": "pip install transformers",
            "torch": "pip install torch",
            "vader": "pip install vaderSentiment",
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
# MODEL LOADING (lazy)
# ═══════════════════════════════════════════════════════════════════════════════

def _get_finbert_pipeline():
    """Lazy-load FinBERT pipeline. Cached after first call."""
    global _finbert_pipeline
    if _finbert_pipeline is not None:
        return _finbert_pipeline

    if not _HAS_TRANSFORMERS or not _HAS_TORCH:
        return None

    try:
        from transformers import pipeline
        _finbert_pipeline = pipeline(
            "sentiment-analysis",
            model="ProsusAI/finbert",
            tokenizer="ProsusAI/finbert",
            top_k=None,
        )
        LOG.info("FinBERT model loaded successfully")
        return _finbert_pipeline
    except Exception as e:
        LOG.warning("FinBERT load failed: %s", e)
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# VADER SENTIMENT (Tier 3 — lightweight, no model download)
# ═══════════════════════════════════════════════════════════════════════════════

def _get_vader():
    """Lazy-load VADER analyzer."""
    global _vader_analyzer
    if _vader_analyzer is not None:
        return _vader_analyzer
    if not _HAS_VADER:
        return None
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        _vader_analyzer = SentimentIntensityAnalyzer()
        return _vader_analyzer
    except Exception:
        return None


def _vader_sentiment(text: str) -> Optional[dict]:
    """VADER sentiment analysis. Returns None if VADER not available."""
    analyzer = _get_vader()
    if analyzer is None:
        return None
    try:
        scores = analyzer.polarity_scores(text)
        compound = scores["compound"]
        if compound >= 0.05:
            sentiment = "positive"
            score = min(0.95, 0.5 + compound * 0.5)
        elif compound <= -0.05:
            sentiment = "negative"
            score = min(0.95, 0.5 + abs(compound) * 0.5)
        else:
            sentiment = "neutral"
            score = 0.5
        return {
            "sentiment": sentiment,
            "score": round(score, 3),
            "engine": "vader",
            "compound": round(compound, 3),
        }
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# KEYWORD FALLBACK
# ═══════════════════════════════════════════════════════════════════════════════

_POSITIVE_WORDS = {
    "surge", "rally", "gain", "growth", "profit", "rise", "increase", "boom",
    "bullish", "recovery", "expansion", "upgrade", "strong", "higher", "improve",
    "outperform", "optimistic", "upbeat", "positive", "demand", "invest",
}

_NEGATIVE_WORDS = {
    "crash", "fall", "drop", "decline", "loss", "slump", "downturn", "bearish",
    "recession", "crisis", "risk", "cut", "lower", "weak", "concern", "worry",
    "plunge", "sell-off", "negative", "sanctions", "threat", "uncertainty",
}


def _keyword_sentiment(text: str) -> dict:
    """Keyword-based financial sentiment fallback."""
    words = set(text.lower().split())
    pos = len(words & _POSITIVE_WORDS)
    neg = len(words & _NEGATIVE_WORDS)

    if pos > neg:
        sentiment = "positive"
        score = min(0.95, 0.5 + (pos - neg) * 0.1)
    elif neg > pos:
        sentiment = "negative"
        score = min(0.95, 0.5 + (neg - pos) * 0.1)
    else:
        sentiment = "neutral"
        score = 0.5

    return {"sentiment": sentiment, "score": round(score, 3), "engine": "keyword"}


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLE TEXT ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

def analyze_financial_sentiment(text: str) -> dict:
    """
    FinBERT sentiment: positive/negative/neutral with financial context.
    Fallback: DistilBERT (nlp_extraction_engine) → keyword-based.
    """
    if not text or not text.strip():
        return {"sentiment": "neutral", "score": 0.5, "engine": "none"}

    # Tier 1: FinBERT
    pipe = _get_finbert_pipeline()
    if pipe is not None:
        try:
            # Truncate to model max length
            truncated = text[:512]
            results = pipe(truncated)
            if isinstance(results, list) and results:
                # results is list of list of dicts: [[{label, score}, ...]]
                if isinstance(results[0], list):
                    results = results[0]
                best = max(results, key=lambda x: x["score"])
                return {
                    "sentiment": best["label"].lower(),
                    "score": round(best["score"], 3),
                    "engine": "finbert",
                    "all_scores": {r["label"].lower(): round(r["score"], 3) for r in results},
                }
        except Exception as e:
            LOG.debug("FinBERT analysis failed: %s", e)

    # Tier 2: DistilBERT via nlp_extraction_engine
    try:
        from nlp_extraction_engine import analyze_sentiment
        result = analyze_sentiment(text)
        if result.get("engine") != "keyword":
            return {
                "sentiment": result["sentiment"],
                "score": result.get("score", 0.5),
                "engine": result.get("engine", "distilbert"),
            }
    except Exception:
        pass

    # Tier 3: VADER sentiment (lightweight, no model download needed)
    vader_result = _vader_sentiment(text)
    if vader_result:
        return vader_result

    # Tier 4: Keyword fallback
    return _keyword_sentiment(text)


# ═══════════════════════════════════════════════════════════════════════════════
# BATCH ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

def analyze_batch(texts: list[str]) -> list[dict]:
    """Batch sentiment analysis for efficiency."""
    if not texts:
        return []

    # Tier 1: FinBERT batch
    pipe = _get_finbert_pipeline()
    if pipe is not None:
        try:
            truncated = [t[:512] for t in texts]
            all_results = pipe(truncated)
            batch_output = []
            for results in all_results:
                if isinstance(results, list):
                    best = max(results, key=lambda x: x["score"])
                    batch_output.append({
                        "sentiment": best["label"].lower(),
                        "score": round(best["score"], 3),
                        "engine": "finbert",
                    })
                else:
                    batch_output.append(_keyword_sentiment(truncated[len(batch_output)]))
            return batch_output
        except Exception as e:
            LOG.debug("FinBERT batch failed: %s", e)

    # Fallback: process individually
    return [analyze_financial_sentiment(t) for t in texts]


# ═══════════════════════════════════════════════════════════════════════════════
# MARKET SENTIMENT AGGREGATION
# ═══════════════════════════════════════════════════════════════════════════════

def get_market_sentiment(articles: list[dict] | None = None) -> dict:
    """
    Aggregate market sentiment from multiple articles.
    Returns: {"overall": str, "score": float, "breakdown": dict, "trend": str}
    """
    if articles is None:
        articles = _load_default_articles()

    if not articles:
        return {
            "overall": "neutral",
            "score": 0.5,
            "breakdown": {"positive": 0, "negative": 0, "neutral": 0},
            "trend": "stable",
            "article_count": 0,
            "engine": "none",
        }

    texts = [
        f"{a.get('title', '')}. {a.get('summary', a.get('description', ''))}"
        for a in articles
    ]
    texts = [t for t in texts if t.strip(". ")]

    results = analyze_batch(texts) if texts else []

    breakdown = {"positive": 0, "negative": 0, "neutral": 0}
    total_score = 0.0
    for r in results:
        sentiment = r.get("sentiment", "neutral")
        breakdown[sentiment] = breakdown.get(sentiment, 0) + 1
        if sentiment == "positive":
            total_score += r.get("score", 0.5)
        elif sentiment == "negative":
            total_score -= r.get("score", 0.5)

    count = len(results) or 1
    avg_score = total_score / count

    if avg_score > 0.15:
        overall = "positive"
        trend = "bullish"
    elif avg_score < -0.15:
        overall = "negative"
        trend = "bearish"
    else:
        overall = "neutral"
        trend = "stable"

    return {
        "overall": overall,
        "score": round(0.5 + avg_score * 0.5, 3),  # Normalize to 0-1
        "breakdown": breakdown,
        "trend": trend,
        "article_count": len(results),
        "engine": results[0].get("engine", "keyword") if results else "none",
    }


def _load_default_articles() -> list[dict]:
    """Load articles from news_data/articles.json."""
    try:
        from pathlib import Path
        path = Path(__file__).resolve().parent / "news_data" / "articles.json"
        if path.exists():
            import json
            data = json.loads(path.read_text(encoding="utf-8"))
            return data[-50:] if isinstance(data, list) else []
    except Exception:
        pass
    return []
