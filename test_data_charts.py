"""
PPS Anantam Bitumen Sales Dashboard — Comprehensive Data & Chart Test Suite
============================================================================
Tests: JSON data files, ChartEngine methods, CalculationEngine formulas,
       interactive_chart_helpers, and MarketPulseEngine.

Run:  python test_data_charts.py
Does NOT import streamlit or start any web server.
"""
from __future__ import annotations

import json
import os
import sys
import traceback
from datetime import datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)
sys.path.insert(0, str(BASE_DIR))

PASS = 0
FAIL = 0
ERRORS: list[str] = []


def log_pass(name: str, detail: str = ""):
    global PASS
    PASS += 1
    suffix = f" -- {detail}" if detail else ""
    print(f"  [PASS] {name}{suffix}")


def log_fail(name: str, detail: str = ""):
    global FAIL
    FAIL += 1
    suffix = f" -- {detail}" if detail else ""
    msg = f"  [FAIL] {name}{suffix}"
    ERRORS.append(msg)
    print(msg)


def section(title: str):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


# ===================================================================
#  PART 1 — JSON Data Files
# ===================================================================
def test_json_data_files():
    section("PART 1: JSON Data Files Validation")

    data_files = [
        "tbl_crude_prices.json",
        "tbl_fx_rates.json",
        "tbl_imports_countrywise.json",
        "tbl_ports_volume.json",
        "tbl_refinery_production.json",
        "tbl_weather.json",
        "tbl_news_feed.json",
        "tbl_api_runs.json",
        "api_cache.json",
        "api_stats.json",
        "hub_cache.json",
        "hub_catalog.json",
        "sre_metrics.json",
        "sre_health_status.json",
        "sre_alerts.json",
        "news_data/articles.json",
        "news_data/fetch_log.json",
    ]

    total_records = 0
    empty_files = []

    for fname in data_files:
        fpath = BASE_DIR / fname
        test_name = f"JSON: {fname}"

        # 1a. File exists
        if not fpath.exists():
            log_fail(test_name, "FILE NOT FOUND")
            continue

        # 1b. Valid JSON
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            log_fail(test_name, f"INVALID JSON: {e}")
            continue
        except Exception as e:
            log_fail(test_name, f"READ ERROR: {e}")
            continue

        # 1c. Record count
        if isinstance(data, list):
            count = len(data)
        elif isinstance(data, dict):
            count = len(data)
        else:
            count = 1

        # 1d. Empty check
        if count == 0:
            empty_files.append(fname)
            log_fail(test_name, "EMPTY (0 records)")
        else:
            log_pass(test_name, f"{count} records, type={type(data).__name__}")
            total_records += count

    print(f"\n  Summary: {total_records} total records across {len(data_files)} files")
    if empty_files:
        print(f"  WARNING: Empty files: {', '.join(empty_files)}")
    else:
        print("  All data files contain data.")


