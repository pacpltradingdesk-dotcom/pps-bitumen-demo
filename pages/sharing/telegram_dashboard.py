"""
PPS Anantam — Telegram Dashboard v5.0
========================================
Manage Telegram bot configuration, channels, send messages,
view logs, and adjust settings.
"""
import streamlit as st
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))
ROOT = Path(__file__).parent.parent.parent

# ── JSON file paths ──────────────────────────────────────────────────────────
_SETTINGS_FILE = ROOT / "telegram_settings.json"
_LOG_FILE = ROOT / "telegram_log.json"

# ── Engine imports (graceful fallback) ───────────────────────────────────────
try:
    from telegram_engine import (
        configure_bot,
        verify_bot,
        get_chat_list,
        add_chat,
        remove_chat,
        send_message,
        send_document,
        broadcast_message,
    )
    _TG_AVAILABLE = True
except ImportError:
    _TG_AVAILABLE = False

    def configure_bot(token):
        return {"ok": False, "description": "telegram_engine module not available."}

    def verify_bot():
        return {"ok": False, "description": "telegram_engine module not available."}

    def get_chat_list():
        return []

    def add_chat(chat_id, label="", chat_type="group"):
        pass

    def remove_chat(chat_id):
        pass

    def send_message(chat_id, text, parse_mode="HTML"):
        return {"ok": False, "description": "telegram_engine module not available."}

    def send_document(chat_id, file_bytes, filename, caption=""):
        return {"ok": False, "description": "telegram_engine module not available."}

    def broadcast_message(text, parse_mode="HTML"):
        return [{"ok": False, "description": "telegram_engine module not available."}]


# ═════════════════════════════════════════════════════════════════════════════
#  JSON helpers
# ═════════════════════════════════════════════════════════════════════════════

def _load_json(filepath, default=None):
    """Load a JSON file with safe fallback."""
    try:
        p = Path(filepath)
        if p.exists():
            raw = p.read_text(encoding="utf-8").strip()
            if raw:
                return json.loads(raw)
    except Exception:
        pass
    return default if default is not None else {}


def _save_json(filepath, data):
    """Write data to a JSON file."""
    try:
        Path(filepath).write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return True
    except Exception:
        return False


def _now_ist() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")


# ═════════════════════════════════════════════════════════════════════════════
#  RENDER
# ═════════════════════════════════════════════════════════════════════════════

