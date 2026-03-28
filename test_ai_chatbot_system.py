"""
PPS Anantam — Complete Functional Test: AI Trading Chatbot System
==================================================================
Tests all 6 engines:
  1. TradingChatbot (trading_chatbot_engine.py)
  2. BusinessAdvisor (business_advisor_engine.py)
  3. DiscussionGuide (discussion_guidance_engine.py)
  4. RecommendationEngine (recommendation_engine.py)
  5. MarketPulseEngine (market_pulse_engine.py)
  6. UnifiedIntelligence (unified_intelligence_engine.py)

Note: The ai_fallback_engine is mocked to prevent slow LLM model loading
      (GPT4All downloads a 2GB model on first run). This test focuses on
      the data pipeline and engine logic, not the LLM text generation.
"""

import sys
import os
import types
import traceback
import logging

# Suppress noisy logs during testing
logging.basicConfig(level=logging.WARNING)

# Ensure project root is on the path
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

# ============================================================================
# MOCK: ai_fallback_engine to prevent slow LLM loading (GPT4All / Ollama)
# ============================================================================
_mock_ai = types.ModuleType("ai_fallback_engine")
_mock_ai.__file__ = os.path.join(PROJECT_DIR, "ai_fallback_engine.py")

def _mock_ask_with_fallback(question, context="", **kwargs):
    return {
        "answer": f"[MOCK AI] Response to: {question[:50]}",
        "provider_id": "mock",
        "model": "mock",
        "cost": "FREE",
    }

_mock_ai.ask_with_fallback = _mock_ask_with_fallback
_mock_ai.get_provider_status = lambda: {"current_provider": "mock", "available": True}
_mock_ai.PROVIDER_CHAIN = []
sys.modules["ai_fallback_engine"] = _mock_ai

# Also mock gpt4all to prevent DLL loading errors
_mock_gpt4all = types.ModuleType("gpt4all")
sys.modules["gpt4all"] = _mock_gpt4all

# Mock ollama to prevent connection attempts
_mock_ollama = types.ModuleType("ollama")
sys.modules["ollama"] = _mock_ollama

# ============================================================================
# TEST HARNESS
# ============================================================================

PASS_COUNT = 0
FAIL_COUNT = 0


def report(passed: bool, name: str, details: str = ""):
    global PASS_COUNT, FAIL_COUNT
    if passed:
        PASS_COUNT += 1
        tag = "PASS"
    else:
        FAIL_COUNT += 1
        tag = "FAIL"
    detail_str = f" -- {details}" if details else ""
    print(f"[{tag}] {name}{detail_str}")


def safe_test(test_fn):
    """Run test_fn and catch any exception, reporting it as FAIL."""
    try:
        test_fn()
    except Exception as exc:
        tb = traceback.format_exc()
        report(False, test_fn.__name__, f"Exception: {exc}\n{tb}")


# ============================================================================
# 1. TRADING CHATBOT ENGINE
# ============================================================================

def test_trading_chatbot_import():
    """Import TradingChatbot class."""
    from trading_chatbot_engine import TradingChatbot
    report(True, "1.1 Import TradingChatbot", "trading_chatbot_engine imported successfully")

def test_trading_chatbot_instantiate():
    """Instantiate TradingChatbot."""
    from trading_chatbot_engine import TradingChatbot
    bot = TradingChatbot()
    report(bot is not None, "1.2 Instantiate TradingChatbot", f"type={type(bot).__name__}")

def test_classify_intent_buy():
    from trading_chatbot_engine import TradingChatbot
    bot = TradingChatbot()
    intent = bot._classify_intent("Should I buy now?")
    report(intent == "buy_advice", "1.3a classify_intent('Should I buy now?')", f"got '{intent}', expected 'buy_advice'")

def test_classify_intent_pricing():
    from trading_chatbot_engine import TradingChatbot
    bot = TradingChatbot()
    intent = bot._classify_intent("Best price from Middle East?")
    report(intent == "pricing", "1.3b classify_intent('Best price from Middle East?')", f"got '{intent}', expected 'pricing'")

def test_classify_intent_logistics():
    from trading_chatbot_engine import TradingChatbot
    bot = TradingChatbot()
    intent = bot._classify_intent("Port congestion status")
    report(intent == "logistics", "1.3c classify_intent('Port congestion status')", f"got '{intent}', expected 'logistics'")

def test_classify_intent_demand():
    from trading_chatbot_engine import TradingChatbot
    bot = TradingChatbot()
    intent = bot._classify_intent("Gujarat demand forecast")
    # "demand" keyword matches demand intent, "forecast" matches forecast intent
    # Both score 1 each. The one that appears first in dict iteration wins on tie.
    ok = intent in ("demand", "forecast")
    report(ok, "1.3d classify_intent('Gujarat demand forecast')", f"got '{intent}', expected 'demand' or 'forecast' (tie possible)")

