"""
PPS Anantam — Universal Share Button v1.0
============================================
Drop-in share button for any dashboard section.
Uses st.popover for compact UI within any page.

Usage:
    from share_button import render_share_button
    render_share_button(
        section_id="price_chart_1",
        section_title="Brent Crude Price Trend",
    )
"""

import os
import sys
import uuid
from datetime import datetime, timezone, timedelta

sys.path.append(os.path.dirname(__file__))

IST = timezone(timedelta(hours=5, minutes=30))


def render_share_button(
    section_id: str,
    section_title: str,
    content_fn=None,
    data_dict: dict = None,
    chart_fig=None,
):
    """Render a share button that opens a popover with sharing options.

    Parameters
    ----------
    section_id : str — Unique ID for this section's share button
    section_title : str — Display name (e.g., "Brent Crude Chart")
    content_fn : callable — Returns PageContext for rich content (optional)
    data_dict : dict — Raw data for export (optional)
    chart_fig : plotly Figure — For image export (optional)
    """
    import streamlit as st

    from settings_engine import get as gs
    if not gs("share_button_enabled", True):
        return

    # Build channel options based on settings
    channels = []
    if gs("share_button_show_email", True):
        channels.append("📧 Email")
    if gs("share_button_show_whatsapp", True):
        channels.append("📱 WhatsApp")
    if gs("share_button_show_pdf", True):
        channels.append("📄 PDF")
    if gs("share_button_show_image", True) and chart_fig:
        channels.append("📸 Image")
    if gs("share_button_show_link", True):
        channels.append("🔗 Copy Link")

    if not channels:
        return

    with st.popover("📤 Share", use_container_width=False):
        st.markdown(f"**Share: {section_title}**")

        channel = st.radio(
            "Channel",
            channels,
            horizontal=True,
            key=f"_share_ch_{section_id}",
            label_visibility="collapsed",
        )

        if channel in ("📧 Email", "📱 WhatsApp"):
            _render_send_panel(section_id, section_title, channel, content_fn)
        elif channel == "📄 PDF":
            _render_pdf_panel(section_id, section_title, content_fn)
        elif channel == "📸 Image":
            _render_image_panel(section_id, chart_fig)
        elif channel == "🔗 Copy Link":
            _render_link_panel(section_id, section_title)


def _render_send_panel(section_id: str, section_title: str, channel: str, content_fn):
    """Render email/whatsapp send panel with recipient selector + AI message."""
    import streamlit as st

    ch_key = "email" if "Email" in channel else "whatsapp"

    # Recipient selector (inline)
    from recipient_selector import render_recipient_selector
    recipients = render_recipient_selector(
        f"_share_{section_id}",
        channel=ch_key,
    )

    # AI message generation
    from ai_message_engine import AIMessageEngine
    ai_eng = AIMessageEngine()
    ctx = {
        "section_title": section_title,
        "page_name": st.session_state.get("_current_page", "Dashboard"),
    }

    # Get context KPIs if available
    if content_fn:
        try:
            page_ctx = content_fn()
            if hasattr(page_ctx, "kpis"):
                ctx["kpis"] = page_ctx.kpis
            if hasattr(page_ctx, "summary_text"):
                ctx["summary"] = page_ctx.summary_text
        except Exception:
            pass

    msg = ai_eng.generate_share_message(ch_key, ctx)

    if ch_key == "email":
        subject = st.text_input(
            "Subject",
            value=msg.get("subject", f"PPS Anantam — {section_title}"),
            key=f"_share_subj_{section_id}",
        )

    edited_msg = st.text_area(
        "Message (edit before sending)",
        value=msg.get("body", ""),
        key=f"_share_msg_{section_id}",
        height=150,
    )

    if st.button("📤 Send", type="primary", key=f"_share_send_{section_id}"):
        if not recipients:
            st.error("Please select at least one recipient.")
            return

        success = _execute_send(
            ch_key, recipients, edited_msg,
            subject if ch_key == "email" else "",
            section_title,
        )
        if success:
            st.success(f"✅ Sent to {len(recipients)} recipient(s) via {ch_key.title()}")
        else:
            st.error("Failed to queue message. Check engine status.")