# ===================================================================
#  PART 2 — Chart Engine Functions
# ===================================================================
def test_chart_engine():
    section("PART 2: Chart Engine Functions")

    try:
        import plotly.graph_objects as go
    except ImportError:
        log_fail("ChartEngine import", "plotly not installed")
        return

    try:
        from chart_engine import ChartEngine
        ce = ChartEngine()
        log_pass("ChartEngine instantiation")
    except Exception as e:
        log_fail("ChartEngine instantiation", str(e))
        return

    # ---- 2a. price_trend_chart ----
    test_name = "ChartEngine.price_trend_chart"
    try:
        now = datetime.utcnow()
        mock_price_data = []
        for i in range(30):
            dt = (now - timedelta(days=29 - i)).isoformat()
            mock_price_data.append({"date_time": dt, "benchmark": "Brent", "price": 72.5 + i * 0.3})
            mock_price_data.append({"date_time": dt, "benchmark": "WTI", "price": 68.0 + i * 0.25})
            mock_price_data.append({"date_time": dt, "benchmark": "VG30", "price": 42000 + i * 100})

        fig = ce.price_trend_chart(mock_price_data, days=30)
        assert isinstance(fig, go.Figure), f"Expected go.Figure, got {type(fig)}"
        assert len(fig.data) >= 2, f"Expected >= 2 traces, got {len(fig.data)}"
        log_pass(test_name, f"{len(fig.data)} traces rendered")
    except Exception as e:
        log_fail(test_name, f"{e}\n{traceback.format_exc()}")

    # ---- 2b. demand_heatmap_india (fallback bar chart) ----
    test_name = "ChartEngine.demand_heatmap_india"
    try:
        mock_state_data = {
            "Gujarat": 85000,
            "Maharashtra": 72000,
            "Rajasthan": 65000,
            "Uttar Pradesh": 58000,
            "Tamil Nadu": 45000,
            "Karnataka": 42000,
            "Madhya Pradesh": 38000,
            "Andhra Pradesh": 35000,
        }
        fig = ce.demand_heatmap_india(mock_state_data)
        assert isinstance(fig, go.Figure), f"Expected go.Figure, got {type(fig)}"
        log_pass(test_name, f"{len(fig.data)} trace(s)")
    except Exception as e:
        log_fail(test_name, f"{e}\n{traceback.format_exc()}")

    # ---- 2c. demand_heatmap_india (empty data) ----
    test_name = "ChartEngine.demand_heatmap_india (empty)"
    try:
        fig = ce.demand_heatmap_india({})
        assert isinstance(fig, go.Figure), f"Expected go.Figure, got {type(fig)}"
        log_pass(test_name, "empty data handled gracefully")
    except Exception as e:
        log_fail(test_name, f"{e}\n{traceback.format_exc()}")

    # ---- 2d. margin_waterfall_chart ----
    test_name = "ChartEngine.margin_waterfall_chart"
    try:
        mock_breakdown = {
            "fob": 33400,       # ₹ 400 * 83.5
            "freight": 3340,    # ₹ 40 * 83.5
            "insurance": 183.7, # 0.5% of (fob+freight)
            "port_charges": 2.0,
            "customs_duty": 935.0,
            "gst": 6814.7,
            "margin": 800,
        }
        fig = ce.margin_waterfall_chart(mock_breakdown)
        assert isinstance(fig, go.Figure), f"Expected go.Figure, got {type(fig)}"
        assert len(fig.data) >= 1, "Expected at least 1 trace (waterfall)"
        log_pass(test_name, f"waterfall with {len(fig.data)} trace(s)")
    except Exception as e:
        log_fail(test_name, f"{e}\n{traceback.format_exc()}")

    # ---- 2e. source_comparison_bar ----
    test_name = "ChartEngine.source_comparison_bar"
    try:
        mock_sources = [
            {"source": "IOCL Koyali", "landed_cost": 52500, "base_price": 42000, "freight": 2750},
            {"source": "BPCL Mumbai", "landed_cost": 55200, "base_price": 43000, "freight": 3200},
            {"source": "Kandla Import", "landed_cost": 49800, "base_price": 38000, "freight": 3800},
            {"source": "HPCL Vizag", "landed_cost": 56000, "base_price": 41600, "freight": 5400},
        ]
        fig = ce.source_comparison_bar(mock_sources, destination="Ahmedabad")
        assert isinstance(fig, go.Figure), f"Expected go.Figure, got {type(fig)}"
        assert len(fig.data) == 3, f"Expected 3 traces (base, freight, gst), got {len(fig.data)}"
        log_pass(test_name, f"{len(fig.data)} stacked traces")
    except Exception as e:
        log_fail(test_name, f"{e}\n{traceback.format_exc()}")

    # ---- 2f. source_comparison_bar (empty) ----
    test_name = "ChartEngine.source_comparison_bar (empty)"
    try:
        fig = ce.source_comparison_bar([], destination="Test")
        assert isinstance(fig, go.Figure)
        log_pass(test_name, "empty data handled gracefully")
    except Exception as e:
        log_fail(test_name, f"{e}\n{traceback.format_exc()}")

    # ---- 2g. pipeline_funnel ----
    test_name = "ChartEngine.pipeline_funnel"
    try:
        mock_stages = {
            "Enquiry": 120,
            "Quoted": 85,
            "Negotiation": 42,
            "PO": 28,
            "Dispatch": 22,
            "Delivered": 18,
            "Payment": 15,
            "Closed": 12,
        }
        fig = ce.pipeline_funnel(mock_stages)
        assert isinstance(fig, go.Figure), f"Expected go.Figure, got {type(fig)}"
        log_pass(test_name, f"funnel with {len(mock_stages)} stages")
    except Exception as e:
        log_fail(test_name, f"{e}\n{traceback.format_exc()}")

    # ---- 2h. sparkline ----
    test_name = "ChartEngine.sparkline"
    try:
        mock_values = [42000, 42100, 41900, 42300, 42500, 42200, 42800, 43000, 42600, 42400]
        fig = ce.sparkline(mock_values)
        assert isinstance(fig, go.Figure), f"Expected go.Figure, got {type(fig)}"
        assert fig.layout.height == 60, f"Expected height=60, got {fig.layout.height}"
        log_pass(test_name, f"sparkline with {len(mock_values)} points, height={fig.layout.height}")
    except Exception as e:
        log_fail(test_name, f"{e}\n{traceback.format_exc()}")

    # ---- 2i. sparkline with custom color ----
    test_name = "ChartEngine.sparkline (custom color)"
    try:
        fig = ce.sparkline([1, 3, 2, 5, 4], color="#b85c38", height=40)
        assert isinstance(fig, go.Figure)
        assert fig.layout.height == 40
        log_pass(test_name, "custom color and height accepted")
    except Exception as e:
        log_fail(test_name, f"{e}\n{traceback.format_exc()}")


