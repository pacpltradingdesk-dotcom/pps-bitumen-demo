"""
PPS Anantam — Bitumen Sales Dashboard v5.0
============================================
Slim router (~500 lines): session init, theme, navigation, page dispatch.
Business logic lives in engine files. UI pages live in pages/ and command_intel/.
"""

# ═══════════════════════════════════════════════════════════════════════════════
# IMPORTS
# ═══════════════════════════════════════════════════════════════════════════════
try:
    from india_localization import format_inr, format_inr_short, format_date, format_datetime_ist, get_financial_year, get_fy_quarter
except ImportError:
    import sys, os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    try:
        from india_localization import format_inr, format_inr_short, format_date, format_datetime_ist, get_financial_year, get_fy_quarter
    except Exception:
        pass

import streamlit as st
import datetime

# Navigation (lightweight — only config dicts)
from nav_config import MODULE_NAV, TOPBAR_MODULES, OVERFLOW_MODULES, PAGE_REDIRECTS
from nav_config import get_tabs, get_module_for_page, get_feature_idx_for_page, resolve_page
from theme import inject_theme
from top_bar import render_top_bar
from subtab_bar import render_sidebar_features

# PDF Export System
try:
    from pdf_export_bar import render_export_bar, inject_print_css
    _PDF_BAR_OK = True
except Exception:
    _PDF_BAR_OK = False
    def render_export_bar(*a, **kw): pass
    def inject_print_css(): pass

# Data Confidence Engine (lazy — only used on data-heavy pages)
_CONFIDENCE_OK = False
def render_confidence_bar(*a, **kw): pass
def render_data_health_card(*a, **kw): pass
try:
    from data_confidence_engine import render_confidence_bar, render_data_health_card
    _CONFIDENCE_OK = True
except Exception:
    pass

# Role Engine
try:
    from role_engine import render_login_form, get_current_role, check_role, init_roles
    init_roles()
    _ROLE_OK = True
except Exception:
    _ROLE_OK = False
    def render_login_form(): return True
    def get_current_role(): return "admin"
    def check_role(r): return True


# ═══════════════════════════════════════════════════════════════════════════════
# ENGINE STARTUP — lazy, runs ONCE per session (not on every rerun)
# ═══════════════════════════════════════════════════════════════════════════════

def _init_engines():
    """Start all background engines once per session."""
    if st.session_state.get("_engines_started"):
        return
    try:
        from api_manager import init_system, start_auto_health
        init_system(); start_auto_health()
    except Exception: pass
    try:
        from sre_engine import init_sre, start_sre_background
        init_sre(); start_sre_background(interval_min=15)
    except Exception: pass
    try:
        from api_hub_engine import init_hub, start_hub_scheduler
        init_hub(); start_hub_scheduler(interval_min=60)
    except Exception as _e:
        import logging; logging.getLogger("startup").warning("API Hub scheduler failed: %s", _e)
    try:
        from sync_engine import start_sync_scheduler
        start_sync_scheduler(interval_minutes=60)
    except Exception as _e:
        import logging; logging.getLogger("startup").warning("Sync scheduler failed: %s", _e)
    try:
        from email_engine import start_email_scheduler
        start_email_scheduler()
    except Exception: pass
    try:
        from whatsapp_engine import start_whatsapp_scheduler
        start_whatsapp_scheduler()
    except Exception: pass
    try:
        from resilience_manager import HeartbeatMonitor
        HeartbeatMonitor.start_checker()
    except Exception: pass
    try:
        from port_tracker_engine import init_port_tracker
        init_port_tracker()
    except Exception: pass
    try:
        from directory_engine import init_directory
        init_directory()
    except Exception: pass
    st.session_state["_engines_started"] = True


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="PPS Anantam — Bitumen Dashboard v6.0",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global "screen shell" CSS ──────────────────────────────────────────────
# Soft grey page background + white rounded card for main content + subtle
# shadow so every page feels like a discrete screen (Aampe / Refera pattern).
# Section sub-cards (expanders, metric tiles) get lighter backing so they
# visually group within the main card.
st.markdown("""
<style>
  /* Page-level grey backdrop — slightly darker so the card pops clearly */
  [data-testid="stAppViewContainer"] {
      background: #E5EAF0 !important;
  }
  [data-testid="stAppViewContainer"] > .main,
  .stApp {
      background: transparent !important;
  }

  /* Main content wrapped as a white card with prominent shadow + border so
     the "screen" boundary is unmistakable. */
  html body [data-testid="stMainBlockContainer"],
  html body [data-testid="stMain"] > div:first-child,
  html body .stMainBlockContainer,
  html body section.main > div.block-container,
  html body .main > div.block-container {
      background: #FFFFFF !important;
      border-radius: 14px !important;
      padding: 20px 24px 26px 24px !important;
      box-shadow: 0 2px 6px rgba(15, 23, 42, 0.06),
                  0 14px 34px rgba(15, 23, 42, 0.08) !important;
      border: 1px solid #CBD5E1 !important;
      margin: 8px 8px 10px 8px !important;
      max-width: none !important;
      width: auto !important;
  }

  /* Main wrapper — ensure the block container has room to show its margin
     AND fills the space to the right of the sidebar (no 1280px centering cap). */
  html body [data-testid="stMain"],
  html body section.main,
  html body [data-testid="stAppViewContainer"] > .main {
      background: transparent !important;
      max-width: none !important;
      width: 100% !important;
      padding-left: 0 !important;
      padding-right: 0 !important;
      margin-left: 0 !important;
      margin-right: 0 !important;
  }

  /* Sidebar — keep clean white so it reads as a rail */
  [data-testid="stSidebar"] {
      background: #FFFFFF;
      border-right: 1px solid #E2E8F0;
  }
  [data-testid="stSidebar"] > div:first-child {
      background: #FFFFFF;
  }

  /* Expanders — soft grey sub-cards inside the main card */
  [data-testid="stExpander"] {
      border-radius: 12px;
      border: 1px solid #E2E8F0;
      background: #F8FAFC;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
      margin-bottom: 12px;
  }
  [data-testid="stExpander"] summary { padding: 6px 10px; }

  /* Metric tiles — subtle card look instead of flat background */
  [data-testid="stMetric"] {
      background: #F8FAFC;
      border: 1px solid #E2E8F0;
      border-radius: 10px;
      padding: 14px 16px;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
  }

  /* Tabs — cleaner separator line */
  [data-baseweb="tab-list"] {
      border-bottom: 1px solid #E2E8F0;
      gap: 4px;
  }

  /* Dividers tighter */
  [data-testid="stHorizontalBlock"] hr { border-color: #E2E8F0; }
</style>
""", unsafe_allow_html=True)

