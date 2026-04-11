"""
PPS Anantam — Shareable Links Engine
======================================
Generate, manage, and serve shareable link tokens for quotes, reports, and showcases.
"""
import uuid
import json
import datetime
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bitumen_dashboard.db")


def _get_conn():
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def create_share_link(page_name, content_json=None, created_by="system", expiry_hours=48):
    """Create a new shareable link and return the token."""
    token = uuid.uuid4().hex[:12]
    expires_at = (datetime.datetime.now() + datetime.timedelta(hours=expiry_hours)).strftime("%Y-%m-%d %H:%M:%S")

    conn = _get_conn()
    try:
        conn.execute("""
            INSERT INTO share_links (link_token, page_name, filters_json, created_by, expires_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (token, page_name, json.dumps(content_json) if content_json else None, created_by, expires_at, _now()))
        conn.commit()
    finally:
        conn.close()

    return token


def get_share_link(token):
    """Retrieve a share link by token. Returns dict or None."""
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM share_links WHERE link_token = ?", (token,)).fetchone()
        if not row:
            return None

        link = dict(row)

        # Check expiry
        if link.get("expires_at"):
            try:
                exp = datetime.datetime.strptime(link["expires_at"], "%Y-%m-%d %H:%M:%S")
                if datetime.datetime.now() > exp:
                    conn.execute("UPDATE share_links SET is_active = 0 WHERE link_token = ?", (token,))
                    conn.commit()
                    return None
            except Exception:
                pass

        # Check if active
        if not link.get("is_active"):
            return None

        # Check max views
        if link.get("max_views") and link.get("max_views") > 0:
            if link.get("view_count", 0) >= link["max_views"]:
                return None

        # Increment view count
        conn.execute("""
            UPDATE share_links SET view_count = view_count + 1, last_accessed = ? WHERE link_token = ?
        """, (_now(), token))
        conn.commit()

        return link
    finally:
        conn.close()


def get_active_links(created_by=None):
    """Get all active share links, optionally filtered by creator."""
    conn = _get_conn()
    try:
        if created_by:
            rows = conn.execute(
                "SELECT * FROM share_links WHERE is_active = 1 AND created_by = ? ORDER BY created_at DESC",
                (created_by,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM share_links WHERE is_active = 1 ORDER BY created_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def deactivate_link(token):
    """Deactivate a share link."""
    conn = _get_conn()
    try:
        conn.execute("UPDATE share_links SET is_active = 0 WHERE link_token = ?", (token,))
        conn.commit()
    finally:
        conn.close()


def cleanup_expired():
    """Deactivate all expired links."""
    conn = _get_conn()
    try:
        conn.execute("""
            UPDATE share_links SET is_active = 0
            WHERE is_active = 1 AND expires_at < ?
        """, (_now(),))
        conn.commit()
    finally:
        conn.close()


def generate_share_url(token, host=None, port=None):
    """Generate the full shareable URL. Auto-detects Streamlit Cloud URL."""
    if host is None:
        try:
            import streamlit as st
            # On Streamlit Cloud, use the app URL
            cloud_url = os.environ.get("STREAMLIT_SERVER_BASE_URL", "")
            if cloud_url:
                return f"{cloud_url}/share/{token}"
            # Try to get from Streamlit config
            app_url = st.get_option("browser.serverAddress") or "localhost"
            app_port = st.get_option("browser.serverPort") or 8501
            return f"http://{app_url}:{app_port}/?share={token}"
        except Exception:
            pass
    host = host or "localhost"
    port = port or 8501
    return f"http://{host}:{port}/?share={token}"


def render_shared_content(link_data):
    """Generate HTML content for a shared link."""
    page = link_data.get("page_name", "")
    filters = json.loads(link_data.get("filters_json", "{}") or "{}")
    created = link_data.get("created_at", "")
    views = link_data.get("view_count", 0)

    # Base HTML template
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PPS Anantams — {page}</title>
    <meta property="og:title" content="PPS Anantams — {page}">
    <meta property="og:description" content="Shared content from PPS Anantams Bitumen Dashboard">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: Inter, -apple-system, sans-serif; background: #F8FAFC; color: #1E293B; }}
        .container {{ max-width: 800px; margin: 0 auto; padding: 32px 24px; }}
        .header {{ background: linear-gradient(135deg, #1E1B4B, #4F46E5); color: white;
                   padding: 32px; border-radius: 16px; margin-bottom: 24px; text-align: center; }}
        .header h1 {{ font-size: 1.5rem; font-weight: 800; }}
        .header p {{ font-size: 0.85rem; color: #C7D2FE; margin-top: 8px; }}
        .card {{ background: white; border: 1px solid #E2E8F0; border-radius: 12px;
                 padding: 24px; margin-bottom: 16px; }}
        .card h2 {{ font-size: 1.1rem; font-weight: 700; color: #4F46E5; margin-bottom: 12px; }}
        .meta {{ font-size: 0.75rem; color: #94A3B8; text-align: center; margin-top: 24px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th {{ background: #F1F5F9; padding: 10px; text-align: left; font-weight: 700; font-size: 0.85rem; }}
        td {{ padding: 10px; border-bottom: 1px solid #F1F5F9; font-size: 0.85rem; }}
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>PPS Anantams Corporation</h1>
        <p>{page}</p>
    </div>
    <div class="card">
        <h2>{page}</h2>
"""

    # Add content based on filters
    if filters:
        html += "        <table>"
        for key, value in filters.items():
            label = key.replace("_", " ").title()
            html += f"            <tr><th>{label}</th><td>{value}</td></tr>"
        html += "        </table>"
    else:
        html += "        <p>This content was shared from the PPS Anantams Dashboard.</p>"

    html += f"""
    </div>
    <div class="meta">
        Shared on {created} | Views: {views} | PPS Anantams Corporation Pvt Ltd, Vadodara
    </div>
</div>
</body>
</html>"""

    return html