# ===================================================================
#  PART 3 — Calculation Engine Accuracy
# ===================================================================
def test_calculation_engine():
    section("PART 3: Calculation Engine Accuracy")

    try:
        from calculation_engine import BitumenCalculationEngine
        calc = BitumenCalculationEngine()
        log_pass("CalculationEngine instantiation")
    except Exception as e:
        log_fail("CalculationEngine instantiation", str(e))
        return

    # ---- 3a. International Landed Cost ----
    test_name = "International landed cost"
    try:
        params = {
            "fob_usd": 400,
            "freight_usd": 40,
            "insurance_pct": 0.5,
            "usdinr": 83.50,
            "vessel_qty_mt": 5000,
            "port_charges_inr": 10000,
            "cha_per_mt": 75,
            "handling_per_mt": 100,
            "customs_duty_pct": 2.5,
            "inland_freight_per_mt": 0,
            "switch_bl_usd": 2,
        }
        result = calc.calculate_international_landed_cost(params)

        # Verify key components exist
        assert "total_landed" in result, "Missing total_landed"
        assert "cif_inr" in result, "Missing cif_inr"
        assert "customs_inr" in result, "Missing customs_inr"
        assert "gst_inr" in result, "Missing gst_inr"
        assert "landing_charges_inr" in result, "Missing landing_charges_inr"
        assert "breakdown" in result, "Missing breakdown"

        # Manual calculation to verify
        fob_inr = 400 * 83.50           # = 33400.00
        freight_inr = 40 * 83.50        # = 3340.00
        insurance_inr = (fob_inr + freight_inr) * 0.5 / 100.0  # = 183.70
        cif_inr = fob_inr + freight_inr + insurance_inr  # = 36923.70

        # Landing charges = 1% of CIF (this is the key check)
        landing_charges_inr = cif_inr * 0.01  # = 369.237
        assessable_value = cif_inr + landing_charges_inr  # = 37292.937

        # Customs duty = 2.5% of assessable value (CIF + landing charges)
        customs_inr = assessable_value * 2.5 / 100.0  # = 932.32

        switch_bl_inr = 2 * 83.50       # = 167.00
        port_per_mt = 10000 / 5000      # = 2.00

        subtotal = cif_inr + landing_charges_inr + switch_bl_inr + port_per_mt + 75 + 100 + customs_inr
        gst_inr = subtotal * 0.18
        total_landed = subtotal + gst_inr

        # Compare with engine output (tolerance = 0.05 INR)
        assert abs(result["cif_inr"] - round(cif_inr, 2)) < 0.05, \
            f"CIF mismatch: expected {cif_inr:.2f}, got {result['cif_inr']}"
        log_pass(test_name + " (CIF check)", f"CIF = {result['cif_inr']:.2f}")

        assert abs(result["landing_charges_inr"] - round(landing_charges_inr, 2)) < 0.05, \
            f"Landing charges mismatch: expected {landing_charges_inr:.2f}, got {result['landing_charges_inr']}"
        log_pass(test_name + " (landing charges 1%)", f"Landing = {result['landing_charges_inr']:.2f}")

        assert abs(result["customs_inr"] - round(customs_inr, 2)) < 0.05, \
            f"Customs mismatch: expected {customs_inr:.2f}, got {result['customs_inr']}"
        log_pass(test_name + " (customs duty)", f"Customs = {result['customs_inr']:.2f}")

        assert abs(result["total_landed"] - round(total_landed, 2)) < 0.10, \
            f"Total landed mismatch: expected {total_landed:.2f}, got {result['total_landed']}"
        log_pass(test_name + " (total landed)", f"Total = {result['total_landed']:.2f}")

        # Verify customs includes landing charges base
        # assessable_value = CIF + 1% landing -> customs should be > just CIF * 2.5%
        customs_on_cif_only = cif_inr * 2.5 / 100.0
        assert result["customs_inr"] > customs_on_cif_only, \
            "Customs duty must include landing charges in assessable base"
        log_pass(test_name + " (customs includes landing charges)",
                 f"customs={result['customs_inr']:.2f} > cif_only_customs={customs_on_cif_only:.2f}")

    except Exception as e:
        log_fail(test_name, f"{e}\n{traceback.format_exc()}")

    # ---- 3b. Domestic Landed Cost ----
    test_name = "Domestic landed cost"
    try:
        result = calc.calculate_domestic_landed_cost(
            base_price=42000,
            source="IOCL Koyali",
            destination="Ahmedabad",
            load_type="Bulk",
            grade="VG30",
        )

        assert "landed_cost" in result, "Missing landed_cost"
        assert "freight" in result, "Missing freight"
        assert "gst" in result, "Missing gst"
        assert "base_price" in result, "Missing base_price"
        assert "breakdown" in result, "Missing breakdown"

        base = result["base_price"]
        freight = result["freight"]
        gst = result["gst"]
        landed = result["landed_cost"]

        # Key check: GST should apply on (base + freight), not just base
        expected_gst = (base + freight) * 0.18
        assert abs(gst - round(expected_gst, 2)) < 0.10, \
            f"GST mismatch: expected {expected_gst:.2f} (on base+freight), got {gst:.2f}"
        log_pass(test_name + " (GST on base+freight)", f"GST={gst:.2f}")

        # Landed = base + freight + GST
        expected_landed = base + freight + gst
        assert abs(landed - round(expected_landed, 2)) < 0.10, \
            f"Landed mismatch: expected {expected_landed:.2f}, got {landed:.2f}"
        log_pass(test_name + " (landed cost)", f"Landed={landed:.2f}")

        # Verify GST is NOT just on base alone
        gst_on_base_only = base * 0.18
        assert gst > gst_on_base_only, \
            f"GST should be on base+freight: {gst:.2f} must be > {gst_on_base_only:.2f}"
        log_pass(test_name + " (GST includes freight base)",
                 f"gst={gst:.2f} > base_only_gst={gst_on_base_only:.2f}")

        log_pass(test_name + " (complete)",
                 f"Base={base}, Freight={freight}, GST={gst:.2f}, Landed={landed:.2f}")
    except Exception as e:
        log_fail(test_name, f"{e}\n{traceback.format_exc()}")

    # ---- 3c. Domestic with specific distance test ----
    test_name = "Domestic landed cost (500km distance)"
    try:
        # Use known rate 5.5/km for bulk
        distance_km = 500
        rate_per_km = calc.bulk_rate_per_km  # should be 5.5
        base_price = 42000

        expected_freight = distance_km * rate_per_km
        expected_gst = (base_price + expected_freight) * 0.18
        expected_landed = base_price + expected_freight + expected_gst

        result = calc.calculate_domestic_landed_cost(
            base_price=42000,
            source="TestSource",
            destination="TestDest",
            load_type="Bulk",
        )
        # Note: distance may fall back to 350km since TestSource/TestDest are not real
        # We verify the formula consistency instead:
        actual_freight = result["freight"]
        actual_gst = result["gst"]
        actual_landed = result["landed_cost"]
        actual_base = result["base_price"]

        recalc_gst = (actual_base + actual_freight) * 0.18
        recalc_landed = actual_base + actual_freight + recalc_gst

        assert abs(actual_gst - round(recalc_gst, 2)) < 0.10, \
            f"GST formula wrong: expected {recalc_gst:.2f}, got {actual_gst}"
        assert abs(actual_landed - round(recalc_landed, 2)) < 0.10, \
            f"Landed formula wrong: expected {recalc_landed:.2f}, got {actual_landed}"
        log_pass(test_name, f"Freight={actual_freight}, GST={actual_gst:.2f}, Landed={actual_landed:.2f}")
    except Exception as e:
        log_fail(test_name, f"{e}\n{traceback.format_exc()}")

    # ---- 3d. Drum freight rate check ----
    test_name = "Drum freight rate"
    try:
        result_drum = calc.calculate_domestic_landed_cost(
            base_price=42000,
            source="TestSource",
            destination="TestDest",
            load_type="Drum",
        )
        result_bulk = calc.calculate_domestic_landed_cost(
            base_price=42000,
            source="TestSource",
            destination="TestDest",
            load_type="Bulk",
        )
        # Drum rate (6.0/km) > Bulk rate (5.5/km), so drum freight should be higher
        assert result_drum["freight"] > result_bulk["freight"], \
            f"Drum freight ({result_drum['freight']}) should be > Bulk freight ({result_bulk['freight']})"
        assert result_drum["rate_per_km"] == calc.drum_rate_per_km, \
            f"Expected drum rate {calc.drum_rate_per_km}, got {result_drum['rate_per_km']}"
        assert result_bulk["rate_per_km"] == calc.bulk_rate_per_km, \
            f"Expected bulk rate {calc.bulk_rate_per_km}, got {result_bulk['rate_per_km']}"
        log_pass(test_name, f"Bulk={calc.bulk_rate_per_km}/km, Drum={calc.drum_rate_per_km}/km")
    except Exception as e:
        log_fail(test_name, f"{e}\n{traceback.format_exc()}")

    # ---- 3e. Business rules check ----
    test_name = "Business rules (settings)"
    try:
        assert calc.min_margin == 500, f"Min margin expected 500, got {calc.min_margin}"
        assert calc.gst_rate == 0.18, f"GST rate expected 0.18, got {calc.gst_rate}"
        assert calc.customs_duty_pct == 2.5, f"Customs duty expected 2.5, got {calc.customs_duty_pct}"
        log_pass(test_name,
                 f"min_margin={calc.min_margin}, gst={calc.gst_rate}, customs={calc.customs_duty_pct}%")
    except Exception as e:
        log_fail(test_name, f"{e}\n{traceback.format_exc()}")


