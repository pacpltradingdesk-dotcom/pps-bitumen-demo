"""
PPS Anantam — Graphical Message Preview Component
==================================================
Renders a pixel-perfect mock of what the recipient will see on
WhatsApp / Email / SMS. Replaces raw `st.text_area` previews that mangle
emojis and lose formatting.

Usage:
    from components.message_preview import render_msg_preview
    render_msg_preview(msg, channel="whatsapp", sender="PPS Anantam")

Channels supported: whatsapp, email, sms, generic.
Converts *text* -> <strong>, preserves line breaks, renders emojis natively
via browser fonts (Segoe UI Emoji on Windows, Apple Color Emoji on Mac).
"""
from __future__ import annotations

import datetime
import html as _html
import re as _re

import streamlit as st


_WA_HEADER = "#075E54"
_WA_BUBBLE = "#DCF8C6"
_WA_CHAT = "#ECE5DD"
_WA_TICK = (
    '<svg width="16" height="12" viewBox="0 0 16 12" style="vertical-align:middle">'
    '<path d="M1 6.5 L4 9.5 L9 3" stroke="#4FC3F7" stroke-width="1.5" fill="none"/>'
    '<path d="M6 6.5 L9 9.5 L14 3" stroke="#4FC3F7" stroke-width="1.5" fill="none"/>'
    '</svg>'
)


def _format_body(msg: str) -> str:
    """Escape HTML, convert *bold* to <strong>, preserve newlines."""
    if not msg:
        return "(empty)"
    out = _html.escape(msg, quote=False)
    out = _re.sub(r"\*([^*\n]+?)\*", r"<strong>\1</strong>", out)
    out = out.replace("\n", "<br>")
    return out


def render_msg_preview(
    msg: str,
    channel: str = "whatsapp",
    sender: str = "PPS Anantam",
    sender_num: str = "+91 77952 42424",
    email_from: str = "sales@ppsanatams.cloud",
    email_subject: str = "Bitumen Offer",
):
    """Render a graphical preview card. Channels: whatsapp, email, sms, generic."""
    body = _format_body(msg)
    now_str = datetime.datetime.now().strftime("%I:%M %p").lstrip("0").lower()

    if channel == "whatsapp":
        st.markdown(
            f'''
<div style="max-width:440px;margin:12px 0;border-radius:14px;overflow:hidden;
            box-shadow:0 4px 16px rgba(15,23,42,0.08);border:1px solid #E2E8F0;
            font-family:-apple-system,'Segoe UI Emoji','Segoe UI',Roboto,sans-serif;">
  <div style="background:{_WA_HEADER};color:#fff;padding:10px 14px;display:flex;
              align-items:center;gap:10px;">
    <div style="width:34px;height:34px;border-radius:50%;background:#25D366;
                display:flex;align-items:center;justify-content:center;
                font-weight:800;font-size:0.9rem;color:#fff;">PA</div>
    <div style="flex:1;">
      <div style="font-weight:700;font-size:0.95rem;">{_html.escape(sender)}</div>
      <div style="font-size:0.72rem;opacity:0.8;">{_html.escape(sender_num)} • online</div>
    </div>
    <div style="font-size:1.1rem;opacity:0.7;">📞</div>
  </div>
  <div style="background:{_WA_CHAT};padding:16px 12px 10px 12px;min-height:60px;">
    <div style="background:{_WA_BUBBLE};max-width:88%;margin-left:auto;
                border-radius:10px 2px 10px 10px;padding:10px 12px 6px 12px;
                font-size:0.88rem;color:#0F172A;line-height:1.55;
                box-shadow:0 1px 2px rgba(0,0,0,0.08);white-space:normal;
                word-break:break-word;">
      {body}
      <div style="text-align:right;font-size:0.68rem;color:#65748B;margin-top:4px;">
        {now_str} &nbsp;{_WA_TICK}
      </div>
    </div>
  </div>
</div>
''',
            unsafe_allow_html=True,
        )
    elif channel == "email":
        st.markdown(
            f'''
<div style="max-width:620px;margin:12px 0;border-radius:12px;overflow:hidden;
            box-shadow:0 4px 16px rgba(15,23,42,0.08);border:1px solid #E2E8F0;
            font-family:-apple-system,'Segoe UI',Roboto,sans-serif;">
  <div style="background:#F8FAFC;padding:14px 18px;border-bottom:1px solid #E2E8F0;
              font-size:0.8rem;color:#475569;">
    <div style="margin-bottom:2px;"><strong style="color:#0F172A;">From:</strong>
         {_html.escape(sender)} &lt;{_html.escape(email_from)}&gt;</div>
    <div><strong style="color:#0F172A;">Subject:</strong> {_html.escape(email_subject)}</div>
  </div>
  <div style="background:#fff;padding:22px 24px;font-size:0.93rem;color:#0F172A;
              line-height:1.65;">
    {body}
  </div>
</div>
''',
            unsafe_allow_html=True,
        )
    elif channel == "sms":
        st.markdown(
            f'''
<div style="max-width:320px;margin:12px 0;padding:12px 14px;border-radius:18px;
            background:#E5E5EA;color:#0F172A;font-size:0.88rem;line-height:1.5;
            border-radius:18px 18px 18px 4px;
            font-family:-apple-system,'SF Pro Text','Segoe UI',Roboto,sans-serif;">
  {body}
  <div style="text-align:right;font-size:0.65rem;color:#8E8E93;margin-top:4px;">
    {now_str}
  </div>
</div>
''',
            unsafe_allow_html=True,
        )
    else:  # generic
        st.markdown(
            f'''
<div style="max-width:500px;margin:12px 0;padding:16px 18px;border-radius:12px;
            background:#fff;border:1px solid #E2E8F0;
            box-shadow:0 4px 14px rgba(15,23,42,0.06);font-size:0.9rem;
            color:#0F172A;line-height:1.55;
            font-family:-apple-system,'Segoe UI',Roboto,sans-serif;">
  {body}
</div>
''',
            unsafe_allow_html=True,
        )
