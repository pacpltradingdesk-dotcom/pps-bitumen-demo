"""
PPS Anantam — Trading Chatbot Engine v1.0
==========================================
Intent-aware AI trading chatbot that integrates with ALL dashboard data,
APIs, news, supply chain, and logistics to answer questions like:
  - "What's the best price from Middle East?"
  - "Should I buy now or wait?"
  - "Which port has least congestion?"
  - "Gujarat demand forecast"
  - "Compare prices from last 3 months"

Pipeline:
  1. Classify intent from query (keyword + pattern matching)
  2. Gather context from appropriate engines based on intent
  3. RAG search for relevant documents
  4. Build system prompt with full trading context
  5. Generate response via ai_fallback_engine
  6. Post-process: format INR, add citations, extract chart specs
  7. Generate follow-up suggestions

All times: IST (Asia/Kolkata)
"""
from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional

# ── Constants ────────────────────────────────────────────────────────────────
IST = timezone(timedelta(hours=5, minutes=30))
BASE = Path(__file__).resolve().parent
LOG = logging.getLogger("trading_chatbot_engine")

MAX_CONTEXT_CHARS = 3000
MAX_HISTORY_TURNS = 5

# ── Optional engine imports (all try/except) ─────────────────────────────────
_ai_fallback = None
_rag_engine = None
_ai_data_layer = None
_purchase_advisor = None
_recommendation_engine = None
_business_advisor = None
_market_pulse = None
_calculation_engine = None
_ml_forecast = None
_market_intel = None
_crm_engine = None
_opportunity_engine = None
_api_hub = None
_maritime_intel = None
_infra_demand = None
_forward_strategy = None
_news_engine = None

try:
    import ai_fallback_engine as _ai_fallback
except Exception:
    LOG.debug("ai_fallback_engine not available")

try:
    import rag_engine as _rag_engine
except Exception:
    LOG.debug("rag_engine not available")

try:
    import ai_data_layer as _ai_data_layer
except Exception:
    LOG.debug("ai_data_layer not available")

try:
    from purchase_advisor_engine import PurchaseAdvisorEngine as _PurchaseAdvisorEngine
    _purchase_advisor = _PurchaseAdvisorEngine
except Exception:
    LOG.debug("purchase_advisor_engine not available")

try:
    import recommendation_engine as _recommendation_engine
except Exception:
    LOG.debug("recommendation_engine not available")

try:
    import business_advisor_engine as _business_advisor
except Exception:
    LOG.debug("business_advisor_engine not available")

try:
    import market_pulse_engine as _market_pulse
except Exception:
    LOG.debug("market_pulse_engine not available")

try:
    from calculation_engine import BitumenCalculationEngine as _BitumenCalcEngine
    _calculation_engine = _BitumenCalcEngine
except Exception:
    LOG.debug("calculation_engine not available")

try:
    import ml_forecast_engine as _ml_forecast
except Exception:
    LOG.debug("ml_forecast_engine not available")

try:
    from market_intelligence_engine import MarketIntelligenceEngine as _MarketIntelEngine
    _market_intel = _MarketIntelEngine
except Exception:
    LOG.debug("market_intelligence_engine not available")

try:
    from crm_engine import IntelligentCRM as _IntelligentCRM
    _crm_engine = _IntelligentCRM
except Exception:
    LOG.debug("crm_engine not available")

try:
    from opportunity_engine import OpportunityEngine as _OpportunityEngine
    _opportunity_engine = _OpportunityEngine
except Exception:
    LOG.debug("opportunity_engine not available")

try:
    from api_hub_engine import HubCache as _HubCache
    _api_hub = _HubCache
except Exception:
    LOG.debug("api_hub_engine not available")

try:
    import maritime_intelligence_engine as _maritime_intel
except Exception:
    LOG.debug("maritime_intelligence_engine not available")

try:
    import infra_demand_engine as _infra_demand
except Exception:
    LOG.debug("infra_demand_engine not available")

try:
    from forward_strategy_engine import ForwardStrategyEngine as _ForwardStrategyEngine
    _forward_strategy = _ForwardStrategyEngine
except Exception:
    LOG.debug("forward_strategy_engine not available")

try:
    import news_engine as _news_engine
except Exception:
    LOG.debug("news_engine not available")


# ── Helpers ──────────────────────────────────────────────────────────────────

def _now_ist() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M IST")


def _safe(fn, label: str, fallback: Any = None) -> Any:
    """Run fn(); on any exception return fallback."""
    try:
        return fn()
    except Exception as exc:
        LOG.debug("%s failed: %s", label, exc)
        return fallback if fallback is not None else {}