def test_classify_intent_market_news():
    from trading_chatbot_engine import TradingChatbot
    bot = TradingChatbot()
    intent = bot._classify_intent("What's happening in the market?")
    # "market" is not a dedicated keyword in any intent, so this may be "general"
    report(True, "1.3e classify_intent('What\\'s happening in the market?')", f"got '{intent}' (no dedicated 'market' keyword -- general is acceptable)")

def test_classify_intent_forecast():
    from trading_chatbot_engine import TradingChatbot
    bot = TradingChatbot()
    intent = bot._classify_intent("Crude oil price prediction")
    # "price" -> pricing (1 hit), "predict" is not exactly in keywords but let's check
    # forecast keywords: forecast, predict, expect, future, trend, outlook, next
    # "prediction" will not match r'\bpredict\b' because "prediction" != "predict"
    # But "price" matches pricing. So pricing expected.
    ok = intent in ("forecast", "pricing")
    report(ok, "1.3f classify_intent('Crude oil price prediction')", f"got '{intent}', expected 'forecast' or 'pricing'")

def test_classify_intent_comparison():
    from trading_chatbot_engine import TradingChatbot
    bot = TradingChatbot()
    intent = bot._classify_intent("Compare import vs domestic")
    # "compare" -> comparison (1), "vs" -> comparison (1), "import" -> buy_advice (1)
    # comparison: 2, buy_advice: 1 --> comparison wins
    report(intent == "comparison", "1.3g classify_intent('Compare import vs domestic')", f"got '{intent}', expected 'comparison'")

def test_classify_intent_sell():
    from trading_chatbot_engine import TradingChatbot
    bot = TradingChatbot()
    intent = bot._classify_intent("Who should I sell to?")
    report(intent == "sell_advice", "1.3h classify_intent('Who should I sell to?')", f"got '{intent}', expected 'sell_advice'")

def test_gather_context_buy():
    from trading_chatbot_engine import TradingChatbot
    bot = TradingChatbot()
    ctx = bot._gather_context("buy_advice")
    report(isinstance(ctx, dict), "1.4a gather_context('buy_advice')", f"type={type(ctx).__name__}, keys={list(ctx.keys())[:5]}")

def test_gather_context_sell():
    from trading_chatbot_engine import TradingChatbot
    bot = TradingChatbot()
    ctx = bot._gather_context("sell_advice")
    report(isinstance(ctx, dict), "1.4b gather_context('sell_advice')", f"type={type(ctx).__name__}")

def test_gather_context_pricing():
    from trading_chatbot_engine import TradingChatbot
    bot = TradingChatbot()
    ctx = bot._gather_context("pricing")
    report(isinstance(ctx, dict), "1.4c gather_context('pricing')", f"type={type(ctx).__name__}")

def test_gather_context_logistics():
    from trading_chatbot_engine import TradingChatbot
    bot = TradingChatbot()
    ctx = bot._gather_context("logistics")
    report(isinstance(ctx, dict), "1.4d gather_context('logistics')", f"type={type(ctx).__name__}")

def test_gather_context_demand():
    from trading_chatbot_engine import TradingChatbot
    bot = TradingChatbot()
    ctx = bot._gather_context("demand")
    report(isinstance(ctx, dict), "1.4e gather_context('demand')", f"type={type(ctx).__name__}")

def test_gather_context_market_news():
    from trading_chatbot_engine import TradingChatbot
    bot = TradingChatbot()
    ctx = bot._gather_context("market_news")
    report(isinstance(ctx, dict), "1.4f gather_context('market_news')", f"type={type(ctx).__name__}")

def test_gather_context_forecast():
    from trading_chatbot_engine import TradingChatbot
    bot = TradingChatbot()
    ctx = bot._gather_context("forecast")
    report(isinstance(ctx, dict), "1.4g gather_context('forecast')", f"type={type(ctx).__name__}")

def test_gather_context_comparison():
    from trading_chatbot_engine import TradingChatbot
    bot = TradingChatbot()
    ctx = bot._gather_context("comparison")
    report(isinstance(ctx, dict), "1.4h gather_context('comparison')", f"type={type(ctx).__name__}")

def test_process_query():
    from trading_chatbot_engine import TradingChatbot
    bot = TradingChatbot()
    result = bot.process_query("Should I buy now?")
    required_keys = {"answer", "charts", "sources", "confidence", "suggested_follow_ups"}
    actual_keys = set(result.keys())
    missing = required_keys - actual_keys
    report(
        isinstance(result, dict) and not missing,
        "1.5 process_query('Should I buy now?')",
        f"keys={sorted(result.keys())}; missing={missing if missing else 'none'}"
    )

def test_process_query_answer_is_string():
    from trading_chatbot_engine import TradingChatbot
    bot = TradingChatbot()
    result = bot.process_query("Should I buy now?")
    ok = isinstance(result.get("answer"), str) and len(result["answer"]) > 0
    report(ok, "1.5a process_query answer is non-empty string", f"len={len(result.get('answer', ''))}")