# Auto-apply DB schema migrations on startup. Cached so it runs at most
# once per Streamlit process, not per rerun. Without this, fresh VPS
# deployments stayed on schema v7 (no Phase 1 tables) until something
# else touched the DB.
@st.cache_resource(show_spinner=False)
def _ensure_db_schema():
    try:
        from database import init_db
        init_db()
        return True
    except Exception as _e:
        # Don't crash the UI — pages with optional DB usage already
        # try/except their own queries.
        import sys
        print(f"[startup] init_db skipped: {_e}", file=sys.stderr)
        return False

_ensure_db_schema()


# ═══════════════════════════════════════════════════════════════════════════════
# THEME + ENGINES — theme first (instant), engines lazy (background)
# ═══════════════════════════════════════════════════════════════════════════════

inject_theme()

try:
    from components.sidebar_toggle import inject as _inject_sidebar_toggle
    _inject_sidebar_toggle()
except Exception:
    pass

# ═══════════════════════════════════════════════════════════════════════════════
# LOGIN GATE — Must authenticate before accessing anything
# ═══════════════════════════════════════════════════════════════════════════════

from login_page import render_login
if not render_login():
    st.stop()

_init_engines()  # skips if already started this session



# ═══════════════════════════════════════════════════════════════════════════════
# CACHED DATA HELPERS
# ═══════════════════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════════════════
# SESSION STATE INIT
# ═══════════════════════════════════════════════════════════════════════════════

if "selected_page" not in st.session_state:
    st.session_state["selected_page"] = "🎯 Command Center"
if "_active_module" not in st.session_state:
    # Migrate from old key if exists
    st.session_state["_active_module"] = st.session_state.get("selected_module", "📊 Price & Info")


# ═══════════════════════════════════════════════════════════════════════════════
# COMMAND CENTER FAST PATH — render clean, skip all nav chrome
# ═══════════════════════════════════════════════════════════════════════════════

# Global _nav_goto consumer — runs on EVERY page so any "Open X" button
# anywhere in the app can navigate by setting st.session_state["_nav_goto"]
# + calling st.rerun(). Previously this only worked on the Command Center
# fast path, leaving Quick Access cards / Live Market AI buttons broken.
if st.session_state.get("_nav_goto"):
    _goto = st.session_state.pop("_nav_goto")
    st.session_state["selected_page"] = resolve_page(_goto)
    _owner = get_module_for_page(_goto)
    if _owner:
        st.session_state["_active_module"] = _owner
    st.rerun()

