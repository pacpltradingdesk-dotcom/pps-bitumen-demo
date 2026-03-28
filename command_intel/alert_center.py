"""
PPS Anantam — Alert Center v2.0
================================
P0/P1/P2 priority-based intelligent alert system.
Smart triggers, context-aware dedup, snooze, escalation.

P0 — Immediate action required (red)
P1 — Action within 24h (orange)
P2 — Informational (blue)
"""
import streamlit as st
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

try:
    from ui_badges import display_badge
except ImportError:
    def display_badge(*a, **kw):
        pass

import json
import datetime
import pytz

IST = pytz.timezone("Asia/Kolkata")
BASE_DIR = os.path.dirname(os.path.dirname(__file__))


def _now():
    return datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")


def render():
    """Render the Alert Center page."""
    display_badge("real-time")

    st.markdown("""
    <div style="background:linear-gradient(135deg,#b85c38,#c9a84c);color:white;
                padding:15px 20px;border-radius:10px;margin-bottom:15px;">
      <div style="font-size:1.2rem;font-weight:700;">Alert Center</div>
      <div style="font-size:0.8rem;opacity:0.85;">Intelligent alerts with priority-based actions</div>
    </div>
    """, unsafe_allow_html=True)

    # Action buttons
    col_scan, col_refresh = st.columns([1, 1])
    with col_scan:
        if st.button("Run Alert Scan", use_container_width=True, type="primary"):
            count = run_alert_scan()
            st.success(f"Scan complete: {count} new alerts generated")
            st.rerun()
    with col_refresh:
        if st.button("Refresh View", use_container_width=True):
            st.rerun()

    # Tabs for alert categories
    tab_all, tab_p0, tab_p1, tab_p2, tab_history = st.tabs([
        "All Active", "P0 Critical", "P1 Important", "P2 Info", "History"
    ])

    try:
        from database import get_alerts, update_alert_status
    except ImportError:
        st.error("Database module not available")
        return

    with tab_all:
        _render_alerts(get_alerts(status="new", limit=50), "all")

    with tab_p0:
        _render_alerts(get_alerts(status="new", priority="P0", limit=20), "p0")

    with tab_p1:
        _render_alerts(get_alerts(status="new", priority="P1", limit=30), "p1")

    with tab_p2:
        _render_alerts(get_alerts(status="new", priority="P2", limit=30), "p2")

    with tab_history:
        st.markdown("##### Resolved Alerts")
        acted = get_alerts(status="acted", limit=50)
        snoozed = get_alerts(status="snoozed", limit=20)
        all_hist = acted + snoozed
        all_hist.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        if all_hist:
            for a in all_hist[:30]:
                st.markdown(
                    f"<div style='padding:4px 8px;margin:2px 0;font-size:0.85rem;'>"
                    f"<span style='color:#888;'>[{a.get('priority', '')}]</span> "
                    f"{a.get('title', '')} — "
                    f"<span style='color:#2d6a4f;'>{a.get('status', '')}</span> "
                    f"at {a.get('acted_at', a.get('snoozed_until', ''))}"
                    f"</div>", unsafe_allow_html=True)
        else:
            st.info("No alert history yet")