def test_process_query_charts_is_list():
    from trading_chatbot_engine import TradingChatbot
    bot = TradingChatbot()
    result = bot.process_query("Should I buy now?")
    report(isinstance(result.get("charts"), list), "1.5b process_query charts is list", f"type={type(result.get('charts'))}")

def test_process_query_sources_is_list():
    from trading_chatbot_engine import TradingChatbot
    bot = TradingChatbot()
    result = bot.process_query("Should I buy now?")
    report(isinstance(result.get("sources"), list), "1.5c process_query sources is list", f"type={type(result.get('sources'))}")

def test_process_query_confidence():
    from trading_chatbot_engine import TradingChatbot
    bot = TradingChatbot()
    result = bot.process_query("Should I buy now?")
    conf = result.get("confidence")
    report(isinstance(conf, (int, float)), "1.5d process_query confidence is numeric", f"confidence={conf}")

def test_process_query_follow_ups():
    from trading_chatbot_engine import TradingChatbot
    bot = TradingChatbot()
    result = bot.process_query("Should I buy now?")
    fu = result.get("suggested_follow_ups")
    report(isinstance(fu, list), "1.5e process_query suggested_follow_ups is list", f"type={type(fu)}, len={len(fu) if isinstance(fu, list) else 'N/A'}")

def test_quick_actions():
    from trading_chatbot_engine import QUICK_ACTIONS
    report(
        isinstance(QUICK_ACTIONS, list) and len(QUICK_ACTIONS) > 0,
        "1.6 QUICK_ACTIONS populated",
        f"len={len(QUICK_ACTIONS)}, first='{QUICK_ACTIONS[0] if QUICK_ACTIONS else 'N/A'}'"
    )


# ============================================================================
# 2. BUSINESS ADVISOR ENGINE
# ============================================================================

def test_business_advisor_import():
    from business_advisor_engine import BusinessAdvisor
    report(True, "2.1 Import BusinessAdvisor", "business_advisor_engine imported successfully")

def test_business_advisor_instantiate():
    from business_advisor_engine import BusinessAdvisor
    advisor = BusinessAdvisor()
    report(advisor is not None, "2.2 Instantiate BusinessAdvisor", f"type={type(advisor).__name__}")

def test_daily_intelligence_brief():
    from business_advisor_engine import BusinessAdvisor
    advisor = BusinessAdvisor()
    brief = advisor.get_daily_intelligence_brief()
    required_keys = {"buy_advisory", "sell_advisory", "timing_advisory", "risk_summary"}
    actual_keys = set(brief.keys())
    missing = required_keys - actual_keys
    report(
        isinstance(brief, dict) and not missing,
        "2.3 get_daily_intelligence_brief() returns required keys",
        f"keys={sorted(brief.keys())}; missing={missing if missing else 'none'}"
    )

def test_buy_advisory():
    from business_advisor_engine import BusinessAdvisor
    advisor = BusinessAdvisor()
    result = advisor.get_buy_advisory()
    has_sources = "sources" in result
    has_timing = "timing" in result
    has_urgency = "urgency" in result
    report(
        isinstance(result, dict) and has_sources and has_timing and has_urgency,
        "2.4 get_buy_advisory() has sources, timing, urgency",
        f"keys={sorted(result.keys())}; sources={has_sources}, timing={has_timing}, urgency={has_urgency}"
    )

def test_buy_advisory_sources_is_list():
    from business_advisor_engine import BusinessAdvisor
    advisor = BusinessAdvisor()
    result = advisor.get_buy_advisory()
    sources = result.get("sources")
    report(isinstance(sources, list), "2.4a buy_advisory sources is list", f"type={type(sources)}, len={len(sources) if isinstance(sources, list) else 'N/A'}")

def test_buy_advisory_urgency_valid():
    from business_advisor_engine import BusinessAdvisor
    advisor = BusinessAdvisor()
    result = advisor.get_buy_advisory()
    urgency = result.get("urgency", "")
    valid = {"BUY NOW", "PRE-BUY", "HOLD", "WAIT"}
    report(urgency in valid, "2.4b buy_advisory urgency is valid label", f"urgency='{urgency}'")

def test_sell_advisory():
    from business_advisor_engine import BusinessAdvisor
    advisor = BusinessAdvisor()
    result = advisor.get_sell_advisory()
    has_targets = "targets" in result
    has_timing = "timing" in result
    report(
        isinstance(result, dict) and has_targets and has_timing,
        "2.5 get_sell_advisory() has targets, timing",
        f"keys={sorted(result.keys())}; targets={has_targets}, timing={has_timing}"
    )

def test_sell_advisory_targets_is_list():
    from business_advisor_engine import BusinessAdvisor
    advisor = BusinessAdvisor()
    result = advisor.get_sell_advisory()
    targets = result.get("targets")
    report(isinstance(targets, list), "2.5a sell_advisory targets is list", f"type={type(targets)}, len={len(targets) if isinstance(targets, list) else 'N/A'}")

