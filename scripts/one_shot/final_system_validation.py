"""
PPS Anantam -- Final System Validation (Step 12)
=================================================
Comprehensive retest after all fixes applied.
Tests: syntax, dispatch chain, imports, navigation, engine integration,
       data files, and export functions.

Run:  python final_system_validation.py
"""
from __future__ import annotations

import importlib
import json
import os
import py_compile
import re
import sys
import threading
import traceback  # noqa: F401
from pathlib import Path

# -- Setup --------------------------------------------------------------------
BASE = Path(__file__).resolve().parent
os.chdir(BASE)
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

# Fix Windows console Unicode handling
os.environ["PYTHONIOENCODING"] = "utf-8"
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PASS_COUNT = 0
FAIL_COUNT = 0
RESULTS: list[str] = []


def _safe_str(s: str) -> str:
    """Replace non-ASCII chars for safe console printing on Windows."""
    return s.encode("ascii", "replace").decode("ascii")


def record(passed: bool, category: str, test: str, detail: str = ""):
    global PASS_COUNT, FAIL_COUNT
    tag = "PASS" if passed else "FAIL"
    if passed:
        PASS_COUNT += 1
    else:
        FAIL_COUNT += 1
    line = f"[{tag}] {category}.{test}"
    if detail:
        line += f" -- {detail}"
    RESULTS.append(line)
    print(_safe_str(line))


def run_with_timeout(fn, timeout_sec=45):
    """Run fn() in a thread with a timeout. Returns (result, error_str|None)."""
    result_box = [None]
    error_box = [None]

    def _worker():
        try:
            result_box[0] = fn()
        except Exception as e:
            error_box[0] = f"{type(e).__name__}: {str(e)[:200]}"

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    t.join(timeout=timeout_sec)
    if t.is_alive():
        return None, f"TIMEOUT after {timeout_sec}s"
    if error_box[0]:
        return None, error_box[0]
    return result_box[0], None


# =============================================================================
# 1. SYNTAX CHECK -- py_compile on all key files
# =============================================================================
print("\n" + "=" * 70)
print("1. SYNTAX CHECK (py_compile)")
print("=" * 70)

SYNTAX_FILES = [
    "dashboard.py",
    "free_api_registry.py",
    "interactive_chart_helpers.py",
    "market_pulse_engine.py",
    "recommendation_engine.py",
    "business_advisor_engine.py",
    "discussion_guidance_engine.py",
    "trading_chatbot_engine.py",
    "unified_intelligence_engine.py",
    "nav_config.py",
    "sync_engine.py",
    "ai_data_layer.py",
    "chart_engine.py",
    "api_hub_engine.py",
]

for fname in SYNTAX_FILES:
    fpath = BASE / fname
    try:
        py_compile.compile(str(fpath), doraise=True)
        record(True, "Syntax", fname, "compiles clean")
    except py_compile.PyCompileError as e:
        record(False, "Syntax", fname, str(e)[:200])


# =============================================================================
# 2. DASHBOARD DISPATCH CHAIN VERIFICATION
# =============================================================================
print("\n" + "=" * 70)
print("2. DISPATCH CHAIN VERIFICATION")
print("=" * 70)

dashboard_src = (BASE / "dashboard.py").read_text(encoding="utf-8")
lines = dashboard_src.splitlines()

# Find all lines with `if selected_page ==` (standalone if, NOT elif)
if_lines = []
elif_lines = []
for i, line in enumerate(lines, 1):
    stripped = line.strip()
    if re.match(r'^if\s+selected_page\s*==', stripped):
        if_lines.append(i)
    elif re.match(r'^elif\s+selected_page\s*==', stripped):
        elif_lines.append(i)

# Test: exactly 1 standalone `if selected_page ==`
if_count = len(if_lines)
record(
    if_count == 1,
    "Dispatch", "standalone_if_count",
    f"found {if_count} standalone 'if selected_page ==' (expected 1) at line(s): {if_lines}"
)

# Test: many elif lines
elif_count = len(elif_lines)
record(
    elif_count >= 50,
    "Dispatch", "elif_count",
    f"found {elif_count} 'elif selected_page ==' branches (expected 50+)"
)

