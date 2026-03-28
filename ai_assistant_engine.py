"""
AI Assistant Engine — Anthropic API orchestration layer.

Responsibilities:
  • Build the role-aware system prompt with live dashboard context
  • Send queries to Claude (haiku for speed, sonnet for depth)
  • Parse structured / free-text + <CHART> responses
  • Log every query to ai_query_log.json
  • Provide query history, FAQ, and confidence scoring

Chart Spec Format (AI outputs inside <CHART>…</CHART>):
  {
    "type":    "bar" | "line" | "heatmap" | "scatter" | "pie",
    "title":   "…",
    "x":       [list],           // bar / line / scatter
    "y":       [list],           // bar / line / scatter
    "traces":  [{name,x,y},…],   // multi-trace line/scatter
    "z":       [[…],…],          // heatmap z-matrix
    "x_labels":[…], "y_labels":[…],  // heatmap axes
    "labels":  [list],           // pie slice labels
    "values":  [list],           // pie slice values
    "x_label": "…", "y_label":"…",
    "color":   "#hex or array",
    "note":    "source footnote"
  }
"""

from __future__ import annotations

import json
import os
import re
import sys
import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

AI_LOG_FILE = BASE_DIR / "ai_query_log.json"

# ── Model constants ────────────────────────────────────────────────────────────
MODEL_FAST  = "claude-haiku-4-5-20251001"    # default — low latency
MODEL_DEEP  = "claude-sonnet-4-6"            # detailed analysis

# ── System prompt template ─────────────────────────────────────────────────────
_SYSTEM_PROMPT_TEMPLATE = """You are the AI Dashboard Assistant for **PPS Anantams Logistics** — India's Bitumen Sales Intelligence Platform.

YOUR ROLE: {role}

CURRENT TIMESTAMP: {ts_ist}

════════════════════════════════════════════════════
LIVE DASHBOARD DATA (use ONLY this for answers):
════════════════════════════════════════════════════
{context_json}

════════════════════════════════════════════════════
HARD RULES — READ CAREFULLY:
════════════════════════════════════════════════════
1. Answer ONLY from the data provided above. If data is absent, say exactly:
   "Data not available in system — [module] not loaded or empty."
2. NEVER hallucinate prices, contractor names, project values, or API stats.
3. Always use Indian formatting:
   • Numbers: ₹ crore/lakh/thousand (e.g., ₹48,302/MT, ₹2.78 lakh crore)
   • Dates: DD-MM-YYYY (e.g., 16-02-2026)
   • Time: IST (e.g., 14:35 IST)
   • Large numbers: use Indian comma style (1,00,000 not 100,000)
4. Always append a data source note at the end of your answer:
   _(Data source: <module>, snapshot {ts_ist})_
5. For calculations: show the formula clearly.
6. For assumptions: prefix with **[ASSUMPTION]**.
7. Confidence levels:
   • HIGH — data directly available in context
   • MEDIUM — calculated from available data
   • LOW — inferred/estimated

════════════════════════════════════════════════════
CHART GENERATION — OUTPUT FORMAT:
════════════════════════════════════════════════════
When the user asks for a chart/graph/visual/heatmap, include this block
ANYWHERE in your response (the UI will render it automatically):

<CHART>
{{
  "type": "bar",
  "title": "Chart Title",
  "x": ["label1","label2"],
  "y": [100, 200],
  "x_label": "X Axis",
  "y_label": "Y Axis (₹/MT or MT or %)",
  "color": "#0284c7",
  "note": "Source: module_name, {ts_ist}"
}}
</CHART>

For line charts use "traces": [{{"name":"Series1","x":[...],"y":[...]}}]
For heatmaps: "z":[[...]], "x_labels":[...], "y_labels":[...]
For pie: "labels":[...], "values":[...]

════════════════════════════════════════════════════
INDIA BITUMEN MARKET — BACKGROUND KNOWLEDGE:
════════════════════════════════════════════════════
• India is the world's 2nd largest bitumen consumer (~8.5–10.5 million MT/year, FY26)
• Domestic production: ~5 MT/year (IOCL, BPCL, HPCL, Reliance) — ~50% import dependent
• PSU price revision cycle: 1st and 16th of every month (24 events/year)
• Grades (IS 73:2013): VG-10, VG-30 (most common ~70%), VG-40, VG-CRMB, PMB
• GST on bitumen: 18% (HSN 2713 20 00) — full ITC credit available in B2B supply chain
• MORTH FY26 road budget: ₹11.11 lakh crore — highest allocation ever
• NHAI FY26 target: 12,000+ km of national highway construction
• Peak construction season: Oct–Mar (post-monsoon); monsoon lean: Jun–Sep
• Primary import routes: Iraq (Basrah), UAE (Fujairah), Saudi Arabia, Kuwait
• Import entry ports: Kandla, Mundra, JNPT, Paradip, Haldia, Vizag, Ennore, Mangalore
• PPS Anantams base: Vadodara, Gujarat — Pan-India supply to contractors and PWDs
• Credit norms: Govt contractors: 45–90 days; Private contractors: 30–45 days
• Key price drivers: Brent crude (~₹110–120/MT per ₹ 1 Brent move), USD/INR (~₹75–90/MT per ₹1 move)
• Bitumen consumption per km: 4-lane highway ~140–160 MT/km; 2-lane road ~55–70 MT/km
• Top consumer states: UP, Maharashtra, Rajasthan, Gujarat, MP

When answering pricing questions, clarify:
  (a) PSU ex-refinery, (b) port ex-stock, or (c) landed at destination.
When answering demand questions, cite the current season (peak Oct–Mar / lean Jun–Sep) and FY26 context.
When answering territory questions, note that Gujarat is PPS Anantams' primary market.

════════════════════════════════════════════════════
RESPONSE STRUCTURE (ALWAYS follow this):
════════════════════════════════════════════════════
Answer the question in clear markdown. Then:
• If a calculation was done → show formula
• If a chart was generated → embed the <CHART> block
• End with: _(Data source: …)_ and _(Confidence: HIGH/MEDIUM/LOW)_

You are a trusted business assistant. Be concise but complete.
"""

