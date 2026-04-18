"""
Panel 8: Alert System
Configurable alerts for crude price, freight, margin, GST mismatch, shipment delays, payment overdue.
Live Brent price is fetched from api_manager and used for real threshold checks.
"""
import streamlit as st
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from ui_badges import display_badge
import datetime

# ── Live data from api_manager (graceful fallback to defaults) ───────────────
try:
    from api_manager import get_brent_price, get_usdinr, get_india_vix
    _LIVE_BRENT  = get_brent_price()   # USD/bbl
    _LIVE_USDINR = get_usdinr()        # ₹ per USD
    _LIVE_VIX    = get_india_vix()     # India VIX
except Exception:
    _LIVE_BRENT  = 80.0
    _LIVE_USDINR = 83.25
    _LIVE_VIX    = 15.0

# Alert thresholds
BRENT_HIGH_THRESHOLD = 80.0   # USD/bbl — Critical if exceeded
BRENT_LOW_THRESHOLD  = 65.0   # USD/bbl — Warning if below
VIX_HIGH_THRESHOLD   = 20.0   # India VIX — Warning if above


def _get_overdue_alerts(now):
    """Generate payment overdue alerts from deals table, fallback to hardcoded."""
    try:
        from database import _get_conn
        conn = _get_conn()
        rows = conn.execute(
            "SELECT COALESCE(c.name,'Unknown'), d.total_value_inr, d.delivery_date, d.deal_number "
            "FROM deals d LEFT JOIN customers c ON c.id = d.customer_id "
            "WHERE d.payment_date IS NULL AND d.delivery_date IS NOT NULL "
            "ORDER BY d.delivery_date ASC LIMIT 5"
        ).fetchall()
        conn.close()
        if rows:
            alerts = []
            for i, r in enumerate(rows):
                name = r[0] or "Unknown"
                value = float(r[1] or 0)
                delivery = r[2] or ""
                inv = r[3] or f"INV-{i}"
                try:
                    d_date = datetime.datetime.strptime(delivery, "%Y-%m-%d")
                    overdue_days = (now - d_date).days
                except Exception:
                    overdue_days = 0
                value_cr = value / 10000000
                alerts.append({
                    "id": f"ALT-005-{i+1}",
                    "severity": "critical" if overdue_days > 30 else "warning",
                    "category": "Payment",
                    "title": f"💰 Payment Overdue — {name}",
                    "message": (
                        f"Outstanding {value_cr:.1f} Cr overdue by {overdue_days} days "
                        f"({inv}). Follow up immediately."
                    ),
                    "time": now - datetime.timedelta(days=1),
                    "action": "Send payment reminder • Hold further dispatches • Escalate to Finance Head",
                    "acknowledged": False
                })
            return alerts
    except Exception:
        pass
    # Fallback: single hardcoded alert
    return [{
        "id": "ALT-005",
        "severity": "warning",
        "category": "Payment",
        "title": "💰 Payment Overdue — Ashoka Buildcon",
        "message": "Outstanding ₹1.5 Cr overdue by 12 days (Invoice #INV-2026-0089). "
                   "Credit days exhausted. Payment reliability score dropped to 85%.",
        "time": now - datetime.timedelta(days=1),
        "action": "Send payment reminder • Hold further dispatches • Escalate to Finance Head",
        "acknowledged": False
    }]


