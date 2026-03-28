"""
Maritime Logistics Intelligence Dashboard
==========================================
4-tab UI for maritime vessel tracking, port activity,
shipment routes, and logistics risk monitoring.

Container shipments shown ABOVE bulk everywhere.
Priority ports (Mundra, Kandla, Mumbai) always at top.

Tabs:
  1. Vessel Tracking  — Interactive Plotly scatter_geo map + vessel table
  2. Port Activity    — Congestion heatmap, factor breakdown, trends
  3. Shipment Routes  — Route map, route cards, active shipments
  4. Logistics Risk   — Risk map, multi-modal status, alerts, daily summary
"""

import streamlit as st
import sys
import os
from datetime import datetime, timezone, timedelta

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

IST = timezone(timedelta(hours=5, minutes=30))


def render():
    """Main entry point for Maritime Logistics Intelligence page."""
    try:
        from ui_badges import display_badge
        display_badge("maritime")
    except Exception:
        pass

    _render_header()
    _render_priority_ports_panel()

    tab1, tab2, tab3, tab4 = st.tabs([
        "🚢 Vessel Tracking",
        "⚓ Port Activity",
        "🗺️ Shipment Routes",
        "⚠️ Logistics Risk Map",
    ])

    # Load data once
    intel = _load_intel()

    with tab1:
        _render_vessel_tracking(intel)
    with tab2:
        _render_port_activity(intel)
    with tab3:
        _render_shipment_routes(intel)
    with tab4:
        _render_risk_map(intel)


def _load_intel() -> dict:
    """Load or refresh maritime intelligence data."""
    from maritime_intelligence_engine import (
        refresh_maritime_intel, TBL_MARITIME_INTEL, _load
    )

    # Check if we need a refresh
    cached = _load(TBL_MARITIME_INTEL, {})
    needs_refresh = not cached or not cached.get("vessels")

    if needs_refresh or st.session_state.get("_maritime_force_refresh"):
        st.session_state["_maritime_force_refresh"] = False
        with st.spinner("Refreshing maritime intelligence..."):
            cached = refresh_maritime_intel()

    return cached


# ═══════════════════════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════════════════════

def _render_header():
    """Gradient banner with refresh button."""
    col1, col2 = st.columns([5, 1])
    with col1:
        st.markdown("""
<div style="background: linear-gradient(135deg, #0a1628 0%, #1e3a5f 50%, #0f4c75 100%);
padding: 20px 25px; border-radius: 12px; margin-bottom: 15px;
box-shadow: 0 10px 30px rgba(10, 22, 40, 0.5);">
<div style="display:flex; align-items:center; gap:15px;">
<span style="font-size:2.2rem;">🚢</span>
<div>
<div style="font-size:1.4rem; font-weight:800; color:#e0e0e0;
background: linear-gradient(90deg, #e0e0e0, #c9a84c); -webkit-background-clip: text;
-webkit-text-fill-color: transparent;">
Maritime Logistics Intelligence
</div>
<div style="font-size:0.72rem; color:#94a3b8; letter-spacing:1.5px; text-transform:uppercase;">
Vessel Tracking &bull; Port Congestion &bull; Route Risk &bull; Multi-Modal Supply Chain
</div>
</div>
</div>
</div>
""", unsafe_allow_html=True)
    with col2:
        if st.button("🔄 Refresh", key="_maritime_refresh_btn", use_container_width=True):
            st.session_state["_maritime_force_refresh"] = True
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# PRIORITY PORTS PANEL — Always visible at top
# ═══════════════════════════════════════════════════════════════════════════════

