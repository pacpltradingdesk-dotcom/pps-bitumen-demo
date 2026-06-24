"""
PPS Anantam — Client Chat Dashboard
======================================
Chat inbox + conversation view + auto-reply + CRM logging.
"""
import streamlit as st
import datetime


def _get_conversations():
    """Get all chat conversations."""
    try:
        from database import get_chat_conversations
        return get_chat_conversations()
    except Exception:
        return []


def _get_messages(conversation_id):
    """Get messages for a conversation."""
    try:
        from database import _get_conn
        conn = _get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM chat_messages WHERE conversation_id = ? ORDER BY created_at ASC",
                (conversation_id,)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
    except Exception:
        return []


def _send_message(conversation_id, sender_name, message, sender_type="agent"):
    """Send a message and log to DB."""
    try:
        from database import insert_chat_message
        insert_chat_message({
            "conversation_id": conversation_id,
            "sender_type": sender_type,
            "sender_name": sender_name,
            "message_text": message,
            "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
    except Exception as e:
        st.error(f"Failed to send: {e}")


def _get_ai_reply(message):
    """Get AI auto-reply for customer query."""
    try:
        from trading_chatbot_engine import TradingChatbot
        bot = TradingChatbot()
        # TradingChatbot's entry point is process_query() → {"answer": ...}.
        # (Earlier this called the non-existent get_response(), so EVERY reply
        # silently fell through to the canned text below — the "AI" never ran.)
        response = bot.process_query(message)
        if isinstance(response, dict):
            answer = response.get("answer") or response.get("response") or response.get("text")
            if answer:
                return str(answer)
        elif response:
            return str(response)
    except Exception:
        pass

    # ── Keyword fallback (used only if the AI engine is unavailable) ──
    msg_lower = message.lower()
    if any(w in msg_lower for w in ["price", "rate", "cost", "kitna"]):
        return "Thank you for your inquiry! Our current VG30 rates vary by location. For the best landed cost to your city, please share your delivery location and quantity. Our team will send you a detailed quote within 30 minutes.\n\n📞 Call: +91 7795242424"
    elif any(w in msg_lower for w in ["delivery", "transport", "ship", "dispatch"]):
        return "We deliver across India via bulk tankers and drum trucks. Standard delivery: 3-5 days depending on location. For urgent requirements, express dispatch is available.\n\n📞 Call: +91 7795242424"
    elif any(w in msg_lower for w in ["payment", "advance", "credit"]):
        return "Our standard terms: 100% advance payment. For regular customers with good track record, we offer flexible payment options. GST 18% applicable on all transactions.\n\n📞 Call: +91 7795242424"
    else:
        return "Thank you for reaching out to PPS Anantams! We're India's leading bitumen trading platform with 24+ years experience. How can we help you today?\n\n📞 For immediate assistance: +91 7795242424"


def _log_to_crm(customer, message, channel="Chat"):
    """Log chat interaction to CRM."""
    try:
        from database import log_communication
        log_communication({
            "customer_id": customer,
            "channel": channel,
            "direction": "inbound",
            "subject": f"Chat: {message[:50]}...",
            "content": message[:500],
            "template_used": "client_chat",
            "sent_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "status": "received",
        })
    except Exception:
        pass


def _current_user() -> str:
    """Stable id for the logged-in dashboard user (used to key their WhatsApp link)."""
    return (st.session_state.get("_auth_username")
            or (st.session_state.get("_auth_user") or {}).get("username")
            or "user")


def render():
    import whatsapp_bridge as wa

    st.header("💬 Client Chat")
    st.caption("Customer WhatsApp inbox — AI drafts a reply, you approve & send. Every message logged to CRM.")

    # Pull any new inbound customer messages from the linked WhatsApp into the inbox.
    try:
        wa.drain_inbound()
    except Exception:
        pass

    user = _current_user()
    tabs = st.tabs(["💬 Chat", "📋 Conversations", "📱 Connect", "⚙️ Settings"])

    # ── Tab 1: Active Chat — approve-then-send WhatsApp flow ──
    with tabs[0]:
        st.session_state.setdefault("_chat_cust_name", None)
        st.session_state.setdefault("_chat_draft", "")

        # Pick the customer to start an outbound thread (inbound threads appear in Conversations).
        c1, c2 = st.columns([2, 1])
        with c1:
            try:
                from components.autosuggest import customer_picker
                customer_name = customer_picker(key="chat_cust", label="Customer Name")
            except Exception:
                customer_name = st.text_input("Customer Name", key="chat_cust",
                                              placeholder="Enter customer name to start chat...")
        with c2:
            if st.button("New Chat", type="primary", use_container_width=True):
                if customer_name:
                    st.session_state["_chat_cust_name"] = customer_name
                    st.session_state["_chat_draft"] = ""
                    st.session_state.pop("_chat_draft_edit", None)
                    st.rerun()

        cust_name = st.session_state.get("_chat_cust_name")
        if not cust_name:
            st.info("Pick a customer and click 'New Chat' to start a WhatsApp conversation.")
        else:
            # A WhatsApp thread is keyed by the customer's phone number.
            phone = st.text_input("Customer WhatsApp number", key="_chat_phone",
                                  placeholder="e.g. 9876543210",
                                  help="Replies are sent to this WhatsApp number. Indian 10-digit numbers get +91 automatically.")
            conv_id = wa.conversation_id_for_phone(phone) if phone.strip() else None

            if not conv_id:
                st.info("Enter the customer's WhatsApp number to open the conversation.")
            else:
                st.markdown(f"**Active conversation:** {cust_name}  ·  📱 {wa.normalize_phone(phone)}")
                st.markdown("---")

                msgs = _get_messages(conv_id)
                for msg in msgs:
                    role = "user" if msg.get("sender_type") == "customer" else "assistant"
                    with st.chat_message(role):
                        st.write(msg.get("message_text", ""))
                        if msg.get("created_at"):
                            st.caption(msg["created_at"])

                # A reply is pending when the last message is from the customer.
                pending = bool(msgs) and msgs[-1].get("sender_type") == "customer"
                if pending:
                    last_customer_msg = msgs[-1].get("message_text", "")
                    if not st.session_state.get("_chat_draft"):
                        with st.spinner("AI drafting a reply…"):
                            st.session_state["_chat_draft"] = _get_ai_reply(last_customer_msg)

                    st.markdown("**🤖 AI-suggested reply** — edit, then approve to send:")
                    draft = st.text_area("Draft reply", value=st.session_state["_chat_draft"],
                                         key="_chat_draft_edit", height=160,
                                         label_visibility="collapsed")
                    b1, b2 = st.columns(2)
                    with b1:
                        if st.button("✅ Approve & Send to WhatsApp", type="primary",
                                     use_container_width=True, disabled=not draft.strip()):
                            res = wa.send_text(phone, draft, from_user=user)
                            if res.get("ok"):
                                _send_message(conv_id, "PPS Anantams", draft, "agent")
                                try:
                                    from database import mark_chat_read
                                    mark_chat_read(conv_id)
                                except Exception:
                                    pass
                                st.session_state["_chat_draft"] = ""
                                st.session_state.pop("_chat_draft_edit", None)
                                st.success(f"Sent ✓ — {res.get('channel', 'whatsapp')}")
                                st.rerun()
                            else:
                                st.error(f"Send failed: {res.get('error', 'unknown error')}")
                    with b2:
                        if st.button("🔄 Regenerate draft", use_container_width=True):
                            st.session_state["_chat_draft"] = ""
                            st.session_state.pop("_chat_draft_edit", None)
                            st.rerun()
                else:
                    st.caption("Waiting for the customer's next message. Use the tester below to simulate one.")

                st.markdown("---")
                with st.expander("🧪 Simulate an incoming customer message (until WhatsApp is connected)"):
                    sim = st.text_input("Customer says…", key="_chat_sim")
                    if st.button("Receive message", key="_chat_sim_btn") and sim.strip():
                        wa.ingest_incoming(phone, cust_name, sim.strip())
                        _log_to_crm(cust_name, sim.strip())
                        st.session_state["_chat_draft"] = ""        # draft a reply to the new message
                        st.session_state.pop("_chat_draft_edit", None)
                        st.rerun()

    # ── Tab 2: Conversations List ──
    with tabs[1]:
        st.subheader("Recent Conversations")
        conversations = _get_conversations()
        if conversations:
            for conv in conversations[:20]:
                cid = conv.get("conversation_id", "?")
                name = conv.get("sender_name") or "Unknown"
                last_msg = conv.get("last_message") or ""
                count = conv.get("message_count") or 0
                unread = conv.get("unread") or 0

                unread_badge = f' 🔴 {unread} new' if unread else ''
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"**{name}**{unread_badge}")
                    st.caption(f"{last_msg[:80]}... ({count} messages)")
                with col2:
                    if st.button("Open", key=f"open_{cid}"):
                        st.session_state["_chat_cust_name"] = name
                        # conversation ids are wa_<phone>; recover the phone so the
                        # Chat tab opens this exact thread.
                        if cid.startswith("wa_"):
                            st.session_state["_chat_phone"] = cid[3:]
                        st.session_state["_chat_draft"] = ""
                        st.session_state.pop("_chat_draft_edit", None)
                        st.rerun()
                st.markdown("---")
        else:
            st.info("No conversations yet. Start a new chat from the Chat tab.")

    # ── Tab 3: Connect WhatsApp (per-user linking, isolated service) ──
    with tabs[2]:
        st.subheader("📱 Connect your WhatsApp")
        st.caption("Link YOUR WhatsApp so customer chats land in this inbox and replies go from your number. "
                   "Fully separate from the bulk sender.")
        status = wa.link_status(user)
        if status.get("offline"):
            st.warning("WhatsApp link service not reachable from here. On the live server it runs as the "
                       "isolated `pps-chat-wa` process.")
        elif status.get("status") == "connected":
            st.success(f"✅ Connected as **{user}** — number **{status.get('number', '?')}**")
            if st.button("🔌 Unlink WhatsApp"):
                wa.unlink(user)
                st.session_state.pop("_wa_link_res", None)
                st.rerun()
        else:
            st.info("Not linked yet. Click **Generate QR**, then scan it in WhatsApp → **Linked Devices → Link a device**.")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("🔗 Generate QR", type="primary"):
                    st.session_state["_wa_link_res"] = wa.start_link(user)
                    st.rerun()
            with c2:
                if st.button("🔄 Refresh status"):
                    st.session_state.pop("_wa_link_res", None)
                    st.rerun()
            res = st.session_state.get("_wa_link_res") or status
            qr = res.get("qr")
            if res.get("status") == "connected":
                st.success(f"✅ Connected — {res.get('number', '?')}")
            elif qr:
                import base64
                try:
                    b64 = qr.split(",", 1)[1] if str(qr).startswith("data:") else qr
                    st.image(base64.b64decode(b64), caption="Scan with WhatsApp → Linked Devices", width=280)
                    st.caption("After scanning, click '🔄 Refresh status'.")
                except Exception:
                    st.warning("Could not render QR image.")
            elif res.get("status") == "qr":
                st.info("Preparing QR… click '🔄 Refresh status' in a moment.")

    # ── Tab 4: Settings ──
    with tabs[3]:
        st.subheader("Chat Settings")
        try:
            from settings_engine import get as gs, save as ss

            auto_reply = st.toggle("Auto-Reply Enabled", value=gs("chat_auto_reply", True), key="chat_ar")
            greeting = st.text_area("Welcome Message",
                                    value=gs("chat_welcome_msg",
                                             "Welcome to PPS Anantams! How can we help you with your bitumen requirements today?"),
                                    key="chat_greet")
            max_len = st.number_input("Max Message Length", value=gs("chat_max_message_length", 2000),
                                      min_value=100, max_value=5000, key="chat_maxlen")

            if st.button("Save Settings", type="primary"):
                ss("chat_auto_reply", auto_reply)
                ss("chat_welcome_msg", greeting)
                ss("chat_max_message_length", max_len)
                st.success("Chat settings saved!")
        except Exception:
            st.info("Settings engine not available. Using defaults.")