def _render_alerts(alerts: list, tab_key: str):
    """Render a list of alerts with action buttons."""
    if not alerts:
        st.info("No alerts in this category")
        return

    from database import update_alert_status

    priority_colors = {"P0": "#b85c38", "P1": "#c9a84c", "P2": "#1e3a5f"}

    for i, alert in enumerate(alerts):
        priority = alert.get("priority", "P2")
        color = priority_colors.get(priority, "#1e3a5f")

        st.markdown(f"""
        <div style="padding:12px 15px;margin:6px 0;border-left:4px solid {color};
                    background:{color}10;border-radius:0 8px 8px 0;">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <div>
              <span style="background:{color};color:white;padding:2px 8px;border-radius:4px;
                           font-size:0.75rem;font-weight:700;">{priority}</span>
              <span style="font-weight:600;margin-left:8px;">{alert.get('title', '')}</span>
            </div>
            <span style="font-size:0.75rem;color:#888;">{alert.get('created_at', '')[:16]}</span>
          </div>
          <div style="margin-top:6px;font-size:0.9rem;color:#444;">
            {alert.get('description', '')}
          </div>
        </div>
        """, unsafe_allow_html=True)

        # Recommended action
        rec = alert.get("recommended_action", "")
        if rec:
            st.caption(f"Recommended: {rec}")

        # Action buttons
        bcol1, bcol2, bcol3 = st.columns(3)
        with bcol1:
            if st.button("Mark Acted", key=f"act_{tab_key}_{alert.get('id', i)}",
                          use_container_width=True):
                update_alert_status(alert["id"], "acted", acted_at=_now())
                st.rerun()
        with bcol2:
            if st.button("Snooze 4h", key=f"snz_{tab_key}_{alert.get('id', i)}",
                          use_container_width=True):
                snooze_until = (datetime.datetime.now(IST) + datetime.timedelta(hours=4)
                                ).strftime("%Y-%m-%d %H:%M:%S")
                update_alert_status(alert["id"], "snoozed", snoozed_until=snooze_until)
                st.rerun()
        with bcol3:
            if st.button("Dismiss", key=f"dis_{tab_key}_{alert.get('id', i)}",
                          use_container_width=True):
                update_alert_status(alert["id"], "expired")
                st.rerun()

    st.caption(f"Showing {len(alerts)} alert(s)")


# ─── Alert Generation Engine ────────────────────────────────────────────────