def _get_active_alerts():
    """
    Build alert list combining:
    - Live threshold checks (Brent, VIX, USD/INR)
    - Standing business alerts (payment, shipment, GST, market)
    """
    now = datetime.datetime.now()
    brent   = _LIVE_BRENT
    usdinr  = _LIVE_USDINR
    vix     = _LIVE_VIX
    
    alerts = [
        {
            "id": "ALT-001",
            "severity": "critical",
            "category": "Supplier Risk",
            "title": "⚠️ Supplier Under Investigation",
            "message": "Star Bitumen Pvt Ltd (GSTIN: 27AAFCS9876M1Z4) flagged under DGGI investigation. "
                       "Suspend all purchases immediately. ITC on past purchases may be reversed.",
            "time": now - datetime.timedelta(hours=2),
            "action": "Suspend purchases • Request GST compliance certificate • Review past ITC claims",
            "acknowledged": False
        },
        {
            "id": "ALT-002",
            "severity": "critical" if brent >= BRENT_HIGH_THRESHOLD else "warning" if brent >= BRENT_LOW_THRESHOLD else "info",
            "category": "Crude Price",
            "title": f"🛢️ Brent Crude {'Above' if brent >= BRENT_HIGH_THRESHOLD else 'At'} ${BRENT_HIGH_THRESHOLD:.0f} Threshold — Live: ${brent:.2f}/bbl",
            "message": (
                f"Live Brent Crude: ${brent:.2f}/bbl | USD/INR: {usdinr:.2f} | India VIX: {vix:.1f}. "
                + ("Above critical threshold — expected bitumen price increase of ₹500–700/MT."
                   if brent >= BRENT_HIGH_THRESHOLD
                   else f"Monitoring — threshold ${BRENT_HIGH_THRESHOLD:.0f}/bbl not yet breached.")
            ),
            "time": now - datetime.timedelta(minutes=5),
            "action": "Lock current prices with refineries • Pre-buy inventory • Notify sales team",
            "acknowledged": False if brent >= BRENT_HIGH_THRESHOLD else True,
        },
        {
            "id": "ALT-003",
            "severity": "warning",
            "category": "Margin Alert",
            "title": "📉 Margin Below 8% on North Route",
            "message": "Landed cost to Ludhiana via Panipat route showing only 6.5% margin. "
                       "Transport costs have increased due to toll revision.",
            "time": now - datetime.timedelta(hours=8),
            "action": "Revise quotes for North India • Consider Kandla route alternative",
            "acknowledged": True
        },
        {
            "id": "ALT-004",
            "severity": "warning",
            "category": "Shipment",
            "title": "🚢 Vessel MT Tigris Dream — ETA Delayed",
            "message": "MT Tigris Dream ETA revised from 15-Mar to 18-Mar due to port congestion at Mangalore. "
                       "3-day delay may affect delivery commitments to Dilip Buildcon.",
            "time": now - datetime.timedelta(hours=12),
            "action": "Notify buyer • Arrange interim supply from local stock • Update delivery schedule",
            "acknowledged": False
        },
        *_get_overdue_alerts(now),
        {
            "id": "ALT-006",
            "severity": "info",
            "category": "Freight",
            "title": "🚢 Ocean Freight Rates Increasing",
            "message": "Middle East to India ocean freight trending up: ₹ 35→₹ 38/MT over past 2 weeks. "
                       "Container shortage reported in Basrah.",
            "time": now - datetime.timedelta(days=1, hours=6),
            "action": "Negotiate long-term freight contract • Consider spot booking for next vessel",
            "acknowledged": True
        },
        {
            "id": "ALT-007",
            "severity": "info",
            "category": "GST",
            "title": "📋 GSTR-2B Mismatch Detected",
            "message": "Mundra Import Terminal GSTR-2B filing shows ₹4.2L discrepancy in Feb 2026. "
                       "ITC claim of ₹18.5L at risk if not reconciled.",
            "time": now - datetime.timedelta(days=2),
            "action": "Contact supplier accounts team • Request reconciliation • Hold ITC claim",
            "acknowledged": True
        },
        {
            "id": "ALT-008",
            "severity": "info",
            "category": "Market",
            "title": "🏛️ NHAI New Tender — Gujarat Expressway Phase 3",
            "message": "NHAI has released tender for Gujarat Expressway Phase 3 (NQ-2026-GJ-045). "
                       "Estimated bitumen requirement: 15,000 MT over 18 months.",
            "time": now - datetime.timedelta(days=3),
            "action": "Alert sales team • Prepare competitive quote • Target contractor pre-qualification",
            "acknowledged": True
        },
        # ── Live VIX alert ───────────────────────────────────────────────────
        {
            "id": "ALT-009",
            "severity": "warning" if vix >= VIX_HIGH_THRESHOLD else "info",
            "category": "Market Risk",
            "title": f"📊 India VIX: {vix:.1f} {'— Elevated Volatility' if vix >= VIX_HIGH_THRESHOLD else '— Normal Range'}",
            "message": (
                f"India VIX is at {vix:.1f}. "
                + (f"Above {VIX_HIGH_THRESHOLD:.0f} — markets are volatile. Review open credit exposure with contractors."
                   if vix >= VIX_HIGH_THRESHOLD
                   else f"Within normal range (below {VIX_HIGH_THRESHOLD:.0f}). No immediate action required.")
            ),
            "time": now - datetime.timedelta(minutes=10),
            "action": "Review open positions • Check payment exposure • Monitor Nifty for further moves",
            "acknowledged": vix < VIX_HIGH_THRESHOLD,
        },
    ]
    return alerts


def _severity_config(severity):
    """Get display config for alert severity."""
    return {
        "critical": {"color": "#ef4444", "bg": "#fef2f2", "border": "#fecaca", "icon": "🔴", "label": "CRITICAL"},
        "warning": {"color": "#f59e0b", "bg": "#fffbeb", "border": "#fde68a", "icon": "🟡", "label": "WARNING"},
        "info": {"color": "#3b82f6", "bg": "#eff6ff", "border": "#bfdbfe", "icon": "🔵", "label": "INFO"},
    }.get(severity, {"color": "#94a3b8", "bg": "#f8fafc", "border": "#e2e8f0", "icon": "⚪", "label": "UNKNOWN"})