def _render_priority_ports_panel():
    """Show Mundra, Kandla, Mumbai status — ALWAYS on top."""
    from maritime_intelligence_engine import (
        INDIAN_PORTS, PortCongestionMonitor, VesselSimulator
    )

    try:
        from settings_engine import get as gs
        priority_names = gs("maritime_priority_ports", ["Mundra", "Kandla", "Mumbai"])
    except Exception:
        priority_names = ["Mundra", "Kandla", "Mumbai"]

    ports_data = PortCongestionMonitor.compute_all_ports()
    vessels = VesselSimulator.generate_vessels(count=12)

    priority_ports = [p for p in ports_data if p["port"] in priority_names]
    if not priority_ports:
        return

    st.markdown("""
<div style="background: linear-gradient(135deg, #0f172a 0%, #1a2744 100%);
padding: 12px 16px; border-radius: 10px; margin-bottom: 15px;
border: 1px solid #1e3a5f;">
<div style="font-size:0.8rem; font-weight:700; color:#c9a84c;
letter-spacing:1px; text-transform:uppercase; margin-bottom:8px;">
🏗️ Priority Ports — Container & Bulk Status
</div>
</div>
""", unsafe_allow_html=True)

    cols = st.columns(len(priority_ports))
    for idx, port in enumerate(priority_ports):
        with cols[idx]:
            port_vessels = [v for v in vessels if v["destination_port"] == port["port"]]
            containers = sum(1 for v in port_vessels if v["cargo_type"] == "container")
            bulk = sum(1 for v in port_vessels if v["cargo_type"] == "bulk")
            next_eta = min((v["eta_hours"] for v in port_vessels), default=0)

            # Congestion color
            score = port["score"]
            if score >= 60:
                dot, color, bg = "🔴", "#ef4444", "rgba(239,68,68,0.08)"
            elif score >= 35:
                dot, color, bg = "🟡", "#f59e0b", "rgba(245,158,11,0.08)"
            else:
                dot, color, bg = "🟢", "#22c55e", "rgba(34,197,94,0.08)"

            label = port.get("label", port["port"])

            st.markdown(f"""
<div style="background:{bg}; border-radius:10px; padding:14px;
border: 1px solid {color}30; text-align:center;">
<div style="font-weight:800; font-size:0.95rem; color:#e0e0e0;">{label}</div>
<div style="margin:6px 0;">
<span style="font-size:1.1rem;">{dot}</span>
<span style="color:{color}; font-weight:600; font-size:0.8rem;">{port['level']}</span>
</div>
<div style="display:flex; justify-content:space-around; margin:8px 0;">
<div style="text-align:center;">
<div style="font-size:1.1rem; font-weight:700; color:#3b82f6;">{containers}</div>
<div style="font-size:0.6rem; color:#94a3b8;">Containers</div>
</div>
<div style="text-align:center;">
<div style="font-size:1.1rem; font-weight:700; color:#f59e0b;">{bulk}</div>
<div style="font-size:0.6rem; color:#94a3b8;">Bulk</div>
</div>
</div>
<div style="font-size:0.7rem; color:#64748b; margin-top:4px;">
Congestion: <strong style="color:{color};">{score}%</strong> |
Wait: {port.get('avg_wait_hours', 0)}h
</div>
<div style="font-size:0.65rem; color:#94a3b8; margin-top:2px;">
Next ETA: {next_eta:.0f}h | Waiting: {port.get('vessels_waiting', 0)}
</div>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1: VESSEL TRACKING
# ═══════════════════════════════════════════════════════════════════════════════

def _render_vessel_tracking(intel: dict):
    """Interactive map + vessel table."""
    st.markdown("### 🚢 Vessel Tracking Map")

    vessels = intel.get("vessels", [])
    port_congestion = intel.get("port_congestion", [])

    if not vessels:
        st.info("No vessel data available. Click Refresh to generate.")
        return

    # Build map
    fig = _build_vessel_map(vessels, port_congestion)
    st.plotly_chart(fig, use_container_width=True, key="_maritime_vessel_map")

    # Vessel table — container FIRST
    st.markdown("### 📋 Active Vessels")
    st.caption("Container shipments shown first")

    for v in vessels:
        is_container = v["cargo_type"] == "container"
        badge_color = "#3b82f6" if is_container else "#f59e0b"
        badge_text = "CONTAINER" if is_container else "BULK"

        # Status styling
        status = v.get("status", "en_route")
        if status == "delayed":
            st_color, st_dot = "#ef4444", "🔴"
        elif status == "arriving":
            st_color, st_dot = "#22c55e", "🟢"
        else:
            st_color, st_dot = "#3b82f6", "🔵"

        st.markdown(f"""
<div style="background:#f8fafc; border-radius:8px; padding:10px 14px; margin-bottom:6px;
border-left:4px solid {badge_color};">
<div style="display:flex; justify-content:space-between; align-items:center;">
<div>
<span style="background:{badge_color}; color:white; padding:1px 6px;
border-radius:3px; font-size:0.55rem; font-weight:700;">{badge_text}</span>
<strong style="font-size:0.85rem; color:#1e293b; margin-left:6px;">{v['vessel_name']}</strong>
<span style="color:#94a3b8; font-size:0.65rem;">({v['imo']})</span>
</div>
<div>
<span style="font-size:0.7rem;">{st_dot}</span>
<span style="color:{st_color}; font-size:0.7rem; font-weight:600;">{status.upper()}</span>
</div>
</div>
<div style="font-size:0.72rem; color:#475569; margin-top:4px;">
{v['departure_port']} → <strong>{v['destination_port']}</strong> |
Speed: {v['speed_knots']} kn | Progress: {v['progress_pct']}% |
{v.get('cargo_mt', 0)} MT {v.get('product_grade', '')}
</div>
<div style="font-size:0.68rem; color:#64748b; margin-top:2px;">
ETA: <strong>{v['eta']}</strong> ({v['eta_hours']}h remaining) |
Heading: {v['heading']}°
</div>
</div>
""", unsafe_allow_html=True)

    # Summary metrics
    st.markdown("---")
    summary = intel.get("summary", {})
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Total Vessels", summary.get("vessels_total", len(vessels)))
    with c2:
        st.metric("Container", summary.get("vessels_container", 0))
    with c3:
        st.metric("Bulk", summary.get("vessels_bulk", 0))
    with c4:
        st.metric("Delayed", summary.get("vessels_delayed", 0))


def _build_vessel_map(vessels: list, port_congestion: list):
    """Build Plotly scatter_geo map with vessels, ports, and routes."""
    import plotly.graph_objects as go
    from maritime_intelligence_engine import INDIAN_PORTS, SUPPLY_PORTS, ROUTES

    fig = go.Figure()

    # Layer 1: Route lines (bulk first so container overlays)
    sorted_routes = sorted(ROUTES, key=lambda r: r["type"] == "container")
    for route in sorted_routes:
        from_port = SUPPLY_PORTS.get(route["from"], {})
        to_port = INDIAN_PORTS.get(route["to"], {})
        is_container = route["type"] == "container"

        fig.add_trace(go.Scattergeo(
            lon=[from_port.get("lon", 0), to_port.get("lon", 0)],
            lat=[from_port.get("lat", 0), to_port.get("lat", 0)],
            mode="lines",
            line=dict(
                width=2.5 if is_container else 1.2,
                color="rgba(59,130,246,0.6)" if is_container else "rgba(245,158,11,0.3)",
                dash="dash",
            ),
            name=f"{'Container' if is_container else 'Bulk'}: {route['from']} → {route['to']}",
            showlegend=False,
            hoverinfo="text",
            hovertext=f"{route['from']} → {route['to']}<br>Type: {route['type']}<br>Avg: {route['avg_days']}d | {route['distance_nm']}nm",
        ))

    # Layer 2: Supply port markers
    supply_lats = [p["lat"] for p in SUPPLY_PORTS.values()]
    supply_lons = [p["lon"] for p in SUPPLY_PORTS.values()]
    supply_names = list(SUPPLY_PORTS.keys())
    supply_hover = [
        f"<b>{name}</b><br>Country: {SUPPLY_PORTS[name]['country']}<br>Products: {', '.join(SUPPLY_PORTS[name].get('products', []))}"
        for name in supply_names
    ]

    fig.add_trace(go.Scattergeo(
        lon=supply_lons, lat=supply_lats,
        mode="markers+text",
        marker=dict(size=10, color="#e2e8f0", symbol="square",
                    line=dict(width=1, color="#94a3b8")),
        text=supply_names,
        textposition="top center",
        textfont=dict(size=8, color="#e2e8f0"),
        name="Supply Ports",
        hoverinfo="text",
        hovertext=supply_hover,
    ))

    # Layer 3: Indian port markers (color by congestion)
    congestion_map = {p["port"]: p for p in port_congestion}
    for port_name, port_data in INDIAN_PORTS.items():
        cong = congestion_map.get(port_name, {})
        score = cong.get("score", 20)
        level = cong.get("level", "Low")
        is_priority = port_data["priority"] == 1

        if score >= 60:
            color = "#ef4444"
        elif score >= 35:
            color = "#f59e0b"
        else:
            color = "#22c55e"

        fig.add_trace(go.Scattergeo(
            lon=[port_data["lon"]], lat=[port_data["lat"]],
            mode="markers+text",
            marker=dict(
                size=16 if is_priority else 10,
                color=color,
                symbol="diamond" if is_priority else "circle",
                line=dict(width=2 if is_priority else 1, color="white"),
            ),
            text=[port_name],
            textposition="bottom center",
            textfont=dict(size=9 if is_priority else 7, color="#e2e8f0",
                          family="Arial Black" if is_priority else "Arial"),
            name=port_name,
            showlegend=False,
            hoverinfo="text",
            hovertext=f"<b>{port_data.get('label', port_name)}</b><br>"
                       f"Type: {port_data['type']}<br>"
                       f"Congestion: {level} ({score}%)<br>"
                       f"Waiting: {cong.get('vessels_waiting', 0)} vessels",
        ))

    # Layer 4: Vessel markers (bulk first, container on top)
    sorted_vessels = sorted(vessels, key=lambda v: v["cargo_type"] == "container")
    for v in sorted_vessels:
        is_container = v["cargo_type"] == "container"
        status = v.get("status", "en_route")

        if status == "delayed":
            v_color = "#ef4444"
        elif status == "arriving":
            v_color = "#22c55e"
        elif is_container:
            v_color = "#3b82f6"
        else:
            v_color = "#f59e0b"

        fig.add_trace(go.Scattergeo(
            lon=[v["lon"]], lat=[v["lat"]],
            mode="markers",
            marker=dict(
                size=14 if is_container else 9,
                color=v_color,
                symbol="diamond" if is_container else "circle",
                line=dict(width=2 if is_container else 1, color="white"),
            ),
            name=v["vessel_name"],
            showlegend=False,
            hoverinfo="text",
            hovertext=(
                f"<b>{v['vessel_name']}</b> ({v['imo']})<br>"
                f"Type: {'CONTAINER' if is_container else 'BULK'}<br>"
                f"{v['departure_port']} → {v['destination_port']}<br>"
                f"Speed: {v['speed_knots']} kn | Heading: {v['heading']}°<br>"
                f"Progress: {v['progress_pct']}% | ETA: {v['eta']}<br>"
                f"Cargo: {v.get('cargo_mt', 0)} MT {v.get('product_grade', '')}<br>"
                f"Status: {status.upper()}"
            ),
        ))

    # Map styling
    try:
        from settings_engine import get as gs
        center_lat = gs("maritime_map_center_lat", 18.0)
        center_lon = gs("maritime_map_center_lon", 68.0)
    except Exception:
        center_lat, center_lon = 18.0, 68.0

    fig.update_geos(
        center=dict(lat=center_lat, lon=center_lon),
        projection_type="natural earth",
        projection_scale=4,
        showland=True, landcolor="#1a1a2e",
        showocean=True, oceancolor="#0a1628",
        showcountries=True, countrycolor="#333355",
        showcoastlines=True, coastlinecolor="#334466",
        showframe=False,
        lonaxis=dict(range=[40, 110]),
        lataxis=dict(range=[-5, 35]),
    )
    fig.update_layout(
        height=550,
        margin=dict(l=0, r=0, t=30, b=0),
        paper_bgcolor="#0f172a",
        plot_bgcolor="#0f172a",
        font=dict(color="#e2e8f0"),
        legend=dict(
            bgcolor="rgba(15,23,42,0.8)",
            font=dict(color="#e2e8f0", size=9),
            x=0.01, y=0.99,
        ),
        title=dict(
            text="Indian Ocean — Bitumen Maritime Routes",
            font=dict(size=14, color="#c9a84c"),
            x=0.5,
        ),
    )

    return fig


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2: PORT ACTIVITY
# ═══════════════════════════════════════════════════════════════════════════════

def _render_port_activity(intel: dict):
    """Port congestion heatmap, factor breakdown, trend."""
    st.markdown("### ⚓ Port Congestion Monitor")

    port_congestion = intel.get("port_congestion", [])
    if not port_congestion:
        st.info("No port data available.")
        return

    # KPI row
    avg_score = sum(p["score"] for p in port_congestion) / len(port_congestion)
    critical_ports = sum(1 for p in port_congestion if p["score"] >= 60)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Avg Congestion", f"{avg_score:.0f}%")
    with c2:
        st.metric("Ports Monitored", len(port_congestion))
    with c3:
        st.metric("High/Critical", critical_ports)
    with c4:
        total_waiting = sum(p.get("vessels_waiting", 0) for p in port_congestion)
        st.metric("Vessels Waiting", total_waiting)

    # Port congestion bar chart
    try:
        import plotly.graph_objects as go

        # Sort: priority first
        sorted_ports = sorted(port_congestion, key=lambda p: (p["priority"], -p["score"]))

        port_names = [p["port"] for p in sorted_ports]
        scores = [p["score"] for p in sorted_ports]
        colors = [
            "#ef4444" if s >= 60 else "#f59e0b" if s >= 35 else "#22c55e"
            for s in scores
        ]

        fig = go.Figure(data=[go.Bar(
            x=port_names, y=scores,
            marker_color=colors,
            text=[f"{s}%" for s in scores],
            textposition="outside",
            textfont=dict(size=10),
        )])
        fig.update_layout(
            title="Port Congestion Scores",
            height=350,
            margin=dict(l=40, r=20, t=50, b=60),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(title="Congestion %", range=[0, 110]),
            font=dict(size=11),
        )
        # Add threshold lines
        fig.add_hline(y=60, line_dash="dash", line_color="#ef4444",
                      annotation_text="Critical", annotation_position="top right")
        fig.add_hline(y=35, line_dash="dash", line_color="#f59e0b",
                      annotation_text="High", annotation_position="top right")
        st.plotly_chart(fig, use_container_width=True, key="_maritime_port_bar")
    except ImportError:
        st.warning("Plotly required for charts.")

    # Factor breakdown per port
    st.markdown("### 📊 Congestion Factor Breakdown")
    for port in port_congestion:
        if port["priority"] <= 2:  # Show details for priority 1 & 2 ports
            with st.expander(f"{port['label']} — {port['level']} ({port['score']}%)", expanded=port["priority"] == 1):
                factors = port.get("factors", {})
                factor_cols = st.columns(5)
                factor_labels = [
                    ("Weather", "weather", "🌊"),
                    ("BDI", "bdi", "📈"),
                    ("News", "news", "📰"),
                    ("Seasonal", "seasonal", "📅"),
                    ("Historical", "historical", "🏛️"),
                ]
                for i, (label, key, icon) in enumerate(factor_labels):
                    with factor_cols[i]:
                        val = factors.get(key, 0)
                        color = "#ef4444" if val >= 60 else "#f59e0b" if val >= 35 else "#22c55e"
                        st.markdown(f"""
<div style="text-align:center; padding:8px; background:#f8fafc; border-radius:8px;">
<div style="font-size:1.2rem;">{icon}</div>
<div style="font-size:0.7rem; color:#64748b;">{label}</div>
<div style="font-size:1.1rem; font-weight:700; color:{color};">{val:.0f}</div>
</div>
""", unsafe_allow_html=True)

                st.caption(f"Vessels waiting: {port.get('vessels_waiting', 0)} | Avg wait: {port.get('avg_wait_hours', 0)}h")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3: SHIPMENT ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

def _render_shipment_routes(intel: dict):
    """Route map, route cards, active shipments."""
    st.markdown("### 🗺️ Active Shipping Routes")

    route_risks = intel.get("route_risks", [])
    vessels = intel.get("vessels", [])

    if not route_risks:
        st.info("No route data available.")
        return

    # Route map (reuse vessel map but focused on routes)
    fig = _build_route_map(route_risks, vessels)
    st.plotly_chart(fig, use_container_width=True, key="_maritime_route_map")

    # Route cards — container FIRST
    st.markdown("### 📋 Route Risk Analysis")
    st.caption("Container routes highlighted first")

    for r in route_risks:
        is_container = r["cargo_type"] == "container"
        risk = r["risk_score"]
        if risk >= 50:
            color = "#ef4444"
        elif risk >= 30:
            color = "#f59e0b"
        else:
            color = "#22c55e"

        badge_color = "#3b82f6" if is_container else "#f59e0b"
        badge_text = "CONTAINER" if is_container else "BULK"

        st.markdown(f"""
<div style="background:#f8fafc; border-radius:10px; padding:12px 16px; margin-bottom:8px;
border-left:4px solid {badge_color};">
<div style="display:flex; justify-content:space-between; align-items:center;">
<div>
<span style="background:{badge_color}; color:white; padding:1px 6px;
border-radius:3px; font-size:0.55rem; font-weight:700;">{badge_text}</span>
<strong style="font-size:0.9rem; color:#1e293b; margin-left:6px;">{r['from']} → {r['to']}</strong>
</div>
<div>
<span style="background:{color}15; color:{color}; padding:2px 10px;
border-radius:4px; font-size:0.7rem; font-weight:600;">{r['risk_level']} ({risk})</span>
</div>
</div>
<div style="display:flex; gap:20px; margin-top:8px; font-size:0.72rem; color:#475569;">
<span>📏 {r.get('distance_nm', 0)} nm</span>
<span>⏱️ Avg {r['avg_transit_days']}d</span>
<span>💰 ~${r.get('avg_cost_usd_mt', 0)}/MT</span>
<span>⚠️ Delay: {r.get('delay_probability_pct', 0):.0f}%</span>
<span>⏳ +{r.get('predicted_delay_hours', 0):.0f}h</span>
</div>
</div>
""", unsafe_allow_html=True)

    # Active shipments table
    st.markdown("### 🚢 Active Shipments")
    if vessels:
        import pandas as pd
        df = pd.DataFrame([{
            "Type": "📦" if v["cargo_type"] == "container" else "🛢️",
            "Vessel": v["vessel_name"],
            "From": v["departure_port"],
            "To": v["destination_port"],
            "ETA (h)": v["eta_hours"],
            "Progress": f"{v['progress_pct']}%",
            "Status": v["status"].upper(),
            "Cargo": f"{v.get('cargo_mt', 0)} MT",
            "Grade": v.get("product_grade", ""),
        } for v in vessels])
        st.dataframe(df, use_container_width=True, hide_index=True)


def _build_route_map(route_risks: list, vessels: list):
    """Build route-focused map."""
    import plotly.graph_objects as go
    from maritime_intelligence_engine import INDIAN_PORTS, SUPPLY_PORTS

    fig = go.Figure()

    # Route lines with risk coloring
    sorted_routes = sorted(route_risks, key=lambda r: r["cargo_type"] == "container")
    for r in sorted_routes:
        from_port = SUPPLY_PORTS.get(r["from"], {})
        to_port = INDIAN_PORTS.get(r["to"], {})
        is_container = r["cargo_type"] == "container"
        risk = r["risk_score"]

        if risk >= 50:
            line_color = "rgba(239,68,68,0.7)"
        elif risk >= 30:
            line_color = "rgba(245,158,11,0.6)"
        else:
            line_color = "rgba(34,197,94,0.5)" if not is_container else "rgba(59,130,246,0.6)"

        fig.add_trace(go.Scattergeo(
            lon=[from_port.get("lon", 0), to_port.get("lon", 0)],
            lat=[from_port.get("lat", 0), to_port.get("lat", 0)],
            mode="lines+markers",
            line=dict(width=3.5 if is_container else 1.5, color=line_color, dash="dash"),
            marker=dict(size=6, color=line_color),
            showlegend=False,
            hoverinfo="text",
            hovertext=(
                f"<b>{r['from']} → {r['to']}</b><br>"
                f"Type: {r['cargo_type']}<br>"
                f"Risk: {r['risk_level']} ({risk})<br>"
                f"Transit: {r['avg_transit_days']}d | {r.get('distance_nm', 0)}nm"
            ),
        ))

    # Port markers
    for port_name, port_data in {**SUPPLY_PORTS, **INDIAN_PORTS}.items():
        is_indian = port_name in INDIAN_PORTS
        is_priority = INDIAN_PORTS.get(port_name, {}).get("priority", 9) == 1

        fig.add_trace(go.Scattergeo(
            lon=[port_data["lon"]], lat=[port_data["lat"]],
            mode="markers+text",
            marker=dict(
                size=14 if is_priority else 8,
                color="#c9a84c" if is_indian else "#e2e8f0",
                symbol="diamond" if is_priority else "circle",
                line=dict(width=1, color="white"),
            ),
            text=[port_name],
            textposition="bottom center",
            textfont=dict(size=8, color="#e2e8f0"),
            showlegend=False,
            hoverinfo="text",
            hovertext=f"<b>{port_name}</b>",
        ))

    fig.update_geos(
        center=dict(lat=18, lon=68), projection_type="natural earth",
        projection_scale=4,
        showland=True, landcolor="#1a1a2e",
        showocean=True, oceancolor="#0a1628",
        showcountries=True, countrycolor="#333355",
        showcoastlines=True, coastlinecolor="#334466",
        showframe=False,
        lonaxis=dict(range=[40, 110]), lataxis=dict(range=[-5, 35]),
    )
    fig.update_layout(
        height=450, margin=dict(l=0, r=0, t=30, b=0),
        paper_bgcolor="#0f172a", plot_bgcolor="#0f172a",
        title=dict(text="Shipping Route Risk Map", font=dict(size=13, color="#c9a84c"), x=0.5),
    )
    return fig


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4: LOGISTICS RISK MAP
# ═══════════════════════════════════════════════════════════════════════════════

def _render_risk_map(intel: dict):
    """Risk map + multi-modal status + alerts + daily summary."""
    st.markdown("### ⚠️ Logistics Risk Overview")

    summary = intel.get("summary", {})

    # Top KPIs
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        lri = summary.get("logistics_risk_index", 0)
        color = "#ef4444" if lri >= 50 else "#f59e0b" if lri >= 30 else "#22c55e"
        st.metric("Logistics Risk Index", f"{lri:.0f}")
    with c2:
        st.metric("Avg Route Risk", f"{summary.get('avg_route_risk', 0):.0f}%")
    with c3:
        st.metric("Avg Port Congestion", f"{summary.get('avg_port_congestion', 0):.0f}%")
    with c4:
        st.metric("Delayed Vessels", summary.get("vessels_delayed", 0))

    # Multi-modal transport status
    st.markdown("### 🚛 Multi-Modal Transport Status")
    multi_modal = intel.get("multi_modal", {})

    if multi_modal:
        modes = [
            ("🚢 Sea", multi_modal.get("sea", {})),
            ("🚛 Road", multi_modal.get("road", {})),
            ("🚂 Rail", multi_modal.get("rail", {})),
            ("✈️ Air", multi_modal.get("air", {})),
        ]
        mode_cols = st.columns(4)
        for i, (label, data) in enumerate(modes):
            with mode_cols[i]:
                risk = data.get("risk_level", "Unknown")
                if risk in ("High", "Critical"):
                    r_color = "#ef4444"
                elif risk == "Medium":
                    r_color = "#f59e0b"
                else:
                    r_color = "#22c55e"

                cpi = data.get("cost_pressure_index", 0)
                status = data.get("status", "Unknown")
                disruptions = data.get("disruptions", [])

                st.markdown(f"""
<div style="background:#f8fafc; border-radius:10px; padding:12px; text-align:center;
border-top:3px solid {r_color};">
<div style="font-size:1.1rem; font-weight:700;">{label}</div>
<div style="color:{r_color}; font-weight:600; font-size:0.8rem; margin:4px 0;">{risk}</div>
<div style="font-size:0.7rem; color:#64748b;">Status: {status}</div>
<div style="font-size:0.7rem; color:#64748b;">Cost Pressure: {cpi}</div>
<div style="font-size:0.65rem; color:#94a3b8;">Disruptions: {len(disruptions)}</div>
</div>
""", unsafe_allow_html=True)

        # Show disruption details
        all_disruptions = []
        for _, data in modes:
            for d in data.get("disruptions", []):
                all_disruptions.append(d)
        if all_disruptions:
            with st.expander(f"📋 Active Disruptions ({len(all_disruptions)})", expanded=False):
                for d in all_disruptions[:10]:
                    st.markdown(f"- {d}")

    # Alerts — container FIRST
    st.markdown("### 🚨 Maritime Alerts")
    from maritime_intelligence_engine import generate_alerts
    alerts = generate_alerts(intel)

    if alerts:
        for a in alerts[:10]:
            sev = a.get("severity", "info")
            if sev == "critical":
                icon, bg = "🔴", "rgba(239,68,68,0.08)"
            elif sev == "warning":
                icon, bg = "🟡", "rgba(245,158,11,0.08)"
            else:
                icon, bg = "🔵", "rgba(59,130,246,0.08)"

            cargo_badge = ""
            if a.get("cargo_type") == "container":
                cargo_badge = '<span style="background:#3b82f6; color:white; padding:0 4px; border-radius:2px; font-size:0.5rem; font-weight:700; margin-right:4px;">CTR</span>'

            st.markdown(f"""
<div style="background:{bg}; border-radius:6px; padding:8px 12px; margin-bottom:4px;">
<span>{icon}</span> {cargo_badge}
<strong style="font-size:0.78rem; color:#1e293b;">{a['title']}</strong>
<div style="font-size:0.68rem; color:#64748b; margin-top:2px;">{a.get('detail', '')}</div>
</div>
""", unsafe_allow_html=True)
    else:
        st.success("No active alerts. All systems nominal.")

    # Daily Summary
    st.markdown("### 📋 Daily Summary Report")
    from maritime_intelligence_engine import generate_daily_summary
    daily = generate_daily_summary(intel)

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"""
**Delay Risk Score:** {daily.get('delay_risk_score', 0)}/100
**Cost Pressure Index:** {daily.get('logistics_cost_pressure_index', 0)}/100
""")

        # Container ETA list
        container_etas = daily.get("container_shipment_etas", [])
        if container_etas:
            st.markdown("**Container ETAs:**")
            for eta in container_etas:
                st.markdown(
                    f"- **{eta['vessel']}** → {eta['to']}: "
                    f"{eta['eta']} ({eta['status']})"
                )

    with col_b:
        priority_status = daily.get("priority_port_status", {})
        if priority_status:
            st.markdown("**Priority Port Status:**")
            for port, data in priority_status.items():
                st.markdown(
                    f"- **{port}**: {data.get('congestion_level', 'N/A')} "
                    f"({data.get('congestion_score', 0)}%) — "
                    f"CTR:{data.get('container_vessels', 0)} / "
                    f"BLK:{data.get('bulk_vessels', 0)}"
                )

    # Share button
    try:
        from share_button import render_share_button
        render_share_button(
            section_id="maritime_daily_summary",
            section_title="Maritime Logistics Daily Summary",
        )
    except Exception:
        pass
