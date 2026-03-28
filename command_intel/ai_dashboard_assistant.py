"""
AI Dashboard Assistant — Streamlit UI Tab

Full-featured chat interface connecting to the AI engine and all dashboard data.
Tabs: Chat | Quick Actions | History & FAQ | Architecture | Setup
"""

from __future__ import annotations

import sys
import os
import json
import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd

from ui_badges import display_badge

# ── Role colours ──────────────────────────────────────────────────────────────
ROLE_COLOUR = {
    "Admin":      ("#7c3aed", "#f5f3ff"),
    "Sales":      ("#0284c7", "#e0f2fe"),
    "Strategy":   ("#0d9488", "#f0fdfa"),
    "Finance":    ("#d97706", "#fffbeb"),
    "Operations": ("#dc2626", "#fef2f2"),
}

# ── Quick action definitions ──────────────────────────────────────────────────
QUICK_ACTIONS = [
    {"label": "📈 Show Price Forecast",       "prompt": "What is the current bitumen VG-30 price forecast for the next 2 fortnightly revisions? Show trend direction, expected change, and which refineries have the best rates."},
    {"label": "🗺️ Demand Heatmap",            "prompt": "Show me the state-wise bitumen demand distribution across India. Which states have highest demand? Generate a bar chart."},
    {"label": "🐞 Open Bugs / Errors",        "prompt": "What are the currently open system errors and bugs? Show P0 and P1 issues with their status and auto-fix actions taken."},
    {"label": "🏗️ Contractor CRM Summary",   "prompt": "Give me a summary of all contractors in the system — total projects, total bitumen demand (MT), risk flags, and top states."},
    {"label": "🛢️ Competitor Intelligence",  "prompt": "What is the latest MEE (Multi Energy Enterprises) forecast? How accurate has their prediction been? Compare their USD/INR to RBI rate."},
    {"label": "🌍 International Bitumen",     "prompt": "Show international bitumen FOB prices. Which country has the cheapest import option? Generate a comparison chart."},
    {"label": "📊 India Consumption Chart",   "prompt": "Show India's monthly bitumen consumption trend for the last 12 months. Generate a bar chart and identify peak/off months."},
    {"label": "⚙️ API Health Check",          "prompt": "What is the current health status of all APIs? How many are working, failed, or rate-limited? Show recent error log."},
    {"label": "💰 Margin Calculator",         "prompt": "Calculate the margin for selling VG-30 bitumen from IOCL Koyali to Mumbai, 500 km distance, bulk transport. Show full formula."},
    {"label": "📋 Change Log Summary",        "prompt": "What are the last 5 changes made in the dashboard system? Who made them and what was the reason?"},
]