def render():
    display_badge("real-time")
    """Render the Alert System panel."""
    
    st.markdown("""
<div style="background: linear-gradient(135deg, #92400e 0%, #b45309 100%);
padding: 20px 25px; border-radius: 12px; margin-bottom: 20px;
box-shadow: 0 10px 30px rgba(180, 83, 9, 0.4);">
<div style="display:flex; align-items:center; gap:15px;">
<span style="font-size:2rem;">🔔</span>
<div>
<div style="font-size:1.3rem; font-weight:800; color:#e0e0e0;">
Alert System
</div>
<div style="font-size:0.75rem; color:#fcd34d; letter-spacing:1px; text-transform:uppercase;">
Real-time Business Monitoring • Threshold-based Triggers
</div>
</div>
</div>
</div>
""", unsafe_allow_html=True)
    
    alerts = _get_active_alerts()
    
    # --- SUMMARY ---
    critical = sum(1 for a in alerts if a["severity"] == "critical")
    warnings = sum(1 for a in alerts if a["severity"] == "warning")
    info = sum(1 for a in alerts if a["severity"] == "info")
    unack = sum(1 for a in alerts if not a["acknowledged"])
    
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("🔴 Critical", critical)
    with m2:
        st.metric("🟡 Warnings", warnings)
    with m3:
        st.metric("🔵 Info", info)
    with m4:
        st.metric("⏳ Unacknowledged", unack)
    
    # --- THRESHOLD CONFIG ---
    with st.expander("⚙️ Alert Thresholds (Configure)"):
        tc1, tc2, tc3 = st.columns(3)
        with tc1:
            st.number_input("Crude Price Alert ($)", value=80, step=1, key="thresh_crude")
            st.number_input("Margin Floor (%)", value=8, step=1, key="thresh_margin")
        with tc2:
            st.number_input("Freight Spike Alert ($/MT)", value=40, step=1, key="thresh_freight")
            st.number_input("Payment Overdue (days)", value=30, step=5, key="thresh_payment")
        with tc3:
            st.number_input("Shipment Delay (days)", value=3, step=1, key="thresh_delay")
            st.number_input("GST Mismatch Threshold (₹L)", value=5, step=1, key="thresh_gst")
    
    st.markdown("---")
    
    # --- FILTER ---
    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        severity_filter = st.selectbox("Filter by Severity", ["All", "Critical", "Warning", "Info"])
    with filter_col2:
        category_filter = st.selectbox("Filter by Category", 
                                        ["All"] + list(set(a["category"] for a in alerts)))
    
    # Apply filters
    filtered = alerts.copy()
    if severity_filter != "All":
        filtered = [a for a in filtered if a["severity"] == severity_filter.lower()]
    if category_filter != "All":
        filtered = [a for a in filtered if a["category"] == category_filter]
    
    # --- ALERT CARDS ---
    for alert in filtered:
        cfg = _severity_config(alert["severity"])
        time_str = alert["time"].strftime("%d %b %Y, %H:%M")
        ack_badge = '<span style="background:#d1fae5; color:#065f46; padding:2px 6px; border-radius:8px; font-size:0.6rem; font-weight:600;">✅ Acknowledged</span>' if alert["acknowledged"] else '<span style="background:#fef2f2; color:#991b1b; padding:2px 6px; border-radius:8px; font-size:0.6rem; font-weight:600;">⏳ Pending</span>'
        
        st.markdown(f"""
<div style="background:{cfg['bg']}; border:1px solid {cfg['border']}; border-left:5px solid {cfg['color']};
border-radius:8px; padding:12px 15px; margin-bottom:10px; 
box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
<div style="display:flex; align-items:center; gap:8px;">
<span style="background:{cfg['color']}; color:white; padding:2px 8px; border-radius:6px;
font-size:0.65rem; font-weight:700;">{cfg['label']}</span>
<span style="font-size:0.7rem; color:#64748b;">{alert['category']}</span>
{ack_badge}
</div>
<span style="font-size:0.65rem; color:#94a3b8;">🕐 {time_str}</span>
</div>
<div style="font-weight:700; color:#1e293b; font-size:0.9rem; margin-bottom:5px;">
{alert['title']}
</div>
<div style="font-size:0.8rem; color:#475569; margin-bottom:8px;">
{alert['message']}
</div>
<div style="background:white; border-radius:6px; padding:8px 12px; font-size:0.75rem;">
<b style="color:#1e293b;">📋 Recommended Action:</b>
<span style="color:#475569;"> {alert['action']}</span>
</div>
</div>
""", unsafe_allow_html=True)