# Test: first if is around line 1579 (tolerance: +-20 lines)
if if_lines:
    first_if_line = if_lines[0]
    record(
        1550 <= first_if_line <= 1600,
        "Dispatch", "first_if_location",
        f"first 'if selected_page ==' at line {first_if_line} (expected ~1579)"
    )
else:
    record(False, "Dispatch", "first_if_location", "no standalone if found at all")

# Test: no standalone `if selected_page ==` after the first one
extra_ifs = [ln for ln in if_lines if ln != if_lines[0]] if if_lines else []
record(
    len(extra_ifs) == 0,
    "Dispatch", "no_broken_chains",
    f"extra standalone if blocks: {extra_ifs}" if extra_ifs else "all branches properly chained with elif"
)


# =============================================================================
# 3. IMPORT CHAIN -- all engines load
# =============================================================================
print("\n" + "=" * 70)
print("3. IMPORT CHAIN")
print("=" * 70)

IMPORT_MODULES = [
    "market_pulse_engine",
    "recommendation_engine",
    "business_advisor_engine",
    "discussion_guidance_engine",
    "trading_chatbot_engine",
    "unified_intelligence_engine",
    "free_api_registry",
    "interactive_chart_helpers",
]

imported_modules = {}
for mod_name in IMPORT_MODULES:
    def _do_import(name=mod_name):
        return importlib.import_module(name)

    mod, err = run_with_timeout(_do_import, timeout_sec=60)
    if err is None and mod is not None:
        imported_modules[mod_name] = mod
        record(True, "Import", mod_name, "loaded successfully")
    else:
        imported_modules[mod_name] = None
        record(False, "Import", mod_name, err or "unknown error")


# =============================================================================
# 4. NAVIGATION COMPLETENESS
# =============================================================================
print("\n" + "=" * 70)
print("4. NAVIGATION COMPLETENESS")
print("=" * 70)

try:
    import nav_config
    all_nav_pages = nav_config.all_pages()
    record(True, "Nav", "all_pages_loaded", f"{len(all_nav_pages)} pages defined")
except Exception as e:
    all_nav_pages = []
    record(False, "Nav", "all_pages_loaded", str(e)[:200])

# Check each nav page has a dispatch handler
dispatch_pages_in_dashboard = set()
for line in lines:
    stripped = line.strip()
    # Match "if/elif selected_page == '...'"
    m = re.match(r'^(?:el)?if\s+selected_page\s*==\s*["\'](.+?)["\']', stripped)
    if m:
        dispatch_pages_in_dashboard.add(m.group(1))
    # Also match "if/elif selected_page in ('...', '...')"
    m2 = re.match(r'^(?:el)?if\s+selected_page\s+in\s*\((.+?)\)', stripped)
    if m2:
        for item in re.findall(r'["\']([^"\']+)["\']', m2.group(1)):
            dispatch_pages_in_dashboard.add(item)

missing_dispatch = []
for page in all_nav_pages:
    if page not in dispatch_pages_in_dashboard:
        missing_dispatch.append(page)

record(
    len(missing_dispatch) == 0,
    "Nav", "dispatch_coverage",
    f"all {len(all_nav_pages)} pages have dispatch handlers" if not missing_dispatch
    else f"MISSING handlers for {len(missing_dispatch)} pages: {[p.encode('ascii','replace').decode() for p in missing_dispatch[:5]]}"
)

# Check MODULE_ROLE_MAP covers all modules
try:
    module_keys = set(nav_config.MODULE_NAV.keys())
    role_keys = set(nav_config.MODULE_ROLE_MAP.keys())
    missing_roles = module_keys - role_keys
    record(
        len(missing_roles) == 0,
        "Nav", "role_map_coverage",
        f"all {len(module_keys)} modules have role mappings" if not missing_roles
        else f"MISSING role mappings for {len(missing_roles)} modules"
    )
except Exception as e:
    record(False, "Nav", "role_map_coverage", str(e)[:200])


# =============================================================================
# 5. ENGINE INTEGRATION SPOT CHECK
# =============================================================================
print("\n" + "=" * 70)
print("5. ENGINE INTEGRATION SPOT CHECK")
print("=" * 70)