# ══════════════════════════════════════════════════════════════════════════════
# API KEY MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

def get_api_key() -> str | None:
    """
    Look up the Anthropic API key in order of priority:
      1. Environment variable ANTHROPIC_API_KEY
      2. ai_config.json in the dashboard folder
      3. Returns None (UI will prompt user)
    """
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if key:
        return key
    config_path = BASE_DIR / "ai_config.json"
    if config_path.exists():
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            return data.get("anthropic_api_key", "").strip() or None
        except Exception:
            pass
    return None


def save_api_key(key: str) -> None:
    """Persist API key to ai_config.json."""
    config_path = BASE_DIR / "ai_config.json"
    data = {}
    if config_path.exists():
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    data["anthropic_api_key"] = key.strip()
    config_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ══════════════════════════════════════════════════════════════════════════════
# SYSTEM PROMPT BUILDER
# ══════════════════════════════════════════════════════════════════════════════

def build_system_prompt(role: str = "Admin") -> str:
    """Build the full system prompt with live context + business knowledge injected."""
    from ai_data_layer import build_context_json
    ts_ist      = datetime.datetime.now().strftime("%Y-%m-%d %H:%M IST")
    context_json = build_context_json(role)

    # Inject PACPL business context
    biz_ctx = ""
    try:
        from business_context import get_business_context
        biz_ctx = "\n\nBUSINESS KNOWLEDGE:\n" + get_business_context("general")
    except Exception:
        pass

    return _SYSTEM_PROMPT_TEMPLATE.format(
        role=role,
        ts_ist=ts_ist,
        context_json=context_json + biz_ctx,
    )


# ══════════════════════════════════════════════════════════════════════════════
# RESPONSE PARSER
# ══════════════════════════════════════════════════════════════════════════════

