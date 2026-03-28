"""
action_bar.py — Universal 6-Button Action Bar for PPS Anantam Dashboard
========================================================================
Drop-in replacement for pdf_export_bar. Every page gets:
  Email | WhatsApp | PDF | Print | Excel/CSV | Share Link

Usage (one line in any render() function):
    from command_intel.action_bar import render_action_bar
    render_action_bar("Page Name", get_context_fn)
"""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

# Vastu colors
NAVY = "#1e3a5f"
GOLD = "#c9a84c"
GREEN = "#2d6a4f"

# ── Print CSS + JS (reused from pdf_export_bar) ──────────────────────────────

_PRINT_CSS_INJECTED_KEY = "_action_bar_print_css"

def _inject_print_css():
    if not st.session_state.get(_PRINT_CSS_INJECTED_KEY):
        try:
            from pdf_export_bar import inject_print_css
            inject_print_css()
        except ImportError:
            st.markdown("""<style>
            @media print {
              [data-testid="stSidebar"], [data-testid="stHeader"],
              [data-testid="stToolbar"], .export-bar-container,
              .stButton > button, footer { display: none !important; }
              .main .block-container { padding: 0.5rem !important; max-width: 100% !important; }
            }
            </style>""", unsafe_allow_html=True)
        st.session_state[_PRINT_CSS_INJECTED_KEY] = True


def _render_print_button():
    components.html("""
    <button onclick="window.top.print()" title="Print this page"
     style="background:#1e3a5f;color:#fff;border:none;padding:5px 10px;
            border-radius:6px;cursor:pointer;font-size:12px;font-weight:600;
            display:inline-flex;align-items:center;gap:4px;width:100%;">
     🖨 Print
    </button>""", height=36, scrolling=False)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════

