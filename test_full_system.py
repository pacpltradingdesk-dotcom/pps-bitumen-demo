#!/usr/bin/env python3
"""
PPS Anantam Bitumen Sales Dashboard -- Full System Test
========================================================
Comprehensive import, dispatch, and function-availability test.
Does NOT start Streamlit -- pure Python validation.
"""
from __future__ import annotations

import importlib
import sys
import os
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Fix Windows console encoding -- must be done BEFORE any print()
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Bootstrap -- make sure the project root is on sys.path
# ---------------------------------------------------------------------------
PROJECT_DIR = Path(__file__).resolve().parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))
os.chdir(PROJECT_DIR)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
PASS = "[PASS]"
FAIL = "[FAIL]"
WARN = "[WARN]"

pass_count = 0
fail_count = 0
warn_count = 0


def _ok(label: str, detail: str = ""):
    global pass_count
    pass_count += 1
    msg = f"  {PASS} {label}"
    if detail:
        msg += f"  -- {detail}"
    print(msg)


def _fail(label: str, detail: str = ""):
    global fail_count
    fail_count += 1
    msg = f"  {FAIL} {label}"
    if detail:
        msg += f"  -- {detail}"
    print(msg)


def _warn(label: str, detail: str = ""):
    global warn_count
    warn_count += 1
    msg = f"  {WARN} {label}"
    if detail:
        msg += f"  -- {detail}"
    print(msg)


# ===================================================================
# PART 1 -- Import Test (ALL engines)
# ===================================================================
print("=" * 72)
print("PART 1: ENGINE IMPORT TEST")
print("=" * 72)

engines = [
    "database", "calculation_engine", "settings_engine", "chart_engine",
    "opportunity_engine", "negotiation_engine", "communication_engine",
    "crm_engine", "sync_engine", "api_hub_engine", "sre_engine",
    "market_intelligence_engine", "purchase_advisor_engine", "ml_forecast_engine",
    "finbert_engine", "rag_engine", "ai_fallback_engine", "ai_data_layer",
    "ai_assistant_engine", "maritime_intelligence_engine", "infra_demand_engine",
    "supply_chain_engine", "correlation_engine", "forward_strategy_engine",
    "director_briefing_engine", "news_engine", "anomaly_engine",
    "backtest_engine", "model_monitor", "signal_weight_learner",
    "page_registry", "log_engine", "vault_engine",
    # NEW engines (Steps 2-10)
    "free_api_registry", "interactive_chart_helpers",
    "market_pulse_engine", "recommendation_engine", "business_advisor_engine",
    "discussion_guidance_engine", "trading_chatbot_engine", "unified_intelligence_engine",
]

imported_modules: dict[str, object] = {}

for name in engines:
    try:
        mod = importlib.import_module(name)
        imported_modules[name] = mod
        _ok(name)
    except Exception as exc:
        short = str(exc).split("\n")[0][:120]
        _fail(name, short)


# ===================================================================
# PART 2 -- Command Intel Dashboard Import Test
# ===================================================================
print()
print("=" * 72)
print("PART 2: COMMAND INTEL DASHBOARD IMPORT TEST")
print("=" * 72)

command_intel_files = [
    "command_intel.global_market_dashboard",
    "command_intel.refinery_supply_dashboard",
    "command_intel.real_time_insights_dashboard",
    "command_intel.recommendation_dashboard",
    "command_intel.business_advisor_dashboard",
    "command_intel.discussion_guidance_dashboard",
    "command_intel.intelligence_hub_dashboard",
]

for name in command_intel_files:
    try:
        mod = importlib.import_module(name)
        imported_modules[name] = mod
        _ok(name)
    except Exception as exc:
        short = str(exc).split("\n")[0][:120]
        _fail(name, short)


# ===================================================================
# PART 3 -- Nav Config Integrity
# ===================================================================
print()
print("=" * 72)
print("PART 3: NAV CONFIG INTEGRITY (page dispatch coverage)")
print("=" * 72)

# Load nav_config
try:
    import nav_config
    _ok("nav_config imported")
except Exception as exc:
    _fail("nav_config import", str(exc)[:120])
    nav_config = None

