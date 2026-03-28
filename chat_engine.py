"""
PPS Anantam — Client Chat Engine v1.0
========================================
Polling-based chat system using SQLite + Streamlit session state.
No WebSocket required — messages persist in chat_messages table.

Uses st.chat_message and st.chat_input for the UI.
"""

import os
import sys
import uuid
from datetime import datetime, timezone, timedelta

sys.path.append(os.path.dirname(__file__))

IST = timezone(timedelta(hours=5, minutes=30))


class ChatEngine:
    """Manage client conversations stored in SQLite."""

    def __init__(self):
        from settings_engine import load_settings
        self.settings = load_settings()

    def get_conversations(self) -> list:
        """Get all conversations with last message info."""
        try:
            from database import get_chat_conversations
            return get_chat_conversations()
        except Exception:
            return []

    def get_messages(self, conversation_id: str, limit: int = 100) -> list:
        """Get messages for a conversation, oldest first."""
        try:
            from database import get_chat_messages
            return get_chat_messages(conversation_id, limit)
        except Exception:
            return []

    def send_message(self, conversation_id: str, text: str,
                     sender_type: str = "internal",
                     sender_name: str = "Admin",
                     attachment_path: str = None) -> int:
        """Send a message in a conversation.
        Returns the new message ID."""
        from database import insert_chat_message
        data = {
            "conversation_id": conversation_id,
            "sender_type": sender_type,
            "sender_name": sender_name,
            "message_text": text.strip(),
            "attachment_path": attachment_path or "",
            "is_read": 1 if sender_type == "internal" else 0,
        }
        msg_id = insert_chat_message(data)

        # Track in comm_tracking
        self._track_message(conversation_id, sender_name, text)
        return msg_id

    def get_unread_count(self) -> dict:
        """Get unread counts per conversation.
        Returns {conversation_id: unread_count}."""
        convos = self.get_conversations()
        return {c["conversation_id"]: c.get("unread", 0) for c in convos if c.get("unread", 0) > 0}

    def mark_read(self, conversation_id: str):
        """Mark all messages in a conversation as read."""
        try:
            from database import mark_chat_read
            mark_chat_read(conversation_id)
        except Exception:
            pass

    def create_conversation(self, customer_name: str, customer_id: int = None) -> str:
        """Create a new conversation. Returns conversation_id."""
        convo_id = f"chat_{customer_name.lower().replace(' ', '_')}_{uuid.uuid4().hex[:6]}"
        # Send initial greeting
        self.send_message(
            convo_id,
            f"Chat started with {customer_name}. How can we help you today?",
            sender_type="internal",
            sender_name="System",
        )
        return convo_id

    def _track_message(self, conversation_id, sender_name, text):
        """Log chat message in comm_tracking."""
        try:
            from database import insert_comm_tracking
            insert_comm_tracking({
                "tracking_id": f"chat_{uuid.uuid4().hex[:8]}",
                "channel": "chat",
                "action": "sent",
                "sender": sender_name,
                "recipient_name": conversation_id,
                "content_type": "message",
                "content_summary": text[:200],
                "delivery_status": "delivered",
            })
        except Exception:
            pass


def render_chat_panel():
    """Render the chat panel UI in Streamlit."""
    import streamlit as st

    engine = ChatEngine()
    conversations = engine.get_conversations()

    if not engine.settings.get("chat_enabled", False):
        st.info("💬 Client Chat is disabled. Enable it in Integrations → Client Chat settings.")
        return

    col_left, col_right = st.columns([1, 3])

    # ── Left: Conversation List ──────────────────────────────────────────────
    with col_left:
        st.markdown("**Conversations**")

        # New conversation button
        with st.popover("➕ New Chat"):
            new_name = st.text_input("Customer name", key="_chat_new_name")
            if st.button("Start Chat", key="_chat_start_btn") and new_name:
                convo_id = engine.create_conversation(new_name.strip())
                st.session_state["_active_chat"] = convo_id
                st.rerun()

        if not conversations:
            st.caption("No conversations yet. Start a new chat above.")
        else:
            for convo in conversations:
                cid = convo["conversation_id"]
                unread = convo.get("unread", 0)
                last_at = convo.get("last_message_at", "")
                badge = f" 🔴 {unread}" if unread > 0 else ""
                display_name = cid.replace("chat_", "").replace("_", " ").title()[:25]

                if st.button(
                    f"{display_name}{badge}",
                    key=f"_chat_conv_{cid}",
                    use_container_width=True,
                ):
                    st.session_state["_active_chat"] = cid
                    engine.mark_read(cid)
                    st.rerun()

    # ── Right: Active Conversation ───────────────────────────────────────────
    with col_right:
        active_id = st.session_state.get("_active_chat", "")

        if not active_id:
            st.markdown("""
<div style="text-align:center; padding:60px 20px; color:#94a3b8;">
<div style="font-size:2rem;">💬</div>
<div style="font-size:0.9rem; margin-top:10px;">Select a conversation or start a new chat</div>
</div>""", unsafe_allow_html=True)
            return

        display_name = active_id.replace("chat_", "").replace("_", " ").title()
        st.markdown(f"**💬 {display_name}**")
        st.markdown("---")

        # Display messages
        messages = engine.get_messages(active_id, limit=50)
        for msg in messages:
            sender_type = msg.get("sender_type", "internal")
            role = "assistant" if sender_type == "internal" else "user"
            name = msg.get("sender_name", "")
            text = msg.get("message_text", "")
            ts = msg.get("created_at", "")

            with st.chat_message(role):
                st.markdown(f"**{name}** — {ts}")
                st.write(text)
                if msg.get("attachment_path"):
                    st.caption(f"📎 {msg['attachment_path']}")

        # Chat input
        user_input = st.chat_input("Type a message...", key=f"_chat_input_{active_id}")
        if user_input:
            engine.send_message(active_id, user_input, sender_type="internal", sender_name="Admin")
            st.rerun()
