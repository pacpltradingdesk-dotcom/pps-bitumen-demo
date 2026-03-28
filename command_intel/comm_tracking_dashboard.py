"""
Communication Tracking Dashboard
=================================
Unified view of all communications across Email, WhatsApp,
Share Links, PDF exports, and Chat.

3-tab layout: Tracking Log | Analytics | Channel Status
"""

import streamlit as st
import sys
import os
from datetime import datetime, timezone, timedelta

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from ui_badges import display_badge

IST = timezone(timedelta(hours=5, minutes=30))


def render():
    display_badge("analytics")
    st.markdown("""
<div style="background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%);
padding: 20px 25px; border-radius: 12px; margin-bottom: 20px;
box-shadow: 0 10px 30px rgba(15, 23, 42, 0.4);">
<div style="display:flex; align-items:center; gap:15px;">
<span style="font-size:2rem;">📊</span>
<div>
<div style="font-size:1.3rem; font-weight:800; color:#e0e0e0;">
Communication Tracking
</div>
<div style="font-size:0.75rem; color:#94a3b8; letter-spacing:1px; text-transform:uppercase;">
Email • WhatsApp • Share Links • PDF Exports • Chat Logs
</div>
</div>
</div>
</div>
""", unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs([
        "📋 Tracking Log",
        "📈 Analytics",
        "🟢 Channel Status",
    ])

    with tab1:
        _render_tracking_log()
    with tab2:
        _render_analytics()
    with tab3:
        _render_channel_status()


def _render_tracking_log():
    """Filterable log table with channel/date/recipient filters."""
    st.markdown("### 📋 Communication Log")

    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        channel_filter = st.selectbox(
            "Channel",
            ["All", "email", "whatsapp", "share_link", "pdf", "chat"],
            key="_ct_ch_filter",
        )
    with col2:
        status_filter = st.selectbox(
            "Status",
            ["All", "pending", "sent", "delivered", "read", "failed"],
            key="_ct_st_filter",
        )
    with col3:
        limit = st.selectbox("Show", [50, 100, 200, 500], key="_ct_limit")

    # Fetch data
    try:
        from database import get_comm_tracking
        ch = channel_filter if channel_filter != "All" else None
        records = get_comm_tracking(channel=ch, limit=limit)
    except Exception:
        records = []

    # Apply status filter
    if status_filter != "All":
        records = [r for r in records if r.get("delivery_status") == status_filter]

    if not records:
        st.info("No communication records found. Records appear when you share, send, or export content.")
        return

    # Display as cards
    for r in records:
        channel = r.get("channel", "?")
        status = r.get("delivery_status", "?")
        created = r.get("created_at", "")
        recipient = r.get("recipient_name", "")
        page = r.get("page_name", "")
        summary = r.get("content_summary", "")
        action = r.get("action", "")

        ch_icons = {"email": "📧", "whatsapp": "📱", "share_link": "🔗", "pdf": "📄", "chat": "💬"}
        st_colors = {"pending": "#f59e0b", "sent": "#3b82f6", "delivered": "#22c55e", "read": "#22c55e", "failed": "#ef4444"}

        ch_icon = ch_icons.get(channel, "📤")
        st_color = st_colors.get(status, "#94a3b8")

        st.markdown(f"""
<div style="background:#f8fafc; border-radius:8px; padding:10px 14px; margin-bottom:6px;
border-left:4px solid {st_color};">
<div style="display:flex; justify-content:space-between; align-items:center;">
<div>
<span style="font-size:0.9rem;">{ch_icon}</span>
<strong style="font-size:0.8rem; color:#1e293b;">{channel.title()}</strong>
<span style="color:#94a3b8; font-size:0.7rem;">• {action}</span>
</div>
<span style="font-size:0.65rem; color:#64748b;">{created}</span>
</div>
<div style="font-size:0.75rem; color:#475569; margin-top:4px;">
To: {recipient} | Page: {page}
</div>
<div style="font-size:0.7rem; color:#94a3b8; margin-top:2px;">{summary[:120]}</div>
<div style="margin-top:4px;">
<span style="background:{st_color}15; color:{st_color}; padding:2px 8px; border-radius:4px;
font-size:0.65rem; font-weight:600;">{status.upper()}</span>
</div>
</div>
""", unsafe_allow_html=True)

    # CSV export
    if records:
        import csv
        import io
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["created_at", "channel", "action", "recipient_name", "page_name", "delivery_status", "content_summary"])
        writer.writeheader()
        for r in records:
            writer.writerow({k: r.get(k, "") for k in writer.fieldnames})
        st.download_button(
            "📥 Export CSV",
            data=output.getvalue(),
            file_name=f"comm_tracking_{datetime.now(IST).strftime('%Y%m%d')}.csv",
            mime="text/csv",
            key="_ct_export_csv",
        )


