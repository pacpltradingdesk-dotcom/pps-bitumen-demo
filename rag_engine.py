"""
rag_engine.py — Retrieval-Augmented Generation Engine
======================================================
Connects LLM to dashboard data via FAISS semantic search / TF-IDF fallback.
Fallback chain: FAISS → TF-IDF (sklearn) → keyword match.
"""
from __future__ import annotations

import json
import logging
import os
import pickle
import re
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import numpy as np

IST = timezone(timedelta(hours=5, minutes=30))
BASE = Path(__file__).resolve().parent
INDEX_DIR = BASE / "rag_index"
INDEX_DIR.mkdir(exist_ok=True)

LOG = logging.getLogger("rag_engine")

# ── Optional dependency detection ────────────────────────────────────────────
_HAS_FAISS = False
_HAS_SENTENCE_TRANSFORMERS = False
_HAS_SKLEARN = False

try:
    import faiss
    _HAS_FAISS = True
except Exception:
    pass

try:
    from sentence_transformers import SentenceTransformer
    _HAS_SENTENCE_TRANSFORMERS = True
except Exception:
    pass

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    _HAS_SKLEARN = True
except Exception:
    pass

# ── Lazy model cache ─────────────────────────────────────────────────────────
_embedding_model = None
_faiss_index = None
_tfidf_vectorizer = None
_tfidf_matrix = None
_documents: list[dict] = []
_index_built = False


def _now_ist() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")


def _load_json(path: Path) -> list | dict:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return []


# ═══════════════════════════════════════════════════════════════════════════════
# STATUS
# ═══════════════════════════════════════════════════════════════════════════════

