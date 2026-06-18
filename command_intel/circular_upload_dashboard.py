"""
PPS Anantam — Update Prices from Circular (Vision upload + human review).

Flow: upload the fortnightly Multi Energy circular image -> Claude vision
extracts the Bitumen (Bulk) table -> circular_parser maps to price_master keys
with a sanity band -> show an old-vs-new diff -> on confirm, write the overrides
to live_prices.json so the whole dashboard reflects them (single source).

Human-in-the-loop: nothing is written until the user clicks Apply, so a misread
number can never reach the live board.
"""
from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

_BASE = Path(__file__).parent.parent
_LIVE_PRICES = _BASE / "live_prices.json"


def _current_value_map() -> dict:
    """key -> current ₹ value, from live_prices overrides on top of price_master."""
    out: dict = {}
    try:
        import price_master as pm
        for r in pm.ALL_RECS:
            out[r.key] = r.price
        out.update(pm.DRUM_PRICES)
        out["VG30_BASE"] = pm.VG30_BASE
    except Exception:
        pass
    try:
        if _LIVE_PRICES.exists():
            out.update(json.loads(_LIVE_PRICES.read_text(encoding="utf-8")))
    except Exception:
        pass
    return out


def _apply_overrides(updates: dict, vg30_base) -> bool:
    """Merge updates (+ VG30_BASE) into live_prices.json. Returns success."""
    try:
        lp = {}
        if _LIVE_PRICES.exists():
            lp = json.loads(_LIVE_PRICES.read_text(encoding="utf-8")) or {}
        lp.update({k: int(v) for k, v in updates.items()})
        if vg30_base:
            lp["VG30_BASE"] = int(vg30_base)
        _LIVE_PRICES.write_text(json.dumps(lp, indent=4, ensure_ascii=False), encoding="utf-8")
        try:
            from calculation_engine import get_engine
            get_engine().reload_prices()
        except Exception:
            pass
        return True
    except Exception:
        return False


def render():
    st.header("📋 Update Prices from Circular")
    st.caption(
        "Upload the fortnightly Multi Energy price circular (image). The system "
        "reads the Bitumen (Bulk) table, you review the changes, then Apply — "
        "prices update everywhere (ticker, calculator, brief)."
    )

    up = st.file_uploader("Circular image (JPG / PNG)", type=["jpg", "jpeg", "png"])
    if up is None:
        st.info("Drag-drop or browse the circular image to begin.")
        return

    st.image(up, caption="Uploaded circular", use_container_width=True)

    if st.button("🔍 Read prices from this circular", type="primary"):
        with st.spinner("Reading circular with AI vision…"):
            from circular_extract import extract_rows
            mt = "image/png" if up.type and "png" in up.type else "image/jpeg"
            res = extract_rows(up.getvalue(), media_type=mt)
        if res.get("error"):
            st.error(f"Could not read automatically: {res['error']}")
            st.caption("You can still update prices manually via Manual Price Entry → Refinery/Import Override.")
            return
        from circular_parser import build_updates
        st.session_state["_circ_result"] = build_updates(res.get("rows", []))

    result = st.session_state.get("_circ_result")
    if not result:
        return

    updates = result.get("updates", {})
    if not updates:
        st.warning("No usable price rows found. Try a clearer image, or use Manual Price Entry.")
        if result.get("unmatched"):
            st.caption(f"Unmatched rows: {len(result['unmatched'])}")
        return

    # ── Review: old vs new diff ──
    current = _current_value_map()
    st.subheader("Review changes")
    rows = []
    for key, new_val in sorted(updates.items()):
        old_val = current.get(key)
        delta = (new_val - old_val) if isinstance(old_val, (int, float)) else None
        rows.append({
            "Price Key": key,
            "Current ₹/MT": f"{old_val:,}" if isinstance(old_val, (int, float)) else "—",
            "New ₹/MT": f"{new_val:,}",
            "Change": (f"{'+' if delta >= 0 else ''}{delta:,}" if delta is not None else "new"),
        })
    st.dataframe(rows, use_container_width=True, hide_index=True)
    if result.get("vg30_base"):
        st.metric("New headline VG30 base", f"₹{int(result['vg30_base']):,}/MT")

    if result.get("rejected"):
        st.warning(f"⚠️ {len(result['rejected'])} row(s) rejected (price out of sane band) — not applied.")
    if result.get("unmatched"):
        st.caption(f"{len(result['unmatched'])} row(s) had an unknown location/grade and were skipped.")

    c1, c2 = st.columns([1, 3])
    if c1.button("✅ Apply these prices", type="primary"):
        if _apply_overrides(updates, result.get("vg30_base")):
            st.success(f"Applied {len(updates)} prices. Now live across the dashboard.")
            st.session_state.pop("_circ_result", None)
            st.rerun()
        else:
            st.error("Could not write prices. Check file permissions.")
    if c2.button("Discard"):
        st.session_state.pop("_circ_result", None)
        st.rerun()