def _render_analytics():
    """Charts: sends by channel, by day, delivery rate."""
    st.markdown("### 📈 Communication Analytics")

    try:
        from database import get_comm_stats, get_comm_tracking
        stats = get_comm_stats(days=30)
        records = get_comm_tracking(limit=500)
    except Exception:
        st.info("No data available for analytics yet.")
        return

    if not stats.get("total"):
        st.info("No communication data in the last 30 days. Start sharing content to see analytics.")
        return

    # KPI row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total (30d)", stats.get("total", 0))
    with col2:
        by_ch = stats.get("by_channel", {})
        st.metric("Emails", by_ch.get("email", 0))
    with col3:
        st.metric("WhatsApp", by_ch.get("whatsapp", 0))
    with col4:
        by_st = stats.get("by_status", {})
        sent = by_st.get("sent", 0) + by_st.get("delivered", 0) + by_st.get("read", 0)
        total = stats.get("total", 1)
        rate = round(sent / total * 100) if total > 0 else 0
        st.metric("Success Rate", f"{rate}%")

    # Channel breakdown chart
    by_channel = stats.get("by_channel", {})
    if by_channel:
        try:
            import plotly.graph_objects as go
            fig = go.Figure(data=[go.Bar(
                x=list(by_channel.keys()),
                y=list(by_channel.values()),
                marker_color=["#3b82f6", "#22c55e", "#f59e0b", "#ef4444", "#8b5cf6"][:len(by_channel)],
            )])
            fig.update_layout(
                title="Messages by Channel (30 days)",
                height=300,
                margin=dict(l=40, r=20, t=40, b=40),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig, use_container_width=True)
        except ImportError:
            st.caption("Plotly not available for charts.")

    # Status breakdown
    by_status = stats.get("by_status", {})
    if by_status:
        try:
            import plotly.graph_objects as go
            colors = {"pending": "#f59e0b", "sent": "#3b82f6", "delivered": "#22c55e", "read": "#10b981", "failed": "#ef4444"}
            fig2 = go.Figure(data=[go.Pie(
                labels=list(by_status.keys()),
                values=list(by_status.values()),
                marker_colors=[colors.get(s, "#94a3b8") for s in by_status.keys()],
                hole=0.4,
            )])
            fig2.update_layout(
                title="Delivery Status Distribution",
                height=300,
                margin=dict(l=20, r=20, t=40, b=20),
            )
            st.plotly_chart(fig2, use_container_width=True)
        except ImportError:
            pass

    # Daily volume
    if records:
        daily = {}
        for r in records:
            day = r.get("created_at", "")[:10]
            if day:
                daily[day] = daily.get(day, 0) + 1

        if daily:
            try:
                import plotly.graph_objects as go
                sorted_days = sorted(daily.keys())
                fig3 = go.Figure(data=[go.Scatter(
                    x=sorted_days,
                    y=[daily[d] for d in sorted_days],
                    mode="lines+markers",
                    marker_color="#3b82f6",
                    line_shape="spline",
                )])
                fig3.update_layout(
                    title="Daily Communication Volume",
                    height=250,
                    margin=dict(l=40, r=20, t=40, b=40),
                    xaxis_title="Date",
                    yaxis_title="Messages",
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                )
                st.plotly_chart(fig3, use_container_width=True)
            except ImportError:
                pass