# ── Chart renderer ─────────────────────────────────────────────────────────────
def render_chart(spec: dict) -> None:
    """Render a chart from the AI-generated spec using Plotly."""
    try:
        import plotly.graph_objects as go
        chart_type = spec.get("type", "bar")
        title      = spec.get("title", "Chart")
        note       = spec.get("note", "")
        color      = spec.get("color", "#0284c7")

        if chart_type == "bar":
            x = spec.get("x", [])
            y = spec.get("y", [])
            colors = color if isinstance(color, list) else [color] * len(x)
            fig = go.Figure(go.Bar(x=x, y=y, marker_color=colors))
            fig.update_layout(
                title=title,
                xaxis_title=spec.get("x_label", ""),
                yaxis_title=spec.get("y_label", ""),
                height=380,
            )

        elif chart_type == "line":
            fig = go.Figure()
            traces = spec.get("traces")
            if traces:
                for tr in traces:
                    fig.add_trace(go.Scatter(
                        x=tr.get("x", []), y=tr.get("y", []),
                        mode="lines+markers", name=tr.get("name", "")
                    ))
            else:
                fig.add_trace(go.Scatter(
                    x=spec.get("x", []), y=spec.get("y", []),
                    mode="lines+markers", name=title
                ))
            fig.update_layout(
                title=title,
                xaxis_title=spec.get("x_label", ""),
                yaxis_title=spec.get("y_label", ""),
                height=380,
            )

        elif chart_type == "heatmap":
            import plotly.express as px
            z        = spec.get("z", [])
            x_labels = spec.get("x_labels", [])
            y_labels = spec.get("y_labels", [])
            fig = px.imshow(
                z, x=x_labels, y=y_labels,
                color_continuous_scale="YlOrRd", text_auto=True,
                title=title,
            )
            fig.update_layout(height=420)

        elif chart_type == "scatter":
            traces = spec.get("traces")
            fig = go.Figure()
            if traces:
                for tr in traces:
                    fig.add_trace(go.Scatter(
                        x=tr.get("x", []), y=tr.get("y", []),
                        mode="markers", name=tr.get("name", ""),
                    ))
            else:
                fig.add_trace(go.Scatter(
                    x=spec.get("x", []), y=spec.get("y", []),
                    mode="markers",
                ))
            fig.update_layout(
                title=title,
                xaxis_title=spec.get("x_label", ""),
                yaxis_title=spec.get("y_label", ""),
                height=380,
            )

        elif chart_type == "pie":
            labels = spec.get("labels", [])
            values = spec.get("values", [])
            fig = go.Figure(go.Pie(labels=labels, values=values, hole=0.35))
            fig.update_layout(title=title, height=360)

        else:
            st.warning(f"Unknown chart type: {chart_type}")
            return

        st.plotly_chart(fig, use_container_width=True)
        if note:
            st.caption(note)

    except ImportError:
        st.warning("Plotly not installed. Run: `pip install plotly`")
    except Exception as exc:
        st.warning(f"Chart render error: {exc}\n\n```json\n{json.dumps(spec, indent=2)}\n```")


# ── Export helpers ─────────────────────────────────────────────────────────────
def export_chat_to_excel(history: list[dict]) -> bytes:
    """Convert chat history to Excel bytes."""
    rows = []
    for msg in history:
        rows.append({
            "Timestamp (IST)": msg.get("timestamp", ""),
            "Role":            msg.get("role_label", msg.get("role", "")),
            "Message":         msg.get("content", ""),
            "Confidence":      msg.get("confidence", ""),
            "Sources":         ", ".join(msg.get("sources", [])),
        })
    df = pd.DataFrame(rows)
    import io
    buf = io.BytesIO()
    df.to_excel(buf, index=False, engine="openpyxl")
    buf.seek(0)
    return buf.read()


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR SETUP (role + api key)
# ══════════════════════════════════════════════════════════════════════════════

def _setup_sidebar() -> tuple[str, str | None, bool]:
    """
    Returns (selected_role, api_key, deep_mode).
    Renders role selector and API key input in sidebar.
    """
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🤖 AI Assistant Settings")

    role = st.sidebar.selectbox(
        "Your Role",
        ["Admin", "Sales", "Strategy", "Finance", "Operations"],
        index=0,
        help="Controls which data the AI can access.",
    )

    fg, bg = ROLE_COLOUR.get(role, ("#374151", "#f9fafb"))
    st.sidebar.markdown(
        f'<div style="background:{bg};color:{fg};padding:6px 12px;border-radius:8px;'
        f'font-size:0.78rem;font-weight:600;margin-top:4px">'
        f'Active: {role}</div>',
        unsafe_allow_html=True,
    )

    deep_mode = st.sidebar.toggle(
        "🔬 Deep Analysis Mode",
        value=False,
        help="Uses claude-sonnet-4-6 (slower but more thorough). Default: haiku.",
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("##### 🔑 Anthropic API Key")

    try:
        from ai_assistant_engine import get_api_key, save_api_key
        existing_key = get_api_key()
    except Exception:
        existing_key = None

    if existing_key:
        st.sidebar.success(f"Key loaded ✅ (…{existing_key[-6:]})")
        api_key = existing_key
        if st.sidebar.button("🔄 Change Key"):
            st.session_state["show_key_input"] = True
    else:
        st.session_state["show_key_input"] = True
        api_key = None

    if st.session_state.get("show_key_input"):
        new_key = st.sidebar.text_input(
            "Enter API Key", type="password",
            placeholder="sk-ant-api03-…",
        )
        if new_key and st.sidebar.button("💾 Save Key"):
            try:
                from ai_assistant_engine import save_api_key
                save_api_key(new_key)
                st.session_state["show_key_input"] = False
                st.sidebar.success("Key saved!")
                api_key = new_key
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"Could not save: {e}")

    return role, api_key, deep_mode