def get_rag_status() -> dict:
    """Returns FAISS/TF-IDF availability and index freshness."""
    index_file = INDEX_DIR / "faiss_index.bin"
    tfidf_file = INDEX_DIR / "tfidf_index.pkl"

    return {
        "faiss_available": _HAS_FAISS,
        "sentence_transformers_available": _HAS_SENTENCE_TRANSFORMERS,
        "sklearn_tfidf_available": _HAS_SKLEARN,
        "active_engine": (
            "faiss" if _HAS_FAISS and _HAS_SENTENCE_TRANSFORMERS else
            "tfidf" if _HAS_SKLEARN else
            "keyword"
        ),
        "index_built": _index_built,
        "documents_indexed": len(_documents),
        "faiss_index_exists": index_file.exists(),
        "tfidf_index_exists": tfidf_file.exists(),
        "install_hints": {
            "faiss": "pip install faiss-cpu",
            "sentence_transformers": "pip install sentence-transformers",
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
# DOCUMENT LOADING
# ═══════════════════════════════════════════════════════════════════════════════

def _load_documents() -> list[dict]:
    """Load documents from all dashboard data sources for indexing."""
    docs = []

    # 1. News articles
    try:
        articles = _load_json(BASE / "news_data" / "articles.json")
        if isinstance(articles, list):
            for a in articles[-200:]:
                text = f"{a.get('title', '')}. {a.get('summary', a.get('description', ''))}"
                if text.strip(". "):
                    docs.append({
                        "text": text.strip(),
                        "source": "news",
                        "metadata": {"title": a.get("title", ""), "date": a.get("published_at", "")},
                    })
    except Exception:
        pass

    # 2. Infra demand scores
    try:
        from database import _get_conn
        conn = _get_conn()
        rows = conn.execute(
            "SELECT state, composite_score, tender_score, budget_score, score_date "
            "FROM infra_demand_scores ORDER BY score_date DESC LIMIT 200"
        ).fetchall()
        cols = [d[0] for d in conn.description]
        conn.close()
        for row in rows:
            r = dict(zip(cols, row))
            text = (f"Infra demand in {r.get('state', '')}: composite score {r.get('composite_score', 0)}, "
                    f"tender score {r.get('tender_score', 0)}, budget score {r.get('budget_score', 0)} "
                    f"on {r.get('score_date', '')}")
            docs.append({"text": text, "source": "infra_demand", "metadata": r})
    except Exception:
        pass

    # 3. News feed (tbl_news_feed.json)
    try:
        news = _load_json(BASE / "tbl_news_feed.json")
        if isinstance(news, list):
            for n in news[-100:]:
                text = f"{n.get('title', '')}. {n.get('summary', '')}"
                if text.strip(". "):
                    docs.append({
                        "text": text.strip(),
                        "source": "news_feed",
                        "metadata": {"title": n.get("title", "")},
                    })
    except Exception:
        pass

    # 4. Crude price context
    try:
        crude = _load_json(BASE / "tbl_crude_prices.json")
        if isinstance(crude, list) and crude:
            latest = crude[-1] if crude else {}
            brent = latest.get("brent_usd", "N/A")
            wti = latest.get("wti_usd", "N/A")
            text = f"Latest crude oil prices: Brent ${brent}/bbl, WTI ${wti}/bbl"
            docs.append({"text": text, "source": "crude_prices", "metadata": latest})
    except Exception:
        pass

    # 5. FX rates
    try:
        fx = _load_json(BASE / "tbl_fx_rates.json")
        if isinstance(fx, list) and fx:
            latest = fx[-1] if fx else {}
            usd_inr = latest.get("USD_INR", latest.get("usd_inr", "N/A"))
            text = f"Latest FX rate: USD/INR = {usd_inr}"
            docs.append({"text": text, "source": "fx_rates", "metadata": latest})
    except Exception:
        pass

    # 6. CRM deals
    try:
        from database import _get_conn
        conn = _get_conn()
        rows = conn.execute(
            "SELECT customer_name, city, grade, quantity_mt, status, created_at "
            "FROM deals ORDER BY created_at DESC LIMIT 100"
        ).fetchall()
        cols = [d[0] for d in conn.description]
        conn.close()
        for row in rows:
            r = dict(zip(cols, row))
            text = (f"Deal with {r.get('customer_name', 'Unknown')} in {r.get('city', '')}: "
                    f"{r.get('quantity_mt', 0)} MT of {r.get('grade', 'VG30')}, "
                    f"status: {r.get('status', 'unknown')}")
            docs.append({"text": text, "source": "deals", "metadata": r})
    except Exception:
        pass

    return docs


# ═══════════════════════════════════════════════════════════════════════════════
# INDEX BUILDING
# ═══════════════════════════════════════════════════════════════════════════════

def build_index(documents: list[dict] | None = None) -> dict:
    """Build search index from dashboard data."""
    global _documents, _faiss_index, _tfidf_vectorizer, _tfidf_matrix
    global _embedding_model, _index_built

    if documents is None:
        documents = _load_documents()

    if not documents:
        return {"indexed": 0, "engine": "none", "error": "No documents found"}

    _documents = documents
    texts = [d["text"] for d in documents]

    # Tier 1: FAISS + Sentence Transformers
    if _HAS_FAISS and _HAS_SENTENCE_TRANSFORMERS:
        try:
            if _embedding_model is None:
                _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
            embeddings = _embedding_model.encode(texts, show_progress_bar=False)
            embeddings = np.array(embeddings, dtype="float32")

            dim = embeddings.shape[1]
            _faiss_index = faiss.IndexFlatIP(dim)  # Inner product (cosine after normalize)
            faiss.normalize_L2(embeddings)
            _faiss_index.add(embeddings)

            # Save index
            faiss.write_index(_faiss_index, str(INDEX_DIR / "faiss_index.bin"))
            _save_documents(documents)
            _index_built = True

            LOG.info("FAISS index built with %d documents", len(documents))
            return {"indexed": len(documents), "engine": "faiss"}
        except Exception as e:
            LOG.warning("FAISS build failed, falling back to TF-IDF: %s", e)

    # Tier 2: TF-IDF (sklearn)
    if _HAS_SKLEARN:
        try:
            _tfidf_vectorizer = TfidfVectorizer(
                max_features=5000,
                stop_words="english",
                ngram_range=(1, 2),
            )
            _tfidf_matrix = _tfidf_vectorizer.fit_transform(texts)

            # Save
            with open(INDEX_DIR / "tfidf_index.pkl", "wb") as f:
                pickle.dump({"vectorizer": _tfidf_vectorizer, "matrix": _tfidf_matrix}, f)
            _save_documents(documents)
            _index_built = True

            LOG.info("TF-IDF index built with %d documents", len(documents))
            return {"indexed": len(documents), "engine": "tfidf"}
        except Exception as e:
            LOG.warning("TF-IDF build failed: %s", e)

    # Tier 3: Just store documents for keyword search
    _save_documents(documents)
    _index_built = True
    return {"indexed": len(documents), "engine": "keyword"}


def _save_documents(documents: list[dict]) -> None:
    """Save documents metadata to disk."""
    try:
        with open(INDEX_DIR / "documents.json", "w", encoding="utf-8") as f:
            json.dump(documents, f, ensure_ascii=False, default=str)
    except Exception:
        pass


def _load_cached_documents() -> list[dict]:
    """Load previously indexed documents from disk."""
    try:
        path = INDEX_DIR / "documents.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return []


# ═══════════════════════════════════════════════════════════════════════════════
# SEARCH
# ═══════════════════════════════════════════════════════════════════════════════

def search(query: str, top_k: int = 5) -> list[dict]:
    """
    Hybrid search across indexed documents.
    Pipeline: synonym expand → fetch 3x candidates → hybrid rank (RRF) → rerank → top-k.
    Fallback chain: FAISS → TF-IDF → keyword match.
    """
    global _documents, _faiss_index, _tfidf_vectorizer, _tfidf_matrix, _embedding_model

    # Ensure documents loaded
    if not _documents:
        _documents = _load_cached_documents()
    if not _documents:
        build_index()
    if not _documents:
        return []

    texts = [d["text"] for d in _documents]

    # Step 1: Expand query with synonyms
    expanded_query = _expand_query(query)

    # Step 2: Get candidates from multiple sources (3x top_k for diversity)
    fetch_k = min(top_k * 3, len(_documents))
    faiss_results = []
    tfidf_results = []

    # Dense retrieval: FAISS
    if _HAS_FAISS and _HAS_SENTENCE_TRANSFORMERS:
        try:
            if _faiss_index is None:
                idx_path = INDEX_DIR / "faiss_index.bin"
                if idx_path.exists():
                    _faiss_index = faiss.read_index(str(idx_path))
            if _embedding_model is None:
                _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

            if _faiss_index is not None:
                q_embedding = _embedding_model.encode([expanded_query])
                q_embedding = np.array(q_embedding, dtype="float32")
                faiss.normalize_L2(q_embedding)

                scores, indices = _faiss_index.search(q_embedding, min(fetch_k, _faiss_index.ntotal))
                for score, idx in zip(scores[0], indices[0]):
                    if idx < 0 or idx >= len(_documents):
                        continue
                    faiss_results.append((int(idx), float(score)))
        except Exception as e:
            LOG.debug("FAISS search failed: %s", e)

    # Sparse retrieval: TF-IDF
    if _HAS_SKLEARN:
        try:
            if _tfidf_vectorizer is None or _tfidf_matrix is None:
                pkl_path = INDEX_DIR / "tfidf_index.pkl"
                if pkl_path.exists():
                    with open(pkl_path, "rb") as f:
                        data = pickle.load(f)
                        _tfidf_vectorizer = data["vectorizer"]
                        _tfidf_matrix = data["matrix"]

            if _tfidf_vectorizer is not None and _tfidf_matrix is not None:
                q_vec = _tfidf_vectorizer.transform([expanded_query])
                similarities = cosine_similarity(q_vec, _tfidf_matrix).flatten()
                top_indices = similarities.argsort()[-fetch_k:][::-1]
                for idx in top_indices:
                    if similarities[idx] >= 0.01:
                        tfidf_results.append((int(idx), float(similarities[idx])))
        except Exception as e:
            LOG.debug("TF-IDF search failed: %s", e)

    # Step 3: Hybrid ranking via Reciprocal Rank Fusion
    if faiss_results and tfidf_results:
        merged = _reciprocal_rank_fusion(faiss_results, tfidf_results, k=60)
        results = []
        for idx, score in merged[:top_k]:
            doc = _documents[idx]
            results.append({
                "text": doc["text"],
                "source": doc.get("source", "unknown"),
                "score": round(score, 3),
                "metadata": doc.get("metadata", {}),
                "engine": "hybrid(faiss+tfidf)",
            })
        return _rerank(results, query)

    # Single-source fallback
    if faiss_results:
        results = []
        for idx, score in faiss_results[:top_k]:
            doc = _documents[idx]
            results.append({
                "text": doc["text"], "source": doc.get("source", "unknown"),
                "score": round(score, 3), "metadata": doc.get("metadata", {}),
                "engine": "faiss",
            })
        return _rerank(results, query)

    if tfidf_results:
        results = []
        for idx, score in tfidf_results[:top_k]:
            doc = _documents[idx]
            results.append({
                "text": doc["text"], "source": doc.get("source", "unknown"),
                "score": round(score, 3), "metadata": doc.get("metadata", {}),
                "engine": "tfidf",
            })
        return results

    # Tier 3: Keyword match
    return _keyword_search(expanded_query, texts, top_k)


# ── Synonym Expansion ──────────────────────────────────────────────────────

_SYNONYMS = {
    "bitumen": ["asphalt", "blacktop", "binder"],
    "asphalt": ["bitumen", "blacktop", "binder"],
    "vg30": ["vg-30", "viscosity grade 30"],
    "vg10": ["vg-10", "viscosity grade 10"],
    "vg40": ["vg-40", "viscosity grade 40"],
    "crude": ["oil", "brent", "wti", "petroleum"],
    "brent": ["crude oil", "brent crude"],
    "price": ["cost", "rate", "pricing"],
    "demand": ["consumption", "requirement", "usage"],
    "supply": ["production", "output", "refinery"],
    "import": ["inbound", "shipment", "cargo"],
    "export": ["outbound", "shipment"],
    "freight": ["transport", "logistics", "shipping"],
    "refinery": ["iocl", "bpcl", "hpcl", "plant"],
    "road": ["highway", "nhai", "infrastructure"],
    "tender": ["bid", "contract", "procurement"],
    "monsoon": ["rain", "rainy season", "rainfall"],
    "fx": ["exchange rate", "usd inr", "forex", "currency"],
}


def _expand_query(query: str) -> str:
    """Expand query with domain-specific synonyms."""
    words = query.lower().split()
    expansions = []
    for word in words:
        clean = re.sub(r'[^\w]', '', word)
        synonyms = _SYNONYMS.get(clean, [])
        if synonyms:
            expansions.extend(synonyms[:2])
    if expansions:
        return f"{query} {' '.join(expansions)}"
    return query


# ── Reciprocal Rank Fusion ────────────────────────────────────────────────

def _reciprocal_rank_fusion(
    dense_results: list[tuple[int, float]],
    sparse_results: list[tuple[int, float]],
    k: int = 60,
) -> list[tuple[int, float]]:
    """Merge two ranked lists using Reciprocal Rank Fusion."""
    rrf_scores: dict[int, float] = {}

    for rank, (idx, _) in enumerate(dense_results):
        rrf_scores[idx] = rrf_scores.get(idx, 0) + 1.0 / (k + rank + 1)

    for rank, (idx, _) in enumerate(sparse_results):
        rrf_scores[idx] = rrf_scores.get(idx, 0) + 1.0 / (k + rank + 1)

    merged = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    return merged


# ── Cross-Encoder Reranking ───────────────────────────────────────────────

_cross_encoder = None
_HAS_CROSS_ENCODER = False

try:
    from sentence_transformers import CrossEncoder as _CE
    _HAS_CROSS_ENCODER = True
except ImportError:
    pass


def _rerank(results: list[dict], query: str) -> list[dict]:
    """Rerank results using cross-encoder if available."""
    global _cross_encoder
    if not _HAS_CROSS_ENCODER or len(results) <= 1:
        return results

    try:
        if _cross_encoder is None:
            _cross_encoder = _CE("cross-encoder/ms-marco-MiniLM-L-6-v2")

        pairs = [(query, r["text"]) for r in results]
        scores = _cross_encoder.predict(pairs)

        for r, score in zip(results, scores):
            r["rerank_score"] = round(float(score), 3)

        results.sort(key=lambda r: r.get("rerank_score", 0), reverse=True)
        return results
    except Exception:
        return results


def _keyword_search(query: str, texts: list[str], top_k: int) -> list[dict]:
    """Simple keyword-based search fallback."""
    query_terms = set(re.findall(r'\w+', query.lower()))
    if not query_terms:
        return []

    scored = []
    for i, text in enumerate(texts):
        text_terms = set(re.findall(r'\w+', text.lower()))
        overlap = len(query_terms & text_terms)
        if overlap > 0:
            score = overlap / max(len(query_terms), 1)
            scored.append((score, i))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = []
    for score, idx in scored[:top_k]:
        doc = _documents[idx] if idx < len(_documents) else {"text": texts[idx]}
        results.append({
            "text": doc.get("text", texts[idx]),
            "source": doc.get("source", "unknown"),
            "score": round(score, 3),
            "metadata": doc.get("metadata", {}),
            "engine": "keyword",
        })
    return results


# ═══════════════════════════════════════════════════════════════════════════════
# RAG PIPELINE — Search + LLM
# ═══════════════════════════════════════════════════════════════════════════════

def ask_with_context(question: str, role: str = "admin") -> dict:
    """RAG pipeline: search → inject context → ask LLM."""
    # Step 1: Search for relevant context
    results = search(question, top_k=5)
    context_texts = [r["text"] for r in results]
    context_block = "\n".join(f"- {t}" for t in context_texts) if context_texts else "No relevant data found."

    # Step 2: Build prompt with context
    rag_prompt = (
        f"Based on the following dashboard data:\n\n{context_block}\n\n"
        f"Answer this question: {question}\n\n"
        f"Be specific and reference the data provided. If the data doesn't contain "
        f"enough information, say so clearly."
    )

    # Step 3: Ask LLM via ai_fallback_engine
    try:
        from ai_fallback_engine import ask_with_fallback
        answer = ask_with_fallback(rag_prompt)
        engine = results[0]["engine"] if results else "none"
        return {
            "answer": answer,
            "sources": results,
            "engine": engine,
            "context_used": len(context_texts),
        }
    except Exception as e:
        return {
            "answer": f"Could not generate answer: {e}",
            "sources": results,
            "engine": "error",
            "context_used": 0,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# INDEX REFRESH (called from sync_engine)
# ═══════════════════════════════════════════════════════════════════════════════

def refresh_index() -> dict:
    """Rebuild index with latest data. Called from sync_engine."""
    global _index_built
    _index_built = False
    return build_index()