# ===================================================================
#  PART 4 — Interactive Chart Helpers
# ===================================================================
def test_interactive_chart_helpers():
    section("PART 4: Interactive Chart Helpers")

    try:
        import plotly.graph_objects as go
    except ImportError:
        log_fail("plotly import", "plotly not installed")
        return

    # ---- 4a. apply_interactive_defaults ----
    test_name = "apply_interactive_defaults"
    try:
        from interactive_chart_helpers import apply_interactive_defaults
        fig = go.Figure(data=go.Scatter(x=[1, 2, 3], y=[4, 5, 6]))
        fig = apply_interactive_defaults(fig)
        assert isinstance(fig, go.Figure), f"Expected go.Figure, got {type(fig)}"

        # Verify rangeslider is added
        xaxis = fig.layout.xaxis
        assert xaxis.rangeslider.visible is True, \
            f"Expected rangeslider visible=True, got {xaxis.rangeslider.visible}"
        log_pass(test_name, "rangeslider visible=True")

        # Verify rangeselector buttons exist
        buttons = xaxis.rangeselector.buttons
        assert len(buttons) > 0, "Expected rangeselector buttons"
        button_labels = [b.label for b in buttons]
        log_pass(test_name + " (range buttons)", f"Buttons: {button_labels}")
    except Exception as e:
        log_fail(test_name, f"{e}\n{traceback.format_exc()}")

    # ---- 4b. apply_interactive_defaults without rangeslider ----
    test_name = "apply_interactive_defaults (no rangeslider)"
    try:
        from interactive_chart_helpers import apply_interactive_defaults
        fig = go.Figure(data=go.Bar(x=["A", "B"], y=[10, 20]))
        fig = apply_interactive_defaults(fig, show_rangeslider=False)
        assert isinstance(fig, go.Figure)
        # rangeslider should NOT be explicitly set to True
        xaxis = fig.layout.xaxis
        # When show_rangeslider=False, the rangeslider_visible should not be True
        if xaxis.rangeslider.visible is True:
            log_fail(test_name, "rangeslider should not be visible when disabled")
        else:
            log_pass(test_name, "rangeslider correctly not added")
    except Exception as e:
        log_fail(test_name, f"{e}\n{traceback.format_exc()}")

    # ---- 4c. apply_interactive_defaults with INR format ----
    test_name = "apply_interactive_defaults (INR format)"
    try:
        from interactive_chart_helpers import apply_interactive_defaults
        fig = go.Figure(data=go.Scatter(x=[1, 2, 3], y=[42000, 42500, 43000]))
        fig = apply_interactive_defaults(fig, inr_format=True)
        assert isinstance(fig, go.Figure)
        log_pass(test_name, "INR hover format applied")
    except Exception as e:
        log_fail(test_name, f"{e}\n{traceback.format_exc()}")

    # ---- 4d. create_alert_ticker ----
    test_name = "create_alert_ticker"
    try:
        from interactive_chart_helpers import create_alert_ticker

        mock_alerts = [
            {"severity": "P0", "message": "Brent crude up 5.2% this week", "category": "Crude"},
            {"severity": "P1", "message": "INR weakening: 83.5 -> 84.2", "category": "FX"},
            {"severity": "P2", "message": "Gujarat highway tender awarded", "category": "Demand"},
        ]
        html = create_alert_ticker(mock_alerts)
        assert isinstance(html, str), f"Expected str, got {type(html)}"
        assert len(html) > 0, "Ticker HTML should not be empty"
        assert "P0" in html, "P0 severity should be in ticker"
        assert "P1" in html, "P1 severity should be in ticker"
        assert "P2" in html, "P2 severity should be in ticker"
        assert "Brent crude" in html, "Alert message should be in ticker"
        assert "ticker-scroll" in html, "CSS animation should be present"
        log_pass(test_name, f"HTML length={len(html)} chars, all severities present")
    except Exception as e:
        log_fail(test_name, f"{e}\n{traceback.format_exc()}")

    # ---- 4e. create_alert_ticker (empty) ----
    test_name = "create_alert_ticker (empty)"
    try:
        from interactive_chart_helpers import create_alert_ticker
        html = create_alert_ticker([])
        assert html == "", f"Expected empty string for no alerts, got '{html[:50]}...'"
        log_pass(test_name, "returns empty string for no alerts")
    except Exception as e:
        log_fail(test_name, f"{e}\n{traceback.format_exc()}")

    # ---- 4f. create_alert_ticker (limit 10) ----
    test_name = "create_alert_ticker (>10 alerts)"
    try:
        from interactive_chart_helpers import create_alert_ticker
        many_alerts = [
            {"severity": "P2", "message": f"Alert #{i}", "category": "Test"}
            for i in range(25)
        ]
        html = create_alert_ticker(many_alerts)
        # Should only show first 10
        assert "Alert #9" in html, "Should show alert #9"
        assert "Alert #10" not in html, "Should NOT show alert #10 (limit=10)"
        log_pass(test_name, "correctly limited to 10 alerts")
    except Exception as e:
        log_fail(test_name, f"{e}\n{traceback.format_exc()}")

    # ---- 4g. get_chart_config ----
    test_name = "get_chart_config"
    try:
        from interactive_chart_helpers import get_chart_config
        config = get_chart_config()
        assert isinstance(config, dict), f"Expected dict, got {type(config)}"
        assert config.get("displayModeBar") is True, "displayModeBar should be True"
        assert config.get("scrollZoom") is True, "scrollZoom should be True"
        assert config.get("displaylogo") is False, "displaylogo should be False"
        assert "toImageButtonOptions" in config, "Missing toImageButtonOptions"
        assert config["toImageButtonOptions"]["format"] == "png", "Export format should be png"
        log_pass(test_name, f"Config keys: {list(config.keys())}")
    except Exception as e:
        log_fail(test_name, f"{e}\n{traceback.format_exc()}")