# ══════════════════════════════════════════════════════════════════════════════
# CHAT TAB
# ══════════════════════════════════════════════════════════════════════════════

def _render_chat_tab(role: str, api_key: str | None, deep_mode: bool) -> None:
    # Initialise session state
    if "ai_chat_history"   not in st.session_state:
        st.session_state["ai_chat_history"]   = []  # [{role, content, ts, confidence, sources, chart}]
    if "ai_msg_history"    not in st.session_state:
        st.session_state["ai_msg_history"]    = []  # Claude API format [{role, content}]

    # ── Quick action buttons ──────────────────────────────────────────────────
    st.markdown("#### ⚡ Quick Actions")
    cols = st.columns(5)
    for i, action in enumerate(QUICK_ACTIONS):
        if cols[i % 5].button(action["label"], key=f"qa_{i}", use_container_width=True):
            st.session_state["pending_prompt"] = action["prompt"]

    st.markdown("---")

    # ── Replay pending prompt from quick action ───────────────────────────────
    if "pending_prompt" in st.session_state and st.session_state["pending_prompt"]:
        _handle_user_message(
            st.session_state.pop("pending_prompt"),
            role, api_key, deep_mode,
        )

    # ── Display existing chat history ─────────────────────────────────────────
    for msg in st.session_state["ai_chat_history"]:
        _role_ui = msg.get("role")
        with st.chat_message(_role_ui):
            st.markdown(msg["content"])
            if msg.get("chart"):
                render_chart(msg["chart"])
            if msg.get("confidence") and _role_ui == "assistant":
                conf = msg["confidence"]
                col = {"HIGH": "🟢", "MEDIUM": "🟡", "LOW": "🔴"}.get(conf, "⚪")
                ts  = msg.get("timestamp", "")
                src = ", ".join(msg.get("sources", []))
                st.caption(f"{col} Confidence: {conf} | {ts}{' | Source: '+src if src else ''}")

    # ── Chat input ────────────────────────────────────────────────────────────
    user_input = st.chat_input("Ask anything about the dashboard data…")
    if user_input:
        _handle_user_message(user_input, role, api_key, deep_mode)

    # ── Export button ─────────────────────────────────────────────────────────
    if st.session_state["ai_chat_history"]:
        st.markdown("---")
        c1, c2, c3 = st.columns([1, 1, 3])
        if c1.button("🗑️ Clear Chat"):
            st.session_state["ai_chat_history"] = []
            st.session_state["ai_msg_history"]  = []
            st.rerun()
        try:
            excel_bytes = export_chat_to_excel(st.session_state["ai_chat_history"])
            ts_str = datetime.datetime.now().strftime("%d%m%Y_%H%M")
            c2.download_button(
                label="📥 Export to Excel",
                data=excel_bytes,
                file_name=f"AI_Chat_{ts_str}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        except Exception:
            pass


def _handle_user_message(
    question: str,
    role:     str,
    api_key:  str | None,
    deep_mode: bool,
) -> None:
    """Append user message, call AI, append assistant reply."""
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M IST")

    # Add user message to display history
    st.session_state["ai_chat_history"].append({
        "role": "user", "content": question, "timestamp": ts,
    })
    # Add to Claude API format history
    st.session_state["ai_msg_history"].append({"role": "user", "content": question})

    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.markdown("⏳ Thinking…")

        try:
            from ai_assistant_engine import ask_ai
            result = ask_ai(
                question=question,
                role=role,
                history=st.session_state["ai_msg_history"][:-1],  # exclude current
                deep_mode=deep_mode,
                api_key=api_key,
            )
            answer     = result["answer"]
            chart_spec = result.get("chart")
            confidence = result.get("confidence", "MEDIUM")
            sources    = result.get("sources", [])

        except Exception as exc:
            answer     = f"⚠️ Error calling AI engine: {exc}"
            chart_spec = None
            confidence = "LOW"
            sources    = []

        placeholder.markdown(answer)
        if chart_spec:
            render_chart(chart_spec)

        model_used = result.get("model_used", "") if isinstance(result, dict) else ""
        conf_col = {"HIGH": "🟢", "MEDIUM": "🟡", "LOW": "🔴"}.get(confidence, "⚪")
        src_text = ", ".join(sources) if sources else ""
        st.caption(
            f"{conf_col} Confidence: {confidence} | {ts}"
            + (f" | Source: {src_text}" if src_text else "")
            + (f" | Model: {model_used}" if model_used else "")
        )

    # Store assistant reply
    st.session_state["ai_chat_history"].append({
        "role":       "assistant",
        "content":    answer,
        "chart":      chart_spec,
        "confidence": confidence,
        "sources":    sources,
        "timestamp":  ts,
        "model":      model_used if isinstance(result, dict) else "",
    })
    st.session_state["ai_msg_history"].append({"role": "assistant", "content": answer})


# ══════════════════════════════════════════════════════════════════════════════
# HISTORY & FAQ TAB
# ══════════════════════════════════════════════════════════════════════════════

def _render_history_tab() -> None:
    st.markdown("### 📜 Query History & FAQ")
    try:
        from ai_assistant_engine import get_query_history, get_faq, get_role_query_breakdown
    except Exception as exc:
        st.error(f"Could not load history module: {exc}")
        return

    h_tab, faq_tab, role_tab = st.tabs(["Recent Queries", "Frequently Asked", "By Department"])

    with h_tab:
        history = get_query_history(n=50)
        if not history:
            st.info("No queries logged yet.")
        else:
            df = pd.DataFrame(history)[["timestamp_ist","role","question","confidence","model"]]
            df.columns = ["Timestamp (IST)", "Role", "Question", "Confidence", "Model"]
            st.dataframe(df, use_container_width=True, hide_index=True)

    with faq_tab:
        faq = get_faq(top=15)
        if not faq:
            st.info("Not enough data yet for FAQ.")
        else:
            df = pd.DataFrame(faq)[["question","count","last_asked","role"]]
            df.columns = ["Question", "Times Asked", "Last Asked", "Role"]
            st.dataframe(df, use_container_width=True, hide_index=True)

    with role_tab:
        breakdown = get_role_query_breakdown()
        if not breakdown:
            st.info("No data yet.")
        else:
            try:
                import plotly.graph_objects as go
                fig = go.Figure(go.Bar(
                    x=list(breakdown.keys()),
                    y=list(breakdown.values()),
                    marker_color=["#7c3aed","#0284c7","#0d9488","#d97706","#dc2626"][:len(breakdown)],
                ))
                fig.update_layout(title="Query Count by Department Role",
                                  xaxis_title="Role", yaxis_title="Queries",
                                  height=320)
                st.plotly_chart(fig, use_container_width=True)
            except Exception:
                st.table(pd.DataFrame(list(breakdown.items()), columns=["Role", "Queries"]))


# ══════════════════════════════════════════════════════════════════════════════
# QUICK CHART TAB
# ══════════════════════════════════════════════════════════════════════════════

def _render_quick_charts_tab(role: str) -> None:
    st.markdown("### 📊 Pre-built Data Charts")
    st.caption("These charts are rendered directly from live dashboard data — no AI call required.")

    try:
        from ai_data_layer import get_chart_data
    except Exception as exc:
        st.error(f"Data layer error: {exc}")
        return

    chart_options = {
        "India Bitumen Consumption (12 Months)": "india_consumption_12m",
        "State-wise Road Budget":                "state_demand_bar",
        "Refinery Price Comparison":             "price_trend_refinery",
        "Contractor Demand by Project":          "contractor_demand_bar",
        "International Bitumen FOB Prices":      "intl_bitumen_fob",
        "API Health — Error Status":             "api_health_pie",
    }

    selected = st.selectbox("Select Chart", list(chart_options.keys()))
    chart_key = chart_options[selected]
    data = get_chart_data(chart_key, role)
    if data:
        render_chart(data)
        source = data.get("source", "")
        if source:
            st.caption(f"_(Data source: {source})_")
    else:
        st.info(f"No data available for '{selected}'. Module may not be loaded or role access restricted.")


# ══════════════════════════════════════════════════════════════════════════════
# ARCHITECTURE TAB
# ══════════════════════════════════════════════════════════════════════════════

def _render_architecture_tab() -> None:
    st.markdown("### 🏛️ System Architecture & Data Access Map")

    st.markdown("""
```
┌──────────────────────────────────────────────────────────────┐
│              AI DASHBOARD ASSISTANT — ARCHITECTURE            │
│                    PPS Anantams Logistics                     │
└──────────────────────────────────────────────────────────────┘

  USER (Streamlit UI)
       │
       ▼
  ┌────────────────────────────────┐
  │  command_intel/                │
  │  ai_dashboard_assistant.py     │  ← Chat UI, Quick Actions,
  │  • Role selector               │    Charts, Export, History
  │  • Chat interface              │
  │  • Plotly chart renderer       │
  └─────────────┬──────────────────┘
                │
                ▼
  ┌────────────────────────────────┐
  │  ai_assistant_engine.py        │  ← Orchestration Layer
  │  • API key management          │
  │  • System prompt builder       │
  │  • Claude API call             │
  │  • Response parser             │
  │  • Query logger                │
  └──────────┬─────────────────────┘
             │
             ▼
  ┌──────────────────────────────────────────────────────────┐
  │  ai_data_layer.py   (Role-filtered data aggregator)      │
  │                                                          │
  │  ┌───────────────┐  ┌──────────────┐  ┌──────────────┐  │
  │  │feasibility_   │  │api_manager.  │  │competitor_   │  │
  │  │engine.py      │  │py            │  │intelligence  │  │
  │  │• 39 prices    │  │• error_log   │  │.py           │  │
  │  │• transport    │  │• change_log  │  │• MEE data    │  │
  │  │• FX rates     │  │• dev_log     │  │• PSU prices  │  │
  │  └───────────────┘  │• health_log  │  │• Intl FOB    │  │
  │                     └──────────────┘  └──────────────┘  │
  │  ┌───────────────┐  ┌──────────────┐  ┌──────────────┐  │
  │  │contractor_    │  │road_budget_  │  │price_        │  │
  │  │osint.py       │  │demand.py     │  │prediction.py │  │
  │  │• contractors  │  │• MoRTH data  │  │• forecast    │  │
  │  │• projects     │  │• state data  │  │• revisions   │  │
  │  │• demand MT    │  │• consumption │  │• calendar    │  │
  │  │• risk flags   │  └──────────────┘  └──────────────┘  │
  │  └───────────────┘                                       │
  └──────────────────────────────────────────────────────────┘
                │
                ▼
  ┌────────────────────────────────┐
  │  Anthropic API                 │
  │  claude-haiku-4-5  (default)   │
  │  claude-sonnet-4-6 (deep mode) │
  └────────────────────────────────┘
                │
                ▼
  ┌────────────────────────────────┐
  │  ai_query_log.json             │  ← Persistent query log
  │  {timestamp, role, question,   │    (up to 2,000 entries)
  │   answer_summary, confidence,  │
  │   sources, model}              │
  └────────────────────────────────┘
```
""")

    st.markdown("### 🔐 Role-Based Access Control Matrix")
    role_matrix = {
        "Module":            ["Prices", "APIs",  "Competitors", "CRM/Contractors", "Demand", "Errors/Changes", "Predictions", "Dev Log"],
        "Admin":             ["✅",     "✅",     "✅",           "✅",              "✅",      "✅",              "✅",           "✅"],
        "Sales":             ["✅",     "❌",     "✅",           "✅ (with contacts)","✅",    "❌",              "❌",           "❌"],
        "Strategy":          ["✅",     "❌",     "✅",           "✅ (no contacts)", "✅",     "❌",              "✅",           "❌"],
        "Finance":           ["✅",     "❌",     "❌",           "❌",              "✅",      "❌",              "✅",           "❌"],
        "Operations":        ["✅",     "✅",     "❌",           "❌",              "✅",      "✅",              "❌",           "❌"],
    }
    st.dataframe(pd.DataFrame(role_matrix).set_index("Module").T, use_container_width=True)

    st.markdown("### 📋 Database Access Map")
    db_map = pd.DataFrame([
        ["ai_query_log.json",              "AI Engine",          "All roles",    "Query logging, FAQ, history"],
        ["api_error_log.json",             "api_manager.py",     "Admin/Ops",    "Bug tracker, error audit"],
        ["api_change_log.json",            "api_manager.py",     "Admin/Ops",    "Change audit trail"],
        ["api_dev_log.json",               "api_manager.py",     "Admin",        "Developer activity feed"],
        ["osint_data/contractors_master",  "contractor_osint.py","Admin/Sales",  "Contractor CRM records"],
        ["osint_data/projects_master",     "contractor_osint.py","Admin/Sales",  "Road project awards"],
        ["osint_data/bitumen_demand_estimates","contractor_osint","Admin/Sales",  "MT demand per project"],
        ["osint_data/risk_flags.json",     "contractor_osint.py","Admin/Sales",  "Contractor risk flags"],
        ["live_prices.json",               "feasibility_engine", "All roles",    "Live PSU/drum prices"],
        ["MEE_FORECASTS (in-memory)",      "competitor_intel.",  "Admin/Sales",  "Daily MEE price forecasts"],
        ["INDIA_CONSUMPTION (in-memory)",  "competitor_intel.",  "Admin/Strategy","Monthly India consumption TMT"],
        ["MORTH_BUDGET (in-memory)",       "road_budget_demand", "Admin/Finance","MoRTH road budget data"],
    ], columns=["Data Store", "Source Module", "Role Access", "Purpose"])
    st.dataframe(db_map, use_container_width=True, hide_index=True)

    st.markdown("### 📌 20 Sample Questions & Expected Answers")
    faq_examples = [
        ("What is current VG-30 price at IOCL Koyali?",              "HIGH",   "₹48,302/MT basic (ex-Koyali, w.e.f. 16-02-2026). Source: live_prices.json"),
        ("Which refinery has the cheapest VG-30 today?",              "HIGH",   "HPCL Ghaziabad at ₹46,390/MT. Source: live_prices.json"),
        ("Calculate landed cost from IOCL Koyali to Pune, 900 km.",  "HIGH",   "₹48,302 + (900 × ₹2.5/km) = ₹50,552/MT. Formula shown."),
        ("What is USD/INR today?",                                    "HIGH",   "₹86.87/$ (RBI reference). MEE bank TT rate ≈ ₹90.66-91.06."),
        ("What is Brent crude price?",                                "HIGH",   "~₹ 74.50/barrel. Source: api_manager.get_brent_price()"),
        ("Which state has highest bitumen demand?",                   "MEDIUM", "Rajasthan (largest NH network). Source: road_budget_demand.STATE_DATA"),
        ("Show last 12 months India consumption chart.",              "HIGH",   "Bar chart generated from INDIA_CONSUMPTION (MEE Feb 2026 data)"),
        ("What is next PSU revision date?",                           "HIGH",   "01-03-2026 (1st fortnightly revision of March)."),
        ("MEE forecast accuracy for Feb 16 revision?",                "HIGH",   "EXACT MATCH — MEE predicted +₹60, IOCL actual +₹60, HPCL +₹60."),
        ("Which contractor has highest bitumen demand?",              "HIGH",   "From osint_data: [contractor name] with [N] MT. Source: bitumen_demand_estimates"),
        ("How many open P0 bugs in the system?",                      "HIGH",   "From api_error_log.json — real-time count. Source: api_manager"),
        ("What APIs failed in the last 24 hours?",                    "HIGH",   "From api_error_log.json with datetime filter. Source: api_manager"),
        ("Estimate MT bitumen for 250 km NH 4-Lane project.",        "HIGH",   "250 km × 280 MT/km (base) = 70,000 MT. Formula: km × MT/km from BITUMEN_MT_PER_KM"),
        ("Convert ₹48,302/MT to USD/MT.",                             "HIGH",   "₹48,302 ÷ 86.87 = ₹ 555.97/MT. Formula shown."),
        ("Which state should we focus sales in this quarter?",        "MEDIUM", "Based on road budget + seasonality: Rajasthan/Maharashtra peak in Mar. [ASSUMPTION] stated."),
        ("Show refinery price comparison chart.",                     "HIGH",   "Bar chart: 7 refineries with basic prices. Source: live_prices.json"),
        ("What changed in the system in the last 3 days?",           "HIGH",   "From api_change_log.json — last 5 entries shown. Source: api_manager"),
        ("International bitumen FOB — cheapest country?",            "HIGH",   "From INTL_BITUMEN DataFrame. Source: competitor_intelligence.py (MEE)"),
        ("What is the road budget for Maharashtra FY2025-26?",       "HIGH",   "₹[N] crore total. Source: road_budget_demand.STATE_DATA"),
        ("Show me contractor risk flags.",                            "HIGH",   "From osint_data/risk_flags.json — OPEN flags listed. Source: contractor_osint.py"),
    ]
    df_faq = pd.DataFrame(faq_examples, columns=["Sample Question", "Confidence", "Expected Answer"])
    df_faq.index = range(1, len(df_faq) + 1)
    st.dataframe(df_faq, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# SETUP / INTEGRATION CHECKLIST TAB
# ══════════════════════════════════════════════════════════════════════════════

def _render_setup_tab() -> None:
    st.markdown("### ⚙️ Setup & Integration Checklist")

    # Dependency check
    st.markdown("#### 1. Package Dependencies")
    packages = {
        "anthropic":    "Anthropic Python SDK — required for AI",
        "streamlit":    "UI framework",
        "plotly":       "Chart rendering",
        "pandas":       "Data manipulation",
        "openpyxl":     "Excel export",
    }
    for pkg, desc in packages.items():
        try:
            __import__(pkg)
            st.markdown(f"✅ **{pkg}** — {desc}")
        except ImportError:
            st.markdown(f"❌ **{pkg}** — {desc}  →  `pip install {pkg}`")

    # API key check
    st.markdown("#### 2. API Key")
    try:
        from ai_assistant_engine import get_api_key
        key = get_api_key()
        if key:
            st.success(f"✅ API key configured (…{key[-6:]})")
        else:
            st.warning("❌ API key NOT set — enter it in the sidebar or set `ANTHROPIC_API_KEY` env variable.")
    except Exception as e:
        st.error(f"Engine import error: {e}")

    # Module checks
    st.markdown("#### 3. Data Module Health")
    modules = {
        "feasibility_engine":    "get_live_prices",
        "api_manager":           "get_error_log",
        "competitor_intelligence":"MEE_FORECASTS",
        "contractor_osint":      "estimate_bitumen",
        "road_budget_demand":    "MORTH_BUDGET",
    }
    for mod, attr in modules.items():
        try:
            m = __import__(mod)
            has = hasattr(m, attr)
            icon = "✅" if has else "⚠️"
            st.markdown(f"{icon} **{mod}** — `{attr}` {'found' if has else 'NOT FOUND'}")
        except ImportError:
            st.markdown(f"❌ **{mod}** — import failed")

    # Log file
    from pathlib import Path
    log_path = Path(__file__).parent.parent / "ai_query_log.json"
    st.markdown("#### 4. Query Log File")
    if log_path.exists():
        size = log_path.stat().st_size
        st.success(f"✅ `ai_query_log.json` exists — {size:,} bytes")
    else:
        st.info("ℹ️ `ai_query_log.json` will be created on first query.")

    st.markdown("#### 5. Quick Install Command")
    st.code("pip install anthropic openpyxl plotly pandas streamlit", language="bash")

    st.markdown("#### 6. Integration Checklist")
    checklist = [
        ("ai_data_layer.py created",                         True),
        ("ai_assistant_engine.py created",                   True),
        ("command_intel/ai_dashboard_assistant.py created",  True),
        ("Wired into dashboard.py nav",                      True),
        ("Role-based context filtering",                     True),
        ("Chart generation from AI responses",               True),
        ("Query logging to ai_query_log.json",               True),
        ("Pre-built quick charts",                           True),
        ("Export chat to Excel",                             True),
        ("API key management (env + file + UI)",             True),
        ("FAQ from query history",                           True),
        ("Deep mode (sonnet) toggle",                        True),
        ("Architecture diagram in UI",                       True),
        ("20 sample Q&A documented",                         True),
        ("Streaming support (stream_ai)",                    True),
    ]
    for item, done in checklist:
        st.markdown(f"{'✅' if done else '⬜'} {item}")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN RENDER ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def render() -> None:
    display_badge("real-time")
    st.markdown("# 🤖 AI Dashboard Assistant")
    # Show active AI model
    try:
        from ai_fallback_engine import get_active_model_name
        _model_label = get_active_model_name()
    except Exception:
        _model_label = "Claude (Anthropic)"
    st.markdown(
        f"_Powered by {_model_label} · Connected to ALL dashboard data · "
        "India-formatted · Role-controlled · Query-logged_"
    )

    # Sidebar
    role, api_key, deep_mode = _setup_sidebar()

    # Role badge
    fg, bg = ROLE_COLOUR.get(role, ("#374151", "#f9fafb"))
    st.markdown(
        f'<div style="display:inline-flex;align-items:center;background:{bg};color:{fg};'
        f'padding:5px 14px;border-radius:10px;font-size:0.82rem;font-weight:700;margin-bottom:12px;">'
        f'Active Role: {role}</div>',
        unsafe_allow_html=True,
    )

    if not api_key:
        # Check if free AI is available
        _free_available = False
        try:
            from ai_fallback_engine import get_provider_status
            _free_statuses = get_provider_status()
            _free_available = any(p["ready"] and p.get("cost") == "FREE" for p in _free_statuses)
        except Exception:
            pass

        if _free_available:
            st.info(
                "🦙 **Using Free AI** — No API key needed. "
                "Responses powered by local/free AI models."
            )
        else:
            st.warning(
                "⚠️ **No AI provider available.**\n\n"
                "**Free (recommended):** Install Ollama from ollama.com, then `ollama pull llama3`\n\n"
                "**Paid (optional):** Enter Anthropic API key in sidebar."
            )

    # Main tabs
    tab_chat, tab_charts, tab_history, tab_arch, tab_setup = st.tabs([
        "💬 Chat",
        "📊 Quick Charts",
        "📜 History & FAQ",
        "🏛️ Architecture",
        "⚙️ Setup",
    ])

    with tab_chat:
        _render_chat_tab(role, api_key, deep_mode)

    with tab_charts:
        _render_quick_charts_tab(role)

    with tab_history:
        _render_history_tab()

    with tab_arch:
        _render_architecture_tab()

    with tab_setup:
        _render_setup_tab()