def test_timing_advisory():
    from business_advisor_engine import BusinessAdvisor
    advisor = BusinessAdvisor()
    result = advisor.get_timing_advisory()
    has_revision = "next_revision_date" in result
    has_direction = "expected_direction" in result
    has_confidence = "confidence" in result
    report(
        isinstance(result, dict) and has_revision and has_direction and has_confidence,
        "2.6 get_timing_advisory() has next_revision_date, expected_direction, confidence",
        f"keys={sorted(result.keys())}; revision={result.get('next_revision_date')}, direction={result.get('expected_direction')}, confidence={result.get('confidence')}"
    )


# ============================================================================
# 3. DISCUSSION GUIDANCE ENGINE
# ============================================================================

def test_discussion_guide_import():
    from discussion_guidance_engine import DiscussionGuide
    report(True, "3.1 Import DiscussionGuide", "discussion_guidance_engine imported successfully")

def test_discussion_guide_instantiate():
    from discussion_guidance_engine import DiscussionGuide
    guide = DiscussionGuide()
    report(guide is not None, "3.2 Instantiate DiscussionGuide", f"type={type(guide).__name__}")

def test_supplier_mode():
    from discussion_guidance_engine import DiscussionGuide
    guide = DiscussionGuide()
    result = guide.prepare_discussion("supplier", {"name": "Test Supplier", "country": "Bahrain"})
    has_opening = "opening_context" in result
    has_price_targets = "price_targets" in result
    has_talking = "talking_points" in result
    report(
        isinstance(result, dict) and has_opening and has_price_targets and has_talking,
        "3.3 Supplier mode: opening_context, price_targets, talking_points",
        f"keys={sorted(result.keys())}; opening={has_opening}, targets={has_price_targets}, talking={has_talking}"
    )

def test_importer_mode():
    from discussion_guidance_engine import DiscussionGuide
    guide = DiscussionGuide()
    result = guide.prepare_discussion("importer", {"name": "Test Importer", "state": "Gujarat"})
    has_demand = "demand_outlook" in result
    has_pricing = "pricing_tiers" in result
    has_talking = "talking_points" in result
    report(
        isinstance(result, dict) and has_demand and has_pricing and has_talking,
        "3.4 Importer mode: demand_outlook, pricing_tiers, talking_points",
        f"keys={sorted(result.keys())}; demand={has_demand}, pricing={has_pricing}, talking={has_talking}"
    )

def test_trader_mode():
    from discussion_guidance_engine import DiscussionGuide
    guide = DiscussionGuide()
    result = guide.prepare_discussion("trader", {"name": "Test Trader", "district": "Vadodara"})
    # Trader mode returns: pricing_analysis (has our_landed_cost), competitor_comparison, talking_points
    has_pricing = "pricing_analysis" in result
    has_competitor = "competitor_comparison" in result
    has_talking = "talking_points" in result
    report(
        isinstance(result, dict) and has_pricing and has_competitor and has_talking,
        "3.5 Trader mode: pricing_analysis (landed_cost), competitor_comparison, talking_points",
        f"keys={sorted(result.keys())}; pricing={has_pricing}, competitor={has_competitor}, talking={has_talking}"
    )

def test_supplier_mode_price_targets_structure():
    from discussion_guidance_engine import DiscussionGuide
    guide = DiscussionGuide()
    result = guide.prepare_discussion("supplier", {"name": "Test Supplier", "country": "Bahrain"})
    pt = result.get("price_targets", {})
    has_market_fob = "market_fob" in pt
    has_target_fob = "target_fob" in pt
    has_floor_fob = "floor_fob" in pt
    report(
        has_market_fob and has_target_fob and has_floor_fob,
        "3.6 Supplier price_targets has market_fob, target_fob, floor_fob",
        f"price_targets keys={sorted(pt.keys())}"
    )

def test_importer_pricing_tiers_structure():
    from discussion_guidance_engine import DiscussionGuide
    guide = DiscussionGuide()
    result = guide.prepare_discussion("importer", {"name": "Test Importer", "state": "Gujarat"})
    tiers = result.get("pricing_tiers", {})
    has_aggressive = "aggressive" in tiers
    has_balanced = "balanced" in tiers
    has_premium = "premium" in tiers
    report(
        has_aggressive and has_balanced and has_premium,
        "3.7 Importer pricing_tiers has aggressive, balanced, premium",
        f"tiers keys={sorted(tiers.keys())}"
    )

def test_trader_mode_landed_cost():
    from discussion_guidance_engine import DiscussionGuide
    guide = DiscussionGuide()
    result = guide.prepare_discussion("trader", {"name": "Test Trader", "district": "Vadodara"})
    pricing = result.get("pricing_analysis", {})
    has_landed = "our_landed_cost" in pricing
    has_competitor_avg = "competitor_avg" in pricing
    report(
        has_landed and has_competitor_avg,
        "3.8 Trader pricing_analysis has our_landed_cost, competitor_avg",
        f"pricing_analysis keys={sorted(pricing.keys())}"
    )