if st.session_state.get("selected_page") == "🎯 Command Center":
    # Render sidebar even on CC (render_sidebar_features already imported at top)
    render_sidebar_features("📊 Price & Info")
    # Render CC content
    from pages.home.command_center import render as render_cc_v5
    render_cc_v5()
    # Belt + braces: in case render set _nav_goto AFTER the global check above
    if st.session_state.get("_nav_goto"):
        _goto = st.session_state.pop("_nav_goto")
        st.session_state["selected_page"] = resolve_page(_goto)
        _owner = get_module_for_page(_goto)
        if _owner:
            st.session_state["_active_module"] = _owner
        st.rerun()
    st.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# NAVIGATION — Top Bar + Sidebar Features
# ═══════════════════════════════════════════════════════════════════════════════

# RBAC Gate
if not render_login_form():
    st.stop()

# Top navigation bar (modules)
render_top_bar()

# Sidebar feature list for active module
_active_module = st.session_state.get("_active_module", "🏠 Home")
_sidebar_page = render_sidebar_features(_active_module)
if _sidebar_page:
    st.session_state["selected_page"] = _sidebar_page

# Resolve selected page (apply redirects)
selected_page = resolve_page(st.session_state.get("selected_page", "🎯 Command Center"))
st.session_state["selected_page"] = selected_page

# Track page visit + breadcrumb + active customer context strip
try:
    from navigation_engine import (track_page_visit, render_breadcrumb,
                                    render_active_context_strip)
    track_page_visit(selected_page)
    render_breadcrumb(selected_page)
    render_active_context_strip()
except Exception:
    pass

# Action bar moved to sidebar Quick Actions — no longer rendered in main content
inject_print_css()

# Data confidence bar — removed from main content (was showing low scores due to
# unavailable external APIs like UN Comtrade, PPAC). Data health available in System > Health Monitor.


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE DISPATCH — clean dictionary-based routing
# ═══════════════════════════════════════════════════════════════════════════════

def _safe_render(render_fn, page_name: str):
    """Wrap a page render in try/except for graceful error handling."""
    try:
        render_fn()
    except Exception as e:
        st.error(f"{page_name} failed to load: {e}")
        st.info("Try reloading the page. If this persists, check Health Monitor.")


def _page_home():
    try:
        from market_data import get_live_market_data, get_simulated_data
        api_active = st.session_state.get("_api_toggle_v3", False)
        mkt = get_live_market_data() if api_active else get_simulated_data()
        from pages.home.live_market import render
        render(mkt=mkt, _CONFIDENCE_OK=_CONFIDENCE_OK,
               render_data_health_card=render_data_health_card if _CONFIDENCE_OK else None)
    except Exception as e:
        st.error(f"Home page failed to load: {e}")

def _page_pricing_calc():
    try:
        from pages.pricing.pricing_calculator import render
        render()
    except Exception as e:
        st.error(f"Pricing Calculator failed to load: {e}")

def _page_sales_workspace():
    try:
        import sales_workspace
        sales_workspace.render_deal_room()
    except Exception as e:
        st.error(f"Sales Workspace failed to load: {e}")

def _page_sales_calendar():
    try:
        from pages.sales.sales_calendar import render
        render()
    except Exception as e:
        st.error(f"Sales Calendar failed to load: {e}")

def _page_ecosystem():
    try:
        from pages.logistics.ecosystem import render
        render()
    except Exception as e:
        st.error(f"Ecosystem Management failed to load: {e}")

def _page_ai_fallback():
    _safe_render(lambda: __import__("command_intel.ai_fallback_dashboard", fromlist=["render"]).render(), "AI Fallback")

def _page_ai_assistant():
    _safe_render(lambda: __import__("command_intel.ai_dashboard_assistant", fromlist=["render"]).render(), "AI Assistant")

def _page_settings():
    try:
        from pages.system.settings_page import render
        render()
    except Exception as e:
        st.error(f"Settings failed to load: {e}")

def _page_data_manager():
    try:
        from command_intel import data_manager_dashboard
        data_manager_dashboard.render()
    except Exception as e:
        st.error(f"Data Manager failed to load: {e}")

def _page_contact_importer():
    try:
        from command_intel import contact_importer
        contact_importer.render()
    except Exception as e:
        st.error(f"Contact Importer failed to load: {e}")

def _page_source_directory():
    try:
        from command_intel import directory_dashboard
        directory_dashboard.render()
    except Exception as e:
        st.error(f"Source Directory failed to load: {e}")