def render_action_bar(
    page_name: str,
    context_fn=None,
    role: str = "admin",
):
    """
    Render the universal 6-button action bar.

    Parameters
    ----------
    page_name  : str      — current page name
    context_fn : callable — zero-arg fn returning PageContext (lazy). None = generic.
    role       : str      — current user role (admin/manager/viewer)
    """
    _inject_print_css()

    # Check settings
    try:
        from settings_engine import get as gs
        if not gs("action_bar_enabled", True):
            return
        show_email = gs("action_bar_show_email", True)
        show_wa = gs("action_bar_show_whatsapp", True)
        show_pdf = gs("action_bar_show_pdf", True)
        show_print = gs("action_bar_show_print", True)
        show_excel = gs("action_bar_show_excel", True)
        show_share = gs("action_bar_show_share", True)
    except Exception:
        show_email = show_wa = show_pdf = show_print = show_excel = show_share = True

    # Role-based: viewer can't send
    can_send = role in ("admin", "manager")

    # Session key for this page's action bar state
    sk = f"_actbar_{page_name.replace(' ', '_').replace('/', '-')[:30]}"

    # Helper to get context lazily
    def _get_ctx():
        from universal_action_engine import PageContext, build_generic_context
        if context_fn is not None:
            try:
                c = context_fn()
                if isinstance(c, PageContext):
                    return c
            except Exception:
                pass
        return build_generic_context(page_name)

    # ── Button Row ────────────────────────────────────────────────────────
    st.markdown(
        '<div class="export-bar-container" style="display:flex;justify-content:flex-end;'
        'gap:6px;margin-bottom:6px;flex-wrap:wrap;">',
        unsafe_allow_html=True,
    )

    # Build columns based on which buttons are visible
    buttons = []
    if can_send and show_email:
        buttons.append("email")
    if can_send and show_wa:
        buttons.append("whatsapp")
    if show_pdf:
        buttons.append("pdf")
    if show_print:
        buttons.append("print")
    if show_excel:
        buttons.append("excel")
    if show_share:
        buttons.append("share")
    # Image export (if share_button_show_image is enabled)
    try:
        from settings_engine import get as _gs
        if _gs("share_button_show_image", True):
            buttons.append("image")
    except Exception:
        pass

    if not buttons:
        st.markdown("</div>", unsafe_allow_html=True)
        return

    # Spacer + buttons
    n_btn = len(buttons)
    col_weights = [max(8 - n_btn, 2)] + [1] * n_btn
    cols = st.columns(col_weights)

    btn_map = {}
    col_idx = 1
    for btn_name in buttons:
        with cols[col_idx]:
            if btn_name == "email":
                btn_map["email"] = st.button("📩 Email", key=f"{sk}_email", use_container_width=True)
            elif btn_name == "whatsapp":
                btn_map["whatsapp"] = st.button("💬 WhatsApp", key=f"{sk}_wa", use_container_width=True)
            elif btn_name == "pdf":
                btn_map["pdf"] = st.button("📄 PDF", key=f"{sk}_pdf", use_container_width=True)
            elif btn_name == "print":
                _render_print_button()
            elif btn_name == "excel":
                btn_map["excel"] = st.button("📊 Excel", key=f"{sk}_excel", use_container_width=True)
            elif btn_name == "share":
                btn_map["share"] = st.button("🔗 Share", key=f"{sk}_share", use_container_width=True)
            elif btn_name == "image":
                btn_map["image"] = st.button("📸 Image", key=f"{sk}_image", use_container_width=True)
        col_idx += 1

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Handle Button Actions ─────────────────────────────────────────────

    # EMAIL
    if btn_map.get("email"):
        _toggle_panel(sk, "email")
    if _is_panel_open(sk, "email"):
        _render_email_panel(sk, page_name, _get_ctx)

    # WHATSAPP
    if btn_map.get("whatsapp"):
        _toggle_panel(sk, "whatsapp")
    if _is_panel_open(sk, "whatsapp"):
        _render_whatsapp_panel(sk, page_name, _get_ctx)

    # PDF
    if btn_map.get("pdf"):
        _toggle_panel(sk, "pdf")
    if _is_panel_open(sk, "pdf"):
        _render_pdf_panel(sk, page_name, _get_ctx)

    # EXCEL/CSV
    if btn_map.get("excel"):
        _toggle_panel(sk, "excel")
    if _is_panel_open(sk, "excel"):
        _render_excel_panel(sk, page_name, _get_ctx)

    # SHARE (enhanced with recipient selector + AI messages)
    if btn_map.get("share"):
        _toggle_panel(sk, "share")
    if _is_panel_open(sk, "share"):
        _render_share_panel(sk, page_name, _get_ctx)

    # IMAGE
    if btn_map.get("image"):
        _toggle_panel(sk, "image")
    if _is_panel_open(sk, "image"):
        _render_image_panel(sk, page_name, _get_ctx)


# ── Panel State Helpers ───────────────────────────────────────────────────────

def _toggle_panel(sk: str, panel: str):
    key = f"{sk}_panel"
    current = st.session_state.get(key, "")
    st.session_state[key] = "" if current == panel else panel

def _is_panel_open(sk: str, panel: str) -> bool:
    return st.session_state.get(f"{sk}_panel", "") == panel


# ── Email Send Panel ─────────────────────────────────────────────────────────