def run_alert_scan() -> int:
    """Scan all data sources and generate smart alerts. Returns count of new alerts."""
    from database import insert_alert, get_alerts
    from pathlib import Path
    base = Path(BASE_DIR)
    count = 0

    # Get existing alerts to avoid duplicates
    existing = get_alerts(limit=200)
    existing_titles = {a.get("title", "") for a in existing
                       if a.get("status") in ("new", "snoozed")}

    def _add_alert(alert_type, priority, title, description,
                   recommended_action="", data_dict=None):
        nonlocal count
        if title in existing_titles:
            return
        insert_alert({
            "alert_type": alert_type,
            "priority": priority,
            "title": title,
            "description": description,
            "recommended_action": recommended_action,
            "data": json.dumps(data_dict) if data_dict else None,
        })
        count += 1

    # 1. Crude price movement
    try:
        crude_data = json.loads((base / "tbl_crude_prices.json").read_text(encoding="utf-8"))
        brent = [r for r in crude_data if r.get("benchmark") == "Brent" and r.get("price")]
        if len(brent) >= 2:
            latest = brent[-1]["price"]
            prev = brent[-2]["price"]
            if prev > 0:
                change = (latest - prev) / prev * 100
                if abs(change) > 5:
                    _add_alert("price_spike", "P0",
                               f"Brent moved {change:+.1f}% (${prev:.1f} -> ${latest:.1f})",
                               "Significant crude price movement detected. Review all open quotes.",
                               "Review pending quotes and update pricing")
                elif abs(change) > 3:
                    _add_alert("price_move", "P1",
                               f"Brent moved {change:+.1f}%",
                               f"Brent at ${latest:.2f}/bbl",
                               "Monitor closely, may need price adjustment")
    except Exception:
        pass

    # 2. FX movement
    try:
        fx_data = json.loads((base / "tbl_fx_rates.json").read_text(encoding="utf-8"))
        usd_inr = [r for r in fx_data if "USD" in str(r.get("from_currency", "")) and r.get("rate")]
        if len(usd_inr) >= 2:
            latest_fx = usd_inr[-1]["rate"]
            prev_fx = usd_inr[-2]["rate"]
            if prev_fx > 0:
                fx_change = (latest_fx - prev_fx) / prev_fx * 100
                if abs(fx_change) > 1:
                    direction = "weakened" if fx_change > 0 else "strengthened"
                    _add_alert("fx_move", "P1",
                               f"INR {direction} {abs(fx_change):.1f}% against USD",
                               f"USD/INR now at {latest_fx:.2f}. Import costs affected.",
                               "Review international procurement pricing")
    except Exception:
        pass

    # 3. Payment overdue
    try:
        from database import get_all_deals
        deals = get_all_deals()
        today = datetime.datetime.now(IST).strftime("%Y-%m-%d")
        for d in deals:
            if d.get("status") != "active":
                continue
            outstanding = (d.get("total_value_inr") or 0) - (d.get("payment_received_inr") or 0)
            if outstanding <= 0:
                continue
            payment_date = d.get("payment_date") or d.get("delivery_date")
            if payment_date and payment_date < today:
                try:
                    delta = (datetime.datetime.strptime(today, "%Y-%m-%d") -
                             datetime.datetime.strptime(payment_date[:10], "%Y-%m-%d")).days
                except ValueError:
                    delta = 0
                if delta > 30:
                    _add_alert("payment_overdue", "P0",
                               f"Payment overdue: {d.get('deal_number', 'N/A')} ({delta} days)",
                               f"Outstanding: Rs {outstanding:,.0f}",
                               "Send payment reminder immediately")
                elif delta > 7:
                    _add_alert("payment_overdue", "P1",
                               f"Payment due: {d.get('deal_number', 'N/A')} ({delta} days)",
                               f"Outstanding: Rs {outstanding:,.0f}",
                               "Follow up on payment")
    except Exception:
        pass

    # 4. Customer relationship decay
    try:
        from database import get_all_customers
        customers = get_all_customers()
        for c in customers:
            if c.get("relationship_stage") == "dormant":
                _add_alert("customer_dormant", "P1",
                           f"Customer dormant: {c.get('name', 'Unknown')}",
                           f"No activity for 90+ days in {c.get('city', 'unknown city')}",
                           "Consider reactivation offer")
    except Exception:
        pass

    # 5. Low margin deals
    try:
        from database import get_all_deals
        for d in get_all_deals():
            margin = d.get("margin_per_mt", 0) or 0
            if d.get("status") == "active" and 0 < margin < 300:
                _add_alert("low_margin", "P0",
                           f"Low margin deal: {d.get('deal_number', 'N/A')} (Rs{margin:.0f}/MT)",
                           "Margin below minimum threshold",
                           "Review deal pricing or renegotiate")
    except Exception:
        pass

    # 6. Weather impact
    try:
        weather = json.loads((base / "tbl_weather.json").read_text(encoding="utf-8"))
        for w in weather[-5:]:
            rain = w.get("rain_mm", w.get("rain", 0))
            if rain and float(rain) > 50:
                city = w.get("city", w.get("location", "Unknown"))
                _add_alert("heavy_rain", "P2",
                           f"Heavy rain forecast: {city} ({rain}mm)",
                           "Construction activity may slow, affecting demand",
                           "Adjust delivery schedules for affected areas")
    except Exception:
        pass

    # 7. Escalation: P1 alerts older than 24h become P0
    try:
        from database import get_alerts as _get_alerts, update_alert_status
        p1_alerts = _get_alerts(status="new", priority="P1")
        cutoff = (datetime.datetime.now(IST) - datetime.timedelta(hours=24)
                  ).strftime("%Y-%m-%d %H:%M:%S")
        for a in p1_alerts:
            if a.get("created_at", "") < cutoff:
                update_alert_status(a["id"], "new")
                # Re-insert as P0
                insert_alert({
                    "alert_type": a.get("alert_type", "escalated"),
                    "priority": "P0",
                    "title": f"[ESCALATED] {a.get('title', '')}",
                    "description": f"P1 alert not acted on for 24h. {a.get('description', '')}",
                    "recommended_action": a.get("recommended_action", ""),
                })
                update_alert_status(a["id"], "expired")
                count += 1
    except Exception:
        pass

    return count


def get_p0_alert_banner() -> str:
    """Return HTML for P0 alert banner (for Home page). Empty string if no P0 alerts."""
    try:
        from database import get_alerts
        p0 = get_alerts(status="new", priority="P0", limit=5)
        if not p0:
            return ""
        titles = " | ".join([a.get("title", "")[:60] for a in p0[:3]])
        return f"""
        <div style="background:#b85c38;color:white;padding:8px 15px;border-radius:6px;
                    margin-bottom:10px;font-size:0.85rem;">
          <strong>ALERT ({len(p0)}):</strong> {titles}
        </div>
        """
    except Exception:
        return ""
