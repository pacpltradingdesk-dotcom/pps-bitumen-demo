"""
AI Fallback Dashboard — Streamlit UI
=====================================
Multi-provider AI chat for PPS Anantams Dashboard.

Tabs:
  💬 Chat          — Q&A with active AI + 'Who is this?' banner
  🔌 Provider Hub  — Status of all 5 providers + install guide
  📋 Switch & Test — Manual provider override + health ping
  📜 Event Log     — Full fallback/restore event history
  ℹ️  About        — How the fallback system works
"""

from __future__ import annotations

import sys
import datetime
from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

# ── Import fallback engine ────────────────────────────────────────────────────
try:
    import ai_fallback_engine as afe
    AFE_OK = True
except ImportError as _e:
    AFE_OK = False
    _AFE_ERR = str(_e)

# ── Try to import live dashboard context ──────────────────────────────────────
try:
    from ai_data_layer import build_context_json
    DATA_LAYER_OK = True
except ImportError:
    DATA_LAYER_OK = False
    def build_context_json(role="Admin"):
        return '{"note": "ai_data_layer not available — context limited."}'

# ── Colour palette ────────────────────────────────────────────────────────────
PROVIDER_COLORS = {
    "openai":      "#10b981",   # green
    "ollama":      "#8b5cf6",   # purple
    "huggingface": "#f59e0b",   # amber
    "gpt4all":     "#06b6d4",   # cyan
    "claude":      "#3b82f6",   # blue
    "none":        "#ef4444",   # red
}

STATUS_COLORS = {
    "ready":    "#22c55e",
    "partial":  "#f59e0b",
    "offline":  "#ef4444",
}

EVENT_COLORS = {
    "success":         "#22c55e",
    "fallback":        "#f59e0b",
    "restored":        "#06b6d4",
    "all_failed":      "#ef4444",
    "manual_override": "#8b5cf6",
}

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _hdr(icon: str, title: str, color: str = "#3b82f6"):
    st.markdown(
        f'<div style="border-left:4px solid {color};padding:6px 14px;'
        f'margin:14px 0 8px 0;background:linear-gradient(90deg,{color}18,transparent)">'
        f'<span style="font-size:1.05rem;font-weight:700">{icon} {title}</span></div>',
        unsafe_allow_html=True,
    )


def _card(col, label: str, val: str, sub: str = "", color: str = "#3b82f6"):
    col.markdown(
        f'<div style="background:linear-gradient(135deg,#1e293b,#0f172a);'
        f'border-left:4px solid {color};border-radius:10px;'
        f'padding:12px 16px;text-align:center;margin:3px">'
        f'<div style="color:#94a3b8;font-size:0.76rem">{label}</div>'
        f'<div style="color:#f8fafc;font-size:1.25rem;font-weight:800">{val}</div>'
        f'<div style="color:{color};font-size:0.74rem">{sub}</div></div>',
        unsafe_allow_html=True,
    )