def _render_email_panel(sk: str, page_name: str, get_ctx_fn):
    with st.container():
        st.markdown(
            f'<div style="background:#0d1b2e;border:1px solid {NAVY};border-radius:8px;'
            f'padding:12px 16px;margin-bottom:8px;">',
            unsafe_allow_html=True,
        )
        st.markdown("**📩 Send Email Report**")

        # Recipient mode
        mode = st.radio(
            "Send to",
            ["Custom Email", "Recipient List"],
            horizontal=True,
            key=f"{sk}_email_mode",
        )

        if mode == "Custom Email":
            to_emails = st.text_input(
                "Email(s) — comma-separated",
                key=f"{sk}_email_to",
                placeholder="director@company.com, team@company.com",
            )
            recipients = [e.strip() for e in to_emails.split(",") if e.strip()] if to_emails else []
        else:
            # Load recipient lists
            try:
                from database import get_recipient_lists
                r_lists = get_recipient_lists("email")
                list_names = [rl["list_name"] for rl in r_lists] if r_lists else ["(No lists configured)"]
            except Exception:
                list_names = ["(No lists configured)"]
            selected_list = st.selectbox("Recipient List", list_names, key=f"{sk}_email_list")
            if selected_list and not selected_list.startswith("("):
                from universal_action_engine import resolve_recipients
                recipients = resolve_recipients(selected_list, "email")
                if recipients:
                    st.caption(f"Will send to: {', '.join(recipients)}")
                else:
                    st.caption("No email addresses in this list.")
                    recipients = []
            else:
                recipients = []

        cc = st.text_input("CC (optional)", key=f"{sk}_email_cc")

        ec1, ec2 = st.columns(2)
        with ec1:
            if st.button("Send Email", type="primary", key=f"{sk}_email_send"):
                if recipients:
                    ctx = get_ctx_fn()
                    from universal_action_engine import send_email_report
                    result = send_email_report(ctx, recipients, cc=cc)
                    if result["queued"] > 0:
                        st.success(f"Queued {result['queued']} email(s). Will be sent in next processing cycle.")
                    if result["failed"] > 0:
                        st.warning(f"{result['failed']} email(s) failed to queue.")
                else:
                    st.warning("Enter at least one recipient email.")
        with ec2:
            if st.button("Cancel", key=f"{sk}_email_cancel"):
                st.session_state[f"{sk}_panel"] = ""
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)


# ── WhatsApp Send Panel ──────────────────────────────────────────────────────

def _render_whatsapp_panel(sk: str, page_name: str, get_ctx_fn):
    with st.container():
        st.markdown(
            f'<div style="background:#0d1b2e;border:1px solid {GREEN};border-radius:8px;'
            f'padding:12px 16px;margin-bottom:8px;">',
            unsafe_allow_html=True,
        )
        st.markdown("**💬 Send WhatsApp Report**")

        phone_input = st.text_input(
            "Phone Number(s) — comma-separated (Indian mobile)",
            key=f"{sk}_wa_to",
            placeholder="9876543210, 9123456789",
        )
        phones = [p.strip() for p in phone_input.split(",") if p.strip()] if phone_input else []

        # Preview
        if st.checkbox("Preview message", key=f"{sk}_wa_preview"):
            ctx = get_ctx_fn()
            from universal_action_engine import build_whatsapp_summary
            preview = build_whatsapp_summary(ctx)
            st.text_area("Preview", value=preview, height=200, disabled=True, key=f"{sk}_wa_prev_txt")

        wc1, wc2 = st.columns(2)
        with wc1:
            if st.button("Send WhatsApp", type="primary", key=f"{sk}_wa_send"):
                if phones:
                    ctx = get_ctx_fn()
                    from universal_action_engine import send_whatsapp_report
                    result = send_whatsapp_report(ctx, phones)
                    if result["queued"] > 0:
                        st.success(f"Queued {result['queued']} WhatsApp message(s).")
                    if result["failed"] > 0:
                        st.warning(f"{result['failed']} message(s) failed to queue.")
                else:
                    st.warning("Enter at least one phone number.")
        with wc2:
            if st.button("Cancel", key=f"{sk}_wa_cancel"):
                st.session_state[f"{sk}_panel"] = ""
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)


# ── PDF Export Panel ──────────────────────────────────────────────────────────