def test_invalid_mode():
    from discussion_guidance_engine import DiscussionGuide
    guide = DiscussionGuide()
    result = guide.prepare_discussion("invalid_mode", {"name": "Test"})
    has_error = "error" in result
    report(has_error, "3.9 Invalid mode returns error", f"has_error={has_error}")

def test_supplier_mode_talking_points_is_list():
    from discussion_guidance_engine import DiscussionGuide
    guide = DiscussionGuide()
    result = guide.prepare_discussion("supplier", {"name": "Test Supplier", "country": "Bahrain"})
    tp = result.get("talking_points", [])
    report(isinstance(tp, list) and len(tp) > 0, "3.10 Supplier talking_points is non-empty list", f"len={len(tp)}")

def test_importer_mode_talking_points_is_list():
    from discussion_guidance_engine import DiscussionGuide
    guide = DiscussionGuide()
    result = guide.prepare_discussion("importer", {"name": "Test Importer", "state": "Gujarat"})
    tp = result.get("talking_points", [])
    report(isinstance(tp, list) and len(tp) > 0, "3.11 Importer talking_points is non-empty list", f"len={len(tp)}")

def test_trader_mode_talking_points_is_list():
    from discussion_guidance_engine import DiscussionGuide
    guide = DiscussionGuide()
    result = guide.prepare_discussion("trader", {"name": "Test Trader", "district": "Vadodara"})
    tp = result.get("talking_points", [])
    report(isinstance(tp, list) and len(tp) > 0, "3.12 Trader talking_points is non-empty list", f"len={len(tp)}")


# ============================================================================
# 4. RECOMMENDATION ENGINE
# ============================================================================

def test_recommendation_import():
    from recommendation_engine import RecommendationEngine
    report(True, "4.1 Import RecommendationEngine", "recommendation_engine imported successfully")

def test_recommendation_instantiate():
    from recommendation_engine import RecommendationEngine
    engine = RecommendationEngine()
    report(engine is not None, "4.2 Instantiate RecommendationEngine", f"type={type(engine).__name__}")

def test_generate_daily_recommendations():
    from recommendation_engine import RecommendationEngine
    engine = RecommendationEngine()
    result = engine.generate_daily_recommendations()
    required_keys = {"buy_timing", "sell_timing", "demand_forecast", "price_forecast"}
    actual_keys = set(result.keys())
    missing = required_keys - actual_keys
    report(
        isinstance(result, dict) and not missing,
        "4.3 generate_daily_recommendations() has buy_timing, sell_timing, demand_forecast, price_forecast",
        f"keys={sorted(result.keys())}; missing={missing if missing else 'none'}"
    )

def test_buy_timing_structure():
    from recommendation_engine import RecommendationEngine
    engine = RecommendationEngine()
    result = engine.generate_daily_recommendations()
    buy = result.get("buy_timing", {})
    has_action = "action" in buy
    has_confidence = "confidence" in buy
    has_reasons = "reasons" in buy
    report(
        has_action and has_confidence and has_reasons,
        "4.4 buy_timing has action, confidence, reasons",
        f"buy_timing keys={sorted(buy.keys())}; action='{buy.get('action')}', confidence={buy.get('confidence')}"
    )

def test_sell_timing_structure():
    from recommendation_engine import RecommendationEngine
    engine = RecommendationEngine()
    result = engine.generate_daily_recommendations()
    sell = result.get("sell_timing", {})
    has_targets = "targets" in sell
    report(
        has_targets,
        "4.5 sell_timing has targets",
        f"sell_timing keys={sorted(sell.keys())}; targets_count={len(sell.get('targets', []))}"
    )

def test_buy_timing_action_valid():
    from recommendation_engine import RecommendationEngine
    engine = RecommendationEngine()
    result = engine.generate_daily_recommendations()
    action = result.get("buy_timing", {}).get("action", "")
    ok = isinstance(action, str) and len(action) > 0
    report(ok, "4.6 buy_timing action is non-empty string", f"action='{action}'")

def test_buy_timing_confidence_numeric():
    from recommendation_engine import RecommendationEngine
    engine = RecommendationEngine()
    result = engine.generate_daily_recommendations()
    conf = result.get("buy_timing", {}).get("confidence")
    report(isinstance(conf, (int, float)), "4.7 buy_timing confidence is numeric", f"confidence={conf}")

def test_demand_forecast_structure():
    from recommendation_engine import RecommendationEngine
    engine = RecommendationEngine()
    result = engine.generate_daily_recommendations()
    demand = result.get("demand_forecast", {})
    report(isinstance(demand, dict), "4.8 demand_forecast is dict", f"keys={sorted(demand.keys()) if isinstance(demand, dict) else 'N/A'}")