def _page_feasibility():
    try:
        from feasibility_engine import get_feasibility_assessment, get_comparison_table, DESTINATION_COORDS
        st.header("📊 Feasibility Assessment")
        st.info("Automatic price comparison: **2 Refineries + 2 Import Terminals + 2 Decanters** for any destination")
        all_destinations = sorted(list(DESTINATION_COORDS.keys()))
        selected_dest = st.selectbox("🎯 Select Destination City", all_destinations, key="feasibility_dest")
        if selected_dest:
            assessment = get_feasibility_assessment(selected_dest, top_n=2)
            if assessment:
                st.markdown(f"### 📍 Feasibility Report for: **{selected_dest}**")
                comparison = get_comparison_table(selected_dest)
                if comparison is not None:
                    st.dataframe(comparison, use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"Feasibility Assessment failed to load: {e}")

def _page_knowledge_base():
    try:
        from pages.system.knowledge_base import render
        render()
    except Exception as e:
        st.error(f"Knowledge Base failed to load: {e}")

def _page_crm_tasks():
    try:
        from pages.sales.crm_tasks import render
        render()
    except Exception:
        # Fallback: direct CRM render
        import crm_engine as crm
        st.header("🎯 Sales CRM & Daily Worklist")
        k1, k2, k3, k4 = st.columns(4)
        tasks_today = crm.get_due_tasks("Today")
        tasks_overdue = crm.get_due_tasks("Overdue")
        k1.metric("🔥 Hot Leads", "3", "Active")
        k2.metric("📅 Tasks Due Today", len(tasks_today))
        k3.metric("⚠️ Overdue", len(tasks_overdue), delta_color="inverse")
        k4.metric("💰 Deals Closing", "2", "This Week")

def _page_sos():
    _safe_render(
        lambda: __import__("command_intel.sos_dashboard", fromlist=["render"]).render(),
        "SOS Special Pricing"
    )

def _page_reports():
    st.header("📤 Export Reports")
    st.caption("Generate and download reports as PDF or Excel.")

    report_type = st.selectbox("Report Type", [
        "Director Briefing (PDF)",
        "Financial Summary (Excel)",
        "CRM Contacts (Excel)",
        "Price History (Excel)",
        "Market Signals (Excel)",
        "Full Data Backup (JSON)",
    ])

    if st.button("Generate Report", type="primary"):
        import pandas as pd
        import json as _json
        from pathlib import Path as _Path
        _root = _Path(__file__).parent

        try:
            if "Director Briefing" in report_type:
                try:
                    from director_briefing_engine import generate_briefing
                    briefing = generate_briefing()
                    st.success("Director Briefing generated!")
                    st.markdown(briefing.get("summary", "No summary available."))
                except Exception:
                    st.warning("Director Briefing engine not available. Check system settings.")

            elif "Financial Summary" in report_type:
                try:
                    from database import get_deals
                    deals = get_deals(limit=500)
                    if deals:
                        df = pd.DataFrame(deals)
                        csv = df.to_csv(index=False)
                        st.download_button("Download Financial Summary (CSV)", data=csv,
                                           file_name="pps_financial_summary.csv", mime="text/csv")
                        st.success(f"Financial summary ready — {len(deals)} deals.")
                    else:
                        st.info("No deal data available yet.")
                except Exception:
                    st.warning("Financial data not available.")

            elif "CRM Contacts" in report_type:
                try:
                    _cf = _root / "tbl_contacts.json"
                    if _cf.exists():
                        with open(_cf, "r", encoding="utf-8") as f:
                            contacts = _json.load(f)
                        df = pd.DataFrame(contacts)
                        csv = df.to_csv(index=False)
                        st.download_button("Download Contacts (CSV)", data=csv,
                                           file_name="pps_contacts_export.csv", mime="text/csv")
                        st.success(f"Contacts export ready — {len(contacts)} records.")
                    else:
                        st.info("No contacts data file found.")
                except Exception:
                    st.warning("Contacts export failed.")

            elif "Price History" in report_type:
                try:
                    _pf = _root / "tbl_crude_prices.json"
                    if _pf.exists():
                        with open(_pf, "r", encoding="utf-8") as f:
                            prices = _json.load(f)
                        df = pd.DataFrame(prices)
                        csv = df.to_csv(index=False)
                        st.download_button("Download Price History (CSV)", data=csv,
                                           file_name="pps_price_history.csv", mime="text/csv")
                        st.success(f"Price history ready — {len(prices)} records.")
                    else:
                        st.info("No price history data available.")
                except Exception:
                    st.warning("Price history export failed.")

            elif "Market Signals" in report_type:
                try:
                    _sf = _root / "tbl_market_signals.json"
                    if _sf.exists():
                        with open(_sf, "r", encoding="utf-8") as f:
                            signals = _json.load(f)
                        df = pd.DataFrame(signals if isinstance(signals, list) else [signals])
                        csv = df.to_csv(index=False)
                        st.download_button("Download Market Signals (CSV)", data=csv,
                                           file_name="pps_market_signals.csv", mime="text/csv")
                        st.success("Market signals export ready.")
                    else:
                        st.info("No market signals data available.")
                except Exception:
                    st.warning("Market signals export failed.")

            elif "Full Data Backup" in report_type:
                try:
                    backup = {}
                    for jf in _root.glob("tbl_*.json"):
                        with open(jf, "r", encoding="utf-8") as f:
                            backup[jf.stem] = _json.load(f)
                    backup_str = _json.dumps(backup, indent=2, default=str)
                    st.download_button("Download Full Backup (JSON)", data=backup_str,
                                       file_name="pps_full_backup.json", mime="application/json")
                    st.success(f"Full backup ready — {len(backup)} tables.")
                except Exception:
                    st.warning("Backup generation failed.")

        except Exception as e:
            st.error(f"Report generation failed: {e}")

