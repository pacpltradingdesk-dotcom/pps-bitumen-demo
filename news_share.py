"""
news_share.py — reusable "share news everywhere" helpers.
=========================================================
One place to build share text + multi-channel deep links for news, so EVERY
surface that shows news (News Intelligence page, Command Center, etc.) can offer
the same "share one article" and "share ALL news" (digest) experience.

No auto-send: every channel is an OS/web deep link the user confirms in their own
WhatsApp / Telegram / email / browser. Safe, zero-config, works offline.

Public API:
    build_article_message(article)            -> str
    build_digest_message(articles, title, n)   -> str
    render_article_share(article, key_suffix)  -> st.popover with channel links
    render_digest_share(articles, title, key_suffix, n) -> "Share ALL" popover
"""
from __future__ import annotations

import urllib.parse

import streamlit as st

BRAND = "\U0001f4f0 PPS ANANTAM"
SIGNOFF = "— via PPS Bitumen Dashboard"
_LINE = "━" * 14


def _impact_label(score: int) -> str:
    if score >= 80:
        return "\U0001f534 Breaking"
    if score >= 60:
        return "\U0001f7e0 High"
    if score >= 40:
        return "\U0001f7e1 Medium"
    return "⚫ Low"


# ── message builders ──────────────────────────────────────────────────────────

def build_article_message(a: dict) -> str:
    """Formatted share text for a single article."""
    score    = a.get("impact_score", 0)
    headline = (a.get("headline", "") or "").strip()
    summary  = (a.get("summary", "") or "").strip()
    src      = a.get("source_name", "")
    url      = (a.get("source_url", "") or "").strip()
    pub      = a.get("published_at_ist", "")

    parts = [
        f"{BRAND} — News Alert",
        f"{_impact_label(score)} {score}" + (f" | {src}" if src else ""),
        _LINE,
        headline,
    ]
    if summary:
        parts += ["", summary[:320]]
    if url:
        parts += ["", f"\U0001f517 {url}"]
    if pub:
        parts.append(f"\U0001f550 {pub}")
    parts.append(SIGNOFF)
    return "\n".join(parts)


def build_digest_message(articles: list[dict], title: str = "News Digest",
                         limit: int = 15) -> str:
    """Bundle many articles into ONE shareable digest (share-all)."""
    arts = [a for a in (articles or []) if a.get("headline")][:limit]
    header = f"{BRAND} — {title}"
    if not arts:
        return f"{header}\n{_LINE}\n(No news to share right now)\n{SIGNOFF}"

    lines = [header, f"{len(arts)} top stories", _LINE]
    for i, a in enumerate(arts, 1):
        score = a.get("impact_score", 0)
        hl    = (a.get("headline", "") or "").strip()
        src   = a.get("source_name", "")
        url   = (a.get("source_url", "") or "").strip()
        lines.append(f"{i}. [{score}] {hl}" + (f" — {src}" if src else ""))
        if url:
            lines.append(f"   {url}")
    lines += [_LINE, SIGNOFF]
    return "\n".join(lines)


# ── channel deep links ──────────────────────────────────────────────────────────

def _links(message: str, url: str = "", subject: str = "PPS ANANTAM — News"):
    enc_msg = urllib.parse.quote(message)
    enc_url = urllib.parse.quote(url or "https://ppsanantams.com", safe="")
    enc_sub = urllib.parse.quote(subject[:120])
    return {
        "WhatsApp": ("\U0001f4f1 WhatsApp", f"https://wa.me/?text={enc_msg}"),
        "Telegram": ("✈️ Telegram",          f"https://t.me/share/url?url={enc_url}&text={enc_msg}"),
        "Email":    ("✉️ Email",             f"mailto:?subject={enc_sub}&body={enc_msg}"),
        "Twitter":  ("\U0001f426 X / Twitter", f"https://twitter.com/intent/tweet?text={enc_msg}"),
        "LinkedIn": ("\U0001f4bc LinkedIn",   f"https://www.linkedin.com/sharing/share-offsite/?url={enc_url}"),
    }


def _render_channels(message: str, url: str, subject: str, key_suffix: str,
                     show_source: bool = True):
    links = _links(message, url, subject)
    for _name, (label, href) in links.items():
        st.link_button(label, href, use_container_width=True)
    if show_source and url:
        st.link_button("\U0001f517 Open Source", url, use_container_width=True)
    st.caption("Or copy the text:")
    st.code(message, language=None)


# ── popover renderers ───────────────────────────────────────────────────────────

def render_article_share(a: dict, key_suffix: str = ""):
    """Per-article 'Share' popover."""
    msg      = build_article_message(a)
    url      = (a.get("source_url", "") or "").strip()
    headline = (a.get("headline", "") or "PPS News").strip()
    with st.popover("\U0001f4e4 Share", use_container_width=True):
        st.markdown("**Share this news everywhere**")
        _render_channels(msg, url, f"PPS ANANTAM — {headline}", key_suffix)


def render_digest_share(articles: list[dict], title: str = "News Digest",
                        key_suffix: str = "", limit: int = 15,
                        label: str = "\U0001f4e4 Share ALL News"):
    """'Share ALL' digest popover — bundles many articles into one message."""
    msg = build_digest_message(articles, title, limit)
    n = min(len([a for a in (articles or []) if a.get("headline")]), limit)
    with st.popover(label, use_container_width=True):
        st.markdown(f"**Share {n} stories everywhere**")
        _render_channels(msg, "", f"PPS ANANTAM — {title}", key_suffix,
                         show_source=False)