# 5a. MarketPulseEngine.get_market_state_summary()
def _test_market_pulse():
    mpe = imported_modules.get("market_pulse_engine")
    if not mpe:
        return {"_err": "module not imported"}
    engine = mpe.MarketPulseEngine()
    return engine.get_market_state_summary()

summary, err = run_with_timeout(_test_market_pulse, timeout_sec=30)
if err:
    record(False, "Engine", "MarketPulse_bias", err)
    record(False, "Engine", "MarketPulse_score", err)
elif summary and "_err" in summary:
    record(False, "Engine", "MarketPulse_bias", summary["_err"])
    record(False, "Engine", "MarketPulse_score", summary["_err"])
elif summary:
    keys_str = str(list(summary.keys())[:8]).encode("ascii", "replace").decode()
    has_bias = any(k in str(summary) for k in ("bias", "Bias", "market_bias", "overall_bias"))
    has_score = any(k in str(summary) for k in ("score", "Score", "composite_score", "confidence"))
    record(has_bias, "Engine", "MarketPulse_bias", f"bias field found (keys: {keys_str})")
    record(has_score, "Engine", "MarketPulse_score", f"score field found")
else:
    record(False, "Engine", "MarketPulse_bias", "returned None")
    record(False, "Engine", "MarketPulse_score", "returned None")

# 5b. RecommendationEngine.generate_daily_recommendations()
def _test_recommendation():
    rec = imported_modules.get("recommendation_engine")
    if not rec:
        return {"_err": "module not imported"}
    engine = rec.RecommendationEngine()
    return engine.generate_daily_recommendations()

recs, err = run_with_timeout(_test_recommendation, timeout_sec=30)
if err:
    record(False, "Engine", "Recommendation_buy_timing", err)
    record(False, "Engine", "Recommendation_sell_timing", err)
elif recs and "_err" in recs:
    record(False, "Engine", "Recommendation_buy_timing", recs["_err"])
    record(False, "Engine", "Recommendation_sell_timing", recs["_err"])
elif recs:
    keys_str = str(list(recs.keys())[:8]).encode("ascii", "replace").decode()
    record("buy_timing" in recs, "Engine", "Recommendation_buy_timing",
           f"buy_timing present (keys: {keys_str})")
    record("sell_timing" in recs, "Engine", "Recommendation_sell_timing",
           f"sell_timing present")
else:
    record(False, "Engine", "Recommendation_buy_timing", "returned None")
    record(False, "Engine", "Recommendation_sell_timing", "returned None")

# 5c. BusinessAdvisor.get_daily_intelligence_brief()
def _test_business_advisor():
    ba = imported_modules.get("business_advisor_engine")
    if not ba:
        return {"_err": "module not imported"}
    advisor = ba.BusinessAdvisor()
    return advisor.get_daily_intelligence_brief()

brief, err = run_with_timeout(_test_business_advisor, timeout_sec=90)
if err:
    record(False, "Engine", "BusinessAdvisor_buy_advisory", err)
    record(False, "Engine", "BusinessAdvisor_sell_advisory", err)
    record(False, "Engine", "BusinessAdvisor_timing_advisory", err)
elif brief and "_err" in brief:
    record(False, "Engine", "BusinessAdvisor_buy_advisory", brief["_err"])
    record(False, "Engine", "BusinessAdvisor_sell_advisory", brief["_err"])
    record(False, "Engine", "BusinessAdvisor_timing_advisory", brief["_err"])
elif brief:
    keys_str = str(list(brief.keys())[:8]).encode("ascii", "replace").decode()
    record("buy_advisory" in brief, "Engine", "BusinessAdvisor_buy_advisory",
           f"buy_advisory present (keys: {keys_str})")
    record("sell_advisory" in brief, "Engine", "BusinessAdvisor_sell_advisory",
           f"sell_advisory present")
    record("timing_advisory" in brief, "Engine", "BusinessAdvisor_timing_advisory",
           f"timing_advisory present")
else:
    record(False, "Engine", "BusinessAdvisor_buy_advisory", "returned None")
    record(False, "Engine", "BusinessAdvisor_sell_advisory", "returned None")
    record(False, "Engine", "BusinessAdvisor_timing_advisory", "returned None")

