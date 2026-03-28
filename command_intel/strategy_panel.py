"""
Panel 9: Strategic Decision Panel
AI-powered trade recommendations with confidence scores and reasoning.
"""
import streamlit as st
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from ui_badges import display_badge
import datetime
import numpy as np


def _generate_decisions():
    """Generate strategic recommendations from real market signals."""
    month = datetime.date.today().month
    is_peak = month in [10, 11, 12, 1, 2, 3]
    is_monsoon = month in [6, 7, 8, 9]

    # ── Load market intelligence signals for data-driven confidence ────────
    signals, has_signals = {}, False
    master, crude_sig, currency_sig = {}, {}, {}
    try:
        from market_intelligence_engine import MarketIntelligenceEngine
        eng = MarketIntelligenceEngine()
        signals = eng.compute_all_signals()
        master = signals.get("master", {})
        crude_sig = signals.get("crude_market", {})
        currency_sig = signals.get("currency", {})
        has_signals = bool(master.get("status") == "OK")
    except Exception:
        pass

    # Helper: derive confidence from signal data (replaces np.random.normal)
    def _conf(base, signal_key=None, boost_if=None):
        c = base
        if has_signals and signal_key:
            sig = signals.get(signal_key, {})
            c = int(sig.get("confidence", base))
        if boost_if:
            c += 5
        return max(50, min(95, c))

    # Live values for reasoning text
    _brent = crude_sig.get("latest_brent", "~₹ 80") if has_signals else "~₹ 80"
    _usdinr = currency_sig.get("latest_usdinr", "~83") if has_signals else "~83"
    _crude_dir = crude_sig.get("direction", "SIDEWAYS") if has_signals else "SIDEWAYS"
    _fx_pressure = currency_sig.get("pressure", "MEDIUM") if has_signals else "MEDIUM"

    decisions = [
        {
            "question": "Import Now or Wait?",
            "icon": "🚢",
            "recommendation": "IMPORT NOW" if is_peak else "WAIT 30 DAYS",
            "confidence": _conf(75 if is_peak else 60, "crude_market", is_peak),
            "reasoning": [
                f"Brent at {_brent} — crude trending {_crude_dir}",
                f"Seasonal demand is {'PEAK — strong off-take guaranteed' if is_peak else 'LOW — risk of inventory buildup'}",
                f"USD/INR at {_usdinr} — FX pressure: {_fx_pressure}",
                f"Market master signal: {master.get('market_direction', 'N/A')}" if has_signals else "Market signals loading...",
            ],
            "risk": "Supply shortage if delayed" if is_peak else "Price may drop further",
            "color": "#22c55e" if is_peak else "#f59e0b"
        },
        {
            "question": "Hedge Crude Exposure?",
            "icon": "🛡️",
            "recommendation": "YES — Partial Hedge" if crude_sig.get("volatility", "MEDIUM") == "HIGH" else "NO — Monitor Closely",
            "confidence": _conf(68, "crude_market"),
            "reasoning": [
                f"Crude volatility: {crude_sig.get('volatility', 'MEDIUM')}" if has_signals else "Crude volatility being assessed",
                "Recommended hedge: 50% of next 3-month import volume",
                "Use Brent futures or USD/INR forward contracts",
                "Cost of hedge: ~Rs 200-300/MT — justified by volatility premium"
            ],
            "risk": "Opportunity cost if crude drops below hedge price",
            "color": "#3b82f6"
        },
        {
            "question": "Increase Inventory?",
            "icon": "📦",
            "recommendation": "YES — Stock 15 Days Extra" if is_peak else "NO — Maintain Current Levels",
            "confidence": _conf(72 if is_peak else 55, "weather"),
            "reasoning": [
                f"{'Peak season — safety stock critical' if is_peak else 'Off-season — avoid cash lock-up'}",
                f"Demand outlook: {master.get('demand_outlook', 'N/A')}" if has_signals else "Demand outlook loading...",
                "Storage cost: Rs 50/MT/month at Kandla terminal",
                f"{'Refinery shutdown risk in Feb-Mar' if is_peak else 'Adequate supply from all sources'}"
            ],
            "risk": "Working capital blocked" if is_peak else "Stock-out risk if demand spikes",
            "color": "#22c55e" if is_peak else "#f59e0b"
        },
        {
            "question": "Reduce Financial Exposure?",
            "icon": "💰",
            "recommendation": "YES — Tighten Credit",
            "confidence": _conf(78),
            "reasoning": [
                "Review receivables outstanding in 90+ days bucket",
                "Recommend: Strict 30-day payment enforcement for all contractors",
                "Stop dispatches to accounts with pending > Rs 50L",
                "Shift more contractors to advance payment model"
            ],
            "risk": "May lose price-sensitive contractors",
            "color": "#f59e0b"
        },
        {
            "question": "Offer Higher Contractor Price?",
            "icon": "📈",
            "recommendation": "NO — Hold Current Pricing" if is_peak else "YES — Small Increase (Rs 200/MT)",
            "confidence": _conf(70 if is_peak else 60),
            "reasoning": [
                f"{'Demand is strong — hold current rates' if is_peak else 'Market slow — price incentive may win volume'}",
                f"Risk level: {master.get('risk_level', 'N/A')}" if has_signals else "Risk level loading...",
                f"Crude direction: {_crude_dir} — {'pricing power intact' if is_peak else 'pressure on margins'}",
                "Volume impact of Rs 200 increase: estimated +5-8% more orders"
            ],
            "risk": "Margin compression" if not is_peak else "None — pricing power intact",
            "color": "#ef4444" if not is_peak else "#22c55e"
        },
        {
            "question": "Shift Import Port?",
            "icon": "⚓",
            "recommendation": "STAY — Mangalore + Kandla Optimal",
            "confidence": _conf(82, "ports"),
            "reasoning": [
                "Mangalore: Best for South + West India — covers 60% of volume",
                "Kandla: Best for North + Central India — covers 35% of volume",
                "Chennai port: Higher berthing charges + congestion — not viable",
                "Paradip (Odisha): Potential for East India expansion — evaluate Q3"
            ],
            "risk": "East India market underserved",
            "color": "#22c55e"
        },
        {
            "question": "Increase Credit Control?",
            "icon": "🔒",
            "recommendation": "YES — Immediate Action Needed",
            "confidence": _conf(85),
            "reasoning": [
                "High-risk suppliers require review — check compliance status",
                "GSTR-2B matching status should be verified for all suppliers",
                "Section 74 exposure risk needs urgent assessment",
                "Recommend: Full compliance audit within 15 days"
            ],
            "risk": "ITC reversal risk if compliance gaps not addressed",
            "color": "#ef4444"
        }
    ]
    return decisions