def _page_negotiation():
    try:
        from pages.sales.negotiation import render
        render()
    except Exception as e:
        st.error(f"Negotiation Assistant failed to load: {e}")

def _page_crm_automation():
    try:
        from command_intel.crm_automation_dashboard import render_crm_automation
        render_crm_automation()
    except Exception as e:
        st.error(f"CRM Automation failed to load: {e}")

def _page_comm_hub():
    try:
        from pages.sales.comm_hub import render
        render()
    except Exception as e:
        st.error(f"Communication Hub failed to load: {e}")

def _page_sync_status():
    try:
        from pages.system.sync_status import render
        render()
    except Exception as e:
        st.error(f"Sync Status failed to load: {e}")

def _page_opportunities():
    try:
        from pages.home.opportunities import render
        render()
    except Exception as e:
        st.error(f"Opportunities failed to load: {e}")

def _page_ai_learning():
    try:
        from pages.system.ai_learning import render
        render()
    except Exception as e:
        st.error(f"AI Learning failed to load: {e}")

def _page_contacts_directory():
    try:
        from command_intel import contacts_directory_dashboard
        contacts_directory_dashboard.render()
    except Exception as e:
        st.error(f"Contacts Directory failed to load: {e}")


# ── Page Dispatch Dict ────────────────────────────────────────────────────────