def _render_pdf_panel(section_id: str, section_title: str, content_fn):
    """Render PDF export panel."""
    import streamlit as st

    orientation = st.radio(
        "Orientation",
        ["Portrait", "Landscape"],
        horizontal=True,
        key=f"_share_pdf_orient_{section_id}",
    )

    if st.button("📄 Generate PDF", key=f"_share_pdf_gen_{section_id}"):
        try:
            if content_fn:
                ctx = content_fn()
                from universal_action_engine import build_pdf_report
                pdf_bytes = build_pdf_report(ctx, orientation=orientation.lower())
            else:
                from pdf_export_engine import PDFExportEngine
                engine = PDFExportEngine()
                engine.page_title = section_title
                pdf_bytes = engine.build()

            if pdf_bytes:
                now = datetime.now(IST).strftime("%Y%m%d_%H%M")
                st.download_button(
                    "📥 Download PDF",
                    data=pdf_bytes,
                    file_name=f"PPS_Anantam_{section_title.replace(' ', '_')}_{now}.pdf",
                    mime="application/pdf",
                    key=f"_share_pdf_dl_{section_id}",
                )
                _track_action("pdf", section_title)
            else:
                st.warning("PDF generation returned empty. Try from the action bar.")
        except Exception as e:
            st.error(f"PDF generation failed: {e}")


def _render_image_panel(section_id: str, chart_fig):
    """Render image export panel for Plotly charts."""
    import streamlit as st

    st.markdown("Export chart as PNG image")

    if chart_fig:
        try:
            img_bytes = chart_fig.to_image(format="png", width=1200, height=700, scale=2)
            if img_bytes:
                now = datetime.now(IST).strftime("%Y%m%d_%H%M")
                st.download_button(
                    "📥 Download PNG",
                    data=img_bytes,
                    file_name=f"chart_{section_id}_{now}.png",
                    mime="image/png",
                    key=f"_share_img_dl_{section_id}",
                )
                _track_action("image", section_id)
            else:
                st.warning("Image export returned empty.")
        except ImportError:
            st.warning("Image export requires `kaleido` package. Run: pip install kaleido")
        except Exception as e:
            st.error(f"Image export failed: {e}")
    else:
        st.info("No chart available for image export. Use browser screenshot (Ctrl+Shift+S).")


def _render_link_panel(section_id: str, section_title: str):
    """Render share link generation panel."""
    import streamlit as st

    from settings_engine import get as gs
    expiry_hours = gs("share_links_default_expiry_hours", 48)
    require_password = gs("share_links_require_password", False)

    expiry = st.selectbox(
        "Link expiry",
        ["1 hour", "24 hours", "48 hours", "7 days", "30 days"],
        index=2,
        key=f"_share_link_exp_{section_id}",
    )

    password = ""
    if require_password:
        password = st.text_input(
            "Set password (optional)",
            type="password",
            key=f"_share_link_pwd_{section_id}",
        )

    if st.button("🔗 Generate Link", key=f"_share_link_gen_{section_id}"):
        token = uuid.uuid4().hex[:12]
        expiry_map = {"1 hour": 1, "24 hours": 24, "48 hours": 48, "7 days": 168, "30 days": 720}
        hours = expiry_map.get(expiry, 48)
        expires_at = (datetime.now(IST) + timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")

        try:
            from database import insert_share_link
            insert_share_link({
                "link_token": token,
                "page_name": section_title,
                "created_by": "admin",
                "permissions": "view",
                "password_hash": password if password else None,
                "expires_at": expires_at,
                "max_views": 0,
                "view_count": 0,
                "is_active": 1,
            })
            link = f"?share={token}"
            st.code(link, language=None)
            st.caption(f"Link expires: {expires_at}")
            _track_action("share_link", section_title)
        except Exception as e:
            st.error(f"Failed to generate link: {e}")


def _execute_send(channel: str, recipients: list, message: str,
                  subject: str, section_title: str) -> bool:
    """Execute send via email or whatsapp queue."""
    try:
        from database import _insert_row, _now_ist
        now = _now_ist()

        for r in recipients:
            if channel == "email":
                email = r.get("email", "")
                if not email:
                    continue
                _insert_row("email_queue", {
                    "to_email": email,
                    "subject": subject or f"PPS Anantam — {section_title}",
                    "body_html": message.replace("\n", "<br>"),
                    "body_text": message,
                    "email_type": "share",
                    "status": "queued",
                    "created_at": now,
                })
            else:
                phone = r.get("whatsapp", "")
                if not phone:
                    continue
                _insert_row("whatsapp_queue", {
                    "to_number": phone,
                    "message_type": "session",
                    "session_text": message[:4096],
                    "status": "queued",
                    "created_at": now,
                })

        # Track
        _track_action(channel, section_title, len(recipients))
        return True
    except Exception:
        return False


def _track_action(channel: str, section_title: str, count: int = 1):
    """Log share action in comm_tracking."""
    try:
        from database import insert_comm_tracking
        insert_comm_tracking({
            "tracking_id": f"share_{uuid.uuid4().hex[:8]}",
            "channel": channel,
            "action": "shared",
            "sender": "User",
            "recipient_name": f"{count} recipient(s)",
            "page_name": section_title,
            "content_type": "section",
            "content_summary": f"Shared '{section_title}' via {channel}",
            "delivery_status": "sent",
        })
    except Exception:
        pass