def render():
    """Render the Telegram Dashboard page."""

    # ── Page header ──────────────────────────────────────────────────────
    st.markdown(
        '<div class="pps-page-header"><div class="pps-page-title">'
        '\u2708\ufe0f Telegram Dashboard</div></div>',
        unsafe_allow_html=True,
    )

    if not _TG_AVAILABLE:
        st.warning(
            "Telegram engine (`telegram_engine.py`) is not available. "
            "All operations will run in preview/fallback mode."
        )

    # ── Tabs ─────────────────────────────────────────────────────────────
    tab_analyzer, tab_setup, tab_chats, tab_send, tab_logs, tab_settings = st.tabs([
        "🔍 Chat Analyzer",
        "🔧 Setup",
        "💬 Channels",
        "📨 Send",
        "📋 Logs",
        "⚙️ Settings",
    ])

    # ══════════════════════════════════════════════════════════════════════
    #  TAB 0 — Price Chat Analyzer (price-only, auto-translate, alerts)
    # ══════════════════════════════════════════════════════════════════════
    with tab_analyzer:
        st.subheader("💰 Price Intelligence from Telegram")
        st.caption("Auto-detects price discussions from all languages, translates to English, generates alerts.")

        # Fetch messages
        _analysis_file = ROOT / "telegram_chat_analysis.json"

        col_fetch, col_status = st.columns([2, 1])
        with col_fetch:
            if st.button("📥 Fetch Latest Messages", type="primary", use_container_width=True, key="_tg_fetch"):
                if _TG_AVAILABLE:
                    try:
                        from telegram_engine import get_updates
                        updates = get_updates(offset=0)
                        if updates:
                            # Save raw messages
                            messages = []
                            for u in updates:
                                msg = u.get("message", u.get("channel_post", {}))
                                if msg and msg.get("text"):
                                    messages.append({
                                        "id": msg.get("message_id"),
                                        "chat": msg.get("chat", {}).get("title", msg.get("chat", {}).get("first_name", "Unknown")),
                                        "chat_id": msg.get("chat", {}).get("id"),
                                        "from": msg.get("from", {}).get("first_name", "Bot"),
                                        "text": msg.get("text", ""),
                                        "date": datetime.fromtimestamp(msg.get("date", 0), IST).strftime("%Y-%m-%d %H:%M"),
                                    })
                            if messages:
                                with open(_analysis_file, "w", encoding="utf-8") as f:
                                    json.dump(messages, f, indent=2, ensure_ascii=False)
                                st.success(f"✅ Fetched {len(messages)} messages!")
                                st.rerun()
                            else:
                                st.warning("No new messages found.")
                        else:
                            st.info("No updates from bot. Send a message in a group where bot is added.")
                    except Exception as e:
                        st.error(f"Fetch failed: {e}")
                else:
                    st.warning("Configure bot token in Setup tab first.")

        with col_status:
            msg_count = 0
            if _analysis_file.exists():
                try:
                    with open(_analysis_file, "r", encoding="utf-8") as f:
                        saved_msgs = json.load(f)
                    msg_count = len(saved_msgs)
                except Exception:
                    saved_msgs = []
            st.metric("Messages Loaded", msg_count)

        st.markdown("---")

        # Load and analyze messages
        messages = []
        if _analysis_file.exists():
            try:
                with open(_analysis_file, "r", encoding="utf-8") as f:
                    messages = json.load(f)
            except Exception:
                pass

        if messages:
            # ── KPI Row ──────────────────────────────────────────────
            k1, k2, k3, k4 = st.columns(4)
            chats = set(m.get("chat", "") for m in messages)
            senders = set(m.get("from", "") for m in messages)

            # Price mentions
            import re
            price_pattern = re.compile(r'[\₹$]?\s*[\d,]+(?:\.\d+)?(?:\s*/?\s*(?:MT|mt|KL|kl))?')
            price_msgs = [m for m in messages if price_pattern.search(m.get("text", ""))]

            # Keywords
            biz_keywords = ["price", "rate", "bitumen", "crude", "order", "supply",
                           "delivery", "payment", "tender", "demand", "stock", "refinery",
                           "IOCL", "BPCL", "HPCL", "VG30", "VG10", "freight", "import"]
            biz_msgs = [m for m in messages if any(kw.lower() in m.get("text", "").lower() for kw in biz_keywords)]

            k1.metric("💬 Total Messages", len(messages))
            k2.metric("👥 Groups/Chats", len(chats))
            k3.metric("💰 Price Mentions", len(price_msgs))
            k4.metric("📊 Business Msgs", len(biz_msgs))

            # ── Analysis Tabs ────────────────────────────────────────
            a1, a2, a3, a4 = st.tabs(["📝 Summary", "💰 Price Intel", "📊 Analytics", "💬 All Messages"])

            with a1:
                st.markdown("### 📝 Chat Summary")

                # Auto-generate summary
                st.markdown(f"""
**Period:** {messages[-1].get('date', '?')} to {messages[0].get('date', '?')}
**Total Messages:** {len(messages)} across {len(chats)} chat(s)
**Key Contributors:** {', '.join(list(senders)[:5])}
""")
                # Business highlights
                if biz_msgs:
                    st.markdown("#### 🔑 Key Business Discussions")
                    for bm in biz_msgs[:10]:
                        text = bm.get("text", "")[:150]
                        chat = bm.get("chat", "")
                        sender = bm.get("from", "")
                        date = bm.get("date", "")
                        st.markdown(f"""
<div style="background:#f8fafc;border-left:3px solid #2563eb;border-radius:6px;
            padding:8px 12px;margin-bottom:6px;">
  <div style="font-size:0.82rem;color:#0f172a;line-height:1.4;">{text}</div>
  <div style="font-size:0.65rem;color:#94a3b8;margin-top:4px;">
    👤 {sender} • 💬 {chat} • 🕐 {date}
  </div>
</div>""", unsafe_allow_html=True)
                else:
                    st.info("No business-related messages found.")

                # Topic breakdown
                st.markdown("#### 📂 Topic Breakdown")
                topics = {"Price/Rate": 0, "Order/Supply": 0, "Tender": 0,
                         "Refinery/IOCL": 0, "Import/Freight": 0, "General": 0}
                for m in messages:
                    txt = m.get("text", "").lower()
                    categorized = False
                    if any(w in txt for w in ["price", "rate", "₹", "rs", "cost"]):
                        topics["Price/Rate"] += 1; categorized = True
                    if any(w in txt for w in ["order", "supply", "delivery", "stock"]):
                        topics["Order/Supply"] += 1; categorized = True
                    if any(w in txt for w in ["tender", "nhai", "govt", "government"]):
                        topics["Tender"] += 1; categorized = True
                    if any(w in txt for w in ["iocl", "bpcl", "hpcl", "refinery"]):
                        topics["Refinery/IOCL"] += 1; categorized = True
                    if any(w in txt for w in ["import", "freight", "vessel", "port"]):
                        topics["Import/Freight"] += 1; categorized = True
                    if not categorized:
                        topics["General"] += 1

                for topic, count in sorted(topics.items(), key=lambda x: -x[1]):
                    if count > 0:
                        pct = count / len(messages) * 100
                        st.markdown(f"**{topic}:** {count} msgs ({pct:.0f}%)")
                        st.progress(min(1.0, pct / 100))

            with a2:
                st.markdown("### 💰 Price Intelligence from Chats")
                if price_msgs:
                    for pm in price_msgs[:15]:
                        text = pm.get("text", "")
                        # Highlight numbers
                        highlighted = re.sub(
                            r'([\₹$]?\s*[\d,]+(?:\.\d+)?(?:\s*/?\s*(?:MT|mt|KL|kl))?)',
                            r'<span style="background:#fef3c7;color:#92400e;font-weight:700;padding:1px 4px;border-radius:3px;">\1</span>',
                            text[:200]
                        )
                        st.markdown(f"""
<div style="background:#fffbeb;border-left:3px solid #f59e0b;border-radius:6px;
            padding:10px 12px;margin-bottom:8px;">
  <div style="font-size:0.82rem;color:#0f172a;line-height:1.4;">{highlighted}</div>
  <div style="font-size:0.65rem;color:#92400e;margin-top:4px;">
    👤 {pm.get('from','')} • 💬 {pm.get('chat','')} • 🕐 {pm.get('date','')}
  </div>
</div>""", unsafe_allow_html=True)
                else:
                    st.info("No price mentions found in messages.")

            with a3:
                st.markdown("### 📊 Chat Analytics")

                # Messages per chat
                chat_counts = {}
                for m in messages:
                    c = m.get("chat", "Unknown")
                    chat_counts[c] = chat_counts.get(c, 0) + 1

                st.markdown("**Messages per Chat/Group:**")
                for chat, count in sorted(chat_counts.items(), key=lambda x: -x[1]):
                    st.markdown(f"💬 **{chat}:** {count} messages")

                st.markdown("---")

                # Top senders
                sender_counts = {}
                for m in messages:
                    s = m.get("from", "Unknown")
                    sender_counts[s] = sender_counts.get(s, 0) + 1

                st.markdown("**Top Contributors:**")
                for sender, count in sorted(sender_counts.items(), key=lambda x: -x[1])[:10]:
                    st.markdown(f"👤 **{sender}:** {count} messages")

                # Word cloud (top keywords)
                st.markdown("---")
                st.markdown("**🔤 Top Keywords:**")
                all_words = " ".join(m.get("text", "") for m in messages).lower().split()
                stop_words = {"the", "is", "a", "an", "and", "or", "to", "of", "in", "for", "on",
                             "at", "by", "with", "from", "that", "this", "it", "are", "was", "be",
                             "has", "have", "had", "not", "but", "if", "ke", "ka", "ki", "hai",
                             "me", "se", "ko", "ye", "wo", "kya", "ho", "nahi", "aur", "bhi"}
                word_freq = {}
                for w in all_words:
                    w = re.sub(r'[^\w]', '', w)
                    if len(w) > 2 and w not in stop_words:
                        word_freq[w] = word_freq.get(w, 0) + 1

                top_words = sorted(word_freq.items(), key=lambda x: -x[1])[:20]
                if top_words:
                    for word, freq in top_words:
                        st.markdown(f"`{word}` — {freq}x")

            with a4:
                st.markdown("### 💬 All Messages")
                import pandas as pd
                df = pd.DataFrame(messages)
                display_cols = [c for c in ["date", "chat", "from", "text"] if c in df.columns]
                if display_cols:
                    # Search
                    search = st.text_input("🔍 Search messages", key="_tg_msg_search", placeholder="Type to search...")
                    if search:
                        df = df[df["text"].str.contains(search, case=False, na=False)]
                    st.dataframe(df[display_cols], use_container_width=True, hide_index=True, height=400)
                    st.caption(f"Showing {len(df)} messages")

        else:
            st.info("No messages loaded yet. Click **Fetch Latest Messages** to get started.")
            st.markdown("""
**How to setup:**
1. Go to **Setup** tab → enter your bot token from @BotFather
2. Add the bot to your Telegram group
3. Send some messages in the group
4. Come back here and click **Fetch Latest Messages**
5. The analyzer will automatically categorize and summarize all chats
""")

    # ══════════════════════════════════════════════════════════════════════
    #  TAB 1 — Setup
    # ══════════════════════════════════════════════════════════════════════
    with tab_setup:
        st.subheader("Bot Setup")
        st.caption("Configure and verify your Telegram Bot API token.")

        # Show current status
        current_settings = _load_json(_SETTINGS_FILE, {"bot_token": "", "chats": [], "enabled": True})
        token_masked = ""
        raw_token = current_settings.get("bot_token", "")
        if raw_token:
            token_masked = raw_token[:8] + "..." + raw_token[-4:] if len(raw_token) > 12 else "***configured***"

        st.markdown(f"**Current Token:** `{token_masked}`" if token_masked else "**Current Token:** _Not configured_")

        # ── Verify existing bot ──────────────────────────────────────────
        st.markdown("---")
        st.markdown("**Verify Bot**")
        if st.button("\u2705 Verify Current Bot", key="tg_verify"):
            with st.spinner("Verifying bot token..."):
                result = verify_bot()
            if result.get("ok"):
                bot_info = result.get("bot", {})
                st.success("Bot verified successfully!")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Bot Name", bot_info.get("first_name", "—"))
                with col2:
                    st.metric("Username", f"@{bot_info.get('username', '—')}")
                with col3:
                    st.metric("Bot ID", bot_info.get("id", "—"))
            else:
                st.error(f"Verification failed: {result.get('description', 'Unknown error')}")

        # ── Configure new token ──────────────────────────────────────────
        st.markdown("---")
        st.markdown("**Configure New Bot Token**")
        st.caption("Get a token from [@BotFather](https://t.me/BotFather) on Telegram.")

        new_token = st.text_input(
            "Bot Token",
            type="password",
            placeholder="e.g. 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
            key="tg_new_token",
        )

        if st.button("\U0001f4be Save & Verify Token", type="primary", key="tg_save_token"):
            if not new_token.strip():
                st.error("Token cannot be empty.")
            else:
                with st.spinner("Verifying and saving token..."):
                    result = configure_bot(new_token.strip())
                if result.get("ok"):
                    bot_info = result.get("bot", {})
                    st.success(f"Bot configured: {bot_info.get('first_name', '')} (@{bot_info.get('username', '')})")
                    st.balloons()
                else:
                    st.error(f"Failed: {result.get('description', 'Unknown error')}")

    # ══════════════════════════════════════════════════════════════════════
    #  TAB 2 — Channels
    # ══════════════════════════════════════════════════════════════════════
    with tab_chats:
        st.subheader("Configured Channels / Chats")
        st.caption("Manage Telegram groups, channels, and individual chats.")

        chats = get_chat_list()

        if chats:
            chat_rows = []
            for idx, c in enumerate(chats):
                chat_rows.append({
                    "#": idx + 1,
                    "Label": c.get("label", "—"),
                    "Chat ID": c.get("chat_id", "—"),
                    "Type": c.get("type", "—"),
                })
            st.dataframe(chat_rows, use_container_width=True, hide_index=True)

            # ── Remove a chat ────────────────────────────────────────────
            st.markdown("---")
            st.markdown("**Remove a Channel**")
            chat_labels = [
                f"{c.get('label', 'Unnamed')} ({c.get('chat_id', '?')})"
                for c in chats
            ]
            to_remove = st.selectbox("Select channel to remove", options=chat_labels, key="tg_ch_remove_sel")
            if st.button("\U0001f5d1\ufe0f Remove Channel", key="tg_ch_remove_btn"):
                rm_idx = chat_labels.index(to_remove)
                rm_chat_id = chats[rm_idx].get("chat_id", "")
                remove_chat(rm_chat_id)
                st.success(f"Channel '{chats[rm_idx].get('label', '')}' removed.")
                st.rerun()
        else:
            st.info("No channels configured yet. Add one below.")

        # ── Add new chat ─────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("**Add New Channel / Chat**")

        ac_col1, ac_col2 = st.columns(2)
        with ac_col1:
            new_chat_id = st.text_input(
                "Chat ID",
                placeholder="e.g. -1001234567890",
                key="tg_new_chat_id",
                help="Use @BotFather or forward a message to @userinfobot to find chat IDs.",
            )
            new_chat_label = st.text_input(
                "Label / Name",
                placeholder="e.g. PPS Market Updates",
                key="tg_new_chat_label",
            )
        with ac_col2:
            new_chat_type = st.selectbox(
                "Type",
                options=["group", "channel", "supergroup", "private"],
                key="tg_new_chat_type",
            )

        if st.button("\u2795 Add Channel", type="primary", key="tg_add_chat"):
            if not new_chat_id.strip():
                st.error("Chat ID is required.")
            elif not new_chat_label.strip():
                st.error("A label/name is required.")
            else:
                add_chat(new_chat_id.strip(), new_chat_label.strip(), new_chat_type)
                st.success(f"Channel '{new_chat_label}' added.")
                st.rerun()

    # ══════════════════════════════════════════════════════════════════════
    #  TAB 3 — Send
    # ══════════════════════════════════════════════════════════════════════
    with tab_send:
        st.subheader("Send Message")
        st.caption("Compose and send messages or documents to Telegram chats.")

        chats = get_chat_list()
        if not chats:
            st.warning("No channels configured. Add channels in the Channels tab first.")
        else:
            # ── Chat selection ───────────────────────────────────────────
            chat_options = {
                f"{c.get('label', 'Unnamed')} ({c.get('chat_id', '')})": c.get("chat_id", "")
                for c in chats
            }
            chat_options["All Channels (Broadcast)"] = "__broadcast__"

            selected_chat_label = st.selectbox(
                "Select Chat / Channel",
                options=list(chat_options.keys()),
                key="tg_send_chat",
            )
            selected_chat_id = chat_options[selected_chat_label]

            # ── Message compose ──────────────────────────────────────────
            st.markdown("---")
            st.markdown("**Compose Message**")
            msg_text = st.text_area(
                "Message",
                placeholder="Type your message here...\nHTML formatting is supported: <b>bold</b>, <i>italic</i>, <code>code</code>",
                height=200,
                key="tg_send_msg",
            )

            parse_mode = st.radio(
                "Parse Mode",
                options=["HTML", "Markdown", "None"],
                horizontal=True,
                key="tg_parse_mode",
            )
            if parse_mode == "None":
                parse_mode = None

            if st.button("\U0001f4e8 Send Message", type="primary", use_container_width=True, key="tg_send_btn"):
                if not msg_text.strip():
                    st.error("Message cannot be empty.")
                else:
                    with st.spinner("Sending..."):
                        if selected_chat_id == "__broadcast__":
                            results = broadcast_message(msg_text, parse_mode=parse_mode or "HTML")
                            success_count = sum(1 for r in results if r.get("ok"))
                            fail_count = len(results) - success_count
                            if success_count:
                                st.success(f"Broadcast sent to {success_count} channel(s).")
                            if fail_count:
                                st.warning(f"Failed for {fail_count} channel(s).")
                                for r in results:
                                    if not r.get("ok"):
                                        st.caption(f"  {r.get('chat_id', '?')}: {r.get('description', 'Unknown error')}")
                        else:
                            kwargs = {"chat_id": selected_chat_id, "text": msg_text}
                            if parse_mode:
                                kwargs["parse_mode"] = parse_mode
                            result = send_message(**kwargs)
                            if result.get("ok"):
                                st.success("Message sent successfully!")
                            else:
                                st.error(f"Failed: {result.get('description', 'Unknown error')}")

            # ── File upload ──────────────────────────────────────────────
            st.markdown("---")
            st.markdown("**Send Document**")
            uploaded_file = st.file_uploader(
                "Upload file",
                type=["pdf", "xlsx", "csv", "png", "jpg", "txt", "json"],
                key="tg_send_file",
            )
            file_caption = st.text_input(
                "Caption (optional)",
                placeholder="e.g. Weekly market report",
                key="tg_file_caption",
            )

            if st.button("\U0001f4ce Send Document", key="tg_send_doc_btn"):
                if not uploaded_file:
                    st.error("Please upload a file first.")
                elif selected_chat_id == "__broadcast__":
                    st.warning("Document broadcast is not supported. Select a specific channel.")
                else:
                    with st.spinner("Uploading document..."):
                        file_bytes = uploaded_file.read()
                        result = send_document(
                            selected_chat_id,
                            file_bytes,
                            uploaded_file.name,
                            caption=file_caption,
                        )
                    if result.get("ok"):
                        st.success(f"Document '{uploaded_file.name}' sent successfully!")
                    else:
                        st.error(f"Failed: {result.get('description', 'Unknown error')}")

    # ══════════════════════════════════════════════════════════════════════
    #  TAB 4 — Logs
    # ══════════════════════════════════════════════════════════════════════
    with tab_logs:
        st.subheader("Telegram Logs")
        st.caption("Activity log of all Telegram API interactions.")

        log_data = _load_json(_LOG_FILE, [])

        if not log_data:
            st.info("No log entries found. Send a message to generate log data.")
        else:
            # Ensure it's a list
            if not isinstance(log_data, list):
                log_data = []

            # Sort by timestamp descending
            try:
                log_sorted = sorted(log_data, key=lambda x: x.get("timestamp", ""), reverse=True)
            except Exception:
                log_sorted = log_data

            # Filters
            col_ft, col_fs = st.columns(2)
            with col_ft:
                filter_type = st.selectbox(
                    "Filter by Type",
                    options=["All", "message", "document", "photo"],
                    key="tg_log_filter_type",
                )
            with col_fs:
                filter_status = st.selectbox(
                    "Filter by Status",
                    options=["All", "success", "failed"],
                    key="tg_log_filter_status",
                )

            filtered = log_sorted
            if filter_type != "All":
                filtered = [l for l in filtered if l.get("type", "") == filter_type]
            if filter_status != "All":
                filtered = [l for l in filtered if l.get("status", "") == filter_status]

            # Display
            display_rows = []
            for entry in filtered[:200]:
                display_rows.append({
                    "Timestamp": entry.get("timestamp", "—"),
                    "Chat ID": entry.get("chat_id", "—"),
                    "Type": entry.get("type", "—"),
                    "Status": entry.get("status", "—"),
                    "Error": entry.get("error", ""),
                })

            if display_rows:
                st.dataframe(display_rows, use_container_width=True, hide_index=True)
                st.caption(f"Showing {len(display_rows)} of {len(filtered)} entries.")
            else:
                st.info("No log entries match the selected filters.")

            # Stats summary
            st.markdown("---")
            total = len(log_data)
            success = sum(1 for l in log_data if l.get("status") == "success")
            failed = sum(1 for l in log_data if l.get("status") == "failed")

            col_s1, col_s2, col_s3 = st.columns(3)
            with col_s1:
                st.metric("Total Sends", total)
            with col_s2:
                st.metric("Successful", success)
            with col_s3:
                st.metric("Failed", failed)

    # ══════════════════════════════════════════════════════════════════════
    #  TAB 5 — Settings
    # ══════════════════════════════════════════════════════════════════════
    with tab_settings:
        st.subheader("Telegram Settings")
        st.caption("Enable/disable Telegram integration and configure rate limits.")

        settings = _load_json(_SETTINGS_FILE, {
            "bot_token": "",
            "chats": [],
            "enabled": True,
            "rate_limit_per_second": 1,
            "rate_limit_burst": 5,
            "max_message_length": 4096,
            "default_parse_mode": "HTML",
            "log_retention_days": 30,
        })

        # ── Enable / Disable ────────────────────────────────────────────
        enabled = st.toggle(
            "Telegram Integration Enabled",
            value=settings.get("enabled", True),
            key="tg_enabled",
        )

        if not enabled:
            st.warning("Telegram integration is disabled. Messages will not be sent.")

        st.markdown("---")

        # ── Rate Limiting ────────────────────────────────────────────────
        st.markdown("**Rate Limiting**")
        st.caption(
            "Telegram Bot API allows ~30 messages per second to different chats, "
            "and 1 message per second to the same chat."
        )

        col_r1, col_r2 = st.columns(2)
        with col_r1:
            rate_per_sec = st.number_input(
                "Max sends per second",
                min_value=1,
                max_value=30,
                value=settings.get("rate_limit_per_second", 1),
                step=1,
                key="tg_rate_sec",
            )
        with col_r2:
            rate_burst = st.number_input(
                "Burst limit",
                min_value=1,
                max_value=50,
                value=settings.get("rate_limit_burst", 5),
                step=1,
                key="tg_rate_burst",
            )

        # ── Message Settings ─────────────────────────────────────────────
        st.markdown("---")
        st.markdown("**Message Defaults**")

        col_m1, col_m2 = st.columns(2)
        with col_m1:
            max_msg_len = st.number_input(
                "Max message length",
                min_value=100,
                max_value=4096,
                value=settings.get("max_message_length", 4096),
                step=100,
                key="tg_max_len",
            )
        with col_m2:
            default_parse = st.selectbox(
                "Default parse mode",
                options=["HTML", "Markdown", "None"],
                index=["HTML", "Markdown", "None"].index(settings.get("default_parse_mode", "HTML")) if settings.get("default_parse_mode", "HTML") in ["HTML", "Markdown", "None"] else 0,
                key="tg_default_parse",
            )

        # ── Log Retention ────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("**Log Retention**")
        log_retention = st.number_input(
            "Keep logs for (days)",
            min_value=1,
            max_value=365,
            value=settings.get("log_retention_days", 30),
            step=1,
            key="tg_log_retention",
        )

        # ── Save Settings ────────────────────────────────────────────────
        st.markdown("---")
        if st.button("\U0001f4be Save Settings", type="primary", use_container_width=True, key="tg_save_settings"):
            settings["enabled"] = enabled
            settings["rate_limit_per_second"] = rate_per_sec
            settings["rate_limit_burst"] = rate_burst
            settings["max_message_length"] = max_msg_len
            settings["default_parse_mode"] = default_parse
            settings["log_retention_days"] = log_retention

            if _save_json(_SETTINGS_FILE, settings):
                st.success("Settings saved successfully.")
            else:
                st.error("Failed to save settings.")

        # ── Current Config Summary ───────────────────────────────────────
        st.markdown("---")
        st.markdown("**Current Configuration**")
        with st.expander("View raw settings JSON", expanded=False):
            # Show settings without the token for security
            safe_settings = dict(settings)
            if safe_settings.get("bot_token"):
                t = safe_settings["bot_token"]
                safe_settings["bot_token"] = t[:8] + "..." + t[-4:] if len(t) > 12 else "***"
            st.json(safe_settings)
