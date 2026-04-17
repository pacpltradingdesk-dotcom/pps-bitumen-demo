"""
PPS Anantam — Telegram Channel Analyzer v1.0
===============================================
Standalone page: Connects to user's Telegram account,
reads channels (Persian, Russian, Uzbek, Hindi, English),
auto-translates to English, filters price/bitumen intel,
pushes alerts to dashboard.

Setup needed: API ID + Hash from https://my.telegram.org
"""
import streamlit as st
import json
import re
import asyncio
from pathlib import Path
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))
ROOT = Path(__file__).parent.parent.parent

_CONFIG_FILE = ROOT / "telegram_account_config.json"
# Durable backup location OUTSIDE the repo tree — survives:
#   - git-tracked file resets
#   - VPS snapshot rollbacks that rebuild /opt/pps-bitumen from scratch
#   - redeploys via deploy/hostinger_setup.sh
# Only wiped if the whole VPS is reimaged.
_DURABLE_DIR = Path.home() / ".pps"
_DURABLE_CONFIG_FILE = _DURABLE_DIR / "telegram_account_config.json"
_PRICE_INTEL_FILE = ROOT / "telegram_price_intel.json"
_CHANNEL_DATA_FILE = ROOT / "telegram_channel_messages.json"
_ALERTS_FILE = ROOT / "sre_alerts.json"