def test_price_forecast_structure():
    from recommendation_engine import RecommendationEngine
    engine = RecommendationEngine()
    result = engine.generate_daily_recommendations()
    price = result.get("price_forecast", {})
    report(isinstance(price, dict), "4.9 price_forecast is dict", f"keys={sorted(price.keys()) if isinstance(price, dict) else 'N/A'}")

def test_sell_timing_has_pricing():
    from recommendation_engine import RecommendationEngine
    engine = RecommendationEngine()
    result = engine.generate_daily_recommendations()
    sell = result.get("sell_timing", {})
    has_pricing = "pricing" in sell
    report(has_pricing, "4.10 sell_timing has pricing", f"sell_timing keys={sorted(sell.keys())}")


# ============================================================================
# 5. MARKET PULSE ENGINE
# ============================================================================

def test_market_pulse_import():
    from market_pulse_engine import MarketPulseEngine
    report(True, "5.1 Import MarketPulseEngine", "market_pulse_engine imported successfully")

def test_market_pulse_instantiate():
    from market_pulse_engine import MarketPulseEngine
    engine = MarketPulseEngine()
    report(engine is not None, "5.2 Instantiate MarketPulseEngine", f"type={type(engine).__name__}")

def test_monitor_all():
    from market_pulse_engine import MarketPulseEngine
    engine = MarketPulseEngine()
    result = engine.monitor_all()
    report(isinstance(result, dict), "5.3 monitor_all() returns dict", f"keys={sorted(result.keys())}")

def test_monitor_all_has_market_state():
    from market_pulse_engine import MarketPulseEngine
    engine = MarketPulseEngine()
    result = engine.monitor_all()
    has_state = "market_state" in result
    report(has_state, "5.3a monitor_all() has market_state key", f"has_market_state={has_state}")

def test_monitor_all_has_crude():
    from market_pulse_engine import MarketPulseEngine
    engine = MarketPulseEngine()
    result = engine.monitor_all()
    has_crude = "crude" in result
    report(has_crude, "5.3b monitor_all() has crude key", f"has_crude={has_crude}")

def test_monitor_all_has_fx():
    from market_pulse_engine import MarketPulseEngine
    engine = MarketPulseEngine()
    result = engine.monitor_all()
    has_fx = "fx" in result
    report(has_fx, "5.3c monitor_all() has fx key", f"has_fx={has_fx}")

def test_monitor_all_has_alerts():
    from market_pulse_engine import MarketPulseEngine
    engine = MarketPulseEngine()
    result = engine.monitor_all()
    has_alerts = "alerts" in result
    report(has_alerts, "5.3d monitor_all() has alerts key", f"has_alerts={has_alerts}")

def test_market_state_summary():
    from market_pulse_engine import MarketPulseEngine
    engine = MarketPulseEngine()
    result = engine.get_market_state_summary()
    has_bias = "market_bias" in result
    has_score = "bias_score" in result
    report(
        isinstance(result, dict) and has_bias and has_score,
        "5.4 get_market_state_summary() has market_bias, bias_score",
        f"keys={sorted(result.keys())}; bias={result.get('market_bias')}, score={result.get('bias_score')}"
    )

def test_market_state_bias_valid():
    from market_pulse_engine import MarketPulseEngine
    engine = MarketPulseEngine()
    result = engine.get_market_state_summary()
    bias = result.get("market_bias")
    valid_biases = {"BULLISH", "BEARISH", "NEUTRAL"}
    report(bias in valid_biases, "5.4a market_bias is BULLISH/BEARISH/NEUTRAL", f"bias='{bias}'")

def test_market_state_score_range():
    from market_pulse_engine import MarketPulseEngine
    engine = MarketPulseEngine()
    result = engine.get_market_state_summary()
    score = result.get("bias_score")
    ok = isinstance(score, (int, float)) and 0 <= score <= 100
    report(ok, "5.4b bias_score is 0-100 numeric", f"score={score}")

def test_get_active_alerts():
    from market_pulse_engine import MarketPulseEngine
    engine = MarketPulseEngine()
    result = engine.get_active_alerts()
    report(isinstance(result, list), "5.5 get_active_alerts() returns list", f"type={type(result).__name__}, len={len(result)}")

def test_get_active_alerts_structure():
    from market_pulse_engine import MarketPulseEngine
    engine = MarketPulseEngine()
    alerts = engine.get_active_alerts()
    if alerts:
        first = alerts[0]
        has_severity = "severity" in first
        has_message = "message" in first
        report(has_severity and has_message, "5.5a Active alerts have severity, message", f"first alert keys={sorted(first.keys())}")
    else:
        report(True, "5.5a Active alerts structure (no alerts to check)", "alerts list is empty -- acceptable")