def _render_pdf_panel(sk: str, page_name: str, get_ctx_fn):
    with st.container():
        st.markdown(
            f'<div style="background:#0d1b2e;border:1px solid #2563eb;border-radius:8px;'
            f'padding:12px 16px;margin-bottom:8px;">',
            unsafe_allow_html=True,
        )
        st.markdown("**📄 PDF Export**")

        orientation = st.selectbox(
            "Layout", ["Portrait", "Landscape"], key=f"{sk}_pdf_orient"
        )

        pc1, pc2 = st.columns(2)
        with pc1:
            if st.button("Generate PDF", type="primary", key=f"{sk}_pdf_gen"):
                with st.spinner("Building PDF..."):
                    try:
                        ctx = get_ctx_fn()
                        from universal_action_engine import build_pdf_report, _now_ist_filename
                        orient = "landscape" if orientation == "Landscape" else "portrait"
                        pdf_bytes = build_pdf_report(ctx, orientation=orient)
                        st.session_state[f"{sk}_pdf_bytes"] = pdf_bytes
                        st.success(f"PDF ready — {len(pdf_bytes) // 1024} KB")
                    except Exception as e:
                        st.error(f"PDF generation failed: {e}")

        pdf_bytes = st.session_state.get(f"{sk}_pdf_bytes")
        if pdf_bytes:
            safe_name = page_name.replace(" ", "_").replace("/", "-")[:40]
            from universal_action_engine import _now_ist_filename
            fname = f"{safe_name}_{_now_ist_filename()}.pdf"
            with pc2:
                st.download_button(
                    "📥 Download PDF",
                    data=pdf_bytes,
                    file_name=fname,
                    mime="application/pdf",
                    key=f"{sk}_pdf_dl",
                    use_container_width=True,
                )

        st.markdown("</div>", unsafe_allow_html=True)


# ── Excel/CSV Export Panel ────────────────────────────────────────────────────

def _render_excel_panel(sk: str, page_name: str, get_ctx_fn):
    with st.container():
        st.markdown(
            f'<div style="background:#0d1b2e;border:1px solid {GOLD};border-radius:8px;'
            f'padding:12px 16px;margin-bottom:8px;">',
            unsafe_allow_html=True,
        )
        st.markdown("**📊 Excel / CSV Export**")

        fmt = st.radio("Format", ["Excel (.xlsx)", "CSV (.csv)"], horizontal=True, key=f"{sk}_excel_fmt")

        if st.button("Export", type="primary", key=f"{sk}_excel_gen"):
            ctx = get_ctx_fn()
            safe_name = page_name.replace(" ", "_").replace("/", "-")[:40]
            from universal_action_engine import _now_ist_filename

            if "xlsx" in fmt:
                from universal_action_engine import build_excel_export
                data = build_excel_export(ctx)
                fname = f"{safe_name}_{_now_ist_filename()}.xlsx"
                mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            else:
                from universal_action_engine import build_csv_export
                data = build_csv_export(ctx)
                fname = f"{safe_name}_{_now_ist_filename()}.csv"
                mime = "text/csv"

            st.session_state[f"{sk}_export_data"] = data
            st.session_state[f"{sk}_export_fname"] = fname
            st.session_state[f"{sk}_export_mime"] = mime

        export_data = st.session_state.get(f"{sk}_export_data")
        if export_data:
            st.download_button(
                f"📥 Download {st.session_state.get(f'{sk}_export_fname', 'export')}",
                data=export_data,
                file_name=st.session_state.get(f"{sk}_export_fname", "export"),
                mime=st.session_state.get(f"{sk}_export_mime", "application/octet-stream"),
                key=f"{sk}_export_dl",
                use_container_width=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)


# ── Share Panel (Enhanced with Recipient Selector + AI Messages) ────────────

