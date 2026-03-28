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
        response = bot.get_response(message)
        if isinstance(response, dict):
            return response.get("response", response.get("text", str(response)))
        return str(response)
    except Exception:
        # Fallback responses
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


def render():
    st.header("💬 Client Chat")
    st.caption("Chat with customers — AI-powered auto-replies + CRM logging.")

    tabs = st.tabs(["💬 Chat", "📋 Conversations", "⚙️ Settings"])

    # ── Tab 1: Active Chat ──
    with tabs[0]:
        # Initialize session state
        if "_chat_conv" not in st.session_state:
            st.session_state["_chat_conv"] = None
        if "_chat_msgs" not in st.session_state:
            st.session_state["_chat_msgs"] = []

        # Start new or select existing conversation
        c1, c2 = st.columns([2, 1])
        with c1:
            customer_name = st.text_input("Customer Name", key="chat_cust",
                                          placeholder="Enter customer name to start chat...")
        with c2:
            if st.button("New Chat", type="primary", use_container_width=True):
                if customer_name:
                    conv_id = f"chat_{customer_name.replace(' ', '_')}_{datetime.datetime.now().strftime('%Y%m%d%H%M')}"
                    st.session_state["_chat_conv"] = conv_id
                    st.session_state["_chat_msgs"] = []
                    st.session_state["_chat_cust_name"] = customer_name
                    st.rerun()

        conv_id = st.session_state.get("_chat_conv")
        cust_name = st.session_state.get("_chat_cust_name", "Customer")

        if conv_id:
            st.markdown(f"**Active conversation:** {cust_name}")
            st.markdown("---")

            # Load existing messages
            if not st.session_state["_chat_msgs"]:
                st.session_state["_chat_msgs"] = _get_messages(conv_id)

            # Display messages
            for msg in st.session_state["_chat_msgs"]:
                role = "user" if msg.get("sender_type") == "customer" else "assistant"
                with st.chat_message(role):
                    st.write(msg.get("message_text", ""))
                    ts = msg.get("created_at", "")
                    if ts:
                        st.caption(ts)

            # Chat input
            if prompt := st.chat_input("Type customer's message..."):
                # Save customer message
                _send_message(conv_id, cust_name, prompt, "customer")
                _log_to_crm(cust_name, prompt)
                st.session_state["_chat_msgs"].append({
                    "sender_type": "customer",
                    "sender_name": cust_name,
                    "message_text": prompt,
                    "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                })

                # Auto-reply
                with st.spinner("AI generating reply..."):
                    reply = _get_ai_reply(prompt)
                _send_message(conv_id, "PPS Anantams", reply, "agent")
                st.session_state["_chat_msgs"].append({
                    "sender_type": "agent",
                    "sender_name": "PPS Anantams",
                    "message_text": reply,
                    "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                })
                st.rerun()
        else:
            st.info("Enter a customer name and click 'New Chat' to start a conversation.")

    # ── Tab 2: Conversations List ──
    with tabs[1]:
        st.subheader("Recent Conversations")
        conversations = _get_conversations()
        if conversations:
            for conv in conversations[:20]:
                cid = conv.get("conversation_id", "?")
                name = conv.get("sender_name", "Unknown")
                last_msg = conv.get("last_message", "")
                count = conv.get("message_count", 0)
                unread = conv.get("unread", 0)

                unread_badge = f' 🔴 {unread} new' if unread else ''
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"**{name}**{unread_badge}")
                    st.caption(f"{last_msg[:80]}... ({count} messages)")
                with col2:
                    if st.button("Open", key=f"open_{cid}"):
                        st.session_state["_chat_conv"] = cid
                        st.session_state["_chat_cust_name"] = name
                        st.session_state["_chat_msgs"] = _get_messages(cid)
                        st.rerun()
                st.markdown("---")
        else:
            st.info("No conversations yet. Start a new chat from the Chat tab.")

    # ── Tab 3: Settings ──
    with tabs[2]:
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