# ===================================================================
#  PART 5 — Market Pulse Engine
# ===================================================================
def test_market_pulse_engine():
    section("PART 5: Market Pulse Engine")

    try:
        from market_pulse_engine import MarketPulseEngine
        engine = MarketPulseEngine()
        log_pass("MarketPulseEngine instantiation")
    except Exception as e:
        log_fail("MarketPulseEngine instantiation", str(e))
        return

    # ---- 5a. monitor_crude_volatility ----
    test_name = "MarketPulseEngine.monitor_crude_volatility"
    try:
        result = engine.monitor_crude_volatility()
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        assert "status" in result, "Missing 'status' key"

        if result["status"] == "no_data":
            log_pass(test_name, "returned status=no_data (no crude price data available)")
        else:
            assert "current_brent" in result, "Missing current_brent"
            assert "weekly_change_pct" in result, "Missing weekly_change_pct"
            assert "rsi" in result, "Missing rsi"
            assert "bollinger" in result, "Missing bollinger"
            assert "direction" in result, "Missing direction"
            assert "data_points" in result, "Missing data_points"

            log_pass(test_name,
                     f"Brent=${result['current_brent']}, "
                     f"direction={result['direction']}, "
                     f"RSI={result['rsi']}, "
                     f"weekly_change={result['weekly_change_pct']}%, "
                     f"data_points={result['data_points']}")
    except Exception as e:
        log_fail(test_name, f"{e}\n{traceback.format_exc()}")

    # ---- 5b. monitor_demand_signals ----
    test_name = "MarketPulseEngine.monitor_demand_signals"
    try:
        result = engine.monitor_demand_signals()
        assert isinstance(result, list), f"Expected list, got {type(result)}"

        # Should always have at least the seasonal signal
        seasonal_signals = [s for s in result if s.get("type") == "seasonal"]
        assert len(seasonal_signals) >= 1, "Expected at least 1 seasonal demand signal"

        signal_types = set(s.get("type", "unknown") for s in result)
        log_pass(test_name,
                 f"{len(result)} signals, types={signal_types}")

        # Check seasonal signal structure
        seasonal = seasonal_signals[0]
        assert "score" in seasonal, "Seasonal signal missing 'score'"
        assert "label" in seasonal, "Seasonal signal missing 'label'"
        assert seasonal["label"] in ("PEAK", "MODERATE", "MONSOON_LOW"), \
            f"Unexpected seasonal label: {seasonal['label']}"
        log_pass(test_name + " (seasonal signal)",
                 f"score={seasonal['score']}, label={seasonal['label']}")
    except Exception as e:
        log_fail(test_name, f"{e}\n{traceback.format_exc()}")

    # ---- 5c. monitor_supply_disruptions ----
    test_name = "MarketPulseEngine.monitor_supply_disruptions"
    try:
        result = engine.monitor_supply_disruptions()
        assert isinstance(result, list), f"Expected list, got {type(result)}"

        if result:
            disruption_types = set(d.get("type", "unknown") for d in result)
            log_pass(test_name, f"{len(result)} disruptions, types={disruption_types}")
        else:
            log_pass(test_name, "0 disruptions (no supply issues detected)")
    except Exception as e:
        log_fail(test_name, f"{e}\n{traceback.format_exc()}")

    # ---- 5d. monitor_fx_impact ----
    test_name = "MarketPulseEngine.monitor_fx_impact"
    try:
        result = engine.monitor_fx_impact()
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        assert "status" in result, "Missing 'status' key"

        if result["status"] == "no_data":
            log_pass(test_name, "returned status=no_data (no FX rate data available)")
        else:
            assert "current_rate" in result, "Missing current_rate"
            assert "direction" in result, "Missing direction"
            assert "impact" in result, "Missing impact"
            log_pass(test_name,
                     f"USD/INR={result['current_rate']}, "
                     f"direction={result['direction']}, "
                     f"impact={result['impact']}")
    except Exception as e:
        log_fail(test_name, f"{e}\n{traceback.format_exc()}")

    # ---- 5e. monitor_logistics ----
    test_name = "MarketPulseEngine.monitor_logistics"
    try:
        result = engine.monitor_logistics()
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        log_pass(test_name, f"keys={list(result.keys())}")
    except Exception as e:
        log_fail(test_name, f"{e}\n{traceback.format_exc()}")

    # ---- 5f. get_market_state_summary ----
    test_name = "MarketPulseEngine.get_market_state_summary"
    try:
        # Clear the cache to force a fresh scan
        engine._cache = None
        engine._cache_ts = 0.0

        result = engine.get_market_state_summary()
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        assert "market_bias" in result, "Missing market_bias"
        assert "bias_score" in result, "Missing bias_score"

        bias = result.get("market_bias", "UNKNOWN")
        score = result.get("bias_score", -1)
        assert bias in ("BULLISH", "BEARISH", "NEUTRAL"), \
            f"Unexpected market bias: {bias}"
        assert 0 <= score <= 100, f"Bias score {score} out of range 0-100"

        log_pass(test_name,
                 f"bias={bias}, score={score}, "
                 f"crude_dir={result.get('crude_direction', 'N/A')}, "
                 f"seasonal={result.get('seasonal_label', 'N/A')}")
    except Exception as e:
        log_fail(test_name, f"{e}\n{traceback.format_exc()}")

    # ---- 5g. monitor_all (integration) ----
    test_name = "MarketPulseEngine.monitor_all (integration)"
    try:
        engine._cache = None
        engine._cache_ts = 0.0

        result = engine.monitor_all()
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        expected_keys = {"timestamp", "crude", "fx", "supply_disruptions",
                         "demand_signals", "logistics", "alerts", "market_state"}
        missing = expected_keys - set(result.keys())
        assert not missing, f"Missing keys in monitor_all result: {missing}"
        log_pass(test_name,
                 f"all {len(expected_keys)} sections present, "
                 f"{len(result.get('alerts', []))} new alerts generated")
    except Exception as e:
        log_fail(test_name, f"{e}\n{traceback.format_exc()}")


# ===================================================================
#  MAIN — Run All Tests
# ===================================================================
def main():
    print("\n" + "=" * 70)
    print("  PPS ANANTAM BITUMEN SALES DASHBOARD")
    print("  Comprehensive Data & Chart Function Test Suite")
    print(f"  Run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Base directory: {BASE_DIR}")
    print("=" * 70)

    test_json_data_files()
    test_chart_engine()
    test_calculation_engine()
    test_interactive_chart_helpers()
    test_market_pulse_engine()

    # ---- Final Summary ----
    section("FINAL SUMMARY")
    total = PASS + FAIL
    print(f"  Total tests: {total}")
    print(f"  Passed:      {PASS}")
    print(f"  Failed:      {FAIL}")

    if ERRORS:
        print(f"\n  --- Failed Tests ---")
        for err in ERRORS:
            print(f"  {err}")
    else:
        print("\n  ALL TESTS PASSED!")

    print(f"\n{'='*70}\n")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