def _load_config():
    """Load Telegram config — cloud-resilient via cloud_secrets helper:
       1. st.secrets["telegram"]   (Streamlit Cloud — permanent)
       2. env vars TELEGRAM_*      (self-hosted)
       3. st.session_state         (current session)
       4. Local JSON file          (dev / persistent disk)
    """
    default = {"api_id": "", "api_hash": "", "phone": "", "channels": [],
               "enabled": False, "_source": "default"}

    # 1+2+3 via shared helper
    try:
        from cloud_secrets import get_secret_block, _from_secrets, _from_session
        block = get_secret_block("telegram", env_keys={
            "api_id":   "TELEGRAM_API_ID",
            "api_hash": "TELEGRAM_API_HASH",
            "phone":    "TELEGRAM_PHONE",
        })
        if block.get("api_id"):
            block.setdefault("channels", [])
            block.setdefault("enabled", True)
            if _from_secrets("telegram"):
                block["_source"] = "st.secrets"
            elif _from_session("telegram"):
                block["_source"] = "session"
            else:
                block["_source"] = "env"
            return block
    except Exception:
        pass

    # 4. Local file (works fine on persistent dev disk; ephemeral on cloud)
    try:
        if _CONFIG_FILE.exists():
            with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                cfg["_source"] = "file"
                return cfg
    except Exception:
        pass

    # 5. Durable backup outside repo tree (survives snapshot rollbacks).
    try:
        if _DURABLE_CONFIG_FILE.exists():
            with open(_DURABLE_CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                cfg["_source"] = "durable_backup"
                return cfg
    except Exception:
        pass

    return default


def _save_config(cfg):
    """Persist creds to every durable store we control so the user never has
    to re-enter them: (a) local file in repo, (b) durable backup outside the
    repo, (c) session memory for the current run.
    """
    to_write = {k: v for k, v in cfg.items() if not k.startswith("_")}
    try:
        with open(_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(to_write, f, indent=2)
    except Exception:
        pass
    try:
        _DURABLE_DIR.mkdir(parents=True, exist_ok=True)
        with open(_DURABLE_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(to_write, f, indent=2)
        # chmod 600 so only the service user can read creds
        try:
            import os
            os.chmod(_DURABLE_CONFIG_FILE, 0o600)
        except Exception:
            pass
    except Exception:
        pass
    try:
        from cloud_secrets import remember_in_session
        remember_in_session("telegram", to_write)
    except Exception:
        pass


def render():
    # Phase 2: standardized refresh bar (clears caches + reruns)
    try:
        from components.refresh_bar import render_refresh_bar
        render_refresh_bar('telegram_analyzer')
    except Exception:
        pass
    # Phase 4: active customer banner — shows persistent customer context
    try:
        from navigation_engine import render_active_context_strip
        render_active_context_strip()
    except Exception:
        pass
    st.markdown("""
<div style="background:linear-gradient(135deg,#0f172a,#1e3a5f);border-radius:12px;
            padding:16px 20px;margin-bottom:16px;">
  <div style="font-size:1.1rem;font-weight:800;color:#ffffff;">
    📡 Telegram Channel Analyzer
  </div>
  <div style="font-size:0.75rem;color:#94a3b8;margin-top:4px;">
    Auto-reads your joined channels • Translates all languages to English • Filters price/bitumen intel • Generates alerts
  </div>
</div>""", unsafe_allow_html=True)

    config = _load_config()

    tabs = st.tabs(["💰 Price Intel", "🔗 Connect Account", "📋 Channel Manager", "📤 Auto-Send", "⚙️ Settings"])

    # ══════════════════════════════════════════════════════════════════
    # TAB 1 — Price Intelligence (main view)
    # ══════════════════════════════════════════════════════════════════
    with tabs[0]:
        # Check if connected
        if not config.get("api_id") or not config.get("api_hash"):
            st.warning("⚠️ Telegram account not connected. Go to **Connect Account** tab first.")
            st.markdown("""
### How it works:
1. **Connect Account** — Enter API ID + Hash from [my.telegram.org](https://my.telegram.org)
2. **Select Channels** — Choose which channels to monitor
3. **Auto-Analyze** — System reads messages, translates all languages to English, finds price info
4. **Get Alerts** — Price changes pushed to your dashboard alerts

### Supported Channels:
- 🇮🇷 Persian/Farsi bitumen channels
- 🇷🇺 Russian bitumen/oil channels
- 🇺🇿 Uzbek petroleum channels
- 🇮🇳 Hindi/English bitumen groups
- 🌐 Any language — auto-detected & translated
""")
        else:
            # Connected — show fetch & analyze
            # ── OTP Verification Flow ──
            if st.session_state.get("_tca_otp_needed"):
                st.warning("🔐 Telegram session expired. Enter the OTP sent to your Telegram app.")
                otp_col1, otp_col2 = st.columns([2, 1])
                with otp_col1:
                    otp_code = st.text_input("Enter OTP Code", key="_tca_otp_input", placeholder="12345")
                with otp_col2:
                    st.caption("")
                    if st.button("✅ Verify OTP", type="primary", key="_tca_verify_otp"):
                        if otp_code:
                            with st.spinner("Verifying..."):
                                try:
                                    from telegram_channel_analyzer import verify_otp, TelegramPasswordRequired
                                    loop = asyncio.new_event_loop()
                                    phone_hash = st.session_state.get("_tca_phone_hash", "")
                                    success = loop.run_until_complete(verify_otp(config, otp_code.strip(), phone_hash))
                                    loop.close()
                                    if success:
                                        st.session_state["_tca_otp_needed"] = False
                                        st.session_state.pop("_tca_phone_hash", None)
                                        st.success("✅ Telegram authorized! Click Fetch & Analyze now.")
                                        st.rerun()
                                    else:
                                        st.error("❌ Verification failed. Try again.")
                                except TelegramPasswordRequired:
                                    st.session_state["_tca_otp_needed"] = False
                                    st.session_state["_tca_2fa_needed"] = True
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ OTP Error: {e}")
                        else:
                            st.warning("Enter the code first.")
                st.markdown("---")

            # ── 2FA Password Flow ──
            elif st.session_state.get("_tca_2fa_needed"):
                st.warning("🔒 Two-Factor Authentication enabled. Enter your Telegram 2FA password.")
                pw_col1, pw_col2 = st.columns([2, 1])
                with pw_col1:
                    password = st.text_input("2FA Password", key="_tca_2fa_input", type="password")
                with pw_col2:
                    st.caption("")
                    if st.button("✅ Verify Password", type="primary", key="_tca_verify_2fa"):
                        if password:
                            with st.spinner("Verifying..."):
                                try:
                                    from telegram_channel_analyzer import verify_2fa
                                    loop = asyncio.new_event_loop()
                                    success = loop.run_until_complete(verify_2fa(config, password))
                                    loop.close()
                                    if success:
                                        st.session_state["_tca_2fa_needed"] = False
                                        st.success("✅ Telegram authorized! Click Fetch & Analyze now.")
                                        st.rerun()
                                    else:
                                        st.error("❌ Wrong password.")
                                except Exception as e:
                                    st.error(f"❌ 2FA Error: {e}")
                st.markdown("---")

            # ── Main Fetch & Analyze ──
            c1, c2, c3 = st.columns([2, 1, 1])
            with c1:
                if st.button("🔄 Fetch & Analyze Channels", type="primary", use_container_width=True, key="_tca_fetch"):
                    with st.spinner("Connecting to Telegram & fetching messages..."):
                        try:
                            from telegram_channel_analyzer import (
                                fetch_channel_messages, analyze_messages, save_analysis, TelegramOTPRequired
                            )
                            loop = asyncio.new_event_loop()
                            messages = loop.run_until_complete(fetch_channel_messages(config, limit_per_channel=30))
                            loop.close()
                            if messages:
                                with st.spinner(f"Analyzing {len(messages)} messages, translating..."):
                                    result = analyze_messages(messages)
                                    alerts_count = save_analysis(result)
                                st.success(f"✅ Done! {result['summary']['price_related']} price msgs, {alerts_count} alerts!")
                                st.rerun()
                            else:
                                st.warning("No messages found. Check channel list.")
                        except TelegramOTPRequired:
                            # Session not authorized — trigger OTP flow
                            try:
                                from telegram_channel_analyzer import send_otp
                                loop2 = asyncio.new_event_loop()
                                phone_hash = loop2.run_until_complete(send_otp(config))
                                loop2.close()
                                if phone_hash == "already_authorized":
                                    st.info("Session is valid. Try again.")
                                    st.rerun()
                                else:
                                    st.session_state["_tca_otp_needed"] = True
                                    st.session_state["_tca_phone_hash"] = phone_hash
                                    st.rerun()
                            except Exception as otp_err:
                                st.error(f"Failed to send OTP: {otp_err}")
                        except Exception as e:
                            st.error(f"Failed: {e}")
            with c2:
                try:
                    intel = json.load(open(_PRICE_INTEL_FILE, "r", encoding="utf-8")) if _PRICE_INTEL_FILE.exists() else {}
                    st.caption(f"Last: {intel.get('summary', {}).get('analyzed_at', 'Never')}")
                except Exception:
                    st.caption("Last: Never")
            with c3:
                if st.button("🗑️ Clear", key="_tca_clear"):
                    for f in [_PRICE_INTEL_FILE, _CHANNEL_DATA_FILE]:
                        if f.exists(): f.unlink()
                    st.rerun()

            st.markdown("---")

            # Load saved intel
            price_intel = {}
            try:
                if _PRICE_INTEL_FILE.exists():
                    with open(_PRICE_INTEL_FILE, "r", encoding="utf-8") as f:
                        price_intel = json.load(f)
            except Exception:
                pass

            summary = price_intel.get("summary", {})
            price_msgs = price_intel.get("price_messages", [])

            # Auto-generate conclusion if missing (for old cached data)
            if price_msgs and not summary.get("conclusion"):
                try:
                    from telegram_channel_analyzer import _generate_conclusion
                    summary["conclusion"] = _generate_conclusion(price_msgs, price_msgs, summary)
                except Exception:
                    pass

            if not price_msgs:
                st.info("No data yet. Click **Fetch & Analyze** to start.")
            else:
                # KPI Row
                k1, k2, k3, k4 = st.columns(4)
                k1.metric("📨 Total Messages", summary.get("total_messages", 0))
                k2.metric("💰 Price Related", summary.get("price_related", 0))
                k3.metric("📡 Channels", summary.get("channels_analyzed", 0))
                k4.metric("🔢 Prices Found", summary.get("unique_prices_found", 0))

                # ═══════════════════════════════════════════════════
                # CONCLUSION BOX — AI Summary of all chats
                # ═══════════════════════════════════════════════════
                conclusion = summary.get("conclusion", {})
                if conclusion:
                    headline = conclusion.get("headline", "")
                    mood = conclusion.get("market_mood", "neutral")
                    mood_cfg = {
                        "bullish": ("#059669", "📈"),
                        "bearish": ("#dc2626", "📉"),
                        "neutral": ("#2563eb", "📊"),
                    }
                    mc, memoji = mood_cfg.get(mood, mood_cfg["neutral"])

                    # Build entire conclusion as ONE html block
                    box = f"""<div style="background:linear-gradient(135deg,#0f172a 0%,#1e3a5f 100%);border-radius:14px;
                                padding:20px 24px;margin:16px 0;">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">
    <span style="font-size:1.4rem;">🧠</span>
    <span style="font-size:1.05rem;font-weight:800;color:#ffffff;">Intel Conclusion</span>
    <span style="background:{mc};color:white;font-size:0.65rem;font-weight:700;
          padding:3px 10px;border-radius:12px;margin-left:auto;">{memoji} {mood.upper()}</span>
  </div>
  <div style="font-size:0.92rem;color:#e2e8f0;font-weight:600;line-height:1.6;
              border-left:3px solid #3b82f6;padding-left:14px;margin-bottom:14px;">
    {headline}
  </div>"""

                    # Key Prices badges
                    key_prices = conclusion.get("key_prices", [])
                    fx_update = conclusion.get("fx_update", "")
                    grades = conclusion.get("bitumen_grades", [])

                    badges = ""
                    for p in key_prices:
                        badges += f'<span style="background:#fbbf24;color:#78350f;font-size:0.72rem;font-weight:700;padding:3px 10px;border-radius:10px;">💰 {p}</span> '
                    if fx_update:
                        badges += f'<span style="background:#818cf8;color:white;font-size:0.72rem;font-weight:700;padding:3px 10px;border-radius:10px;">💱 {fx_update}</span> '
                    for g in grades:
                        badges += f'<span style="background:#34d399;color:#064e3b;font-size:0.72rem;font-weight:700;padding:3px 10px;border-radius:10px;">🛢️ {g}</span> '
                    if badges:
                        box += f'<div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:14px;">{badges}</div>'

                    # Product & Supply side by side
                    products = conclusion.get("product_mentions", {})
                    supply_signals = conclusion.get("supply_signals", [])

                    if products or supply_signals:
                        box += '<div style="display:flex;gap:16px;flex-wrap:wrap;margin-bottom:14px;">'
                        if products:
                            box += '<div style="flex:1;min-width:180px;background:rgba(255,255,255,0.08);border-radius:10px;padding:12px 14px;">'
                            box += '<div style="font-size:0.7rem;color:#94a3b8;font-weight:700;margin-bottom:8px;">📦 PRODUCT MENTIONS</div>'
                            sorted_prods = sorted(products.items(), key=lambda x: x[1], reverse=True)
                            max_count = max(p[1] for p in sorted_prods)
                            for cat, count in sorted_prods:
                                bar_w = min(int((count / max_count) * 100), 100)
                                box += f'''<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
                                  <span style="font-size:0.75rem;color:#e2e8f0;min-width:100px;">{cat}</span>
                                  <div style="flex:1;background:rgba(255,255,255,0.1);border-radius:4px;height:14px;overflow:hidden;">
                                    <div style="width:{bar_w}%;background:linear-gradient(90deg,#3b82f6,#60a5fa);height:100%;border-radius:4px;"></div>
                                  </div>
                                  <span style="font-size:0.72rem;color:#cbd5e1;min-width:20px;text-align:right;">{count}</span>
                                </div>'''
                            box += '</div>'
                        if supply_signals:
                            box += '<div style="flex:1;min-width:180px;background:rgba(255,255,255,0.08);border-radius:10px;padding:12px 14px;">'
                            box += '<div style="font-size:0.7rem;color:#94a3b8;font-weight:700;margin-bottom:8px;">📡 SUPPLY SIGNALS</div>'
                            icons = {"export": "🌍", "domestic": "🏠", "tender": "📋", "delivery": "🚢"}
                            for sig in supply_signals:
                                ic = icons.get(sig["type"], "📌")
                                box += f'<div style="font-size:0.78rem;color:#e2e8f0;margin-bottom:5px;">{ic} {sig["type"].title()}: <strong style="color:#fbbf24;">{sig["mentions"]}</strong> mentions</div>'
                            box += '</div>'
                        box += '</div>'

                    # Channel breakdown
                    ch_insights = conclusion.get("channel_insights", [])
                    if ch_insights:
                        box += '<div style="background:rgba(255,255,255,0.06);border-radius:10px;padding:12px 14px;margin-bottom:14px;">'
                        box += '<div style="font-size:0.7rem;color:#94a3b8;font-weight:700;margin-bottom:8px;">📺 CHANNEL BREAKDOWN</div>'
                        for ch in ch_insights:
                            box += f'''<div style="display:flex;justify-content:space-between;align-items:center;
                                padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.08);">
                              <span style="font-size:0.78rem;color:#e2e8f0;font-weight:600;">📡 {ch["channel"]}</span>
                              <div style="display:flex;gap:12px;">
                                <span style="font-size:0.72rem;color:#cbd5e1;">{ch["messages"]} msgs</span>
                                <span style="font-size:0.72rem;color:#fbbf24;font-weight:600;">{ch["price_msgs"]} price</span>
                                <span style="font-size:0.72rem;color:#93c5fd;">{ch["focus"]}</span>
                              </div>
                            </div>'''
                        box += '</div>'

                    # Action items
                    actions = conclusion.get("action_items", [])
                    if actions:
                        box += '<div style="background:rgba(251,191,36,0.12);border-left:3px solid #fbbf24;border-radius:8px;padding:10px 14px;">'
                        box += '<div style="font-size:0.7rem;color:#fbbf24;font-weight:700;margin-bottom:6px;">⚡ ACTION ITEMS</div>'
                        for a in actions:
                            box += f'<div style="font-size:0.8rem;color:#fef3c7;margin-bottom:3px;">→ {a}</div>'
                        box += '</div>'

                    box += '</div>'
                    st.markdown(box, unsafe_allow_html=True)

                    # ── Share Conclusion via WhatsApp ──
                    def _build_wa_text(conc, summ):
                        lines = ["🧠 *PPS ANANTAM — Telegram Intel Summary*"]
                        lines.append(f"📅 {summ.get('analyzed_at', '')}")
                        lines.append("━━━━━━━━━━━━━━")
                        hl = conc.get("headline", "")
                        if hl:
                            lines.append(f"📌 {hl}")
                        mood = conc.get("market_mood", "neutral").upper()
                        lines.append(f"📊 Market Mood: *{mood}*")
                        lines.append("")
                        kp = conc.get("key_prices", [])
                        if kp:
                            lines.append("💰 *Key Prices:*")
                            for p in kp:
                                lines.append(f"  • {p}")
                        fx = conc.get("fx_update", "")
                        if fx:
                            lines.append(f"💱 {fx}")
                        gr = conc.get("bitumen_grades", [])
                        if gr:
                            lines.append(f"🛢️ Grades: {', '.join(gr)}")
                        lines.append("")
                        prods = conc.get("product_mentions", {})
                        if prods:
                            lines.append("📦 *Product Mentions:*")
                            for cat, cnt in sorted(prods.items(), key=lambda x: x[1], reverse=True):
                                lines.append(f"  • {cat}: {cnt}")
                        sigs = conc.get("supply_signals", [])
                        if sigs:
                            lines.append("📡 *Supply Signals:*")
                            for s in sigs:
                                lines.append(f"  • {s['type'].title()}: {s['mentions']} mentions")
                        lines.append("")
                        acts = conc.get("action_items", [])
                        if acts:
                            lines.append("⚡ *Action Items:*")
                            for a in acts:
                                lines.append(f"  → {a}")
                        lines.append("━━━━━━━━━━━━━━")
                        lines.append(f"📨 {summ.get('total_messages',0)} msgs | 💰 {summ.get('price_related',0)} price | 📡 {summ.get('channels_analyzed',0)} channels")
                        lines.append("_Generated by PPS Bitumen Dashboard_")
                        return "\n".join(lines)

                    wa_text = _build_wa_text(conclusion, summary)

                    with st.expander("📤 Share Intel via WhatsApp", expanded=False):
                        sh1, sh2 = st.columns([2, 1])
                        with sh1:
                            wa_phone = st.text_input(
                                "Phone (with 91)", placeholder="919876543210",
                                key="_tca_wa_phone"
                            )
                        with sh2:
                            st.caption("")
                            encoded = wa_text.replace("\n", "%0a").replace(" ", "%20").replace("*", "%2A").replace("#", "%23")
                            if wa_phone:
                                phone_clean = re.sub(r'[^0-9]', '', wa_phone)
                                wa_link = f"https://wa.me/{phone_clean}?text={encoded}"
                            else:
                                wa_link = f"https://wa.me/?text={encoded}"
                            st.markdown(
                                f'<a href="{wa_link}" target="_blank" style="display:inline-block;background:#25D366;'
                                f'color:white;font-weight:700;font-size:0.85rem;padding:8px 20px;border-radius:8px;'
                                f'text-decoration:none;text-align:center;margin-top:4px;">📱 Send via WhatsApp</a>',
                                unsafe_allow_html=True
                            )
                        st.code(wa_text, language=None)

                st.markdown("---")
                st.markdown("### 💰 Price Intelligence Feed")
                st.caption("Auto-translated to English • Prices highlighted • Most recent first")

                for i, msg in enumerate(price_msgs[:20]):
                    original = msg.get("text_original", "")
                    english = msg.get("text_english", original)
                    channel = msg.get("channel", "")
                    date = msg.get("date", "")
                    prices = msg.get("prices_found", [])
                    sender = msg.get("sender", "")

                    # Highlight prices in English text
                    highlighted = english
                    for p in prices:
                        highlighted = highlighted.replace(
                            p,
                            f'<span style="background:#fef3c7;color:#92400e;font-weight:800;'
                            f'padding:1px 6px;border-radius:4px;font-size:0.9rem;">{p}</span>'
                        )

                    # Detect language
                    ascii_ratio = sum(1 for c in original if ord(c) < 128) / max(len(original), 1)
                    is_translated = ascii_ratio < 0.7
                    lang_badge = ""
                    if is_translated:
                        lang_badge = ('<span style="background:#7c3aed;color:white;font-size:0.6rem;'
                                     'padding:2px 6px;border-radius:10px;margin-left:6px;">TRANSLATED</span>')

                    # Card colors (alternate)
                    colors = [
                        ("#eff6ff", "#1e40af", "#2563eb"),
                        ("#fef3c7", "#92400e", "#f59e0b"),
                        ("#f0fdf4", "#065f46", "#059669"),
                        ("#fdf2f8", "#9d174d", "#ec4899"),
                    ]
                    bg, txt, border = colors[i % len(colors)]

                    st.markdown(f"""
<div style="background:{bg};border-left:4px solid {border};border-radius:10px;
            padding:14px 16px;margin-bottom:10px;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
    <span style="font-size:0.7rem;font-weight:700;color:{border};">
      📡 {channel}{lang_badge}
    </span>
    <span style="font-size:0.65rem;color:#64748b;">🕐 {date}</span>
  </div>
  <div style="font-size:0.88rem;color:#0f172a;line-height:1.5;font-weight:500;word-wrap:break-word;">
    {highlighted}
  </div>
""", unsafe_allow_html=True)

                    # Show original if translated
                    if is_translated:
                        st.markdown(f"""
  <div style="font-size:0.72rem;color:#64748b;margin-top:6px;padding-top:6px;
              border-top:1px dashed {border}40;font-style:italic;">
    📝 Original: {original[:150]}{'...' if len(original) > 150 else ''}
  </div>
""", unsafe_allow_html=True)

                    if prices:
                        st.markdown(f"""
  <div style="margin-top:6px;display:flex;gap:6px;flex-wrap:wrap;">
    {''.join(f'<span style="background:{border};color:white;font-size:0.7rem;font-weight:700;padding:2px 8px;border-radius:12px;">{p}</span>' for p in prices[:5])}
  </div>
""", unsafe_allow_html=True)

                    st.markdown("</div>", unsafe_allow_html=True)

                # Prices Summary
                all_prices = summary.get("top_prices", [])
                if all_prices:
                    st.markdown("### 🏷️ All Prices Detected")
                    cols = st.columns(4)
                    for i, p in enumerate(all_prices[:20]):
                        with cols[i % 4]:
                            st.markdown(f"""
<div style="background:#0f172a;color:#fcd34d;border-radius:8px;padding:6px 10px;
            text-align:center;margin-bottom:6px;font-weight:700;font-size:0.85rem;">
  {p}
</div>""", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════
    # TAB 2 — Connect Account
    # ══════════════════════════════════════════════════════════════════
    with tabs[1]:
        st.subheader("🔗 Connect Your Telegram Account")

        # Show source so user knows where creds came from
        _src = config.get("_source", "default")
        if _src == "st.secrets":
            st.success("✅ Credentials loaded from Streamlit Cloud secrets — survives every restart.")
        elif _src == "session" and config.get("api_id"):
            st.info("ℹ️ Credentials in session memory only. Will reset on next cold start.")
        elif _src == "file" and config.get("api_id"):
            st.info("ℹ️ Credentials loaded from local file. **On Streamlit Cloud, file resets on every push** — paste them into Cloud secrets too (see below).")

        # Cloud persistence note (uniform helper)
        try:
            from cloud_secrets import render_cloud_secrets_hint
            render_cloud_secrets_hint("telegram", ["api_id", "api_hash", "phone"])
        except Exception:
            pass

        st.markdown("""
### Step 1: Get API Credentials
1. Go to [my.telegram.org](https://my.telegram.org)
2. Login with your phone number
3. Click **API Development Tools**
4. Create an app — get **API ID** and **API Hash**
""")

        with st.form("tg_connect_form"):
            api_id = st.text_input("API ID", value=config.get("api_id", ""), placeholder="12345678")
            api_hash = st.text_input("API Hash", value=config.get("api_hash", ""), placeholder="abcdef1234567890abcdef", type="password")
            phone = st.text_input("Phone Number (with country code)", value=config.get("phone", ""), placeholder="+919876543210")

            if st.form_submit_button("💾 Save & Connect", type="primary"):
                if api_id and api_hash and phone:
                    # Normalize phone: strip spaces/dashes, keep leading +
                    _phone_norm = "".join(ch for ch in phone if ch.isdigit() or ch == "+")
                    config["api_id"] = api_id.strip()
                    config["api_hash"] = api_hash.strip()
                    config["phone"] = _phone_norm
                    config["enabled"] = True
                    _save_config(config)
                    st.success("✅ Credentials saved! Reloading...")
                    st.rerun()
                else:
                    st.warning("Fill all fields")

        if config.get("api_id"):
            st.success(f"✅ Connected: {config.get('phone', '?')} | API ID: {config.get('api_id', '?')}")

    # ══════════════════════════════════════════════════════════════════
    # TAB 3 — Channel Manager
    # ══════════════════════════════════════════════════════════════════
    with tabs[2]:
        st.subheader("📋 Monitored Channels")
        st.caption("Add channel names to monitor. Leave empty to scan ALL joined channels.")

        channels = config.get("channels", [])

        if channels:
            for i, ch in enumerate(channels):
                c1, c2 = st.columns([4, 1])
                with c1:
                    st.markdown(f"**{i+1}.** 📡 {ch}")
                with c2:
                    if st.button("❌", key=f"_tca_rm_{i}"):
                        channels.pop(i)
                        config["channels"] = channels
                        _save_config(config)
                        st.rerun()
        else:
            st.info("No specific channels set — will scan ALL joined channels/groups.")

        st.markdown("---")
        with st.form("add_channel_form"):
            new_ch = st.text_input("Channel name (or part of name)", placeholder="e.g. bitumen, قیر, битум")
            if st.form_submit_button("➕ Add Channel", type="primary"):
                if new_ch:
                    channels.append(new_ch)
                    config["channels"] = channels
                    _save_config(config)
                    st.success(f"Added: {new_ch}")
                    st.rerun()

        st.markdown("---")
        st.markdown("""
**Suggested channels to add:**
- `قیر` — Persian bitumen channels
- `битум` — Russian bitumen channels
- `bitumen` — English channels
- `Bitumen Hub` — HEMT Bitumen Hub
- `NeftgazProm` — Uzbek petroleum
""")

    # ══════════════════════════════════════════════════════════════════
    # TAB 4 — Auto-Send (WhatsApp + Telegram)
    # ══════════════════════════════════════════════════════════════════
    with tabs[3]:
        _SEND_CONFIG_FILE = ROOT / "telegram_intel_send_config.json"

        # Load send config
        def _load_send_cfg():
            try:
                if _SEND_CONFIG_FILE.exists():
                    with open(_SEND_CONFIG_FILE, "r", encoding="utf-8") as f:
                        return json.load(f)
            except Exception:
                pass
            return {"whatsapp_numbers": [], "telegram_chats": []}

        def _save_send_cfg(cfg):
            with open(_SEND_CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)

        send_cfg = _load_send_cfg()

        st.subheader("📤 Auto-Send Intel Summary")
        st.caption("WhatsApp left, Telegram right — add recipients once, send intel with one click")

        # Load Telegram bot config up front (used in right column)
        _tg_settings_file = ROOT / "telegram_settings.json"
        _tg_settings = {}
        try:
            if _tg_settings_file.exists():
                _tg_settings = json.load(open(_tg_settings_file, "r", encoding="utf-8"))
        except Exception:
            pass

        wa_numbers = send_cfg.get("whatsapp_numbers", [])
        tg_chats = send_cfg.get("telegram_chats", [])

        # ════════════════════════════════════════════════════════════════
        # 2-COLUMN LAYOUT — WhatsApp (left) + Telegram (right)
        # ════════════════════════════════════════════════════════════════
        col_wa, col_tg = st.columns(2, gap="large")

        # ═══════════════════════ LEFT: WhatsApp ═════════════════════════
        with col_wa:
            st.markdown("""
<div style="background:#dcfce7;border-left:4px solid #16a34a;border-radius:10px;padding:14px 18px;margin:4px 0 14px 0;">
  <div style="font-size:1rem;font-weight:800;color:#15803d;">📱 WhatsApp</div>
  <div style="font-size:0.78rem;color:#64748b;margin-top:4px;">
    No setup needed — click Send → WhatsApp Web opens with message ready.
    Works from your personal WhatsApp. No API, no charges.
  </div>
</div>""", unsafe_allow_html=True)

            st.markdown("**Recipients**")
            if wa_numbers:
                for i, num in enumerate(wa_numbers):
                    wc1, wc2, wc3 = st.columns([3, 3, 1])
                    with wc1:
                        st.markdown(f"**{i+1}.** 📱 `{num.get('number', '')}`")
                    with wc2:
                        st.caption(num.get("label", ""))
                    with wc3:
                        if st.button("❌", key=f"_tca_rmwa_{i}"):
                            wa_numbers.pop(i)
                            send_cfg["whatsapp_numbers"] = wa_numbers
                            _save_send_cfg(send_cfg)
                            st.rerun()
            else:
                st.info("No WhatsApp numbers added yet.")

            with st.form("_tca_add_wa_form"):
                new_wa = st.text_input("Phone (with 91)", placeholder="919876543210")
                new_wa_label = st.text_input("Name / Label", placeholder="e.g. Rahul Sir")
                if st.form_submit_button("➕ Add WhatsApp Number", type="primary", use_container_width=True):
                    if new_wa:
                        cleaned = re.sub(r'[^0-9]', '', new_wa)
                        if len(cleaned) >= 10:
                            if not cleaned.startswith("91"):
                                cleaned = "91" + cleaned[-10:]
                            wa_numbers.append({"number": cleaned, "label": new_wa_label})
                            send_cfg["whatsapp_numbers"] = wa_numbers
                            _save_send_cfg(send_cfg)
                            st.success(f"✅ Added: {cleaned} ({new_wa_label})")
                            st.rerun()
                        else:
                            st.warning("Invalid number. Use 10-digit mobile or with 91 prefix.")
                    else:
                        st.warning("Enter a phone number.")

        # ═══════════════════════ RIGHT: Telegram ════════════════════════
        with col_tg:
            st.markdown("""
<div style="background:#dbeafe;border-left:4px solid #2563eb;border-radius:10px;padding:14px 18px;margin:4px 0 14px 0;">
  <div style="font-size:1rem;font-weight:800;color:#1d4ed8;">✈️ Telegram Bot</div>
  <div style="font-size:0.78rem;color:#64748b;margin-top:4px;">
    One-time setup. Bot auto-sends messages to your groups/channels.
  </div>
</div>""", unsafe_allow_html=True)

            if _tg_settings.get("bot_token"):
                st.success("✅ Bot configured")
                if st.button("🔍 Test Bot Connection", key="_tca_test_tg", use_container_width=True):
                    try:
                        from telegram_engine import verify_bot
                        result = verify_bot()
                        if result.get("ok"):
                            bot = result.get("bot", {})
                            st.success(f"✅ @{bot.get('username', '?')} — {bot.get('first_name', '')}")
                        else:
                            st.error(f"❌ {result.get('description', 'Failed')}")
                    except Exception as e:
                        st.error(f"❌ {e}")
            else:
                st.warning("⚠️ No bot token — auto-send disabled")

            with st.expander("🔑 Bot Token Setup", expanded=not _tg_settings.get("bot_token")):
                with st.form("_tca_tg_bot_setup"):
                    st.caption("Get token from [@BotFather](https://t.me/BotFather) on Telegram")
                    tg_bot_token = st.text_input("Bot Token", type="password",
                                                   placeholder="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")
                    if st.form_submit_button("💾 Save Bot Token", type="primary", use_container_width=True):
                        if tg_bot_token:
                            try:
                                from telegram_engine import configure_bot
                                result = configure_bot(tg_bot_token.strip())
                                if result.get("ok"):
                                    bot_info = result.get("bot", {})
                                    st.success(f"✅ @{bot_info.get('username', '?')}")
                                    st.rerun()
                                else:
                                    st.error(f"❌ {result.get('description', 'Invalid token')}")
                            except Exception as e:
                                st.error(f"Error: {e}")
                        else:
                            st.warning("Enter a bot token.")
                st.caption(
                    "**Setup (2 min):** Telegram → @BotFather → `/newbot` → name → copy token → "
                    "paste above → save → add bot to your group/channel as admin."
                )

            st.markdown("**Recipients**")
            if tg_chats:
                for i, ch in enumerate(tg_chats):
                    tc1, tc2, tc3 = st.columns([3, 3, 1])
                    with tc1:
                        st.markdown(f"**{i+1}.** ✈️ `{ch.get('chat_id', '')}`")
                    with tc2:
                        st.caption(ch.get("label", ""))
                    with tc3:
                        if st.button("❌", key=f"_tca_rmtg_{i}"):
                            tg_chats.pop(i)
                            send_cfg["telegram_chats"] = tg_chats
                            _save_send_cfg(send_cfg)
                            st.rerun()
            else:
                st.info("No Telegram chats added yet.")

            with st.form("_tca_add_tg_form"):
                new_tg = st.text_input("Chat ID", placeholder="e.g. -1001234567890 or @channelname")
                new_tg_label = st.text_input("Label", placeholder="e.g. PPS Team Group")
                if st.form_submit_button("➕ Add Telegram Chat", type="primary", use_container_width=True):
                    if new_tg:
                        tg_chats.append({"chat_id": new_tg.strip(), "label": new_tg_label})
                        send_cfg["telegram_chats"] = tg_chats
                        _save_send_cfg(send_cfg)
                        st.success(f"✅ Added: {new_tg.strip()} ({new_tg_label})")
                        st.rerun()
                    else:
                        st.warning("Enter a Chat ID.")

        st.markdown("---")

        # ── Build message & Send ──
        # Load current conclusion
        _intel = {}
        try:
            if _PRICE_INTEL_FILE.exists():
                with open(_PRICE_INTEL_FILE, "r", encoding="utf-8") as f:
                    _intel = json.load(f)
        except Exception:
            pass
        _summ = _intel.get("summary", {})
        _conc = _summ.get("conclusion", {})
        _msgs = _intel.get("price_messages", [])

        # Auto-generate if missing
        if _msgs and not _conc:
            try:
                from telegram_channel_analyzer import _generate_conclusion
                _conc = _generate_conclusion(_msgs, _msgs, _summ)
            except Exception:
                pass

        if not _conc:
            st.warning("⚠️ No intel data. Go to **Price Intel** tab and click **Fetch & Analyze** first.")
        else:
            # Build plain text message
            def _build_send_text(conc, summ):
                lines = ["🧠 *PPS ANANTAM — Telegram Intel*"]
                lines.append(f"📅 {summ.get('analyzed_at', '')}")
                lines.append("━━━━━━━━━━━━━━")
                hl = conc.get("headline", "")
                if hl:
                    lines.append(f"📌 {hl}")
                lines.append(f"📊 Mood: *{conc.get('market_mood','neutral').upper()}*")
                for p in conc.get("key_prices", []):
                    lines.append(f"💰 {p}")
                fx = conc.get("fx_update", "")
                if fx:
                    lines.append(f"💱 {fx}")
                gr = conc.get("bitumen_grades", [])
                if gr:
                    lines.append(f"🛢️ {', '.join(gr)}")
                lines.append("")
                for a in conc.get("action_items", []):
                    lines.append(f"⚡ {a}")
                lines.append("━━━━━━━━━━━━━━")
                lines.append(f"📨 {summ.get('total_messages',0)} msgs • 💰 {summ.get('price_related',0)} price • 📡 {summ.get('channels_analyzed',0)} ch")
                lines.append("_PPS Bitumen Dashboard_")
                return "\n".join(lines)

            send_text = _build_send_text(_conc, _summ)

            st.markdown("### 📝 Message Preview")
            try:
                from components.message_preview import render_msg_preview
                render_msg_preview(send_text, channel="telegram",
                                    sender="PPS Anantam Telegram Bot")
            except Exception:
                st.code(send_text, language=None)

            total_recipients = len(wa_numbers) + len(tg_chats)

            if total_recipients == 0:
                st.warning("Add at least one WhatsApp number or Telegram chat above.")
            else:
                st.markdown(f"""
<div style="background:#f0f9ff;border:2px solid #3b82f6;border-radius:10px;padding:14px 18px;margin:10px 0;">
  <span style="font-size:0.9rem;font-weight:700;color:#1e40af;">📤 Ready to send to {total_recipients} recipient(s)</span>
  <span style="font-size:0.78rem;color:#64748b;margin-left:8px;">
    📱 {len(wa_numbers)} WhatsApp &nbsp;•&nbsp; ✈️ {len(tg_chats)} Telegram
  </span>
</div>""", unsafe_allow_html=True)

                # ── WhatsApp: Generate wa.me links ──
                if wa_numbers:
                    st.markdown("#### 📱 WhatsApp — Click to Send")
                    encoded_msg = send_text.replace("\n", "%0a").replace(" ", "%20").replace("*", "%2A").replace("#", "%23")
                    wa_cols = st.columns(min(len(wa_numbers), 3))
                    for idx, num in enumerate(wa_numbers):
                        phone = num.get("number", "")
                        label = num.get("label", phone)
                        wa_link = f"https://wa.me/{phone}?text={encoded_msg}"
                        with wa_cols[idx % len(wa_cols)]:
                            st.markdown(f"""
<a href="{wa_link}" target="_blank" style="display:block;background:#25D366;color:white;
   font-weight:700;font-size:0.85rem;padding:12px 16px;border-radius:10px;
   text-decoration:none;text-align:center;margin-bottom:8px;">
  📱 {label}
</a>""", unsafe_allow_html=True)

                    st.caption("Click → WhatsApp Web opens → Hit Send. That's it!")

                # ── Telegram: Auto-send via Bot ──
                if tg_chats:
                    st.markdown("#### ✈️ Telegram — Auto Send")
                    if st.button("🚀 Send to Telegram", type="primary", use_container_width=True, key="_tca_send_tg"):
                        tg_results = []
                        progress = st.progress(0, text="Sending to Telegram...")

                        for idx, ch in enumerate(tg_chats):
                            chat_id = ch.get("chat_id", "")
                            label = ch.get("label", chat_id)
                            try:
                                from telegram_engine import send_message as tg_send
                                tg_text = send_text
                                tg_text = re.sub(r'\*([^*]+)\*', r'<b>\1</b>', tg_text)
                                tg_text = re.sub(r'_([^_]+)_', r'<i>\1</i>', tg_text)
                                resp = tg_send(chat_id, tg_text, parse_mode="HTML")
                                if resp.get("ok"):
                                    tg_results.append(("✅", label, "Sent"))
                                else:
                                    tg_results.append(("❌", label, resp.get("description", "Failed")))
                            except Exception as e:
                                tg_results.append(("❌", label, str(e)[:80]))
                            progress.progress((idx + 1) / len(tg_chats))

                        progress.empty()
                        for icon, target, status in tg_results:
                            if icon == "✅":
                                st.success(f"{icon} ✈️ {target} — {status}")
                            else:
                                st.error(f"{icon} ✈️ {target} — {status}")

    # ══════════════════════════════════════════════════════════════════
    # TAB 5 — Settings
    # ══════════════════════════════════════════════════════════════════
    with tabs[4]:
        st.subheader("⚙️ Analyzer Settings")

        auto_translate = st.toggle("Auto-translate to English", value=config.get("auto_translate", True), key="_tca_translate")
        auto_alerts = st.toggle("Push price alerts to dashboard", value=config.get("auto_alerts", True), key="_tca_alerts")
        msg_limit = st.slider("Messages per channel", min_value=10, max_value=100, value=config.get("msg_limit", 30), key="_tca_limit")

        if st.button("Save Settings", type="primary"):
            config["auto_translate"] = auto_translate
            config["auto_alerts"] = auto_alerts
            config["msg_limit"] = msg_limit
            _save_config(config)
            st.success("Settings saved!")
            st.rerun()

        st.markdown("---")
        st.markdown("**Data Files:**")
        for f, label in [(_CONFIG_FILE, "Config"), (_PRICE_INTEL_FILE, "Price Intel"),
                         (_CHANNEL_DATA_FILE, "Messages")]:
            exists = f.exists()
            size = f.stat().st_size if exists else 0
            st.caption(f"{'✅' if exists else '❌'} {label}: {size:,} bytes" if exists else f"❌ {label}: not created")