def _truncate(text: str, max_chars: int = MAX_CONTEXT_CHARS) -> str:
    """Truncate text to fit within context window limits."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n...[truncated]"


def _load_json(path: Path) -> list | dict:
    """Load JSON file with error handling."""
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return []


def _format_inr(amount: float | int) -> str:
    """Format amount in Indian Rupee notation."""
    if amount is None:
        return "N/A"
    try:
        amt = float(amount)
        if amt >= 10_000_000:
            return f"\u20b9{amt / 10_000_000:.2f} Cr"
        if amt >= 100_000:
            return f"\u20b9{amt / 100_000:.2f} L"
        return f"\u20b9{amt:,.0f}"
    except (ValueError, TypeError):
        return str(amount)


# ═══════════════════════════════════════════════════════════════════════════════
# QUICK ACTIONS — Pre-built questions for the UI
# ═══════════════════════════════════════════════════════════════════════════════

QUICK_ACTIONS: list[str] = [
    "Best import source right now?",
    "Should I buy or wait?",
    "Gujarat demand forecast",
    "Port congestion status",
    "Today's best selling price for Mumbai",
    "Refinery shutdown alerts",
    "FX impact on import cost",
    "Weekly market summary",
    "Compare Brent prices last 3 months",
    "Top profitable opportunities today",
]


# ═══════════════════════════════════════════════════════════════════════════════
# TRADING CHATBOT CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class TradingChatbot:
    """Intent-aware AI trading chatbot integrating all dashboard intelligence."""

    # ── Trading-specific system prompt ────────────────────────────────────────
    TRADING_SYSTEM_PROMPT = (
        "You are the AI Trading Advisor for PPS Anantam Capital Pvt Ltd (PACPL), "
        "a bitumen commodity trading company based in Vadodara, Gujarat.\n"
        "Owner: PRINCE P SHAH (PPS), 24 years industry experience.\n"
        "Role: Commission Agent + Logistics Arranger for imported bitumen.\n"
        "Contact Database: 24,000 contacts across Pan India.\n\n"
        "You have access to real-time market data, pricing engines, forecasts, "
        "CRM data, maritime intelligence, and supply chain information.\n\n"
        "Provide specific, actionable advice. Always cite data sources. Use INR "
        "(Rs) formatting for Indian prices and USD ($) for international prices. "
        "When recommending actions, include confidence level and reasoning.\n\n"
        "Key business rules:\n"
        "- STRICT: 100% Advance payment ONLY. NEVER offer credit.\n"
        "- Min margin: Rs 500/MT\n"
        "- 3-tier offers: aggressive(+500), balanced(+800), premium(+1200)\n"
        "- GST: 18%, Customs duty: 2.5%, Landing: 1%, HSN: 27132000\n"
        "- Freight: bulk Rs 5.5/km, drum Rs 6/km\n"
        "- Quote validity: 24 hours\n"
        "- CRM thresholds: hot<=7d, warm<=30d, cold<=90d\n\n"
        "10 Price Factors to Monitor:\n"
        "- Crude oil (Brent/Dubai), USD/INR rate, Ship arrivals at Kandla\n"
        "- Port congestion, Truck availability, Conference/cartel pricing\n"
        "- Seasonal demand (Oct-Mar peak, Jun-Aug monsoon), Middle East supply\n"
        "- Government policy (NHAI budget, customs), PSU prices (IOCL/HPCL/BPCL)\n\n"
        "Regions: West India + Southwest = STRONGHOLD. North + East + South = EXPANSION.\n"
        "8 Customer Segments: Importers, Exporters, Traders, Decanters, "
        "Product Manufacturers, Road Contractors, Truck Transporters, Tanker Transporters.\n"
    )

    # ── Intent classification map ─────────────────────────────────────────────
    INTENT_MAP: dict[str, list[str]] = {
        "buy_advice": [
            "buy", "purchase", "procure", "stock", "order", "source", "import",
        ],
        "sell_advice": [
            "sell", "quote", "offer", "margin", "customer", "client",
        ],
        "pricing": [
            "price", "cost", "rate", "landed", "cfr", "fob", "cif",
        ],
        "logistics": [
            "ship", "port", "vessel", "freight", "maritime", "route",
            "cargo", "congestion",
        ],
        "demand": [
            "demand", "tender", "infra", "construction", "project",
            "road", "highway",
        ],
        "market_news": [
            "news", "alert", "disruption", "shutdown", "delay", "maintenance",
        ],
        "forecast": [
            "forecast", "predict", "expect", "future", "trend", "outlook", "next",
        ],
        "comparison": [
            "compare", "vs", "versus", "difference", "between", "history",
        ],
    }

    def __init__(self):
        self._engines_checked = False

    # ══════════════════════════════════════════════════════════════════════════
    # MAIN ENTRY POINT
    # ══════════════════════════════════════════════════════════════════════════

    def process_query(self, query: str, chat_history: list = None) -> dict:
        """
        Main entry point — routes query through intelligence pipeline.

        Returns:
            {
                "answer": str,              # Natural language response
                "charts": list[dict],        # Chart specs for UI rendering
                "sources": list[str],        # Data sources used
                "confidence": float,         # 0-100
                "intent": str,               # Classified intent
                "suggested_follow_ups": list[str],
                "timestamp": str,            # IST timestamp
                "processing_time_ms": int,   # Response latency
            }
        """
        start_time = time.time()
        chat_history = chat_history or []

        # 1. Classify intent from query
        intent = self._classify_intent(query)
        LOG.info("Query: '%s' → Intent: %s", query[:60], intent)

        # 2. Gather context from appropriate engines based on intent
        context = self._gather_context(intent)
        sources = context.pop("_sources", [])

        # 3. RAG search for relevant documents
        rag_results = self._rag_search(query)

        # 4. Build system prompt with full trading context
        prompt = self._build_trading_prompt(intent, context, rag_results, chat_history)

        # 5. Generate response via ai_fallback_engine
        raw_answer = self._call_llm(prompt, query)

        # 6. Post-process: format INR, add citations, extract chart specs
        answer = self._post_process(raw_answer, sources)
        charts = self._extract_chart_specs(raw_answer)

        # 7. Compute confidence from available data
        confidence = self._compute_confidence(intent, context, rag_results)

        # 8. Generate follow-up suggestions
        follow_ups = self._generate_follow_ups(intent, query)

        elapsed_ms = int((time.time() - start_time) * 1000)

        return {
            "answer": answer,
            "charts": charts,
            "sources": sources,
            "confidence": confidence,
            "intent": intent,
            "suggested_follow_ups": follow_ups,
            "timestamp": _now_ist(),
            "processing_time_ms": elapsed_ms,
        }

    # ══════════════════════════════════════════════════════════════════════════
    # INTENT CLASSIFICATION
    # ══════════════════════════════════════════════════════════════════════════

    def _classify_intent(self, query: str) -> str:
        """Keyword + pattern matching for intent classification."""
        query_lower = query.lower().strip()
        scores: dict[str, int] = {}

        for intent, keywords in self.INTENT_MAP.items():
            score = 0
            for kw in keywords:
                # Full word matching to reduce false positives
                pattern = r'\b' + re.escape(kw) + r'\b'
                matches = re.findall(pattern, query_lower)
                score += len(matches)
            if score > 0:
                scores[intent] = score

        if not scores:
            return "general"

        # Return highest scoring intent
        return max(scores, key=scores.get)

    # ══════════════════════════════════════════════════════════════════════════
    # CONTEXT GATHERING — Route to appropriate engines based on intent
    # ══════════════════════════════════════════════════════════════════════════

    def _gather_context(self, intent: str) -> dict:
        """Route to appropriate engines based on intent."""
        ctx: dict[str, Any] = {"_sources": []}

        if intent == "buy_advice":
            ctx.update(self._ctx_buy_advice())
        elif intent == "sell_advice":
            ctx.update(self._ctx_sell_advice())
        elif intent == "pricing":
            ctx.update(self._ctx_pricing())
        elif intent == "logistics":
            ctx.update(self._ctx_logistics())
        elif intent == "demand":
            ctx.update(self._ctx_demand())
        elif intent == "market_news":
            ctx.update(self._ctx_market_news())
        elif intent == "forecast":
            ctx.update(self._ctx_forecast())
        elif intent == "comparison":
            ctx.update(self._ctx_comparison())
        else:
            ctx.update(self._ctx_general())

        return ctx

    def _ctx_buy_advice(self) -> dict:
        """Context for buy/purchase advisory questions."""
        ctx: dict[str, Any] = {"_sources": []}
        sources = ctx["_sources"]

        # Purchase advisor urgency index
        if _purchase_advisor:
            data = _safe(lambda: _purchase_advisor().compute_urgency_index(),
                         "purchase_advisor")
            if data:
                ctx["purchase_urgency"] = data
                sources.append("PurchaseAdvisorEngine (6-signal urgency)")

        # Latest recommendations
        if _recommendation_engine:
            data = _safe(lambda: _recommendation_engine.get_latest_recommendations(),
                         "recommendation_engine")
            if data:
                ctx["recommendations"] = data
                sources.append("RecommendationEngine (aggregated signals)")

        # Business advisor buy side
        if _business_advisor:
            data = _safe(lambda: _business_advisor.get_buy_advisory(),
                         "business_advisor_buy")
            if data:
                ctx["buy_advisory"] = data
                sources.append("BusinessAdvisorEngine (buy advisory)")

        # Best sources from calculation engine
        if _calculation_engine:
            try:
                eng = _calculation_engine()
                best = eng.find_best_sources("VG30", "Mumbai", 20)
                if best:
                    ctx["best_sources"] = best[:5]
                    sources.append("CalculationEngine (best sources)")
            except Exception:
                pass

        return ctx

    def _ctx_sell_advice(self) -> dict:
        """Context for sell/quote advisory questions."""
        ctx: dict[str, Any] = {"_sources": []}
        sources = ctx["_sources"]

        # CRM customer data
        if _crm_engine:
            try:
                crm = _crm_engine()
                # Fetch all customers — the method may be get_all_customers or similar
                if hasattr(crm, "get_all_customers"):
                    customers = crm.get_all_customers()
                elif hasattr(crm, "get_customer_segments"):
                    customers = crm.get_customer_segments()
                else:
                    customers = {}
                if customers:
                    ctx["crm_data"] = customers
                    sources.append("IntelligentCRM (customer intelligence)")
            except Exception:
                pass

        # Opportunities
        if _opportunity_engine:
            data = _safe(lambda: _opportunity_engine().scan_all_opportunities(),
                         "opportunity_engine")
            if data:
                ctx["opportunities"] = data[:10]
                sources.append("OpportunityEngine (profitable opportunities)")

        # Business advisor sell side
        if _business_advisor:
            data = _safe(lambda: _business_advisor.get_sell_advisory(),
                         "business_advisor_sell")
            if data:
                ctx["sell_advisory"] = data
                sources.append("BusinessAdvisorEngine (sell advisory)")

        # Pricing from calculation engine
        if _calculation_engine:
            try:
                eng = _calculation_engine()
                if hasattr(eng, "get_three_tier_offers"):
                    offers = eng.get_three_tier_offers("VG30", "Mumbai", 20)
                    if offers:
                        ctx["three_tier_offers"] = offers
                        sources.append("CalculationEngine (3-tier pricing)")
            except Exception:
                pass

        return ctx

    def _ctx_pricing(self) -> dict:
        """Context for price/cost/rate questions."""
        ctx: dict[str, Any] = {"_sources": []}
        sources = ctx["_sources"]

        # Live prices from ai_data_layer
        if _ai_data_layer:
            data = _safe(lambda: _ai_data_layer.get_price_snapshot(),
                         "price_snapshot")
            if data:
                ctx["live_prices"] = data
                sources.append("AI Data Layer (live price snapshot)")

        # Crude prices from API hub cache
        if _api_hub:
            crude = _safe(lambda: _api_hub.get("yfinance_crude"), "crude_cache")
            if crude:
                ctx["crude_prices"] = crude
                sources.append("API Hub (yfinance crude prices)")

            fx = _safe(lambda: _api_hub.get("yfinance_fx"), "fx_cache")
            if fx:
                ctx["fx_rates"] = fx
                sources.append("API Hub (FX rates)")

        # Crude prices from JSON fallback
        if "crude_prices" not in ctx:
            crude_data = _load_json(BASE / "tbl_crude_prices.json")
            if isinstance(crude_data, list) and crude_data:
                ctx["crude_prices_history"] = crude_data[-30:]
                sources.append("tbl_crude_prices.json (last 30 entries)")

        # FX rates from JSON fallback
        if "fx_rates" not in ctx:
            fx_data = _load_json(BASE / "tbl_fx_rates.json")
            if isinstance(fx_data, list) and fx_data:
                ctx["fx_rates_history"] = fx_data[-30:]
                sources.append("tbl_fx_rates.json (last 30 entries)")

        return ctx

    def _ctx_logistics(self) -> dict:
        """Context for logistics/maritime/port questions."""
        ctx: dict[str, Any] = {"_sources": []}
        sources = ctx["_sources"]

        # Maritime intelligence — port congestion
        if _maritime_intel:
            if hasattr(_maritime_intel, "MaritimeIntelligence"):
                data = _safe(
                    lambda: _maritime_intel.MaritimeIntelligence.compute_all_ports(),
                    "maritime_all_ports",
                )
                if data:
                    ctx["port_congestion"] = data
                    sources.append("MaritimeIntelligence (port congestion)")

            if hasattr(_maritime_intel, "MaritimeIntelligence"):
                transport = _safe(
                    lambda: _maritime_intel.MaritimeIntelligence.get_transport_status(),
                    "transport_status",
                )
                if transport:
                    ctx["transport_status"] = transport
                    sources.append("MaritimeIntelligence (transport status)")

        # Ports volume from JSON
        ports_data = _load_json(BASE / "tbl_ports_volume.json")
        if isinstance(ports_data, list) and ports_data:
            ctx["ports_volume"] = ports_data[-20:]
            sources.append("tbl_ports_volume.json (port volumes)")

        return ctx

    def _ctx_demand(self) -> dict:
        """Context for demand/tender/infrastructure questions."""
        ctx: dict[str, Any] = {"_sources": []}
        sources = ctx["_sources"]

        # Infra demand engine
        if _infra_demand:
            if hasattr(_infra_demand, "compute_all_state_scores"):
                data = _safe(
                    lambda: _infra_demand.compute_all_state_scores(window_days=30),
                    "infra_demand_scores",
                )
                if data:
                    ctx["state_demand_scores"] = data[:15]
                    sources.append("InfraDemandEngine (state composite scores)")

            if hasattr(_infra_demand, "get_target_rankings"):
                rankings = _safe(
                    lambda: _infra_demand.get_target_rankings(top_n=10),
                    "target_rankings",
                )
                if rankings:
                    ctx["target_rankings"] = rankings
                    sources.append("InfraDemandEngine (target rankings)")

        # ML forecast for state demand
        if _ml_forecast and hasattr(_ml_forecast, "forecast_state_demand"):
            for state in ["Gujarat", "Maharashtra", "Rajasthan"]:
                data = _safe(
                    lambda s=state: _ml_forecast.forecast_state_demand(s, months_ahead=6),
                    f"ml_demand_{state}",
                )
                if data:
                    ctx[f"demand_forecast_{state.lower()}"] = data
                    sources.append(f"ML Forecast ({state} demand)")

        # National demand context from ai_data_layer
        if _ai_data_layer:
            data = _safe(lambda: _ai_data_layer.get_demand_context(),
                         "national_demand")
            if data:
                ctx["national_demand"] = data
                sources.append("AI Data Layer (national demand context)")

        return ctx

    def _ctx_market_news(self) -> dict:
        """Context for news/alerts/disruption questions."""
        ctx: dict[str, Any] = {"_sources": []}
        sources = ctx["_sources"]

        # Market pulse alerts
        if _market_pulse:
            if hasattr(_market_pulse, "get_active_alerts"):
                alerts = _safe(
                    lambda: _market_pulse.get_active_alerts(max_age_hours=24),
                    "market_alerts",
                )
                if alerts:
                    ctx["active_alerts"] = alerts[:15]
                    sources.append("MarketPulseEngine (active alerts)")

            if hasattr(_market_pulse, "get_market_state_summary"):
                summary = _safe(
                    lambda: _market_pulse.get_market_state_summary(),
                    "market_summary",
                )
                if summary:
                    ctx["market_state"] = summary
                    sources.append("MarketPulseEngine (market state)")

        # News feed from JSON
        news = _load_json(BASE / "tbl_news_feed.json")
        if isinstance(news, list) and news:
            ctx["recent_news"] = news[-15:]
            sources.append("tbl_news_feed.json (recent news)")

        # News articles
        articles = _load_json(BASE / "news_data" / "articles.json")
        if isinstance(articles, list) and articles:
            ctx["news_articles"] = articles[-10:]
            sources.append("news_data/articles.json (latest articles)")

        return ctx

    def _ctx_forecast(self) -> dict:
        """Context for forecast/prediction/trend questions."""
        ctx: dict[str, Any] = {"_sources": []}
        sources = ctx["_sources"]

        # ML crude price forecast
        if _ml_forecast:
            if hasattr(_ml_forecast, "forecast_crude_price"):
                data = _safe(
                    lambda: _ml_forecast.forecast_crude_price(days_ahead=90),
                    "crude_forecast",
                )
                if data:
                    ctx["crude_forecast"] = data
                    sources.append("ML Forecast (crude price 90-day)")

            if hasattr(_ml_forecast, "forecast_fx_rate"):
                data = _safe(
                    lambda: _ml_forecast.forecast_fx_rate(days_ahead=30),
                    "fx_forecast",
                )
                if data:
                    ctx["fx_forecast"] = data
                    sources.append("ML Forecast (FX rate 30-day)")

        # Forward strategy 15-day outlook
        if _forward_strategy:
            data = _safe(
                lambda: _forward_strategy().generate_full_outlook(),
                "forward_strategy",
            )
            if data:
                ctx["forward_outlook"] = data
                sources.append("ForwardStrategyEngine (15-day outlook)")

        # Market intelligence master signal
        if _market_intel:
            data = _safe(
                lambda: _market_intel().compute_all_signals(),
                "market_intel",
            )
            if data:
                ctx["market_signals"] = data
                sources.append("MarketIntelligenceEngine (composite signals)")

        return ctx

    def _ctx_comparison(self) -> dict:
        """Context for historical comparison questions."""
        ctx: dict[str, Any] = {"_sources": []}
        sources = ctx["_sources"]

        # Historical crude prices
        crude = _load_json(BASE / "tbl_crude_prices.json")
        if isinstance(crude, list) and crude:
            ctx["crude_history"] = crude[-90:]
            sources.append("tbl_crude_prices.json (last 90 entries)")

        # Historical FX rates
        fx = _load_json(BASE / "tbl_fx_rates.json")
        if isinstance(fx, list) and fx:
            ctx["fx_history"] = fx[-90:]
            sources.append("tbl_fx_rates.json (last 90 entries)")

        # Refinery production
        refinery = _load_json(BASE / "tbl_refinery_production.json")
        if isinstance(refinery, list) and refinery:
            ctx["refinery_history"] = refinery[-30:]
            sources.append("tbl_refinery_production.json (last 30 entries)")

        # Import data
        imports = _load_json(BASE / "tbl_imports_countrywise.json")
        if isinstance(imports, list) and imports:
            ctx["import_history"] = imports[-30:]
            sources.append("tbl_imports_countrywise.json (country-wise imports)")

        return ctx

    def _ctx_general(self) -> dict:
        """General context — full trading data from ai_data_layer."""
        ctx: dict[str, Any] = {"_sources": []}
        sources = ctx["_sources"]

        if _ai_data_layer:
            data = _safe(
                lambda: _ai_data_layer.build_full_context(role="Admin"),
                "full_context",
            )
            if data:
                ctx["full_trading_context"] = data
                sources.append("AI Data Layer (full admin context)")
        else:
            # Minimal fallback from JSON files
            crude = _load_json(BASE / "tbl_crude_prices.json")
            if isinstance(crude, list) and crude:
                ctx["crude_latest"] = crude[-5:]
                sources.append("tbl_crude_prices.json")

            fx = _load_json(BASE / "tbl_fx_rates.json")
            if isinstance(fx, list) and fx:
                ctx["fx_latest"] = fx[-5:]
                sources.append("tbl_fx_rates.json")

        return ctx

    # ══════════════════════════════════════════════════════════════════════════
    # RAG SEARCH
    # ══════════════════════════════════════════════════════════════════════════

    def _rag_search(self, query: str) -> list[dict]:
        """Search indexed documents for relevant context via RAG engine."""
        if not _rag_engine:
            return []
        try:
            results = _rag_engine.search(query, top_k=5)
            return results if results else []
        except Exception as exc:
            LOG.debug("RAG search failed: %s", exc)
            return []

    # ══════════════════════════════════════════════════════════════════════════
    # PROMPT BUILDING
    # ══════════════════════════════════════════════════════════════════════════

    def _build_trading_prompt(self, intent: str, context: dict,
                               rag_results: list, chat_history: list) -> str:
        """Build context-rich prompt for LLM."""
        parts: list[str] = []

        # Intent-specific context (truncated for context window)
        if context:
            ctx_json = json.dumps(context, indent=1, ensure_ascii=False, default=str)
            parts.append(f"TRADING DATA ({intent.upper()} context):\n{_truncate(ctx_json)}")

        # RAG results
        if rag_results:
            rag_text = "\n".join(
                f"- [{r.get('source', '?')}] {r.get('text', '')[:200]}"
                for r in rag_results[:5]
            )
            parts.append(f"RELEVANT DOCUMENTS:\n{_truncate(rag_text, 800)}")

        # Chat history (last N turns for continuity)
        if chat_history:
            recent = chat_history[-MAX_HISTORY_TURNS:]
            history_text = "\n".join(
                f"{'User' if i % 2 == 0 else 'AI'}: {str(msg)[:150]}"
                for i, msg in enumerate(recent)
            )
            parts.append(f"CONVERSATION HISTORY:\n{history_text}")

        # Instructions
        parts.append(
            "INSTRUCTIONS:\n"
            "- Be specific and actionable. Cite data sources.\n"
            "- Use \u20b9 for Indian prices, $ for international.\n"
            "- Include confidence level (Low/Medium/High) and reasoning.\n"
            "- If data is insufficient, say so clearly.\n"
            f"- Current time: {_now_ist()}\n"
        )

        return "\n\n".join(parts)

    # ══════════════════════════════════════════════════════════════════════════
    # LLM CALL
    # ══════════════════════════════════════════════════════════════════════════

    def _call_llm(self, prompt: str, query: str) -> str:
        """Call LLM via ai_fallback_engine with trading system prompt + business context."""
        if not _ai_fallback:
            return self._generate_offline_response(query)

        # Inject full business context with price factors + payment policy
        biz_ctx = ""
        try:
            from business_context import get_business_context
            biz_ctx = get_business_context("full")
        except Exception:
            pass

        try:
            # Try task-routed call first (customer_chat), fall back to global
            ctx = f"{self.TRADING_SYSTEM_PROMPT}\n\n{biz_ctx}\n\n{prompt}"
            try:
                result = _ai_fallback.ask_routed(
                    question=query, context=ctx, task_type="customer_chat",
                )
            except (AttributeError, Exception):
                result = _ai_fallback.ask_with_fallback(
                    question=query, context=ctx,
                )
            answer = result.get("answer", "")
            if answer and result.get("error") != "all_failed":
                return answer
        except Exception as exc:
            LOG.warning("LLM call failed: %s", exc)

        return self._generate_offline_response(query)

    def _generate_offline_response(self, query: str) -> str:
        """Generate a basic response when no LLM is available."""
        intent = self._classify_intent(query)

        # Try to build a data-driven response without LLM
        lines = [
            "**AI Trading Advisor (Offline Mode)**",
            f"Intent detected: {intent}",
            f"Query: {query}",
            "",
        ]

        if intent == "pricing":
            crude = _load_json(BASE / "tbl_crude_prices.json")
            if isinstance(crude, list) and crude:
                latest = crude[-1]
                lines.append(f"Latest Brent: ${latest.get('brent_usd', 'N/A')}/bbl")
                lines.append(f"Latest WTI: ${latest.get('wti_usd', 'N/A')}/bbl")
            fx = _load_json(BASE / "tbl_fx_rates.json")
            if isinstance(fx, list) and fx:
                latest_fx = fx[-1]
                lines.append(f"USD/INR: {latest_fx.get('USD_INR', latest_fx.get('usd_inr', 'N/A'))}")

        elif intent == "buy_advice":
            if _purchase_advisor:
                data = _safe(lambda: _purchase_advisor().compute_urgency_index(),
                             "purchase_advisor")
                if data:
                    lines.append(f"Urgency Index: {data.get('urgency_index', 'N/A')}/100")
                    lines.append(f"Recommendation: {data.get('recommendation', 'N/A')}")
                    lines.append(f"Detail: {data.get('recommendation_detail', '')}")

        lines.append("")
        lines.append("_Note: Full AI analysis unavailable. Install an AI provider "
                      "(Ollama, HuggingFace, GPT4All) for detailed responses._")

        return "\n".join(lines)

    # ══════════════════════════════════════════════════════════════════════════
    # POST-PROCESSING
    # ══════════════════════════════════════════════════════════════════════════

    def _post_process(self, raw_answer: str, sources: list[str]) -> str:
        """Format INR amounts and add source citations."""
        answer = raw_answer

        # Format standalone large numbers preceded by Rs/INR/rupee as INR
        answer = re.sub(
            r'(?:Rs\.?|INR)\s*(\d{5,})',
            lambda m: _format_inr(int(m.group(1))),
            answer,
        )

        # Add source citations footer if sources available
        if sources:
            unique_sources = list(dict.fromkeys(sources))  # deduplicate, preserve order
            citation_block = "\n\n---\n**Data Sources:** " + " | ".join(unique_sources[:6])
            answer += citation_block

        return answer

    def _extract_chart_specs(self, response: str) -> list[dict]:
        """Extract chart requests from LLM response (if any)."""
        charts: list[dict] = []

        # Look for embedded chart directives: [CHART: type=bar, title=..., data=...]
        chart_pattern = r'\[CHART:\s*(.+?)\]'
        matches = re.findall(chart_pattern, response, re.IGNORECASE)

        for match in matches:
            spec: dict[str, Any] = {}
            # Parse key=value pairs
            for pair in match.split(","):
                pair = pair.strip()
                if "=" in pair:
                    key, val = pair.split("=", 1)
                    spec[key.strip()] = val.strip()
            if spec:
                charts.append(spec)

        # Also suggest charts based on common patterns in response
        response_lower = response.lower()
        if any(kw in response_lower for kw in ["price trend", "price history", "brent"]):
            charts.append({
                "type": "line",
                "chart_key": "price_trend_refinery",
                "suggested": True,
            })
        if any(kw in response_lower for kw in ["state demand", "gujarat", "maharashtra"]):
            charts.append({
                "type": "bar",
                "chart_key": "state_demand_bar",
                "suggested": True,
            })
        if any(kw in response_lower for kw in ["port congestion", "port volume"]):
            charts.append({
                "type": "bar",
                "chart_key": "port_congestion",
                "suggested": True,
            })

        return charts

    # ══════════════════════════════════════════════════════════════════════════
    # CONFIDENCE ESTIMATION
    # ══════════════════════════════════════════════════════════════════════════

    def _compute_confidence(self, intent: str, context: dict,
                             rag_results: list) -> float:
        """Estimate confidence based on data availability and freshness."""
        score = 30.0  # Base confidence

        # More context data = higher confidence
        ctx_keys = [k for k in context if k != "_sources"]
        if ctx_keys:
            score += min(30.0, len(ctx_keys) * 6.0)

        # RAG results boost
        if rag_results:
            avg_rag_score = sum(r.get("score", 0) for r in rag_results) / len(rag_results)
            score += min(20.0, avg_rag_score * 20.0)

        # Intent-specific data availability boost
        intent_has_engine = {
            "buy_advice": _purchase_advisor is not None,
            "sell_advice": _crm_engine is not None,
            "pricing": _calculation_engine is not None,
            "logistics": _maritime_intel is not None,
            "demand": _infra_demand is not None,
            "market_news": _market_pulse is not None,
            "forecast": _ml_forecast is not None,
            "comparison": True,  # Always available from JSON files
        }
        if intent_has_engine.get(intent, False):
            score += 15.0

        # LLM availability
        if _ai_fallback:
            score += 5.0

        return min(100.0, round(score, 1))

    # ══════════════════════════════════════════════════════════════════════════
    # FOLLOW-UP SUGGESTIONS
    # ══════════════════════════════════════════════════════════════════════════

    def _generate_follow_ups(self, intent: str, query: str) -> list[str]:
        """Generate 3 relevant follow-up question suggestions."""
        follow_up_map: dict[str, list[str]] = {
            "buy_advice": [
                "What's the optimal purchase quantity for this month?",
                "Compare import vs domestic sourcing costs",
                "When is the next IOCL price revision expected?",
            ],
            "sell_advice": [
                "Which customers are due for re-engagement?",
                "Generate a competitive quote for Mumbai delivery",
                "What margins are achievable this week?",
            ],
            "pricing": [
                "How does current price compare to 3-month average?",
                "What's the landed cost from Iran FOB?",
                "Forecast price movement for next 30 days",
            ],
            "logistics": [
                "Which route has lowest freight cost to Gujarat?",
                "Any vessel delays or port shutdowns?",
                "Compare Kandla vs JNPT for bitumen imports",
            ],
            "demand": [
                "Which state has highest growth potential?",
                "Any upcoming NHAI tenders for Gujarat?",
                "Monsoon impact on Q3 demand forecast",
            ],
            "market_news": [
                "Any refinery maintenance shutdowns planned?",
                "OPEC decision impact on bitumen pricing",
                "Supply disruption risk assessment",
            ],
            "forecast": [
                "Should I hedge FX exposure now?",
                "Brent crude 90-day price forecast",
                "State-wise demand forecast for next quarter",
            ],
            "comparison": [
                "Compare import sources: Middle East vs Singapore",
                "Month-on-month price change analysis",
                "How does current Brent compare to 2025 average?",
            ],
            "general": [
                "Best import source right now?",
                "Should I buy or wait?",
                "Top profitable opportunities today",
            ],
        }

        suggestions = follow_up_map.get(intent, follow_up_map["general"])

        # Personalize: avoid repeating the user's query topic
        query_lower = query.lower()
        filtered = [s for s in suggestions if not any(
            w in s.lower() for w in query_lower.split() if len(w) > 3
        )]

        # If filtering removed too many, use originals
        if len(filtered) < 2:
            filtered = suggestions

        return filtered[:3]


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE-LEVEL CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

# Singleton instance
_chatbot_instance: Optional[TradingChatbot] = None


def _get_chatbot() -> TradingChatbot:
    """Get or create singleton chatbot instance."""
    global _chatbot_instance
    if _chatbot_instance is None:
        _chatbot_instance = TradingChatbot()
    return _chatbot_instance


def ask_trading_question(query: str, history: list = None) -> dict:
    """
    One-shot query function — convenience wrapper around TradingChatbot.

    Args:
        query:   Natural language trading question.
        history: Optional list of previous messages for context.

    Returns:
        dict with keys: answer, charts, sources, confidence, intent,
        suggested_follow_ups, timestamp, processing_time_ms.
    """
    bot = _get_chatbot()
    return bot.process_query(query, chat_history=history)


def get_chatbot_status() -> dict:
    """
    Return chatbot engine health status.

    Checks availability of all sub-engines and returns readiness info.
    """
    engines = {
        "ai_fallback_engine": _ai_fallback is not None,
        "rag_engine": _rag_engine is not None,
        "ai_data_layer": _ai_data_layer is not None,
        "purchase_advisor_engine": _purchase_advisor is not None,
        "recommendation_engine": _recommendation_engine is not None,
        "business_advisor_engine": _business_advisor is not None,
        "market_pulse_engine": _market_pulse is not None,
        "calculation_engine": _calculation_engine is not None,
        "ml_forecast_engine": _ml_forecast is not None,
        "market_intelligence_engine": _market_intel is not None,
        "crm_engine": _crm_engine is not None,
        "opportunity_engine": _opportunity_engine is not None,
        "api_hub_engine": _api_hub is not None,
        "maritime_intelligence_engine": _maritime_intel is not None,
        "infra_demand_engine": _infra_demand is not None,
        "forward_strategy_engine": _forward_strategy is not None,
        "news_engine": _news_engine is not None,
    }

    available = sum(1 for v in engines.values() if v)
    total = len(engines)

    # RAG index status
    rag_status = {}
    if _rag_engine and hasattr(_rag_engine, "get_rag_status"):
        rag_status = _safe(lambda: _rag_engine.get_rag_status(), "rag_status", {})

    # LLM provider info
    llm_info = {}
    if _ai_fallback and hasattr(_ai_fallback, "get_active_provider"):
        provider = _safe(lambda: _ai_fallback.get_active_provider(), "llm_provider", {})
        if provider:
            llm_info = {
                "active_provider": provider.get("name", "Unknown"),
                "provider_type": provider.get("type", "Unknown"),
                "cost": provider.get("cost", "Unknown"),
            }

    return {
        "status": "operational" if available >= 5 else "degraded" if available >= 2 else "minimal",
        "engines_available": available,
        "engines_total": total,
        "engine_details": engines,
        "intents_supported": list(TradingChatbot.INTENT_MAP.keys()) + ["general"],
        "quick_actions_count": len(QUICK_ACTIONS),
        "rag_index": rag_status,
        "llm_provider": llm_info,
        "timestamp": _now_ist(),
    }
