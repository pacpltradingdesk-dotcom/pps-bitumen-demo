import datetime
import json
import random
from pathlib import Path

import yfinance as yf
from api_manager import fetch_api_data

_ROOT = Path(__file__).parent
_HUB_CACHE_PATH = _ROOT / "hub_cache.json"
_LIVE_PRICES_PATH = _ROOT / "live_prices.json"

# Reject time-series records older than this when picking the "current" price.
# Prevents a stalled feed (multi-month gap) from surfacing a months-old record
# as today's price — the root cause of brent 95.68 (April) / usdinr 93.1 (March)
# leaking in. When every record is stale, selection falls through to the live
# fetch / deterministic default instead.
_MAX_PRICE_AGE_DAYS = 3.0
_TS_FORMATS = ("%Y-%m-%d %H:%M:%S", "%d-%m-%Y %H:%M:%S", "%Y-%m-%d", "%d-%m-%Y")


def _rec_too_old(rec: dict, max_days: float = _MAX_PRICE_AGE_DAYS) -> bool:
    """True if rec's timestamp is older than max_days. Missing/unparseable
    timestamps are treated as fresh (False) so we never over-reject good data."""
    ts = str(rec.get("date_time") or rec.get("date") or rec.get("timestamp") or "").strip()
    if not ts:
        return False
    ts = ts.replace(" IST", "").strip()[:19]
    for fmt in _TS_FORMATS:
        try:
            dt = datetime.datetime.strptime(ts, fmt)
            return (datetime.datetime.now() - dt).total_seconds() > max_days * 86400
        except ValueError:
            continue
    return False


def _series_change_pct(rows, match, price_field="price", lookback=7):
    """% change of the latest matching record vs ~`lookback` records earlier.
    `rows` are in chronological (file) order. Returns 0.0 if <2 usable points.
    Used to populate *_chg_pct on the normal JSON path — previously these were
    only set in the live-fetch fallback, so the pulse bar was frozen at +0.00%."""
    seq = []
    for rec in (rows if isinstance(rows, list) else []):
        if not isinstance(rec, dict) or not match(rec):
            continue
        v = rec.get(price_field)
        try:
            if v is not None:
                seq.append(float(v))
        except (TypeError, ValueError):
            continue
    if len(seq) < 2:
        return 0.0
    prior = seq[max(0, len(seq) - 1 - lookback)]
    if not prior:
        return 0.0
    return (seq[-1] - prior) / prior * 100


