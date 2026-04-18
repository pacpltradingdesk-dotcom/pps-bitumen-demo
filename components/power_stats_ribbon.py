"""
Power Stats Ribbon — global "always visible" scale indicator.

Renders a thin row under the top bar on every page:

  📊 25,667 contacts · 56K rows live · VG30 ₹50,327 · 🟢 BULLISH 78 · ⚠️ 4 alerts

All reads are defensive — any failure falls back to "—" for that metric
so a missing table or cache never breaks the UI.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import streamlit as st

_ROOT = Path(__file__).resolve().parent.parent
_DB = _ROOT / "bitumen_dashboard.db"
_HUB_CACHE = _ROOT / "hub_cache.json"


def _count(table: str) -> int | None:
    try:
        conn = sqlite3.connect(_DB)
        try:
            return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        finally:
            conn.close()
    except Exception:
        return None


def _total_rows() -> int | None:
    parts = [_count(t) for t in ("contacts", "customers",
                                 "customer_profiles", "suppliers")]
    parts = [p for p in parts if p is not None]
    if not parts:
        return None
    return sum(parts)


def _vg30_price() -> int | None:
    """Return VG30 price ₹/MT from hub cache, best-effort."""
    try:
        data = json.loads(_HUB_CACHE.read_text(encoding="utf-8"))
    except Exception:
        return None
    # Current schema: hub_cache["iocl_circular"]["data"]["snapshot"]["VG30_IOCL_Koyali_basic_per_MT"] = 42000
    try:
        snap = data.get("iocl_circular", {}).get("data", {}).get("snapshot", {})
        preferred = [
            "VG30_IOCL_Koyali_basic_per_MT",
            "VG30_IOCL_Mathura_basic_per_MT",
            "VG30_BPCL_Mumbai_basic_per_MT",
            "VG30_HPCL_Mumbai_basic_per_MT",
        ]
        for key in preferred:
            v = snap.get(key)
            if isinstance(v, (int, float)) and v > 0:
                return int(v)
        # Fallback: average any VG30_* basic keys
        vals = [v for k, v in snap.items()
                if k.startswith("VG30_") and "basic" in k and isinstance(v, (int, float)) and v > 0]
        if vals:
            return int(sum(vals) / len(vals))
    except Exception:
        pass
    # Legacy shapes (kept for forward-compat)
    for path in (
        ("markets", "bitumen", "vg30_mumbai"),
        ("bitumen", "vg30", "price"),
        ("vg30_mumbai",),
        ("markets", "vg30"),
    ):
        d = data
        try:
            for k in path:
                d = d[k]
            if isinstance(d, (int, float)):
                return int(d)
            if isinstance(d, dict) and "value" in d:
                return int(d["value"])
        except Exception:
            continue
    return None


_DIRECTION_LABEL = {"UP": "BULLISH", "DOWN": "BEARISH", "SIDEWAYS": "NEUTRAL"}


def _composite_signal() -> tuple[str, int] | None:
    """Return (label, score) for the 10-signal master composite.

    Reads cached tbl_market_signals.json (refreshed by sync_engine every 60 min).
    Shape: [{computed_at, signals: {crude_market, ..., master}}, ...]
    Master fields: market_direction (UP/DOWN/SIDEWAYS), confidence (0-100).
    """
    try:
        data = json.loads((_ROOT / "tbl_market_signals.json").read_text(encoding="utf-8"))
        if isinstance(data, list) and data:
            last = data[-1]
            master = (last.get("signals") or {}).get("master") or {}
            direction = master.get("market_direction")
            confidence = master.get("confidence")
            if direction and confidence is not None:
                label = _DIRECTION_LABEL.get(str(direction).upper(), str(direction).upper())
                return (label, int(confidence))
    except Exception:
        pass
    return None


def _alerts_count() -> int | None:
    """Count active alerts — SRE + market, matching what command_center shows."""
    total = 0
    seen = False
    for fname in ("sre_alerts.json", "market_alerts.json"):
        try:
            data = json.loads((_ROOT / fname).read_text(encoding="utf-8"))
        except Exception:
            continue
        seen = True
        if isinstance(data, list):
            total += sum(1 for a in data
                         if isinstance(a, dict) and a.get("status") != "dismissed")
        elif isinstance(data, dict):
            total += len(data.get("active", []))
    return total if seen else None


def _fmt_int(n: int | None) -> str:
    """Indian comma format up to 1M, then M-suffix."""
    if n is None:
        return "—"
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n < 1000:
        return str(n)
    s = str(n)
    last3 = s[-3:]
    rest = s[:-3]
    groups = []
    while rest:
        groups.insert(0, rest[-2:])
        rest = rest[:-2]
    return ",".join(groups) + "," + last3


def _fmt_price(n: int | None) -> str:
    if n is None:
        return "—"
    return f"₹{_fmt_int(n)}"


def _dot_for(label: str | None) -> str:
    if not label:
        return "⚪"
    l = label.upper()
    if "BULL" in l:
        return "🟢"
    if "BEAR" in l:
        return "🔴"
    return "🟡"


def render_power_stats_ribbon() -> None:
    """Mount the ribbon. Safe to call on every rerun."""
    contacts = _count("contacts")
    rows = _total_rows()
    vg30 = _vg30_price()
    sig = _composite_signal()
    alerts = _alerts_count()

    sig_dot, sig_text = ("⚪", "SIGNAL —")
    if sig:
        sig_dot = _dot_for(sig[0])
        sig_text = f"{sig[0]} {sig[1]}"

    alerts_text = f"⚠️ {alerts} alerts" if alerts is not None else "⚠️ — alerts"

    parts = [
        f"📊 <b>{_fmt_int(contacts)}</b> contacts",
        f"🗄️ <b>{_fmt_int(rows)}</b> rows live",
        f"💵 VG30 <b>{_fmt_price(vg30)}</b>",
        f"{sig_dot} <b>{sig_text}</b>",
        f"<span style='color:#B45309;'>{alerts_text}</span>",
    ]
    sep = " <span style='opacity:0.35;padding:0 6px;'>·</span> "

    st.markdown(
        f"""
<div style="
    background:linear-gradient(90deg,#0B1220 0%,#11192D 100%);
    color:#F5F7FC;
    border-bottom:1px solid #2A3450;
    padding:6px 18px;
    font-size:0.78rem;
    letter-spacing:0.01em;
    font-family:-apple-system,'Segoe UI',sans-serif;
    margin:-8px -1rem 12px -1rem;
    white-space:nowrap;
    overflow-x:auto;
">
{sep.join(parts)}
</div>
""",
        unsafe_allow_html=True,
    )
