"""
PPS Anantam Agentic AI Eco System
Highway KM vs Bitumen Demand Correlation Engine v1.0
=====================================================
Cross-lag Pearson correlation + OLS regression between:
  X: km_completed from tbl_highway_km.json (lagged 0–6 months)
  Y: demand_proxy from tbl_imports_countrywise.json (total HS 271320 monthly imports)
Controls: crude_price (tbl_crude_prices), fx_usdinr (tbl_fx_rates)

Outputs:
  tbl_corr_results.json       — lag × correlation table
  tbl_regression_coeff.json   — OLS coefficients with interpretation
  tbl_insights.json           — auto-generated insight strings

Uses only stdlib + pandas + numpy. scipy.stats used if available,
falls back to manual t-test for p-values.
"""

import json
import math
import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict

import pytz

try:
    import pandas as pd
    import numpy as np
    _PANDAS = True
except ImportError:
    _PANDAS = False

try:
    from scipy import stats as _scipy_stats
    _SCIPY = True
except ImportError:
    _SCIPY = False

try:
    from api_hub_engine import _load, _save, _ts, BASE
except ImportError:
    import threading
    BASE = Path(__file__).parent
    def _load(p, d):
        try:
            if Path(p).exists():
                return json.load(open(p, encoding="utf-8"))
        except Exception:
            pass
        return d
    def _save(p, data):
        Path(p).parent.mkdir(parents=True, exist_ok=True)
        json.dump(data, open(p,"w",encoding="utf-8"), indent=2, ensure_ascii=False, default=str)
    def _ts():
        return datetime.datetime.now(pytz.timezone("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S IST")


# ─── Output table paths ────────────────────────────────────────────────────────
TBL_CORR   = BASE / "tbl_corr_results.json"
TBL_REGR   = BASE / "tbl_regression_coeff.json"
TBL_INSIGH = BASE / "tbl_insights.json"


# ─────────────────────────────────────────────────────────────────────────────
# DATA LOADING — monthly time series
# ─────────────────────────────────────────────────────────────────────────────

def _period_to_ym(p: str) -> Optional[Tuple[int, int]]:
    """Parse 'YYYY-MM' or 'YYYY' into (year, month). Returns None on failure."""
    p = str(p).strip()
    if len(p) >= 7 and p[4] == "-":
        try:
            return int(p[:4]), int(p[5:7])
        except ValueError:
            pass
    if len(p) == 4:
        try:
            return int(p), 1
        except ValueError:
            pass
    return None


def _month_key(year: int, month: int) -> str:
    return f"{year}-{month:02d}"


def load_monthly_series() -> "pd.DataFrame":
    """
    Build a monthly-frequency DataFrame aligned on period_label (YYYY-MM).
    Columns: period_label, km_completed, demand_proxy_mt, crude_usd, fx_usdinr
    Missing values forward-filled (not zero-filled).
    """
    if not _PANDAS:
        raise ImportError("pandas is required for correlation analysis")

    # ── Highway KM ─────────────────────────────────────────────────────────
    hw_rows = _load(BASE / "tbl_highway_km.json", [])
    # Filter All India, sum across agencies per period
    hw_monthly: Dict[str, float] = defaultdict(float)
    for r in hw_rows:
        ym = _period_to_ym(r.get("period_label", ""))
        if ym is None:
            continue
        if r.get("state", "").startswith("All India"):
            key = _month_key(*ym)
            km  = float(r.get("km_completed", 0) or 0)
            hw_monthly[key] = max(hw_monthly[key], km)  # take max if multiple agency rows

    # ── Demand proxy (HS 271320 total imports into India in MT) ────────────
    imp_rows = _load(BASE / "tbl_imports_countrywise.json", [])
    dem_monthly: Dict[str, float] = defaultdict(float)
    for r in imp_rows:
        ym = _period_to_ym(r.get("period_label", ""))
        if ym is None:
            continue
        # Convert annual data to monthly average (divide by 12)
        qty_kg = float(r.get("qty_kg", 0) or 0)
        key    = _month_key(*ym)
        dem_monthly[key] += qty_kg / 1000.0 / 12.0  # MT per month estimate

    # If no countrywise data, fallback to tbl_trade_imports aggregate
    if not dem_monthly:
        trade_rows = _load(BASE / "tbl_trade_imports.json", [])
        for r in trade_rows:
            ym = _period_to_ym(r.get("date", r.get("period_label", "")))
            if ym is None:
                continue
            qty = float(r.get("quantity", 0) or 0)
            key = _month_key(*ym)
            dem_monthly[key] += qty / 1000.0 / 12.0

    # ── Crude price (monthly avg from tbl_crude_prices) ────────────────────
    crude_rows  = _load(BASE / "tbl_crude_prices.json", [])
    crude_m: Dict[str, list] = defaultdict(list)
    for r in crude_rows:
        dt_str = r.get("date_time", r.get("date", ""))
        # date_time is "DD-MM-YYYY HH:MM:SS IST" format
        try:
            if len(dt_str) >= 10:
                if dt_str[2] == "-":  # DD-MM-YYYY
                    key = f"{dt_str[6:10]}-{dt_str[3:5]}"
                else:                 # YYYY-MM-DD
                    key = dt_str[:7]
                crude_m[key].append(float(r.get("price", 0) or 0))
        except Exception:
            pass
    crude_monthly: Dict[str, float] = {
        k: round(sum(v)/len(v), 2) for k, v in crude_m.items() if v
    }

    # ── FX USD/INR (monthly avg) ────────────────────────────────────────────
    # period_label takes priority (historical records have "YYYY-MM");
    # fall back to date_time (fetch-time stamp "DD-MM-YYYY HH:MM:SS IST")
    fx_rows    = _load(BASE / "tbl_fx_rates.json", [])
    fx_m: Dict[str, list] = defaultdict(list)
    for r in fx_rows:
        if "INR" not in r.get("pair", ""):
            continue
        dt_str = r.get("period_label", r.get("date_time", r.get("date", "")))
        try:
            if len(dt_str) >= 7:
                if dt_str[2] == "-":      # DD-MM-YYYY ... (fetch timestamp)
                    key = f"{dt_str[6:10]}-{dt_str[3:5]}"
                elif "-" in dt_str:       # YYYY-MM or YYYY-MM-DD (period_label)
                    key = dt_str[:7]
                else:
                    continue
                fx_m[key].append(float(r.get("rate", 0) or 0))
        except Exception:
            pass
    fx_monthly: Dict[str, float] = {
        k: round(sum(v)/len(v), 4) for k, v in fx_m.items() if v
    }

    # ── Assemble DataFrame ──────────────────────────────────────────────────
    all_periods = sorted(set(
        list(hw_monthly.keys()) +
        list(dem_monthly.keys()) +
        list(crude_monthly.keys()) +
        list(fx_monthly.keys())
    ))

    if not all_periods:
        return pd.DataFrame(columns=[
            "period_label", "km_completed", "demand_proxy_mt",
            "crude_usd", "fx_usdinr"
        ])

    rows = []
    for p in all_periods:
        rows.append({
            "period_label":    p,
            "km_completed":    hw_monthly.get(p, float("nan")),
            "demand_proxy_mt": dem_monthly.get(p, float("nan")),
            "crude_usd":       crude_monthly.get(p, float("nan")),
            "fx_usdinr":       fx_monthly.get(p, float("nan")),
        })

    df = pd.DataFrame(rows)
    df = df.sort_values("period_label").reset_index(drop=True)
    # Forward-fill missing values (never fake zeros)
    df = df.ffill().bfill()
    return df


# ─────────────────────────────────────────────────────────────────────────────
# PEARSON CORRELATION — manual implementation (no scipy required)
# ─────────────────────────────────────────────────────────────────────────────

def _pearson(x: list, y: list) -> Tuple[float, float, int]:
    """Returns (r, p_value, n) using manual formula."""
    pairs = [(xi, yi) for xi, yi in zip(x, y)
             if xi is not None and yi is not None
             and not math.isnan(xi) and not math.isnan(yi)]
    n = len(pairs)
    if n < 4:
        return 0.0, 1.0, n

    xs, ys = zip(*pairs)
    n  = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    cov  = sum((xi - mx) * (yi - my) for xi, yi in zip(xs, ys))
    sdx  = math.sqrt(sum((xi - mx) ** 2 for xi in xs))
    sdy  = math.sqrt(sum((yi - my) ** 2 for yi in ys))

    if sdx == 0 or sdy == 0:
        return 0.0, 1.0, n

    r = cov / (sdx * sdy)
    r = max(-1.0, min(1.0, r))

    # t-stat → p-value approximation
    if abs(r) == 1.0:
        return round(r, 4), 0.0, n
    t   = r * math.sqrt(n - 2) / math.sqrt(1 - r * r)
    df  = n - 2
    # Approximation using normal distribution for df > 30
    if df >= 30:
        z     = abs(t)
        p_val = 2 * (1 - 0.5 * (1 + math.erf(z / math.sqrt(2))))
    else:
        # Wilson-Hilferty approximation for small df
        x3   = (1 - 2.0 / (9 * df)) + abs(t) / math.sqrt(df) * (2.0 / (9 * df)) ** 0.5
        p_val = max(0.001, min(1.0, 2 * (1 - 0.5 * (1 + math.erf(x3 / math.sqrt(2))))))
    return round(r, 4), round(p_val, 4), n


# ─────────────────────────────────────────────────────────────────────────────
# CROSS-CORRELATION
# ─────────────────────────────────────────────────────────────────────────────

def cross_correlate(df: "pd.DataFrame", max_lag: int = 6) -> List[Dict]:
    """
    Compute Pearson r between demand_proxy_mt[t] and km_completed[t-lag]
    for lag = 0 to max_lag months.

    The lag interpretation: highway activity at time t-lag correlates
    with bitumen demand at time t (construction leads demand by `lag` months).

    Returns list of {lag_months, correlation, p_value, n_obs, notes}.
    """
    if not _PANDAS or df is None or df.empty:
        return []

    results = []
    demand  = df["demand_proxy_mt"].tolist()
    km      = df["km_completed"].tolist()

    for lag in range(0, max_lag + 1):
        if lag == 0:
            x = km
            y = demand
        else:
            x = km[:-lag]
            y = demand[lag:]

        r, p_val, n = _pearson(x, y)

        strength = (
            "very strong" if abs(r) >= 0.8 else
            "strong"      if abs(r) >= 0.6 else
            "moderate"    if abs(r) >= 0.4 else
            "weak"        if abs(r) >= 0.2 else
            "negligible"
        )
        direction = "positive" if r >= 0 else "negative"
        sig = "significant" if p_val < 0.05 else "not significant"

        notes = (
            f"Highway activity leads bitumen demand by {lag} months; "
            f"{strength} {direction} correlation ({sig})"
        ) if lag > 0 else (
            f"Same-month: {strength} {direction} correlation ({sig})"
        )

        results.append({
            "run_date_ist": _ts(),
            "lag_months":   lag,
            "correlation":  r,
            "p_value":      p_val,
            "n_obs":        n,
            "series_x":     f"km_completed[t-{lag}]",
            "series_y":     "demand_proxy_mt[t]",
            "notes":        notes,
        })

    return results


# ─────────────────────────────────────────────────────────────────────────────
# OLS REGRESSION
# ─────────────────────────────────────────────────────────────────────────────

def _ols(X_cols: List[List[float]], y: List[float]) -> Dict:
    """
    Manual OLS via normal equations: β = (XᵀX)⁻¹ Xᵀy
    X_cols: list of column vectors (each column is one feature).
    Returns {coefficients: [(name,coef)], r_squared, intercept}.
    """
    n = len(y)
    k = len(X_cols)

    # Build design matrix [1, x1, x2, ...] with complete cases only
    complete = []
    for i in range(n):
        row_vals = [1.0] + [float(X_cols[j][i]) for j in range(k)]
        y_val    = float(y[i])
        if all(not math.isnan(v) for v in row_vals) and not math.isnan(y_val):
            complete.append((row_vals, y_val))

    if len(complete) < k + 3:
        return {"coefficients": [], "r_squared": 0.0,
                "intercept": 0.0, "n_obs": len(complete),
                "error": "Insufficient data for regression"}

    X = [row for row, _ in complete]
    Y = [yv for _, yv in complete]
    nc = len(complete)
    nf = len(X[0])

    # XᵀX and Xᵀy
    XtX = [[sum(X[i][r] * X[i][c] for i in range(nc)) for c in range(nf)] for r in range(nf)]
    XtY = [sum(X[i][r] * Y[i] for i in range(nc)) for r in range(nf)]

    # Inverse via Gauss-Jordan (for small matrices nf ≤ 5)
    try:
        aug = [XtX[r][:] + [XtY[r]] for r in range(nf)]
        for col in range(nf):
            pivot = aug[col][col]
            if abs(pivot) < 1e-12:
                return {"coefficients": [], "r_squared": 0.0,
                        "intercept": 0.0, "n_obs": nc,
                        "error": "Singular matrix — multicollinearity likely"}
            for r in range(nf):
                if r != col:
                    factor = aug[r][col] / pivot
                    aug[r] = [aug[r][c] - factor * aug[col][c] for c in range(nf + 1)]
            aug[col] = [aug[col][c] / pivot for c in range(nf + 1)]

        beta = [aug[r][nf] for r in range(nf)]
    except Exception as e:
        return {"coefficients": [], "r_squared": 0.0,
                "intercept": 0.0, "n_obs": nc, "error": str(e)}

    # R²
    y_mean  = sum(Y) / nc
    y_pred  = [sum(beta[c] * X[i][c] for c in range(nf)) for i in range(nc)]
    ss_res  = sum((Y[i] - y_pred[i]) ** 2 for i in range(nc))
    ss_tot  = sum((Y[i] - y_mean)    ** 2 for i in range(nc))
    r2      = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    return {
        "intercept":    round(beta[0], 6),
        "coefficients": [(f"feature_{j}", round(beta[j + 1], 8)) for j in range(k)],
        "r_squared":    round(r2, 4),
        "n_obs":        nc,
    }


def run_regression(df: "pd.DataFrame", lag: int) -> Dict:
    """
    OLS: demand_proxy_mt[t] = α + β₁·km_completed[t-lag] + β₂·crude_usd[t] + β₃·fx_usdinr[t] + ε
    Returns coefficient dict with interpretation strings.
    """
    if not _PANDAS or df is None or df.empty:
        return {"error": "No data"}

    n = len(df)
    if lag >= n:
        return {"error": f"Lag {lag} exceeds data length {n}"}

    demand  = df["demand_proxy_mt"].tolist()
    km      = df["km_completed"].tolist()
    crude   = df["crude_usd"].tolist()
    fx      = df["fx_usdinr"].tolist()

    if lag > 0:
        y    = demand[lag:]
        x_km = km[:-lag]
        x_cr = crude[lag:]
        x_fx = fx[lag:]
    else:
        y    = demand
        x_km = km
        x_cr = crude
        x_fx = fx

    feat_names = [
        f"km_completed_lag{lag}m",
        "crude_usd",
        "fx_usdinr",
    ]

    ols = _ols([x_km, x_cr, x_fx], y)
    if "error" in ols:
        return ols

    coeffs = ols["coefficients"]
    coeff_rows = []
    for i, name in enumerate(feat_names):
        if i >= len(coeffs):
            break
        _, coef = coeffs[i]
        sign   = "+" if coef >= 0 else "-"
        conf   = "Medium" if abs(coef) > 0 else "Low"

        if name.startswith("km_completed"):
            interp = (
                f"Each 100 km highway completion → "
                f"{'increase' if coef >= 0 else 'decrease'} in demand by "
                f"{abs(coef)*100:,.0f} MT (at lag {lag} months)"
            )
        elif name == "crude_usd":
            interp = (
                f"₹ 1 rise in crude → "
                f"{'increase' if coef >= 0 else 'decrease'} demand by "
                f"{abs(coef):,.1f} MT"
            )
        else:
            interp = (
                f"₹1 change in USD/INR → "
                f"{'increase' if coef >= 0 else 'decrease'} demand by "
                f"{abs(coef):,.1f} MT"
            )

        coeff_rows.append({
            "run_date_ist":    _ts(),
            "feature":         name,
            "coefficient":     coef,
            "sign":            sign,
            "confidence_level": conf,
            "p_value":         None,  # not computed in manual OLS
            "interpretation":  interp,
        })

    # Add intercept row
    coeff_rows.insert(0, {
        "run_date_ist":    _ts(),
        "feature":         "intercept",
        "coefficient":     ols["intercept"],
        "sign":            "+" if ols["intercept"] >= 0 else "-",
        "confidence_level": "N/A",
        "p_value":         None,
        "interpretation":  f"Baseline demand when all predictors = 0: {ols['intercept']:,.1f} MT",
    })

    return {
        "coefficients": coeff_rows,
        "r_squared":    ols["r_squared"],
        "n_obs":        ols["n_obs"],
        "lag_used":     lag,
        "formula":      (
            f"demand[t] = {ols['intercept']:.2f} "
            f"+ {coeffs[0][1]:.6f}·km[t-{lag}m] "
            f"+ {coeffs[1][1]:.4f}·crude[t] "
            f"+ {coeffs[2][1]:.4f}·fx[t]"
            if len(coeffs) >= 3 else "Insufficient features"
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# INSIGHT GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

def generate_insights(corr_results: List[Dict],
                      reg_result: Dict,
                      df: "pd.DataFrame") -> List[Dict]:
    """
    Auto-generate insight strings from correlation + regression results.
    Returns list of {date_ist, insight_text, trigger_metric, severity}.
    """
    insights = []
    ts = _ts()

    if not corr_results:
        return insights

    # Best lag
    best = max(corr_results, key=lambda x: abs(x.get("correlation", 0)))
    best_r   = best.get("correlation", 0)
    best_lag = best.get("lag_months", 0)

    insights.append({
        "date_ist":       ts,
        "insight_text":   (
            f"Strongest correlation: Highway KM at lag {best_lag} months "
            f"→ r = {best_r:.2f} "
            f"({'positive' if best_r > 0 else 'negative'}, "
            f"{'significant p<0.05' if best.get('p_value',1)<0.05 else 'not significant'})"
        ),
        "trigger_metric": "cross_correlation",
        "severity":       "INFO",
    })

    # R² from regression
    r2 = reg_result.get("r_squared", 0)
    if r2 > 0:
        insights.append({
            "date_ist":       ts,
            "insight_text":   (
                f"Regression model explains {r2*100:.1f}% of demand variance "
                f"(R² = {r2:.3f}, lag = {reg_result.get('lag_used',0)} months, "
                f"n = {reg_result.get('n_obs',0)} months)"
            ),
            "trigger_metric": "regression_r_squared",
            "severity":       "INFO" if r2 > 0.3 else "WARNING",
        })

    # Alert: data gap signal (highway up, demand down or missing)
    if _PANDAS and df is not None and not df.empty and len(df) >= 2:
        last   = df.iloc[-1]
        prev   = df.iloc[-2]
        km_chg = last["km_completed"]    - prev["km_completed"]
        dm_chg = last["demand_proxy_mt"] - prev["demand_proxy_mt"]

        if km_chg > 50 and dm_chg < -10:
            insights.append({
                "date_ist":       ts,
                "insight_text":   (
                    f"ALERT: Highway KM grew by {km_chg:.0f} km this month but "
                    f"bitumen imports fell by {abs(dm_chg):.0f} MT — "
                    f"monitor for supply gap or data lag."
                ),
                "trigger_metric": "km_up_demand_down",
                "severity":       "WARNING",
            })

    # Lag 0 correlation (same-month signal)
    lag0 = next((c for c in corr_results if c["lag_months"] == 0), None)
    if lag0 and abs(lag0["correlation"]) > 0.5:
        insights.append({
            "date_ist":       ts,
            "insight_text":   (
                f"Same-month correlation r = {lag0['correlation']:.2f} — "
                f"highway and bitumen activity tend to move {'together' if lag0['correlation']>0 else 'inversely'} "
                f"in the same month."
            ),
            "trigger_metric": "same_month_correlation",
            "severity":       "INFO",
        })

    return insights


# ─────────────────────────────────────────────────────────────────────────────
# FULL ANALYSIS ORCHESTRATOR
# ─────────────────────────────────────────────────────────────────────────────

def run_full_analysis(max_lag: int = 6) -> Dict:
    """
    1. Load monthly time series
    2. Compute cross-correlations (lag 0..max_lag)
    3. Identify best lag
    4. Run OLS regression at best lag
    5. Generate insights
    6. Write 3 output JSON tables
    Returns: {best_lag, best_r, r_squared, n_obs, error (if any)}
    """
    if not _PANDAS:
        return {"error": "pandas not installed — install with: pip install pandas numpy"}

    try:
        df = load_monthly_series()
    except Exception as e:
        return {"error": f"Data load failed: {e}"}

    if df.empty or len(df) < 4:
        # Write empty tables with placeholder insight
        placeholder_corr = [
            {"run_date_ist": _ts(), "lag_months": lag, "correlation": 0.0,
             "p_value": 1.0, "n_obs": 0, "series_x": f"km_completed[t-{lag}]",
             "series_y": "demand_proxy_mt[t]",
             "notes": "Insufficient data — run connectors to populate tables"}
            for lag in range(max_lag + 1)
        ]
        _save(TBL_CORR, placeholder_corr)
        _save(TBL_REGR, [])
        _save(TBL_INSIGH, [{
            "date_ist":       _ts(),
            "insight_text":   "Insufficient monthly data for analysis. Run 'comtrade_hs271320' and 'data_gov_in_highways' connectors first.",
            "trigger_metric": "data_missing",
            "severity":       "WARNING",
        }])
        return {"best_lag": 0, "best_r": 0.0, "r_squared": 0.0,
                "n_obs": len(df), "warning": "Insufficient data"}

    # Cross-correlations
    corr_results = cross_correlate(df, max_lag=max_lag)
    _save(TBL_CORR, corr_results)

    # Best lag
    best_row = max(corr_results, key=lambda x: abs(x.get("correlation", 0)),
                   default={"lag_months": 0, "correlation": 0.0})
    best_lag = best_row["lag_months"]
    best_r   = best_row["correlation"]

    # OLS regression at best lag
    reg_result = run_regression(df, lag=best_lag)
    if "coefficients" in reg_result:
        _save(TBL_REGR, reg_result["coefficients"])

    # Insights
    insights = generate_insights(corr_results, reg_result, df)
    _save(TBL_INSIGH, insights)

    r2 = reg_result.get("r_squared", 0.0)
    return {
        "best_lag":   best_lag,
        "best_r":     round(best_r, 4),
        "r_squared":  r2,
        "n_obs":      reg_result.get("n_obs", len(df)),
        "n_periods":  len(df),
        "formula":    reg_result.get("formula", ""),
        "insights":   len(insights),
    }