if nav_config is not None:
    # Collect every page string from MODULE_NAV
    all_nav_pages: list[str] = []
    for mod_key, mod_data in nav_config.MODULE_NAV.items():
        for tab in mod_data.get("tabs", []):
            pg = tab.get("page", "")
            if pg and not pg.startswith("_"):
                all_nav_pages.append(pg)
            for also_pg in tab.get("also", []):
                all_nav_pages.append(also_pg)

    # Read dashboard.py and extract every page string from dispatch chain
    dashboard_path = PROJECT_DIR / "dashboard.py"
    dashboard_src = dashboard_path.read_text(encoding="utf-8")

    # Match patterns like: selected_page == "..." or selected_page in ("...", "...")
    dispatch_pages: set[str] = set()
    # Pattern 1: selected_page == "..."
    for m in re.finditer(r'selected_page\s*==\s*"([^"]+)"', dashboard_src):
        dispatch_pages.add(m.group(1))
    # Pattern 2: selected_page in ("...", "...")
    for m in re.finditer(r'selected_page\s+in\s*\(([^)]+)\)', dashboard_src):
        inner = m.group(1)
        for sm in re.finditer(r'"([^"]+)"', inner):
            dispatch_pages.add(sm.group(1))

    print(f"\n  Nav pages total:      {len(all_nav_pages)}")
    print(f"  Dispatch handlers:    {len(dispatch_pages)}")

    missing_dispatch: list[str] = []
    for pg in all_nav_pages:
        if pg not in dispatch_pages:
            missing_dispatch.append(pg)

    if missing_dispatch:
        print(f"\n  Pages in nav_config WITHOUT a dispatch handler in dashboard.py:")
        for pg in sorted(set(missing_dispatch)):
            _fail(f"NO DISPATCH: {pg}")
    else:
        _ok("All nav pages have matching dispatch handlers")

    # Bonus: check for dispatch pages NOT in nav (orphans)
    nav_set = set(all_nav_pages)
    orphans = [pg for pg in sorted(dispatch_pages) if pg not in nav_set]
    if orphans:
        print(f"\n  Dispatch pages NOT reachable from nav_config ({len(orphans)}):")
        for pg in orphans:
            _warn(f"ORPHAN DISPATCH: {pg}")
    else:
        _ok("No orphan dispatch handlers (all dispatches are nav-reachable)")


# ===================================================================
# PART 4 -- Function Availability Test
# ===================================================================
print()
print("=" * 72)
print("PART 4: FUNCTION / ATTRIBUTE AVAILABILITY TEST")
print("=" * 72)

required_functions: dict[str, list[str]] = {
    "market_pulse_engine":       ["monitor_all", "get_active_alerts", "get_market_state_summary"],
    "recommendation_engine":     ["generate_daily_recommendations", "get_latest_recommendations", "track_accuracy"],
    "business_advisor_engine":   ["get_daily_brief", "get_buy_advisory", "get_sell_advisory", "get_timing_advisory"],
    "discussion_guidance_engine": ["prepare_discussion", "get_discussion_modes"],
    "trading_chatbot_engine":    ["ask_trading_question", "get_chatbot_status", "QUICK_ACTIONS"],
    "unified_intelligence_engine": ["get_complete_state", "get_dashboard_summary", "refresh_intelligence", "health_check"],
}

for engine_name, attrs in required_functions.items():
    mod = imported_modules.get(engine_name)
    if mod is None:
        _fail(f"{engine_name}: skipped (import failed)")
        continue
    for attr in attrs:
        if hasattr(mod, attr):
            obj = getattr(mod, attr)
            kind = "function" if callable(obj) else type(obj).__name__
            _ok(f"{engine_name}.{attr}", kind)
        else:
            _fail(f"{engine_name}.{attr}", "NOT FOUND")


# ===================================================================
# PART 5 -- API Connector Test
# ===================================================================
print()
print("=" * 72)
print("PART 5: API HUB ENGINE CONNECTOR TEST")
print("=" * 72)

original_connectors = [
    "connect_eia", "connect_fx", "connect_comtrade", "connect_weather",
    "connect_news", "connect_ports", "connect_refinery", "connect_maritime",
    "connect_bdi", "connect_gold",
]

new_connectors = [
    "connect_rbi_fx", "connect_opec_monthly", "connect_eia_steo",
    "connect_dgft_imports", "connect_nhai_tenders", "connect_cement_index",
    "connect_iocl_circular", "connect_fred_data",
]

api_mod = imported_modules.get("api_hub_engine")
if api_mod is None:
    _fail("api_hub_engine: skipped (import failed)")
else:
    print("\n  -- Original 10 connectors --")
    for fn_name in original_connectors:
        if hasattr(api_mod, fn_name) and callable(getattr(api_mod, fn_name)):
            _ok(f"api_hub_engine.{fn_name}")
        else:
            _fail(f"api_hub_engine.{fn_name}", "NOT FOUND or not callable")

    print("\n  -- New 8 connectors --")
    for fn_name in new_connectors:
        if hasattr(api_mod, fn_name) and callable(getattr(api_mod, fn_name)):
            _ok(f"api_hub_engine.{fn_name}")
        else:
            _fail(f"api_hub_engine.{fn_name}", "NOT FOUND or not callable")


# ===================================================================
# SUMMARY
# ===================================================================
print()
print("=" * 72)
print("FINAL SUMMARY")
print("=" * 72)
total = pass_count + fail_count + warn_count
print(f"  Total checks:  {total}")
print(f"  PASSED:        {pass_count}")
print(f"  FAILED:        {fail_count}")
print(f"  WARNINGS:      {warn_count}")
print()
if fail_count == 0:
    print("  >>> ALL TESTS PASSED <<<")
else:
    print(f"  >>> {fail_count} FAILURE(S) DETECTED <<<")
print("=" * 72)

sys.exit(0 if fail_count == 0 else 1)