# 5d. TradingChatbot.process_query()
def _test_chatbot():
    tc = imported_modules.get("trading_chatbot_engine")
    if not tc:
        return {"_err": "module not imported"}
    chatbot = tc.TradingChatbot()
    return chatbot.process_query("Current crude price?")

response, err = run_with_timeout(_test_chatbot, timeout_sec=90)
if err:
    record(False, "Engine", "TradingChatbot_answer", err)
elif response and "_err" in response:
    record(False, "Engine", "TradingChatbot_answer", response["_err"])
elif response:
    has_answer = "answer" in response and len(str(response.get("answer", ""))) > 0
    keys_str = str(list(response.keys())[:6]).encode("ascii", "replace").decode()
    record(has_answer, "Engine", "TradingChatbot_answer",
           f"answer returned ({len(str(response.get('answer', '')))} chars, keys: {keys_str})")
else:
    record(False, "Engine", "TradingChatbot_answer", "returned None")

# 5e. UnifiedIntelligence.health_check()
def _test_unified():
    ui = imported_modules.get("unified_intelligence_engine")
    if not ui:
        return {"_err": "module not imported"}
    return ui.health_check()

hc, err = run_with_timeout(_test_unified, timeout_sec=30)
if err:
    record(False, "Engine", "UnifiedIntelligence_engines_listed", err)
    record(False, "Engine", "UnifiedIntelligence_engines_available", err)
elif hc and "_err" in hc:
    record(False, "Engine", "UnifiedIntelligence_engines_listed", hc["_err"])
    record(False, "Engine", "UnifiedIntelligence_engines_available", hc["_err"])
elif hc:
    summ = hc.get("_summary", {})
    total = summ.get("total", 0)
    available = summ.get("available", 0)
    record(total >= 5, "Engine", "UnifiedIntelligence_engines_listed",
           f"{total} engines total, {available} available")
    record(available >= 3, "Engine", "UnifiedIntelligence_engines_available",
           f"{available}/{total} engines loaded successfully")
else:
    record(False, "Engine", "UnifiedIntelligence_engines_listed", "returned None")
    record(False, "Engine", "UnifiedIntelligence_engines_available", "returned None")

# 5f. DiscussionGuide.prepare_discussion()
def _test_discussion():
    dg = imported_modules.get("discussion_guidance_engine")
    if not dg:
        return {"_err": "module not imported"}
    guide = dg.DiscussionGuide()
    return guide.prepare_discussion("supplier", {"name": "Test Supplier", "city": "Mumbai"})

result, err = run_with_timeout(_test_discussion, timeout_sec=30)
if err:
    record(False, "Engine", "DiscussionGuide_supplier_mode", err)
elif result and "_err" in result:
    record(False, "Engine", "DiscussionGuide_supplier_mode", result["_err"])
elif result:
    has_no_error = "error" not in result
    has_content = len(result) >= 3
    keys_str = str(list(result.keys())[:6]).encode("ascii", "replace").decode()
    record(has_no_error and has_content, "Engine", "DiscussionGuide_supplier_mode",
           f"returned valid guide ({len(result)} keys: {keys_str})")
else:
    record(False, "Engine", "DiscussionGuide_supplier_mode", "returned None")


# =============================================================================
# 6. DATA FILE VALIDATION
# =============================================================================
print("\n" + "=" * 70)
print("6. DATA FILE VALIDATION")
print("=" * 70)

DATA_FILES = [
    "tbl_crude_prices.json",
    "tbl_fx_rates.json",
    "tbl_weather.json",
    "tbl_news_feed.json",
    "tbl_imports_countrywise.json",
    "tbl_ports_volume.json",
    "tbl_refinery_production.json",
    "api_cache.json",
    "hub_cache.json",
    "sre_health_status.json",
    "sre_alerts.json",
]

for fname in DATA_FILES:
    fpath = BASE / fname
    if not fpath.exists():
        record(False, "Data", fname, "file not found")
        continue
    try:
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            record(True, "Data", fname, f"valid JSON array with {len(data)} entries")
        elif isinstance(data, dict):
            record(True, "Data", fname, f"valid JSON object with {len(data)} keys")
        else:
            record(True, "Data", fname, f"valid JSON ({type(data).__name__})")
    except json.JSONDecodeError as e:
        record(False, "Data", fname, f"JSON decode error: {str(e)[:150]}")
    except Exception as e:
        record(False, "Data", fname, f"{type(e).__name__}: {str(e)[:150]}")