def _render_channel_status():
    """Real-time status of all communication channels."""
    st.markdown("### 🟢 Channel Status")

    channels = [
        _get_email_status(),
        _get_whatsapp_status(),
        _get_share_links_status(),
        _get_chat_status(),
    ]

    cols = st.columns(2)
    for i, ch in enumerate(channels):
        with cols[i % 2]:
            color = "#22c55e" if ch["status"] == "active" else "#f59e0b" if ch["status"] == "configured" else "#94a3b8"
            dot = "🟢" if ch["status"] == "active" else "🟡" if ch["status"] == "configured" else "⚫"

            st.markdown(f"""
<div style="background:white; border-radius:10px; padding:16px;
border-left:4px solid {color}; box-shadow:0 2px 8px rgba(0,0,0,0.06);
margin-bottom:12px;">
<div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;">
<span style="font-size:1.2rem;">{ch['icon']}</span>
<span style="font-weight:700; font-size:0.9rem; color:#1e293b;">{ch['name']}</span>
<span style="font-size:0.7rem; color:{color}; font-weight:600;">{dot} {ch['status'].title()}</span>
</div>
<div style="font-size:0.75rem; color:#64748b;">
Queue: {ch.get('queue', 0)} pending | Sent: {ch.get('sent', 0)} (30d)
</div>
</div>
""", unsafe_allow_html=True)


def _get_email_status() -> dict:
    result = {"name": "Email", "icon": "📧", "status": "disabled", "queue": 0, "sent": 0}
    try:
        from settings_engine import get as gs
        if gs("email_enabled", False):
            result["status"] = "active"
        from database import _get_conn
        conn = _get_conn()
        try:
            result["queue"] = conn.execute("SELECT COUNT(*) as c FROM email_queue WHERE status = 'queued'").fetchone()["c"]
            result["sent"] = conn.execute("SELECT COUNT(*) as c FROM email_queue WHERE status = 'sent'").fetchone()["c"]
        finally:
            conn.close()
    except Exception:
        pass
    return result


def _get_whatsapp_status() -> dict:
    result = {"name": "WhatsApp", "icon": "📱", "status": "disabled", "queue": 0, "sent": 0}
    try:
        from settings_engine import get as gs
        if gs("whatsapp_enabled", False):
            result["status"] = "active"
        from database import _get_conn
        conn = _get_conn()
        try:
            result["queue"] = conn.execute("SELECT COUNT(*) as c FROM whatsapp_queue WHERE status = 'queued'").fetchone()["c"]
            result["sent"] = conn.execute("SELECT COUNT(*) as c FROM whatsapp_queue WHERE status = 'sent'").fetchone()["c"]
        finally:
            conn.close()
    except Exception:
        pass
    return result


def _get_share_links_status() -> dict:
    result = {"name": "Share Links", "icon": "🔗", "status": "disabled", "queue": 0, "sent": 0}
    try:
        from settings_engine import get as gs
        if gs("share_links_enabled", True):
            result["status"] = "active"
        from database import get_all_share_links
        links = get_all_share_links(active_only=True)
        result["queue"] = len(links)
        result["sent"] = sum(l.get("view_count", 0) for l in links)
    except Exception:
        pass
    return result


def _get_chat_status() -> dict:
    result = {"name": "Client Chat", "icon": "💬", "status": "disabled", "queue": 0, "sent": 0}
    try:
        from settings_engine import get as gs
        if gs("chat_enabled", False):
            result["status"] = "active"
        from database import get_chat_conversations
        convos = get_chat_conversations()
        result["queue"] = sum(c.get("unread", 0) for c in convos)
        result["sent"] = len(convos)
    except Exception:
        pass
    return result