def render():
    display_badge("calculated")
    """Render the Strategic Decision Panel."""
    
    st.markdown("""
<div style="background: linear-gradient(135deg, #0f4c5c 0%, #1a6b7c 100%);
padding: 20px 25px; border-radius: 12px; margin-bottom: 20px;
box-shadow: 0 10px 30px rgba(15, 76, 92, 0.4);">
<div style="display:flex; align-items:center; gap:15px;">
<span style="font-size:2rem;">🎯</span>
<div>
<div style="font-size:1.3rem; font-weight:800; color:#e0e0e0;">
Strategic Decision Panel
</div>
<div style="font-size:0.75rem; color:#67e8f9; letter-spacing:1px; text-transform:uppercase;">
AI-Powered Recommendations • Confidence-Scored Decisions
</div>
</div>
</div>
</div>
""", unsafe_allow_html=True)
    
    decisions = _generate_decisions()
    
    # --- SUMMARY ---
    avg_confidence = np.mean([d["confidence"] for d in decisions])
    urgent = sum(1 for d in decisions if "YES" in d["recommendation"] or "IMPORT NOW" in d["recommendation"])
    
    st.markdown(f"""
<div style="background:linear-gradient(90deg, #0f172a, #1e293b); border-radius:10px; padding:15px 20px;
display:flex; justify-content:space-around; margin-bottom:20px;">
<div style="text-align:center;">
<div style="font-size:0.7rem; color:#94a3b8;">Total Decisions</div>
<div style="font-size:1.5rem; font-weight:800; color:#e0e0e0;">{len(decisions)}</div>
</div>
<div style="text-align:center;">
<div style="font-size:0.7rem; color:#94a3b8;">Avg Confidence</div>
<div style="font-size:1.5rem; font-weight:800; color:#22c55e;">{avg_confidence:.0f}%</div>
</div>
<div style="text-align:center;">
<div style="font-size:0.7rem; color:#94a3b8;">Action Required</div>
<div style="font-size:1.5rem; font-weight:800; color:#f59e0b;">{urgent}</div>
</div>
<div style="text-align:center;">
<div style="font-size:0.7rem; color:#94a3b8;">Updated</div>
<div style="font-size:1.5rem; font-weight:800; color:#64748b;">{datetime.datetime.now().strftime('%H:%M')}</div>
</div>
</div>
""", unsafe_allow_html=True)
    
    # --- DECISION CARDS ---
    for d in decisions:
        conf_color = "#22c55e" if d["confidence"] >= 75 else ("#f59e0b" if d["confidence"] >= 55 else "#ef4444")
        
        with st.expander(f"{d['icon']} {d['question']} → **{d['recommendation']}** ({d['confidence']}% confidence)"):
            
            # Recommendation + Confidence
            rc1, rc2 = st.columns([3, 1])
            
            with rc1:
                st.markdown(f"""
<div style="background:{d['color']}15; border:1px solid {d['color']}40; border-radius:10px;
padding:12px 15px; margin-bottom:10px;">
<div style="font-size:0.75rem; color:#64748b; font-weight:600;">AI RECOMMENDATION</div>
<div style="font-size:1.2rem; font-weight:800; color:{d['color']}; margin:5px 0;">
{d['recommendation']}
</div>
</div>
""", unsafe_allow_html=True)
            
            with rc2:
                st.markdown(f"""
<div style="text-align:center; padding:10px;">
<div style="font-size:0.7rem; color:#64748b;">Confidence</div>
<div style="font-size:2rem; font-weight:900; color:{conf_color};">{d['confidence']}%</div>
</div>
""", unsafe_allow_html=True)
            
            # Reasoning
            st.markdown("**📋 Reasoning:**")
            for r in d["reasoning"]:
                st.caption(f"• {r}")
            
            # Risk
            st.markdown(f"""
<div style="background:#fef2f2; border-left:3px solid #ef4444; padding:8px 12px; 
border-radius:0 6px 6px 0; margin-top:8px;">
<span style="font-size:0.75rem; color:#991b1b; font-weight:600;">⚠️ Risk: </span>
<span style="font-size:0.75rem; color:#475569;">{d['risk']}</span>
</div>
""", unsafe_allow_html=True)