def _render_share_panel(sk: str, page_name: str, get_ctx_fn):
    with st.container():
        st.markdown(
            f'<div style="background:#0d1b2e;border:1px solid #8b5cf6;border-radius:8px;'
            f'padding:12px 16px;margin-bottom:8px;">',
            unsafe_allow_html=True,
        )
        st.markdown("**📤 Share Report**")

        channel = st.radio(
            "Share via",
            ["📧 Email", "📱 WhatsApp", "🔗 Link"],
            horizontal=True,
            key=f"{sk}_share_ch",
        )

        if channel == "🔗 Link":
            ctx = get_ctx_fn()
            from universal_action_engine import generate_share_link
            link = generate_share_link(ctx)
            st.code(link, language=None)
            st.caption("Link valid for current session. For persistent links, use Integrations → Dashboard Sharing.")
        else:
            ch_key = "email" if "Email" in channel else "whatsapp"
            try:
                from recipient_selector import render_recipient_selector
                recipients = render_recipient_selector(f"{sk}_share", channel=ch_key)
            except ImportError:
                recipients = []
                st.caption("Recipient selector not available.")

            try:
                from ai_message_engine import AIMessageEngine
                ai_eng = AIMessageEngine()
                msg = ai_eng.generate_share_message(
                    ch_key,
                    {"section_title": page_name, "page_name": page_name},
                )
                edited = st.text_area("Message", value=msg.get("body", ""), key=f"{sk}_share_msg", height=120)
            except ImportError:
                edited = st.text_area("Message", value=f"Sharing report: {page_name}", key=f"{sk}_share_msg", height=120)

            sc1, sc2 = st.columns(2)
            with sc1:
                if st.button("📤 Send", type="primary", key=f"{sk}_share_send"):
                    if recipients:
                        try:
                            from share_button import _execute_send
                            subject = f"PPS Anantam — {page_name}"
                            _execute_send(ch_key, recipients, edited, subject, page_name)
                            st.success(f"Sent to {len(recipients)} recipient(s)!")
                        except Exception as _e:
                            st.error(f"Send failed: {_e}")
                    else:
                        st.warning("Select at least one recipient.")
            with sc2:
                if st.button("Cancel", key=f"{sk}_share_cancel"):
                    st.session_state[f"{sk}_panel"] = ""
                    st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)


# ── Image Export Panel ──────────────────────────────────────────────────────

def _render_image_panel(sk: str, page_name: str, get_ctx_fn):
    with st.container():
        st.markdown(
            f'<div style="background:#0d1b2e;border:1px solid #ec4899;border-radius:8px;'
            f'padding:12px 16px;margin-bottom:8px;">',
            unsafe_allow_html=True,
        )
        st.markdown("**📸 Image Export**")

        ctx = None
        try:
            ctx = get_ctx_fn()
        except Exception:
            pass

        has_charts = ctx and hasattr(ctx, "chart_figures") and ctx.chart_figures
        if has_charts:
            for i, cf in enumerate(ctx.chart_figures):
                fig = cf.get("fig") if isinstance(cf, dict) else cf
                caption = cf.get("caption", f"Chart {i + 1}") if isinstance(cf, dict) else f"Chart {i + 1}"
                if fig:
                    try:
                        img_bytes = fig.to_image(format="png", width=1200, height=700, scale=2)
                        if img_bytes:
                            from datetime import datetime, timezone, timedelta
                            _ist = timezone(timedelta(hours=5, minutes=30))
                            now = datetime.now(_ist).strftime("%Y%m%d_%H%M")
                            st.download_button(
                                f"📥 {caption}",
                                data=img_bytes,
                                file_name=f"{caption.replace(' ', '_')}_{now}.png",
                                mime="image/png",
                                key=f"{sk}_img_{i}",
                                use_container_width=True,
                            )
                    except ImportError:
                        st.warning("Image export requires `kaleido`. Run: pip install kaleido")
                    except Exception as _e:
                        st.caption(f"Chart {i + 1} export failed: {_e}")
        else:
            st.info("No charts on this page, or context not available. Use browser screenshot (Ctrl+Shift+S).")

        if st.button("Close", key=f"{sk}_image_cancel"):
            st.session_state[f"{sk}_panel"] = ""
            st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)