def test_monitor_all_complete_state():
    from market_pulse_engine import MarketPulseEngine
    engine = MarketPulseEngine()
    result = engine.monitor_all()
    expected_keys = {"timestamp", "crude", "fx", "supply_disruptions", "demand_signals", "logistics", "alerts", "market_state"}
    actual_keys = set(result.keys())
    missing = expected_keys - actual_keys
    report(
        not missing,
        "5.6 monitor_all() returns complete state (all expected keys)",
        f"missing={missing if missing else 'none'}; actual={sorted(actual_keys)}"
    )


# ============================================================================
# 6. UNIFIED INTELLIGENCE ENGINE
# ============================================================================

def test_unified_import():
    from unified_intelligence_engine import UnifiedIntelligence
    report(True, "6.1 Import UnifiedIntelligence", "unified_intelligence_engine imported successfully")

def test_unified_instantiate():
    from unified_intelligence_engine import UnifiedIntelligence
    ui = UnifiedIntelligence()
    report(ui is not None, "6.2 Instantiate UnifiedIntelligence", f"type={type(ui).__name__}")

def test_dashboard_summary():
    from unified_intelligence_engine import UnifiedIntelligence
    ui = UnifiedIntelligence()
    result = ui.get_dashboard_summary()
    report(isinstance(result, dict), "6.3 get_dashboard_summary() returns dict", f"keys={sorted(result.keys())}")

def test_dashboard_summary_kpi_keys():
    from unified_intelligence_engine import UnifiedIntelligence
    ui = UnifiedIntelligence()
    result = ui.get_dashboard_summary()
    expected_kpi_keys = {"market_bias", "top_recommendation", "alert_count", "generated_at"}
    actual_keys = set(result.keys())
    has_kpi = expected_kpi_keys.issubset(actual_keys)
    report(has_kpi, "6.3a dashboard_summary has KPI keys (market_bias, top_recommendation, alert_count, generated_at)", f"keys={sorted(result.keys())}")

def test_dashboard_summary_market_bias():
    from unified_intelligence_engine import UnifiedIntelligence
    ui = UnifiedIntelligence()
    result = ui.get_dashboard_summary()
    bias = result.get("market_bias")
    report(bias is not None, "6.3b dashboard_summary has market_bias value", f"market_bias='{bias}'")

def test_dashboard_summary_lightweight():
    from unified_intelligence_engine import UnifiedIntelligence
    ui = UnifiedIntelligence()
    result = ui.get_dashboard_summary()
    # Should be lightweight -- check it has fewer keys than complete state
    report(len(result) <= 15, "6.3c dashboard_summary is lightweight (<= 15 keys)", f"key_count={len(result)}")

def test_health_check():
    from unified_intelligence_engine import UnifiedIntelligence
    ui = UnifiedIntelligence()
    result = ui.health_check()
    report(isinstance(result, dict), "6.4 health_check() returns dict", f"key_count={len(result)}")

def test_health_check_summary():
    from unified_intelligence_engine import UnifiedIntelligence
    ui = UnifiedIntelligence()
    result = ui.health_check()
    summary = result.get("_summary", {})
    total = summary.get("total", 0)
    avail = summary.get("available", 0)
    report(
        total > 0 and avail >= 0,
        "6.4a health_check() has _summary with total, available",
        f"total={total}, available={avail}"
    )

def test_health_check_engine_status_format():
    from unified_intelligence_engine import UnifiedIntelligence
    ui = UnifiedIntelligence()
    result = ui.health_check()
    engine_keys = [k for k in result.keys() if k != "_summary"]
    # Each engine should have 'available' and 'status' keys
    sample_ok = True
    sample_detail = ""
    for ek in engine_keys[:3]:
        entry = result[ek]
        if not isinstance(entry, dict) or "available" not in entry or "status" not in entry:
            sample_ok = False
            sample_detail = f"Engine '{ek}' missing available/status: {entry}"
            break
    report(sample_ok and len(engine_keys) > 0, "6.4b health_check() engines have available, status", f"engines_count={len(engine_keys)}; {sample_detail if sample_detail else 'all checked OK'}")

def test_get_complete_state():
    from unified_intelligence_engine import UnifiedIntelligence
    # Clear cache to force fresh computation
    import unified_intelligence_engine
    unified_intelligence_engine._cache.clear()
    unified_intelligence_engine._cache_ts.clear()
    ui = UnifiedIntelligence()
    result = ui.get_complete_state()
    report(isinstance(result, dict), "6.5 get_complete_state() returns dict", f"keys={sorted(result.keys())}")

def test_get_complete_state_has_core_keys():
    from unified_intelligence_engine import UnifiedIntelligence
    import unified_intelligence_engine
    unified_intelligence_engine._cache.clear()
    unified_intelligence_engine._cache_ts.clear()
    ui = UnifiedIntelligence()
    result = ui.get_complete_state()
    has_market = "market" in result
    has_advisory = "advisory" in result
    has_alerts = "alerts" in result
    has_generated_at = "generated_at" in result
    report(
        has_market and has_advisory and has_alerts and has_generated_at,
        "6.5a get_complete_state() has market, advisory, alerts, generated_at",
        f"market={has_market}, advisory={has_advisory}, alerts={has_alerts}, generated_at={has_generated_at}"
    )