# =============================================================================
# 7. EXPORT FUNCTION VALIDATION
# =============================================================================
print("\n" + "=" * 70)
print("7. EXPORT FUNCTION VALIDATION")
print("=" * 70)

# 7a. pdf_export_engine.build_generic_pdf()
def _test_pdf():
    import pdf_export_engine
    return pdf_export_engine.build_generic_pdf(
        page_title="Validation Test",
        sections=[
            {"type": "section", "text": "System Validation"},
            {"type": "paragraph", "text": "This is a test PDF generated during final validation."},
            {"type": "kpis", "items": [("Tests Run", "50+", "+5"), ("Health", "98%", "+2%")]},
        ],
        role="Admin",
    )

pdf_bytes, err = run_with_timeout(_test_pdf, timeout_sec=30)
if err:
    record(False, "Export", "build_generic_pdf", err)
elif pdf_bytes:
    is_pdf = isinstance(pdf_bytes, bytes) and len(pdf_bytes) > 100
    record(is_pdf, "Export", "build_generic_pdf",
           f"produced {len(pdf_bytes)} bytes of PDF" if is_pdf else "did not produce valid PDF bytes")
else:
    record(False, "Export", "build_generic_pdf", "returned None")

# 7b. interactive_chart_helpers.get_chart_config()
try:
    ich = imported_modules.get("interactive_chart_helpers")
    if ich:
        cfg = ich.get_chart_config()
        has_keys = isinstance(cfg, dict) and "displayModeBar" in cfg and "scrollZoom" in cfg
        record(has_keys, "Export", "get_chart_config",
               f"returned config with {len(cfg)} keys" if has_keys else f"missing expected keys")
    else:
        record(False, "Export", "get_chart_config", "module not imported")
except Exception as e:
    record(False, "Export", "get_chart_config", f"{type(e).__name__}: {str(e)[:200]}")

# 7c. CommunicationHub has whatsapp + email methods
try:
    from communication_engine import CommunicationHub
    hub = CommunicationHub()
    has_whatsapp = hasattr(hub, "whatsapp_offer") and callable(hub.whatsapp_offer)
    has_email = hasattr(hub, "email_offer") and callable(hub.email_offer)

    wa_methods = [m for m in dir(hub) if m.startswith("whatsapp_")]
    em_methods = [m for m in dir(hub) if m.startswith("email_")]

    record(has_whatsapp, "Export", "CommunicationHub_whatsapp",
           f"{len(wa_methods)} whatsapp methods: {wa_methods}")
    record(has_email, "Export", "CommunicationHub_email",
           f"{len(em_methods)} email methods: {em_methods}")
except Exception as e:
    record(False, "Export", "CommunicationHub_whatsapp", f"{type(e).__name__}: {str(e)[:200]}")
    record(False, "Export", "CommunicationHub_email", f"{type(e).__name__}: {str(e)[:200]}")


# =============================================================================
# FINAL VERDICT
# =============================================================================
print("\n" + "=" * 70)
print("FINAL SYSTEM VALIDATION REPORT")
print("=" * 70)

total = PASS_COUNT + FAIL_COUNT
health = round((PASS_COUNT / total) * 100, 1) if total else 0

print(f"\nTotal tests : {total}")
print(f"Passed      : {PASS_COUNT}")
print(f"Failed      : {FAIL_COUNT}")
print(f"Health      : {health}%")

# Collect failures
failures = [r for r in RESULTS if r.startswith("[FAIL]")]
if failures:
    print(f"\n--- Remaining Issues ({len(failures)}) ---")
    for f in failures:
        print(_safe_str(f"  {f}"))
else:
    print("\nNo issues found.")

# Overall status
if health >= 95:
    status = "PRODUCTION READY"
elif health >= 80:
    status = "NEEDS MINOR FIXES"
else:
    status = "NEEDS FIXES"

print(f"\nOverall Status: {status}")
print("=" * 70)