PAGE_DISPATCH = {
    # Home
    "💎 One-Click Quote": lambda: _safe_render(
        lambda: __import__("pages.home.director_cockpit", fromlist=["render"]).render(),
        "One-Click Quote"),
    "🌐 Client Showcase": lambda: _safe_render(
        lambda: __import__("pages.home.client_showcase", fromlist=["render"]).render(),
        "Client Showcase"),
    "💎 Subscription Pricing": lambda: _safe_render(
        lambda: __import__("pages.home.subscription_pricing", fromlist=["render"]).render(),
        "Subscription Pricing"),
    "🏠 Home": _page_home,
    "🎯 Command Center": lambda: _safe_render(
        lambda: __import__("pages.home.command_center", fromlist=["render"]).render(),
        "Command Center"),
    "🔍 Opportunities": _page_opportunities,
    "🚨 Alert Center": lambda: _safe_render(
        lambda: __import__("command_intel.alert_center", fromlist=["render"]).render(), "Alert Center"),

    # Pricing
    "🧮 Pricing Calculator": _page_pricing_calc,
    "📦 Import Cost Model": lambda: _safe_render(
        lambda: __import__("command_intel.import_cost_model", fromlist=["render"]).render(), "Import Cost Model"),
    "🔮 Price Prediction": lambda: _safe_render(
        lambda: __import__("command_intel.price_prediction", fromlist=["render"]).render(), "Price Prediction"),
    "📝 Manual Price Entry": lambda: _safe_render(
        lambda: __import__("command_intel.manual_entry", fromlist=["render"]).render(), "Manual Price Entry"),
    "🚨 SPECIAL PRICE (SOS)": _page_sos,
    "⏳ Past Predictions": lambda: _safe_render(
        lambda: __import__("command_intel.historical_revisions", fromlist=["render"]).render(), "Past Predictions"),

    # Sales & CRM
    "🎯 CRM & Tasks": _page_crm_tasks,
    "💼 Sales Workspace": _page_sales_workspace,
    "🤝 Negotiation Assistant": _page_negotiation,
    "💬 Communication Hub": _page_comm_hub,
    "🤖 CRM Automation": _page_crm_automation,
    "📓 Daily Log": lambda: _safe_render(
        lambda: __import__("command_intel.daily_log_panel", fromlist=["render"]).render(), "Daily Log"),
    "📱 Contacts Directory": _page_contacts_directory,
    "📊 Comm Tracking": lambda: _safe_render(
        lambda: __import__("command_intel.comm_tracking_dashboard", fromlist=["render"]).render(),
        "Comm Tracking"),
    "💬 Client Chat": lambda: _safe_render(
        lambda: __import__("command_intel.client_chat_dashboard", fromlist=["render"]).render(),
        "Client Chat"),
    "💳 Credit & Aging": lambda: _safe_render(
        lambda: __import__("command_intel.credit_aging_dashboard", fromlist=["render"]).render(),
        "Credit & Aging"),
    "📡 Rate Broadcast": lambda: _safe_render(
        lambda: __import__("command_intel.rate_broadcast_dashboard", fromlist=["render"]).render(),
        "Rate Broadcast"),
    "📅 Sales Calendar": _page_sales_calendar,

    # Intelligence
    "📡 Market Signals": lambda: _safe_render(
        lambda: __import__("command_intel.market_signals_dashboard", fromlist=["render"]).render(), "Market Signals"),
    "🔴 Real-time Insights": lambda: _safe_render(
        lambda: __import__("command_intel.real_time_insights_dashboard", fromlist=["render"]).render(),
        "Real-time Insights"),
    "📰 News Intelligence": lambda: _safe_render(
        lambda: __import__("command_intel.news_dashboard", fromlist=["render"]).render(),
        "News Intelligence"),
    "🕵️ Competitor Intelligence": lambda: _safe_render(
        lambda: __import__("competitor_intelligence", fromlist=["render"]).render(),
        "Competitor Intel"),
    "🧑‍💼 Business Advisor": lambda: _safe_render(
        lambda: __import__("command_intel.business_advisor_dashboard", fromlist=["render"]).render(),
        "Business Advisor"),
    "🛒 Purchase Advisor": lambda: _safe_render(
        lambda: __import__("command_intel.purchase_advisor_dashboard", fromlist=["render"]).render(),
        "Purchase Advisor"),
    "💡 Recommendations": lambda: _safe_render(
        lambda: __import__("command_intel.recommendation_dashboard", fromlist=["render"]).render(),
        "Recommendations"),
    "🌐 Global Markets": lambda: _safe_render(
        lambda: __import__("command_intel.global_market_dashboard", fromlist=["render"]).render(),
        "Global Markets"),
    "📡 Telegram Analyzer": lambda: _safe_render(
        lambda: __import__("pages.intelligence.telegram_analyzer", fromlist=["render"]).render(),
        "Telegram Analyzer"),
    "🏗️ NHAI Tenders": lambda: _safe_render(
        lambda: __import__("command_intel.nhai_tender_dashboard", fromlist=["render"]).render(),
        "NHAI Tenders"),

    # Documents
    "📋 Purchase Orders": lambda: _safe_render(
        lambda: __import__("command_intel.document_management", fromlist=["render_purchase_order"]).render_purchase_order(),
        "Purchase Orders"),
    "📋 Sales Orders": lambda: _safe_render(
        lambda: __import__("command_intel.document_management", fromlist=["render_sales_order"]).render_sales_order(),
        "Sales Orders"),
    "💳 Payment Orders": lambda: _safe_render(
        lambda: __import__("command_intel.document_management", fromlist=["render_payment_order"]).render_payment_order(),
        "Payment Orders"),
    "👥 Party Master": lambda: _safe_render(
        lambda: __import__("command_intel.document_management", fromlist=["render_party_master"]).render_party_master(),
        "Party Master"),
    "📁 PDF Archive": lambda: _safe_render(
        lambda: __import__("command_intel.pdf_archive", fromlist=["render"]).render(),
        "PDF Archive"),

    # Logistics
    "🚢 Maritime Logistics": lambda: _safe_render(
        lambda: __import__("command_intel.maritime_logistics_dashboard", fromlist=["render"]).render(),
        "Maritime Logistics"),
    "🚢 Supply Chain": lambda: _safe_render(
        lambda: __import__("command_intel.supply_chain", fromlist=["render"]).render(), "Supply Chain"),
    "⚓ Port Import Tracker": lambda: _safe_render(
        lambda: __import__("command_intel.port_tracker_dashboard", fromlist=["render"]).render(), "Port Tracker"),
    "🏭 Feasibility": _page_feasibility,
    "👥 Ecosystem Management": _page_ecosystem,
    "🏭 Refinery Supply": lambda: _safe_render(
        lambda: __import__("command_intel.refinery_supply_dashboard", fromlist=["render"]).render(),
        "Refinery Supply"),
    "🚛 Tanker Tracking": lambda: _safe_render(
        lambda: __import__("command_intel.tanker_tracking_dashboard", fromlist=["render"]).render(),
        "Tanker Tracking"),

    # Reports
    "💰 Financial Intelligence": lambda: _safe_render(
        lambda: __import__("command_intel.financial_intel", fromlist=["render"]).render(), "Financial Intelligence"),
    "🎯 Strategy Panel": lambda: _safe_render(
        lambda: __import__("command_intel.strategy_panel", fromlist=["render"]).render(), "Strategy Panel"),
    "👷 Demand Analytics": lambda: _safe_render(
        lambda: __import__("command_intel.demand_analytics", fromlist=["render"]).render(), "Demand Analytics"),
    "📈 Demand Correlation": lambda: _safe_render(
        lambda: __import__("command_intel.correlation_dashboard", fromlist=["render"]).render(), "Demand Correlation"),
    "🛣️ Road Budget & Demand": lambda: _safe_render(
        lambda: __import__("command_intel.road_budget_dashboard", fromlist=["render"]).render(),
        "Road Budget"),
    "⚡ Risk Scoring": lambda: _safe_render(
        lambda: __import__("command_intel.risk_scoring", fromlist=["render"]).render(), "Risk Scoring"),
    "📤 Reports": _page_reports,
    "📋 Director Briefing": lambda: _safe_render(
        lambda: __import__("command_intel.director_dashboard", fromlist=["render"]).render(), "Director Briefing"),
    "💰 Profitability Analytics": lambda: _safe_render(
        lambda: __import__("command_intel.profitability_dashboard", fromlist=["render"]).render(),
        "Profitability Analytics"),

    # Compliance
    "🏗️ Govt Data Hub": lambda: _safe_render(
        lambda: __import__("command_intel.govt_hub_dashboard", fromlist=["render"]).render(), "Govt Data Hub"),
    "🛡️ GST & Legal Monitor": lambda: _safe_render(
        lambda: __import__("command_intel.gst_legal_monitor", fromlist=["render"]).render(), "GST & Legal"),
    "🔔 Alert System": lambda: _safe_render(
        lambda: __import__("command_intel.alert_system", fromlist=["render"]).render(), "Alert System"),
    "🔔 Change Notifications": lambda: _safe_render(
        lambda: __import__("command_intel.change_log", fromlist=["render"]).render(), "Change Log"),
    "🗂️ India Procurement Directory": lambda: _safe_render(
        lambda: __import__("command_intel.directory_dashboard", fromlist=["render"]).render(), "Procurement Dir"),
    "📄 E-Way Bills": lambda: _safe_render(
        lambda: __import__("command_intel.eway_bill_dashboard", fromlist=["render"]).render(),
        "E-Way Bills"),
    "🛠️ Data Manager": lambda: _safe_render(
        lambda: __import__("command_intel.data_manager_dashboard", fromlist=["render"]).render(),
        "Data Manager"),

    # System & AI
    "💬 Trading Chatbot": lambda: _safe_render(
        lambda: __import__("command_intel.ai_dashboard_assistant", fromlist=["render"]).render(),
        "Trading Chatbot"),
    "🔄 AI Fallback Engine": _page_ai_fallback,
    "📚 Knowledge Base": _page_knowledge_base,
    "🤖 AI Learning": _page_ai_learning,
    "🎛️ System Control Center": lambda: _safe_render(
        lambda: __import__("command_intel.system_control_center", fromlist=["render"]).render(),
        "System Control Center"),
    "🌐 API Dashboard": lambda: _safe_render(
        lambda: __import__("api_dashboard", fromlist=["render"]).render(), "API Dashboard"),
    "🔗 API HUB": lambda: _safe_render(
        lambda: __import__("command_intel.api_hub_dashboard", fromlist=["render"]).render(), "API Hub"),
    "🏥 Health Monitor": lambda: _safe_render(
        lambda: __import__("command_intel.health_monitor_dashboard", fromlist=["render"]).render(),
        "Health Monitor"),
    "⚙️ Settings": _page_settings,
    "📥 Import Wizard": lambda: _safe_render(
        lambda: __import__("pages.system.import_wizard", fromlist=["render"]).render(),
        "Import Wizard"),
    "🗂️ Import History": lambda: _safe_render(
        lambda: __import__("pages.system.import_history", fromlist=["render"]).render(),
        "Import History"),
    "🐞 Bug Tracker": lambda: _safe_render(
        lambda: __import__("command_intel.bug_tracker", fromlist=["render"]).render(), "Bug Tracker"),
    "🛠️ Developer Ops Map": lambda: _safe_render(
        lambda: __import__("command_intel.developer_ops_dashboard", fromlist=["render"]).render(), "Developer Ops"),
    "🗺️ Dashboard Flow Map": lambda: _safe_render(
        lambda: __import__("command_intel.dashboard_flow_map", fromlist=["render"]).render(), "Dashboard Flow"),

    # Legacy pages (still accessible)
    "🏥 System Health": lambda: _safe_render(
        lambda: __import__("command_intel.sre_dashboard", fromlist=["render"]).render(), "System Health"),
    "📋 Source Directory": lambda: _safe_render(
        lambda: __import__("command_intel.directory_dashboard", fromlist=["render"]).render(), "Source Directory"),
    "🔭 Contractor OSINT": lambda: _safe_render(
        lambda: __import__("contractor_osint", fromlist=["render"]).render(),
        "Contractor OSINT"),
    "🏛️ Business Intelligence": lambda: _safe_render(
        lambda: __import__("business_knowledge_base", fromlist=["render"]).render(),
        "Business Intelligence"),
    "📋 Discussion Guide": lambda: _safe_render(
        lambda: __import__("command_intel.discussion_guidance_dashboard", fromlist=["render"]).render(),
        "Discussion Guide"),
    "🔄 Sync Status": _page_sync_status,
    "🏗️ Infra Demand Intelligence": lambda: _safe_render(
        lambda: __import__("command_intel.infra_demand_dashboard", fromlist=["render"]).render(), "Infra Demand"),

    # Sharing
    "📤 Share Center": lambda: _safe_render(
        lambda: __import__("pages.sharing.share_center", fromlist=["render"]).render(),
        "Share Center"),
    "✈️ Telegram Dashboard": lambda: _safe_render(
        lambda: __import__("pages.sharing.telegram_dashboard", fromlist=["render"]).render(),
        "Telegram Dashboard"),
}