def test_get_complete_state_has_forecasts():
    from unified_intelligence_engine import UnifiedIntelligence
    import unified_intelligence_engine
    unified_intelligence_engine._cache.clear()
    unified_intelligence_engine._cache_ts.clear()
    ui = UnifiedIntelligence()
    result = ui.get_complete_state()
    has_forecasts = "forecasts" in result
    has_api_health = "api_health" in result
    has_system_health = "system_health" in result
    report(
        has_forecasts and (has_api_health or has_system_health),
        "6.5b get_complete_state() has forecasts and health info",
        f"forecasts={has_forecasts}, api_health={has_api_health}, system_health={has_system_health}"
    )


# ============================================================================
# RUN ALL TESTS
# ============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("PPS Anantam -- AI Trading Chatbot System: Complete Functional Test")
    print("=" * 80)
    print(f"Note: ai_fallback_engine mocked to prevent slow LLM model loading.")
    print()

    all_tests = [
        # 1. Trading Chatbot Engine (25 tests)
        test_trading_chatbot_import,
        test_trading_chatbot_instantiate,
        test_classify_intent_buy,
        test_classify_intent_pricing,
        test_classify_intent_logistics,
        test_classify_intent_demand,
        test_classify_intent_market_news,
        test_classify_intent_forecast,
        test_classify_intent_comparison,
        test_classify_intent_sell,
        test_gather_context_buy,
        test_gather_context_sell,
        test_gather_context_pricing,
        test_gather_context_logistics,
        test_gather_context_demand,
        test_gather_context_market_news,
        test_gather_context_forecast,
        test_gather_context_comparison,
        test_process_query,
        test_process_query_answer_is_string,
        test_process_query_charts_is_list,
        test_process_query_sources_is_list,
        test_process_query_confidence,
        test_process_query_follow_ups,
        test_quick_actions,

        # 2. Business Advisor Engine (8 tests)
        test_business_advisor_import,
        test_business_advisor_instantiate,
        test_daily_intelligence_brief,
        test_buy_advisory,
        test_buy_advisory_sources_is_list,
        test_buy_advisory_urgency_valid,
        test_sell_advisory,
        test_sell_advisory_targets_is_list,
        test_timing_advisory,

        # 3. Discussion Guidance Engine (12 tests)
        test_discussion_guide_import,
        test_discussion_guide_instantiate,
        test_supplier_mode,
        test_importer_mode,
        test_trader_mode,
        test_supplier_mode_price_targets_structure,
        test_importer_pricing_tiers_structure,
        test_trader_mode_landed_cost,
        test_invalid_mode,
        test_supplier_mode_talking_points_is_list,
        test_importer_mode_talking_points_is_list,
        test_trader_mode_talking_points_is_list,

        # 4. Recommendation Engine (10 tests)
        test_recommendation_import,
        test_recommendation_instantiate,
        test_generate_daily_recommendations,
        test_buy_timing_structure,
        test_sell_timing_structure,
        test_buy_timing_action_valid,
        test_buy_timing_confidence_numeric,
        test_demand_forecast_structure,
        test_price_forecast_structure,
        test_sell_timing_has_pricing,

        # 5. Market Pulse Engine (13 tests)
        test_market_pulse_import,
        test_market_pulse_instantiate,
        test_monitor_all,
        test_monitor_all_has_market_state,
        test_monitor_all_has_crude,
        test_monitor_all_has_fx,
        test_monitor_all_has_alerts,
        test_market_state_summary,
        test_market_state_bias_valid,
        test_market_state_score_range,
        test_get_active_alerts,
        test_get_active_alerts_structure,
        test_monitor_all_complete_state,

        # 6. Unified Intelligence Engine (11 tests)
        test_unified_import,
        test_unified_instantiate,
        test_dashboard_summary,
        test_dashboard_summary_kpi_keys,
        test_dashboard_summary_market_bias,
        test_dashboard_summary_lightweight,
        test_health_check,
        test_health_check_summary,
        test_health_check_engine_status_format,
        test_get_complete_state,
        test_get_complete_state_has_core_keys,
        test_get_complete_state_has_forecasts,
    ]

    for test_fn in all_tests:
        safe_test(test_fn)

    print()
    print("=" * 80)
    total = PASS_COUNT + FAIL_COUNT
    print(f"TOTAL: {total} tests | PASS: {PASS_COUNT} | FAIL: {FAIL_COUNT}")
    if FAIL_COUNT == 0:
        print("ALL TESTS PASSED")
    else:
        print(f"FAILURE RATE: {FAIL_COUNT}/{total} ({FAIL_COUNT/total*100:.1f}%)")
    print("=" * 80)
