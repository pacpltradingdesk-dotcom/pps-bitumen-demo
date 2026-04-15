"""
Hero "Today's Call" card — the dominant decision artifact at the top
of the Command Center.

Reads the latest master composite signal from tbl_market_signals.json
and renders a single big card:

  TODAY'S CALL: BUY (or SELL / HOLD)
  Confidence 78% · MEDIUM risk · STRONG demand
  Action: <recommended_action>

Defensive: if the cache is missing or malformed, falls back to a
neutral HOLD card so the page never blows up.
"""
from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

_ROOT = Path(__file__).resolve().parent.parent
_SIGNALS = _ROOT / "tbl_market_signals.json"


def _load_master() -> dict | None:
    try:
        data = json.loads(_SIGNALS.read_text(encoding="utf-8"))
        if isinstance(data, list) and data:
            return data[-1].get("signals", {}).get("master")
    except Exception:
        return None
    return None


def _verdict(master: dict | None) -> dict:
    """Map master signal → display fields."""
    if not master:
        return {
            "verdict": "HOLD",
            "color": "#6B7280",
            "bg": "#F3F4F6",
            "subtitle": "Awaiting first market computation",
            "confidence": None,
            "risk": None,
            "demand": None,
            "action": "Run the market intelligence engine to refresh signals.",
        }
    direction = (master.get("market_direction") or "SIDEWAYS").upper()
    score = master.get("weighted_score", 0.0) or 0.0
    confidence = master.get("confidence")
    risk = master.get("risk_level")
    demand = master.get("demand_outlook")
    action = master.get("recommended_action") or ""

    if direction == "UP":
        verdict = "BUY"
        color, bg = "#047857", "#ECFDF5"
        subtitle = "Market trending up — procurement window favorable"
    elif direction == "DOWN":
        verdict = "WAIT"
        color, bg = "#B45309", "#FEF3C7"
        subtitle = "Prices easing — defer non-urgent purchases"
    else:
        verdict = "HOLD"
        color, bg = "#475569", "#F1F5F9"
        subtitle = "Market sideways — follow normal procurement rhythm"

    # Risk override: HIGH risk + sideways/down → BUY signal (lock supply)
    if risk == "HIGH" and verdict in ("WAIT", "HOLD"):
        verdict = "SECURE"
        color, bg = "#C2410C", "#FFF7ED"
        subtitle = "High risk — lock in reliable supply now"

    return {
        "verdict": verdict,
        "color": color,
        "bg": bg,
        "subtitle": subtitle,
        "confidence": confidence,
        "risk": risk,
        "demand": demand,
        "action": action,
        "score": score,
    }


def render_hero_call_card() -> None:
    """Drop-in for the top of Command Center."""
    master = _load_master()
    v = _verdict(master)

    # Stat strip — confidence / risk / demand
    stats: list[str] = []
    if v["confidence"] is not None:
        stats.append(f"<b>Confidence</b> {v['confidence']}%")
    if v["risk"]:
        stats.append(f"<b>Risk</b> {v['risk']}")
    if v["demand"]:
        stats.append(f"<b>Demand</b> {v['demand']}")
    stats_html = " · ".join(stats) if stats else "—"

    st.markdown(
        f"""
<div style="
  position:relative;
  background:linear-gradient(135deg,{v['bg']} 0%,#FFFFFF 60%);
  border:1px solid {v['color']}33;
  border-left:6px solid {v['color']};
  border-radius:14px;
  padding:20px 24px 18px 24px;
  margin:4px 0 18px 0;
  box-shadow:0 4px 14px {v['color']}14;
">
  <div style="display:flex;align-items:baseline;justify-content:space-between;flex-wrap:wrap;gap:12px;">
    <div>
      <div style="font-size:0.7rem;font-weight:800;letter-spacing:0.14em;
                  color:{v['color']};text-transform:uppercase;opacity:0.85;">
        ⚡ Today's Call · 10-Signal Composite
      </div>
      <div style="font-size:2.2rem;font-weight:900;color:{v['color']};
                  line-height:1.1;margin-top:2px;letter-spacing:-0.02em;">
        {v['verdict']}
      </div>
    </div>
    <div style="text-align:right;font-size:0.78rem;color:#475569;">
      {stats_html}
    </div>
  </div>
  <div style="margin-top:6px;font-size:0.95rem;color:#1F2937;font-weight:500;">
    {v['subtitle']}
  </div>
  <div style="margin-top:10px;font-size:0.82rem;color:#475569;
              border-top:1px solid #E5E7EB;padding-top:8px;">
    <b style="color:#0F172A;">AI Recommendation:</b> {v['action']}
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