# ═══════════════════════════════════════════════════════════════════════════════
# DISPATCH — run the selected page
# ═══════════════════════════════════════════════════════════════════════════════

handler = PAGE_DISPATCH.get(selected_page)
if handler:
    handler()
    # Central hook: render contextual Next Step cards after EVERY page.
    # Pages that added cards inline won't duplicate — NEXT_STEPS lookup
    # determines if cards render. Pages without entries render nothing.
    try:
        from navigation_engine import render_next_step_cards, NEXT_STEPS
        # Skip if this page already calls render_next_step_cards inline
        # (we track which pages self-render via a sentinel in session_state)
        _inline_rendered = st.session_state.pop("_ns_rendered_inline", False)
        if not _inline_rendered and selected_page in NEXT_STEPS:
            render_next_step_cards(selected_page)
    except Exception:
        pass
else:
    st.warning(f"Page not found: {selected_page}")
    st.info("Use the navigation bar to select a page.")


# ═══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div style="
  background: #FFFFFF;
  border-top: 1px solid #E5E7EB;
  padding: 20px 32px;
  margin-top: 64px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-family: inherit;
  border-radius: var(--radius-lg) var(--radius-lg) 0 0;
  box-shadow: 0 -4px 6px -1px rgba(0,0,0,0.02);
">
  <div style="display:flex; align-items:center; gap:12px;">
    <span style="font-size:1.0rem; font-weight: 800; color: var(--text-main); letter-spacing: -0.02em;">
      🏛️ PPS Anantam
    </span>
    <span style="font-size:0.75rem; color:var(--text-muted); font-weight: 500; border-left: 1px solid #E5E7EB; padding-left: 12px;">
      Bitumen Sales Dashboard — HQ: Vadodara, GJ
    </span>
  </div>
  <div style="font-size:0.75rem; color:var(--text-muted); display:flex; gap:16px; flex-wrap:wrap; font-weight: 600; align-items:center;">
    <span style="background:#F3F4F6; padding:4px 8px; border-radius:6px; border:1px solid #E5E7EB;">v6.1</span>
    <span>Build: 28-03-2026</span>
    <span style="color:#059669;">● Production</span>
    <span style="color:var(--text-blue); background:#EEF2FF; padding:4px 8px; border-radius:6px; font-weight:800; border:1px solid rgba(79, 70, 229, 0.2);">GST: 24AAHCV1611L2ZD</span>
  </div>
</div>
""", unsafe_allow_html=True)