def _provider_badge(p: dict):
    """Render a full provider status card."""
    pid   = p["id"]
    color = PROVIDER_COLORS.get(pid, "#475569")
    ready = p["ready"]
    active= p.get("is_active", False)
    border = f"3px solid {color}" if not active else f"3px solid #fff"
    glow   = f"box-shadow:0 0 12px {color}88;" if active else ""

    pkg_icon  = "✅" if p["pkg_installed"]  else "❌"
    key_icon  = "✅" if p["has_key"]        else ("—" if not p["needs_key"] else "❌")
    dmn_icon  = "✅" if p.get("daemon_ok", True) else "❌"
    rdy_icon  = "🟢" if ready               else "🔴"
    act_badge = ' <span style="background:#facc15;color:#000;padding:1px 7px;border-radius:8px;font-size:0.7rem">ACTIVE</span>' if active else ""

    last_err = p.get("last_error", "")
    err_html = (
        f'<div style="color:#ef4444;font-size:0.74rem;margin-top:4px">Last error: {last_err[:80]}</div>'
        if last_err else ""
    )

    st.markdown(
        f'<div style="background:#0f172a;border:{border};{glow}'
        f'border-radius:10px;padding:12px 16px;margin-bottom:10px">'
        f'<div style="display:flex;justify-content:space-between;align-items:center">'
        f'<span style="color:{color};font-size:1.1rem;font-weight:800">'
        f'{p["icon"]} {p["name"]}{act_badge}</span>'
        f'<span style="color:#94a3b8;font-size:0.78rem">{p["type"]}'
        f'{" <span style=&quot;background:#22c55e;color:#fff;padding:1px 6px;border-radius:4px;font-size:0.65rem&quot;>FREE</span>" if p.get("cost") == "FREE" else " <span style=&quot;background:#f59e0b;color:#000;padding:1px 6px;border-radius:4px;font-size:0.65rem&quot;>PAID</span>"}'
        f'</span></div>'
        f'<div style="display:flex;gap:18px;margin-top:6px;font-size:0.8rem">'
        f'<span style="color:#94a3b8">Package: <b style="color:#f8fafc">{pkg_icon} {p["pkg"]}</b></span>'
        f'<span style="color:#94a3b8">API Key: <b style="color:#f8fafc">{key_icon}</b></span>'
        f'<span style="color:#94a3b8">Ready: <b style="color:#f8fafc">{rdy_icon}</b></span></div>'
        f'{err_html}'
        f'<div style="color:#475569;font-size:0.74rem;margin-top:4px">'
        f'Install: <code style="color:#94a3b8">{p["install_cmd"]}</code></div>'
        f'<div style="color:#64748b;font-size:0.73rem">{p["setup_note"]}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — CHAT
# ══════════════════════════════════════════════════════════════════════════════

def _tab_chat():
    _hdr("💬", "Dashboard Q&A — Auto-Fallback AI Chat", "#3b82f6")

    if not AFE_OK:
        st.error(f"ai_fallback_engine.py not found: {_AFE_ERR}")
        return

    # Start background monitor
    afe.start_monitor()

    # ── Sidebar-style controls ─────────────────────────────────────────────
    with st.expander("⚙️ Settings & API Keys", expanded=False):
        st.caption("Keys saved to ai_fallback_config.json. Priority: env var → config file → UI input.")
        col_a, col_b = st.columns(2)
        with col_a:
            oai_key = st.text_input("OpenAI API Key", type="password",
                                    value=afe.get_api_key("openai") or "",
                                    placeholder="sk-…", key="fallback_oai")
            if st.button("💾 Save OpenAI Key", key="save_oai"):
                afe.save_api_key("openai", oai_key)
                st.success("Saved!")
        with col_b:
            hf_token = st.text_input("HuggingFace Token (optional)", type="password",
                                     value=afe.get_api_key("huggingface") or "",
                                     placeholder="hf_…", key="fallback_hf")
            if st.button("💾 Save HF Token", key="save_hf"):
                afe.save_api_key("huggingface", hf_token)
                st.success("Saved!")

        col_c, _ = st.columns(2)
        with col_c:
            claude_key = st.text_input("Anthropic (Claude) Key", type="password",
                                       value=afe.get_api_key("claude") or "",
                                       placeholder="sk-ant-…", key="fallback_claude")
            if st.button("💾 Save Claude Key", key="save_claude"):
                afe.save_api_key("claude", claude_key)
                st.success("Saved!")

    # ── Active provider banner ─────────────────────────────────────────────
    active = afe.get_active_provider()
    acolor = PROVIDER_COLORS.get(active["id"], "#3b82f6")
    st.markdown(
        f'<div style="background:linear-gradient(135deg,#1e293b,#0f172a);'
        f'border:2px solid {acolor};border-radius:10px;padding:10px 16px;margin-bottom:12px">'
        f'<span style="color:{acolor};font-size:1rem;font-weight:700">'
        f'{active["icon"]} Active AI: {active["name"]}</span>'
        f'<span style="color:#94a3b8;font-size:0.82rem"> — {active["type"]}</span>'
        f'<div style="color:#64748b;font-size:0.76rem;margin-top:3px">'
        f'Auto-monitors OpenAI every 5 min | Switches back silently when recovered</div></div>',
        unsafe_allow_html=True,
    )

    # ── Quick action buttons ───────────────────────────────────────────────
    _hdr("⚡", "Quick Dashboard Questions", "#22c55e")
    QUICK_QS = [
        "What are today's bitumen prices?",
        "Show me the top 5 projects by bitumen demand",
        "What is the total order book value across all contractors?",
        "Explain the monthly demand heatmap",
        "Which contractor has the highest bitumen requirement this month?",
        "What are the active risk flags?",
        "Show competitor price forecasts",
        "What is the landed cost from Koyali to Bhopal?",
    ]
    cols = st.columns(4)
    for i, q in enumerate(QUICK_QS):
        if cols[i % 4].button(q[:35] + ("…" if len(q) > 35 else ""), key=f"fq_{i}"):
            st.session_state["fallback_pending_q"] = q

    # ── Chat history ───────────────────────────────────────────────────────
    if "fallback_history" not in st.session_state:
        st.session_state["fallback_history"] = []

    for msg in st.session_state["fallback_history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # ── Handle pending quick question ──────────────────────────────────────
    pending = st.session_state.pop("fallback_pending_q", None)

    # ── Chat input ─────────────────────────────────────────────────────────
    user_input = st.chat_input("Ask any dashboard question… (auto-fallback AI active)")
    question   = pending or user_input

    if question:
        st.session_state["fallback_history"].append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("Querying AI (auto-fallback active)…"):
                # Build dashboard context
                context = build_context_json("Admin") if DATA_LAYER_OK else ""

                result   = afe.ask_with_fallback(question, context)
                response = afe.format_who_response(result)

            st.markdown(response)

            # Show fallback trail if any
            if result.get("tried"):
                with st.expander("🔄 Fallback Trail"):
                    for t in result["tried"]:
                        st.markdown(
                            f'<span style="color:#f59e0b">↳ Skipped {t["name"]}: {t["reason"]}</span>',
                            unsafe_allow_html=True,
                        )

        st.session_state["fallback_history"].append({"role": "assistant", "content": response})

    # ── Clear chat ─────────────────────────────────────────────────────────
    if st.session_state["fallback_history"]:
        if st.button("🗑️ Clear Chat", key="clear_fallback_chat"):
            st.session_state["fallback_history"] = []
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — PROVIDER HUB
# ══════════════════════════════════════════════════════════════════════════════

def _tab_providers():
    _hdr("🔌", "AI Provider Status Hub", "#8b5cf6")
    st.caption("Real-time status of all 5 AI providers in the fallback chain.")

    if not AFE_OK:
        st.error("ai_fallback_engine.py not found.")
        return

    statuses = afe.get_provider_status()

    # KPI row
    total   = len(statuses)
    ready   = sum(1 for p in statuses if p["ready"])
    active  = next((p["name"] for p in statuses if p.get("is_active")), "None")
    free_rdy= sum(1 for p in statuses if p["ready"] and "Free" in p["type"])

    k1, k2, k3, k4 = st.columns(4)
    _card(k1, "Total Providers",    str(total),    "In chain",          "#3b82f6")
    _card(k2, "Providers Ready",    str(ready),    "Configured + OK",   "#22c55e")
    _card(k3, "Free Providers",     str(free_rdy), "Ready & free",      "#8b5cf6")
    _card(k4, "Active AI",          active[:16],   "Serving queries",   "#f59e0b")

    st.markdown("---")
    _hdr("📋", "Provider Chain (Priority Order)", "#3b82f6")
    st.caption("Queries fall through this chain top-to-bottom until a provider succeeds.")

    for i, p in enumerate(statuses):
        col_num, col_card = st.columns([0.06, 0.94])
        color = PROVIDER_COLORS.get(p["id"], "#475569")
        col_num.markdown(
            f'<div style="background:{color};color:#fff;border-radius:50%;'
            f'width:28px;height:28px;display:flex;align-items:center;'
            f'justify-content:center;font-weight:800;font-size:0.9rem;margin-top:8px">'
            f'{i+1}</div>',
            unsafe_allow_html=True,
        )
        with col_card:
            _provider_badge(p)

    # ── Ollama Model Selector ──────────────────────────────────────────────
    st.markdown("---")
    _hdr("🦙", "Ollama Model Selection", "#8b5cf6")
    st.caption("Choose which model Ollama uses. Requires `ollama pull <model>` first.")
    try:
        current_model = afe.get_preferred_ollama_model()
        selected = st.selectbox(
            "Preferred Ollama Model",
            afe.OLLAMA_MODELS,
            index=afe.OLLAMA_MODELS.index(current_model) if current_model in afe.OLLAMA_MODELS else 0,
            key="ollama_model_select",
        )
        if selected != current_model:
            if st.button("Save Model Choice"):
                afe.set_preferred_ollama_model(selected)
                st.success(f"Ollama model set to: **{selected}**")
                st.rerun()
    except Exception:
        st.info("Ollama model selection unavailable.")

    # ── ML & NLP Status ─────────────────────────────────────────────────
    st.markdown("---")
    _hdr("🧠", "ML & NLP Engine Status", "#06b6d4")
    _ml_col1, _ml_col2, _ml_col3 = st.columns(3)
    try:
        from ml_forecast_engine import get_ml_status
        ml = get_ml_status()
        _ml_col1.metric("Prophet", "Installed" if ml.get("prophet_available") else "Not installed")
        _ml_col1.metric("scikit-learn", "Installed" if ml.get("sklearn_available") else "Not installed")
    except Exception:
        _ml_col1.metric("Prophet", "Not available")
        _ml_col1.metric("scikit-learn", "Not available")
    try:
        from nlp_extraction_engine import get_nlp_status
        nlp = get_nlp_status()
        _ml_col2.metric("spaCy", "Installed" if nlp.get("spacy_available") else "Not installed")
        _ml_col2.metric("spaCy Model", "Loaded" if nlp.get("spacy_model_loaded") else "Not loaded")
    except Exception:
        _ml_col2.metric("spaCy", "Not available")
        _ml_col2.metric("spaCy Model", "Not available")
    try:
        _ml_col3.metric("Transformers", "Installed" if nlp.get("transformers_available") else "Not installed")
    except Exception:
        _ml_col3.metric("Transformers", "Not available")
    try:
        from data_confidence_engine import get_overall_health
        dh = get_overall_health()
        _ml_col3.metric("Data Health", f'{dh["average_score"]}%', dh["overall"].title())
    except Exception:
        _ml_col3.metric("Data Health", "N/A")

    # ── Install Guide ───────────────────────────────────────────────────
    st.markdown("---")
    _hdr("📥", "Setup Guide (All FREE)", "#06b6d4")
    st.code("""# ── Step 1: FREE AI Providers (recommended) ──────────────────
pip install ollama                   # Local AI (primary)
pip install huggingface-hub          # Cloud AI (free tier)
pip install gpt4all                  # Offline AI (no internet)

# Set up Ollama (best free option):
# 1. Download from: https://ollama.com/download
# 2. Run: ollama pull llama3
# 3. Optional: ollama pull mistral

# ── Step 2: ML & NLP (optional, enhances accuracy) ──────────
pip install prophet                  # Time-series forecasting
pip install scikit-learn             # ML scoring models
pip install spacy                    # NLP entity extraction
python -m spacy download en_core_web_sm

# ── Step 3: Paid Providers (OPTIONAL — only if you have keys) ─
pip install openai                   # Paid: OpenAI GPT-4o-mini
pip install anthropic                # Paid: Anthropic Claude
""", language="bash")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — SWITCH & TEST
# ══════════════════════════════════════════════════════════════════════════════

def _tab_switch():
    _hdr("🔄", "Manual Provider Override & Health Test", "#22c55e")
    st.caption("Test each provider individually or force the system to use a specific AI.")

    if not AFE_OK:
        st.error("ai_fallback_engine.py not found.")
        return

    statuses = afe.get_provider_status()

    col_sw, col_test = st.columns(2)

    with col_sw:
        _hdr("🎛️", "Force Active Provider", "#f59e0b")
        options  = [p["id"] for p in statuses]
        labels   = {p["id"]: f'{p["icon"]} {p["name"]}' for p in statuses}
        active   = afe.get_active_provider()["id"]
        sel      = st.selectbox("Override to:", options, index=options.index(active),
                                format_func=lambda x: labels[x], key="force_sel")
        if st.button("⚡ Force Switch", key="force_btn"):
            afe.force_provider(sel)
            st.success(f"✅ Switched to {labels[sel]}")
            st.rerun()

        st.info("The background monitor will still try to restore OpenAI every 5 minutes "
                "if it was previously primary.")

    with col_test:
        _hdr("🩺", "Provider Health Ping", "#06b6d4")
        ping_sel = st.selectbox("Ping provider:", options,
                                format_func=lambda x: labels[x], key="ping_sel")
        if st.button("🔔 Send Test Ping", key="ping_btn"):
            with st.spinner("Pinging…"):
                answer, err = afe._run_provider(
                    ping_sel,
                    "Respond with exactly: PONG — I am [your model name]",
                    "Health check — no dashboard data needed.",
                )
            if err:
                st.error(f"❌ {labels[ping_sel]} failed: {err}")
            else:
                st.success(f"✅ {labels[ping_sel]} responded:")
                st.markdown(f"> {answer}")

    st.markdown("---")
    _hdr("⏱️", "Monitor Status", "#8b5cf6")
    monitor_info = [
        ("Monitoring Interval", "Every 5 minutes"),
        ("Primary Provider",    "OpenAI GPT-4o-mini"),
        ("Monitor Action",      "If fallback is active → test primary → restore silently"),
        ("Current Active",      afe.get_active_provider()["name"]),
    ]
    for label, val in monitor_info:
        st.markdown(
            f'<div style="padding:3px 0;font-size:0.85rem">'
            f'<b style="color:#94a3b8">{label}:</b> '
            f'<span style="color:#f8fafc">{val}</span></div>',
            unsafe_allow_html=True,
        )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — EVENT LOG
# ══════════════════════════════════════════════════════════════════════════════

def _tab_log():
    _hdr("📜", "AI Fallback Event Log", "#f59e0b")
    st.caption("Real-time log of provider switches, failures, and restorations.")

    if not AFE_OK:
        st.error("ai_fallback_engine.py not found.")
        return

    logs = afe.get_logs(200)

    if not logs:
        st.info("No events logged yet. Start chatting to generate activity.")
        return

    # Filter
    fc1, fc2 = st.columns(2)
    all_events  = ["All"] + sorted(set(l.get("event","") for l in logs))
    all_prov    = ["All"] + sorted(set(l.get("provider","") for l in logs))
    sel_ev      = fc1.selectbox("Event Type", all_events,  key="log_ev")
    sel_prov    = fc2.selectbox("Provider",   all_prov,    key="log_prov")

    filtered = [l for l in logs if
        (sel_ev   == "All" or l.get("event")    == sel_ev) and
        (sel_prov == "All" or l.get("provider") == sel_prov)]

    for log in filtered:
        ev    = log.get("event", "")
        color = EVENT_COLORS.get(ev, "#475569")
        prov  = log.get("provider", "—")
        st.markdown(
            f'<div style="border-left:3px solid {color};padding:5px 10px;'
            f'margin-bottom:4px;background:#0f172a;border-radius:0 6px 6px 0">'
            f'<div style="display:flex;justify-content:space-between">'
            f'<span style="color:{color};font-weight:700;font-size:0.8rem">[{ev.upper()}]</span>'
            f'<span style="color:#64748b;font-size:0.75rem">{log.get("ts","")}</span></div>'
            f'<div style="color:#f8fafc;font-size:0.83rem">{log.get("message","")}</div>'
            f'<div style="color:#475569;font-size:0.74rem">Provider: {prov}</div></div>',
            unsafe_allow_html=True,
        )

    st.caption(f"Showing {len(filtered)} of {len(logs)} events | Max 1,000 stored")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — ABOUT
# ══════════════════════════════════════════════════════════════════════════════

def _tab_about():
    _hdr("ℹ️", "How the AI Fallback System Works", "#06b6d4")

    st.markdown("""
### Auto-Fallback Priority Chain

| Priority | Provider | Type | Cost |
|----------|----------|------|------|
| 1 | 🤖 OpenAI GPT-4o-mini | Paid Primary | ~₹ 0.15/1M tokens |
| 2 | 🦙 Ollama Llama3 | Free · Local | Free (GPU/CPU) |
| 3 | 🤗 HuggingFace Zephyr-7B | Free · Cloud | Free tier |
| 4 | 💻 GPT4All Phi-3 Mini | Free · Offline | Free (download ~2 GB) |
| 5 | 🔮 Anthropic Claude Haiku | Paid Fallback | ~₹ 0.25/1M tokens |

### How It Works
1. **Every query** → tries Provider 1 (OpenAI) first
2. If OpenAI **fails** (rate limit / downtime / no key) → tries Provider 2
3. Falls through chain until **one succeeds**
4. **Background thread** (every 5 minutes) tests if OpenAI has recovered → restores silently
5. Every response starts with **"Who is this?"** banner identifying the active AI

### Response Format

```
Who is this? I am [Provider Name] Dashboard AI — [Type].
⚠️ Paid OpenAI API is unavailable (reason). Auto-switched to [Provider].

---
[Dashboard answer here]
---
Active AI: [Name] | [Type] | DD-MM-YYYY HH:MM IST
```

### Setting Up Each Provider

**OpenAI (Primary):**
```bash
pip install openai
# Get key at: https://platform.openai.com/api-keys
```

**Ollama + Llama3 (Free Local):**
```bash
pip install ollama
# 1. Download Ollama from https://ollama.com/download
# 2. Install and run the Ollama app
# 3. ollama pull llama3
```

**HuggingFace (Free Cloud):**
```bash
pip install huggingface-hub
# Works without a token (rate-limited)
# Optional: get free token at https://huggingface.co/settings/tokens
```

**GPT4All (Fully Offline):**
```bash
pip install gpt4all
# First run downloads Phi-3-mini model (~2 GB) automatically
```

**Claude (Final Fallback):**
```bash
pip install anthropic
# Get key at: https://console.anthropic.com
```

### Example Fallback Response
> 🤗 **Who is this?** I am **HuggingFace Zephyr-7B Dashboard AI** — Free · Cloud API.
> ⚠️ Paid OpenAI API is **unavailable** (rate limit exceeded). Auto-switched to **HuggingFace**.
> Will restore silently when OpenAI recovers.
>
> ---
>
> **Today's Bitumen Prices** (as of 01-03-2026):
> IOCL VG-30 ex-Koyali: ₹48,302/MT (Basic) | ₹56,996/MT (Total incl. GST)...
""")

# ══════════════════════════════════════════════════════════════════════════════
# MAIN RENDER
# ══════════════════════════════════════════════════════════════════════════════

def render():
    st.markdown("""
<div style="background:linear-gradient(135deg,#1e293b 0%,#0f172a 100%);
padding:20px 24px;border-radius:12px;margin-bottom:20px;
border-left:5px solid #10b981;">
<div style="font-size:1.5rem;font-weight:900;color:#f8fafc;">
🔄 AI Fallback Engine — Dashboard Q&A
</div>
<div style="color:#94a3b8;font-size:0.9rem;margin-top:4px">
FREE-FIRST chain: Ollama Llama3 → HuggingFace → GPT4All → OpenAI → Claude.
Zero-cost by default. Paid providers only used when API keys configured. Auto-restores primary every 5 min.
</div>
</div>
""", unsafe_allow_html=True)

    if not AFE_OK:
        st.error(
            "⚠️ **ai_fallback_engine.py** not found in dashboard folder. "
            "Please ensure the file exists alongside dashboard.py."
        )
        return

    # Start background monitor on first render
    afe.start_monitor()

    tabs = st.tabs([
        "💬 Chat",
        "🔌 Provider Hub",
        "🔄 Switch & Test",
        "📜 Event Log",
        "ℹ️ About",
    ])

    with tabs[0]: _tab_chat()
    with tabs[1]: _tab_providers()
    with tabs[2]: _tab_switch()
    with tabs[3]: _tab_log()
    with tabs[4]: _tab_about()

    st.markdown(
        '<div style="color:#475569;font-size:0.76rem;text-align:center;margin-top:16px">'
        'AI Fallback Engine v2.0 (FREE-FIRST) | PPS Anantam Logistics | '
        'Chain: Ollama → HuggingFace → GPT4All → OpenAI → Claude | '
        'Monitor: every 5 min</div>',
        unsafe_allow_html=True,
    )