def parse_ai_response(raw_text: str) -> dict:
    """
    Parse the AI's raw response into structured fields.
    Extracts <CHART>…</CHART> blocks and cleans the answer text.
    Returns:
      {answer, chart, confidence, sources}
    """
    # Extract chart spec
    chart = None
    chart_match = re.search(r"<CHART>([\s\S]*?)</CHART>", raw_text, re.IGNORECASE)
    if chart_match:
        try:
            chart = json.loads(chart_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Clean text (remove chart block)
    answer = re.sub(r"<CHART>[\s\S]*?</CHART>", "", raw_text, flags=re.IGNORECASE).strip()

    # Extract confidence level
    confidence = "MEDIUM"
    conf_match = re.search(r"Confidence:\s*(HIGH|MEDIUM|LOW)", answer, re.IGNORECASE)
    if conf_match:
        confidence = conf_match.group(1).upper()

    # Extract sources from "Data source: …" footer
    sources: list[str] = []
    src_match = re.search(r"Data source:\s*([^\n_)]+)", answer)
    if src_match:
        sources = [src_match.group(1).strip()]

    return {
        "answer":     answer,
        "chart":      chart,
        "confidence": confidence,
        "sources":    sources,
    }


# ══════════════════════════════════════════════════════════════════════════════
# MAIN QUERY FUNCTION
# ══════════════════════════════════════════════════════════════════════════════

def ask_ai(
    question:    str,
    role:        str = "Admin",
    history:     list[dict] | None = None,  # [{"role":"user","content":"…"},…]
    deep_mode:   bool = False,
    api_key:     str | None = None,
) -> dict:
    """
    Send a question to Claude with full dashboard context.

    Returns:
      {
        "answer":     str,
        "chart":      dict | None,
        "confidence": "HIGH" | "MEDIUM" | "LOW",
        "sources":    [str],
        "error":      str | None,
        "model_used": str,
      }
    """
    key = api_key or get_api_key()

    # ── RAG context injection — enrich question with relevant data ──────
    rag_context = ""
    try:
        from rag_engine import search as rag_search
        rag_results = rag_search(question, top_k=3)
        if rag_results:
            rag_context = "\n\nRelevant dashboard data:\n" + "\n".join(
                f"- {r['text']}" for r in rag_results
            )
    except Exception:
        pass

    enriched_question = question + rag_context if rag_context else question

    # ── Claude path (best quality — when API key available) ──────────────
    if key:
        try:
            import anthropic
        except ImportError:
            anthropic = None

        if anthropic is not None:
            model = MODEL_DEEP if deep_mode else MODEL_FAST
            system_prompt = build_system_prompt(role)
            messages: list[dict] = []
            if history:
                messages.extend(history[-10:])
            messages.append({"role": "user", "content": enriched_question})
            try:
                client   = anthropic.Anthropic(api_key=key)
                response = client.messages.create(
                    model=model,
                    max_tokens=2048,
                    system=system_prompt,
                    messages=messages,
                )
                raw_text = response.content[0].text
                parsed   = parse_ai_response(raw_text)
                parsed["model_used"] = model
                parsed["error"]      = None
                log_query(
                    question=question, role=role,
                    answer_summary=parsed["answer"][:300],
                    confidence=parsed["confidence"],
                    sources=parsed["sources"], model=model,
                )
                return parsed
            except Exception as exc:
                pass  # Fall through to free providers

    # ── Free AI path (Ollama → HuggingFace → GPT4All via fallback engine) ──
    try:
        from ai_fallback_engine import ask_with_fallback, get_active_model_name
        context = build_system_prompt(role)
        result = ask_with_fallback(enriched_question, context=context)
        if not result.get("error"):
            raw_text = result["answer"]
            parsed = parse_ai_response(raw_text)
            model_label = get_active_model_name()
            parsed["model_used"] = model_label
            parsed["error"] = None
            log_query(
                question=question, role=role,
                answer_summary=parsed["answer"][:300],
                confidence=parsed["confidence"],
                sources=parsed["sources"], model=model_label,
            )
            return parsed
    except Exception:
        pass

    # ── All providers failed ─────────────────────────────────────────────
    return {
        "answer": (
            "⚠️ **No AI provider available.**\n\n"
            "**Free options (recommended):**\n"
            "1. Install Ollama from ollama.com → `ollama pull llama3`\n"
            "2. `pip install huggingface-hub` (free cloud AI)\n"
            "3. `pip install gpt4all` (free offline AI)\n\n"
            "**Paid option:** Enter Anthropic API key in sidebar."
        ),
        "chart": None, "confidence": "LOW", "sources": [],
        "error": "no_provider", "model_used": "",
    }


def stream_ai(
    question:  str,
    role:      str = "Admin",
    history:   list[dict] | None = None,
    deep_mode: bool = False,
    api_key:   str | None = None,
):
    """
    Generator: yields text chunks for Streamlit streaming display.
    Use with st.write_stream().
    After completion, call parse_ai_response() on the full text.
    """
    key = api_key or get_api_key()

    # ── Claude streaming (when API key available) ────────────────────────
    if key:
        try:
            import anthropic
            model = MODEL_DEEP if deep_mode else MODEL_FAST
            system_prompt = build_system_prompt(role)
            messages: list[dict] = []
            if history:
                messages.extend(history[-10:])
            messages.append({"role": "user", "content": question})
            client = anthropic.Anthropic(api_key=key)
            with client.messages.stream(
                model=model,
                max_tokens=2048,
                system=system_prompt,
                messages=messages,
            ) as stream:
                for chunk in stream.text_stream:
                    yield chunk
            return
        except Exception:
            pass  # Fall through to free path

    # ── Free AI fallback (non-streaming — yields full answer) ────────────
    try:
        from ai_fallback_engine import ask_with_fallback, get_active_model_name
        context = build_system_prompt(role)
        result = ask_with_fallback(question, context=context)
        if not result.get("error"):
            model_label = get_active_model_name()
            yield result["answer"]
            yield f"\n\n---\n_Answered by {model_label}_"
            return
    except Exception:
        pass

    yield "⚠️ No AI provider available. Install Ollama (free) or enter an API key."


# ══════════════════════════════════════════════════════════════════════════════
# QUERY LOGGING
# ══════════════════════════════════════════════════════════════════════════════

def log_query(
    question:      str,
    role:          str,
    answer_summary:str,
    confidence:    str,
    sources:       list[str],
    model:         str = "",
) -> None:
    """Append one query record to ai_query_log.json."""
    record = {
        "timestamp_ist": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S IST"),
        "role":           role,
        "question":       question,
        "answer_summary": answer_summary,
        "confidence":     confidence,
        "sources":        sources,
        "model":          model,
    }
    try:
        existing: list = []
        if AI_LOG_FILE.exists():
            existing = json.loads(AI_LOG_FILE.read_text(encoding="utf-8"))
        existing.append(record)
        if len(existing) > 2000:
            existing = existing[-2000:]
        AI_LOG_FILE.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def get_query_history(n: int = 50) -> list[dict]:
    """Return last n logged queries (newest first)."""
    if not AI_LOG_FILE.exists():
        return []
    try:
        data = json.loads(AI_LOG_FILE.read_text(encoding="utf-8"))
        return list(reversed(data[-n:]))
    except Exception:
        return []


def get_faq(top: int = 10) -> list[dict]:
    """
    Return the top recurring questions by frequency.
    Returns list of {question, count, last_asked, role}.
    """
    if not AI_LOG_FILE.exists():
        return []
    try:
        data = json.loads(AI_LOG_FILE.read_text(encoding="utf-8"))
        freq: dict[str, dict] = {}
        for r in data:
            q = r.get("question", "").strip().lower()
            if q not in freq:
                freq[q] = {"question": r["question"], "count": 0,
                            "last_asked": r["timestamp_ist"], "role": r["role"]}
            freq[q]["count"] += 1
            freq[q]["last_asked"] = r["timestamp_ist"]
        ranked = sorted(freq.values(), key=lambda x: x["count"], reverse=True)
        return ranked[:top]
    except Exception:
        return []


def get_role_query_breakdown() -> dict[str, int]:
    """Return count of queries by role."""
    if not AI_LOG_FILE.exists():
        return {}
    try:
        data = json.loads(AI_LOG_FILE.read_text(encoding="utf-8"))
        counts: dict[str, int] = {}
        for r in data:
            role = r.get("role", "Unknown")
            counts[role] = counts.get(role, 0) + 1
        return counts
    except Exception:
        return {}