def get_unified_prices() -> dict:
    """SINGLE SOURCE OF TRUTH for Brent/WTI/USD-INR/VG30 across every UI component.

    Read priority (high to low):
      1. hub_cache.json — populated by background API-refresh daemon from
         yfinance (crude) + Frankfurter/ECB (fx). Authoritative live snapshot.
      2. fetch_api_data() fallback — direct yfinance call if hub_cache empty.
      3. Hard coded deterministic defaults — NEVER randomized (randomized
         fallbacks were the root cause of cross-component divergence).

    Returns flat dict: {brent, wti, usdinr, vg30, brent_chg_pct, wti_chg_pct,
    usdinr_chg_pct, vg30_chg_pct, timestamp, source}. Values are floats (prices)
    / percentages (floats), NOT preformatted strings — each consumer formats
    its own way. This prevents format-string divergence.
    """
    out = {
        "brent": None, "wti": None, "usdinr": None, "vg30": None,
        "brent_chg_pct": 0.0, "wti_chg_pct": 0.0,
        "usdinr_chg_pct": 0.0, "vg30_chg_pct": 0.0,
        "timestamp": "",
        "source": "unknown",
    }

    # ── 0. Canonical time-series files (the SAME data the Global Market
    # Dashboard charts). Reading the latest point from these makes every page
    # (Command Center, Live Market, FX Monitor, charts) agree — fixes the
    # "USD/INR shows 94.72 here but 86.19 there" inconsistency. ────────────
    _root = _HUB_CACHE_PATH.parent
    try:
        crude = json.loads((_root / "tbl_crude_prices.json").read_text(encoding="utf-8"))
        rows = crude if isinstance(crude, list) else crude.get("data", [])
        for rec in reversed(rows if isinstance(rows, list) else []):
            if not isinstance(rec, dict):
                continue
            # Skip monthly-average rows (e.g. OPEC monthly) — use only live dailies.
            if rec.get("period_label") or _rec_too_old(rec):
                continue
            b = str(rec.get("benchmark", "")).lower()
            p = rec.get("price")
            if p is None:
                continue
            if "brent" in b and out["brent"] is None:
                out["brent"] = float(p)
                out["timestamp"] = rec.get("date_time", "")
            elif "wti" in b and out["wti"] is None:
                out["wti"] = float(p)
            if out["brent"] is not None and out["wti"] is not None:
                break
        # 7-day change from the same series so the pulse bar isn't frozen green.
        if out["brent"] is not None:
            out["brent_chg_pct"] = _series_change_pct(
                rows, lambda r: ("brent" in str(r.get("benchmark", "")).lower()
                                 and not r.get("period_label")))
        if out["wti"] is not None:
            out["wti_chg_pct"] = _series_change_pct(
                rows, lambda r: ("wti" in str(r.get("benchmark", "")).lower()
                                 and not r.get("period_label")))
    except Exception:
        pass
    try:
        fx = json.loads((_root / "tbl_fx_rates.json").read_text(encoding="utf-8"))
        rows = fx if isinstance(fx, list) else fx.get("data", [])
        for rec in reversed(rows if isinstance(rows, list) else []):
            if isinstance(rec, dict) and "INR" in str(rec.get("pair", "")).upper():
                # Skip monthly-average proxy rows (period_label): they carry a stale
                # month value stamped with a fresh timestamp and would otherwise
                # override the live spot USD/INR (yfinance INR=X / Frankfurter daily).
                if rec.get("period_label") or _rec_too_old(rec):
                    continue
                r = rec.get("rate")
                if r:
                    out["usdinr"] = float(r)
                    break
        if out["usdinr"] is not None:
            out["usdinr_chg_pct"] = _series_change_pct(
                rows, lambda r: ("INR" in str(r.get("pair", "")).upper()
                                 and not r.get("period_label")), "rate")
    except Exception:
        pass
    if out["brent"] or out["wti"] or out["usdinr"]:
        out["source"] = "tbl_series"

    # ── 1. Try hub_cache.json (authoritative) ────────────────────────────
    try:
        hub = json.loads(_HUB_CACHE_PATH.read_text(encoding="utf-8"))
        crude_rows = hub.get("eia_crude", {}).get("data", [])
        brent_from_hub = wti_from_hub = usd_from_hub = False
        if isinstance(crude_rows, list):
            for rec in crude_rows:
                if not isinstance(rec, dict):
                    continue
                if _rec_too_old(rec):
                    continue
                b = rec.get("benchmark", "").lower()
                p = rec.get("price")
                if p is None:
                    continue
                if "brent" in b and out["brent"] is None:
                    out["brent"] = float(p)
                    out["timestamp"] = rec.get("date_time", "")
                    brent_from_hub = True
                elif "wti" in b and out["wti"] is None:
                    out["wti"] = float(p)
                    wti_from_hub = True
        fx_rows = hub.get("frankfurter_fx", hub.get("fx", {})).get("data", [])
        if isinstance(fx_rows, list):
            for rec in fx_rows:
                if not isinstance(rec, dict):
                    continue
                if rec.get("period_label") or _rec_too_old(rec):
                    continue  # skip monthly-avg proxy; live spot only
                if "INR" in rec.get("pair", "").upper() and out["usdinr"] is None:
                    out["usdinr"] = float(rec.get("rate", 0) or 0) or None
                    usd_from_hub = out["usdinr"] is not None
        # Recompute change % from the hub series for any benchmark whose price
        # came from hub_cache — otherwise the pulse bar shows a live hub price
        # with a frozen +0.00% (section-0 default that was never overwritten).
        if brent_from_hub and isinstance(crude_rows, list):
            out["brent_chg_pct"] = _series_change_pct(
                crude_rows, lambda r: "brent" in str(r.get("benchmark", "")).lower())
        if wti_from_hub and isinstance(crude_rows, list):
            out["wti_chg_pct"] = _series_change_pct(
                crude_rows, lambda r: "wti" in str(r.get("benchmark", "")).lower())
        if usd_from_hub and isinstance(fx_rows, list):
            out["usdinr_chg_pct"] = _series_change_pct(
                fx_rows, lambda r: "INR" in str(r.get("pair", "")).upper(), "rate")
        if out["brent"] or out["wti"] or out["usdinr"]:
            out["source"] = "hub_cache"
    except Exception:
        pass

    # ── 2. Live fetch fallback (only for keys still missing) ─────────────
    try:
        if out["brent"] is None:
            d = fetch_api_data("brent")
            if d and "current" in d:
                out["brent"] = float(d["current"])
                if "history_7d" in d and d["history_7d"]:
                    out["brent_chg_pct"] = ((out["brent"] - float(d["history_7d"])) /
                                             float(d["history_7d"])) * 100
                out["source"] = out["source"] if out["source"] != "unknown" else "live_api"
        if out["wti"] is None:
            d = fetch_api_data("wti")
            if d and "current" in d:
                out["wti"] = float(d["current"])
                if "history_7d" in d and d["history_7d"]:
                    out["wti_chg_pct"] = ((out["wti"] - float(d["history_7d"])) /
                                           float(d["history_7d"])) * 100
        if out["usdinr"] is None:
            d = fetch_api_data("usdinr")
            if d and "current" in d:
                out["usdinr"] = float(d["current"])
                if "history_7d" in d and d["history_7d"]:
                    out["usdinr_chg_pct"] = ((out["usdinr"] - float(d["history_7d"])) /
                                              float(d["history_7d"])) * 100
    except Exception:
        pass

    # ── 3. VG30 bitumen base (Indian domestic bulk, not from crude/fx APIs) ──
    # Real Ex-Mumbai bulk VG30 (60/70) reference. Reads the dedicated VG30_BASE
    # key; falls back to the legacy DRUM_KANDLA_VG30 key, then a real default.
    # Source: All India Petroleum Products Price Revision (Multi Energy).
    try:
        from price_master import VG30_BASE as _VG30_BASE
    except Exception:
        _VG30_BASE = 76870
    try:
        lp = json.loads(_LIVE_PRICES_PATH.read_text(encoding="utf-8"))
        out["vg30"] = float(lp.get("VG30_BASE") or lp.get("DRUM_KANDLA_VG30") or _VG30_BASE)
    except Exception:
        out["vg30"] = float(_VG30_BASE)

    # ── 4. Deterministic defaults (NEVER random) ─────────────────────────
    # Aligned with get_simulated_data() Q1-2026 baselines so the two last-resort
    # fallback paths don't disagree ~25% (was 98/89/93 here vs 75.5/71.5/86.8).
    if out["brent"] is None:
        out["brent"] = 75.5
    if out["wti"] is None:
        out["wti"] = 71.5
    if out["usdinr"] is None:
        out["usdinr"] = 86.8
    if not out["timestamp"]:
        out["timestamp"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M IST")
    if out["source"] == "unknown":
        out["source"] = "fallback"

    # ── 5. VG30 auto-drift: DISABLED ─────────────────────────────────────────
    # The intra-fortnight drift nudged VG30 with crude/FX moves since the circular,
    # so the board showed a price the user never set (e.g. set ₹77,000 → shown
    # ₹75,155 after Brent fell). For a *quoting* board the displayed VG30 MUST equal
    # the published/set base — drift = unauthorised quote risk. So VG30 = the set
    # VG30_BASE as-is. (Crude/FX still move on their own cards.) To re-enable, restore
    # the price_drift.drift_vg30(...) call here.

    return out

def format_change(chg_7d):
    color = "green" if chg_7d >= 0 else "red"
    return f"{chg_7d:+.2f}%", color

def get_live_market_data():
    """
    Build the market dict from the SINGLE SOURCE OF TRUTH get_unified_prices()
    so every surface (Command Center, Live Market pulse bar, ticker) shows the
    SAME Brent / WTI / USD-INR. (Previously this hit fetch_api_data() directly
    and the dashboard defaulted to get_simulated_data(), so pages disagreed.)
    """
    data = {}
    try:
        u = get_unified_prices() or {}
    except Exception:
        u = {}

    def _block(key, prefix):
        val = u.get(key)
        if val is None:
            return {"value": "N/A", "value_7d": "N/A", "change": "0.00%", "color": "grey"}
        chg = float(u.get(f"{key}_chg_pct", 0.0) or 0.0)
        chg_str, color = format_change(chg)
        v = float(val)
        v7 = v / (1 + chg / 100) if chg else v
        return {"value": f"{prefix}{v:.2f}", "value_7d": f"{prefix}{v7:.2f}",
                "change": chg_str, "color": color}

    data['brent']  = _block('brent', "$")
    data['wti']    = _block('wti', "$")
    data['usdinr'] = _block('usdinr', "")

    # If the single source has nothing at all, fall back to the offline simulator.
    if data['brent']['value'] == "N/A" and data['usdinr']['value'] == "N/A":
        return get_simulated_data()

    # 4. DXY
    dxy_data = fetch_api_data("dxy")
    if dxy_data and 'current' in dxy_data:
        curr = float(dxy_data['current'])
        hist = float(dxy_data.get('history_7d', curr))
        chg = ((curr - hist) / hist) * 100 if hist else 0.0
        chg_str, color = format_change(chg)
        data['dxy'] = {"value": f"{curr:.2f}", "value_7d": f"{hist:.2f}", "change": chg_str, "color": color}
    else:
        data['dxy'] = {"value": "N/A", "value_7d": "N/A", "change": "0.00%", "color": "grey"}
        
    # 5. Timestamp
    time_data = fetch_api_data("current_time")
    if time_data and 'current' in time_data:
        data['timestamp'] = f"{time_data['current']} IST"
    else:
        data['timestamp'] = datetime.datetime.now().strftime("%H:%M IST")

    return data

def get_simulated_data():
    """Fallback if internet is completely down. Baselines updated Q1 2026."""
    brent  = 75.50 + random.uniform(-0.5, 0.5)
    wti    = 71.50 + random.uniform(-0.5, 0.5)
    usdinr = 86.80 + random.uniform(-0.15, 0.15)
    dxy    = 104.2

    brent_7d  = brent  / 1.008
    wti_7d    = wti    / 0.994
    usdinr_7d = usdinr / 1.003

    chg_b = f"{((brent  - brent_7d)  / brent_7d  * 100):+.2f}%"
    chg_w = f"{((wti    - wti_7d)    / wti_7d    * 100):+.2f}%"
    chg_fx = f"{((usdinr - usdinr_7d) / usdinr_7d * 100):+.2f}%"

    return {
        "brent":  {"value": f"${brent:.2f}",   "value_7d": f"${brent_7d:.2f}",   "change": chg_b,  "color": "green" if brent  > brent_7d  else "red"},
        "wti":    {"value": f"${wti:.2f}",     "value_7d": f"${wti_7d:.2f}",     "change": chg_w,  "color": "green" if wti    > wti_7d    else "red"},
        "usdinr": {"value": f"{usdinr:.2f}",   "value_7d": f"{usdinr_7d:.2f}",   "change": chg_fx, "color": "green" if usdinr > usdinr_7d else "red"},
        "dxy":    {"value": f"{dxy:.2f}",      "value_7d": "104.20",             "change": "0.0%", "color": "grey"},
        "timestamp": datetime.datetime.now().strftime("%H:%M IST (Offline)"),
    }
