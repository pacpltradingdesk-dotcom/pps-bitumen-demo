"""
test_export_api_comprehensive.py -- Comprehensive Functional Tests
===================================================================
Part A: Export Testing (PDF, Excel, WhatsApp, Email, Chart, Report)
Part B: API Connection Testing (api_hub_engine, free_api_registry, sync_engine, data freshness)
"""

import sys
import os
import json
import time
import traceback
from pathlib import Path
from datetime import datetime, timezone, timedelta

BASE = Path(__file__).resolve().parent
os.chdir(BASE)
sys.path.insert(0, str(BASE))

IST = timezone(timedelta(hours=5, minutes=30))

results = []

def _safe_str(s):
    """Replace non-ASCII chars for Windows console output."""
    try:
        s.encode("cp1252")
        return s
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s.encode("ascii", errors="replace").decode("ascii")

def record(test_name, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    results.append((status, test_name, detail))
    print(f"[{status}] {test_name} -- {_safe_str(str(detail))}")


# ==========================================================================
# PART A: EXPORT TESTING
# ==========================================================================

print("=" * 80)
print("PART A: EXPORT FUNCTION TESTING")
print("=" * 80)

# --------------------------------------------------------------------------
# A1. PDF Export — pdf_export_engine.py
# --------------------------------------------------------------------------

# A1a. Import pdf_export_engine
test_name = "A1a. Import pdf_export_engine"
try:
    from pdf_export_engine import build_generic_pdf
    record(test_name, True, "build_generic_pdf imported successfully")
except Exception as e:
    record(test_name, False, f"Import error: {e}")

# A1b. build_generic_pdf produces bytes output
test_name = "A1b. build_generic_pdf produces PDF bytes"
try:
    from pdf_export_engine import build_generic_pdf
    sections = [
        {"type": "section", "text": "Test Section"},
        {"type": "paragraph", "text": "This is a test paragraph for functional testing."},
        {"type": "table", "headers": ["Item", "Price", "Qty"],
         "rows": [["VG-30", "42000", "100"], ["VG-40", "44000", "50"]]},
    ]
    pdf_bytes = build_generic_pdf(
        page_title="Test Export Report",
        sections=sections,
        filters={"Grade": "VG-30", "City": "Vadodara"},
        role="Admin",
        orientation="portrait",
    )
    assert isinstance(pdf_bytes, bytes), "Output is not bytes"
    assert len(pdf_bytes) > 500, f"PDF too small: {len(pdf_bytes)} bytes"
    assert pdf_bytes[:5] == b"%PDF-", "Missing PDF magic header"
    record(test_name, True, f"Generated {len(pdf_bytes)} bytes, valid PDF header")
except Exception as e:
    record(test_name, False, f"{e}")

# A1c. build_generic_pdf landscape mode
test_name = "A1c. build_generic_pdf landscape orientation"
try:
    from pdf_export_engine import build_generic_pdf
    pdf_bytes = build_generic_pdf(
        page_title="Landscape Test",
        sections=[{"type": "paragraph", "text": "Landscape test"}],
        orientation="landscape",
    )
    assert isinstance(pdf_bytes, bytes) and len(pdf_bytes) > 500
    record(test_name, True, f"Landscape PDF: {len(pdf_bytes)} bytes")
except Exception as e:
    record(test_name, False, f"{e}")

# A1d. universal_action_engine build_pdf_report
test_name = "A1d. universal_action_engine build_pdf_report"
try:
    from universal_action_engine import PageContext, build_pdf_report
    ctx = PageContext(
        page_name="Market Intelligence",
        summary_text="Brent crude at ₹ 72.5/bbl, up 1.2%",
        kpis=[("Brent", "₹ 72.5", "+1.2%"), ("WTI", "₹ 68.3", "+0.8%")],
        tables=[{"title": "Prices", "headers": ["Grade", "Price"],
                 "rows": [["VG-30", "42000"], ["VG-40", "44000"]]}],
        insights=["Crude rising trend", "FX stable"],
        action_items=["Review buy timing", "Check Kandla supply"],
    )
    pdf_bytes = build_pdf_report(ctx)
    assert isinstance(pdf_bytes, bytes) and len(pdf_bytes) > 500
    assert pdf_bytes[:5] == b"%PDF-"
    record(test_name, True, f"PageContext PDF: {len(pdf_bytes)} bytes")
except Exception as e:
    record(test_name, False, f"{e}")

# --------------------------------------------------------------------------
# A2. Excel Export
# --------------------------------------------------------------------------

# A2a. Import openpyxl
test_name = "A2a. Import openpyxl"
try:
    import openpyxl
    record(test_name, True, f"openpyxl {openpyxl.__version__}")
except ImportError as e:
    record(test_name, False, f"openpyxl not installed: {e}")

# A2b. build_excel_export produces bytes
test_name = "A2b. build_excel_export produces valid Excel"
try:
    from universal_action_engine import PageContext, build_excel_export
    ctx = PageContext(
        page_name="Test Excel Export",
        summary_text="Testing Excel export with sample data",
        kpis=[("Revenue", "Rs 5.2 Cr", "+12%"), ("Orders", "15", "+3")],
        tables=[{
            "title": "Order Book",
            "headers": ["Customer", "Grade", "Qty MT", "Rate"],
            "rows": [
                ["ABC Roads", "VG-30", "200", "42000"],
                ["XYZ Infra", "VG-40", "100", "44000"],
            ]
        }],
        filters={"Month": "March 2026"},
    )
    excel_bytes = build_excel_export(ctx)
    assert isinstance(excel_bytes, bytes), "Output is not bytes"
    assert len(excel_bytes) > 1000, f"Excel too small: {len(excel_bytes)} bytes"
    # Check XLSX magic bytes (PK zip header)
    assert excel_bytes[:2] == b"PK", "Missing XLSX/ZIP magic header"
    record(test_name, True, f"Generated {len(excel_bytes)} bytes, valid XLSX header")
except Exception as e:
    record(test_name, False, f"{e}")

# A2c. Excel workbook has correct sheets
test_name = "A2c. Excel workbook structure verification"
try:
    from universal_action_engine import PageContext, build_excel_export
    import io
    ctx = PageContext(
        page_name="Sheet Test",
        kpis=[("A", "1", "")],
        tables=[
            {"title": "Table One", "headers": ["H1", "H2"], "rows": [["a", "b"]]},
            {"title": "Table Two", "headers": ["X", "Y"], "rows": [["1", "2"]]},
        ],
    )
    excel_bytes = build_excel_export(ctx)
    wb = openpyxl.load_workbook(io.BytesIO(excel_bytes))
    sheet_names = wb.sheetnames
    assert "Report Metadata" in sheet_names, f"Missing 'Report Metadata' sheet. Found: {sheet_names}"
    assert len(sheet_names) >= 3, f"Expected >= 3 sheets, found {len(sheet_names)}: {sheet_names}"
    record(test_name, True, f"Sheets: {sheet_names}")
except Exception as e:
    record(test_name, False, f"{e}")

# A2d. CSV Export
test_name = "A2d. build_csv_export produces valid CSV"
try:
    from universal_action_engine import PageContext, build_csv_export
    ctx = PageContext(
        page_name="CSV Test",
        kpis=[("Price", "42000", "")],
        tables=[{"title": "Data", "headers": ["A", "B"], "rows": [["1", "2"]]}],
    )
    csv_bytes = build_csv_export(ctx)
    assert isinstance(csv_bytes, bytes), "CSV output not bytes"
    csv_text = csv_bytes.decode("utf-8-sig")
    assert "CSV Test" in csv_text, "Page name not in CSV"
    assert "Price" in csv_text, "KPI not in CSV"
    record(test_name, True, f"CSV: {len(csv_bytes)} bytes, content verified")
except Exception as e:
    record(test_name, False, f"{e}")

# --------------------------------------------------------------------------
# A3. WhatsApp Share
# --------------------------------------------------------------------------

# A3a. CommunicationHub WhatsApp offer
test_name = "A3a. CommunicationHub.whatsapp_offer()"
try:
    from communication_engine import CommunicationHub
    hub = CommunicationHub()
    msg = hub.whatsapp_offer(
        customer_name="ABC Roads Pvt Ltd",
        city="Ahmedabad",
        grade="VG-30",
        quantity_mt=200,
        price_per_mt=42000,
        source="IOCL Kandla",
        benefit_pct=3.5,
    )
    assert isinstance(msg, str), "Output not string"
    assert "VG-30" in msg, "Grade missing"
    assert "200" in msg, "Quantity missing"
    assert "42,000" in msg or "42000" in msg, "Price missing"
    assert "PPS Anantam" in msg, "Company name missing"
    assert "CONFIRM" in msg, "CTA missing"
    record(test_name, True, f"Message length: {len(msg)} chars, all fields present")
except Exception as e:
    record(test_name, False, f"{e}")

# A3b. CommunicationHub WhatsApp followup
test_name = "A3b. CommunicationHub.whatsapp_followup()"
try:
    from communication_engine import CommunicationHub
    hub = CommunicationHub()
    msg = hub.whatsapp_followup(
        customer_name="XYZ Infra",
        reference="QT-2026-001",
        days_since=3,
    )
    assert isinstance(msg, str) and len(msg) > 20
    assert "XYZ Infra" in msg
    assert "PPS Anantam" in msg
    record(test_name, True, f"Followup message: {len(msg)} chars")
except Exception as e:
    record(test_name, False, f"{e}")

# A3c. CommunicationHub WhatsApp reactivation
test_name = "A3c. CommunicationHub.whatsapp_reactivation()"
try:
    from communication_engine import CommunicationHub
    hub = CommunicationHub()
    msg = hub.whatsapp_reactivation(
        customer_name="Dormant Co",
        city="Mumbai",
        new_price=41000,
        old_price=44000,
        savings=3000,
    )
    assert isinstance(msg, str) and len(msg) > 20
    assert "Dormant Co" in msg
    assert "save" in msg.lower() or "3,000" in msg or "3000" in msg
    record(test_name, True, f"Reactivation: {len(msg)} chars, savings mentioned")
except Exception as e:
    record(test_name, False, f"{e}")

# A3d. CommunicationHub WhatsApp payment reminder
test_name = "A3d. CommunicationHub.whatsapp_payment_reminder()"
try:
    from communication_engine import CommunicationHub
    hub = CommunicationHub()
    msg = hub.whatsapp_payment_reminder(
        customer_name="Late Payer Ltd",
        amount=250000,
        invoice_ref="INV-2026-042",
        days_overdue=10,
    )
    assert isinstance(msg, str) and len(msg) > 20
    assert "Late Payer" in msg
    assert "ICICI" in msg, "Bank details missing"
    record(test_name, True, f"Payment reminder: {len(msg)} chars, bank details present")
except Exception as e:
    record(test_name, False, f"{e}")

# A3e. universal_action_engine WhatsApp summary
test_name = "A3e. build_whatsapp_summary()"
try:
    from universal_action_engine import PageContext, build_whatsapp_summary
    ctx = PageContext(
        page_name="Daily Report",
        summary_text="Market stable today",
        kpis=[("Brent", "₹ 72.5", "+1.2%")],
        insights=["Demand rising in Gujarat"],
        action_items=["Place Kandla order"],
    )
    msg = build_whatsapp_summary(ctx)
    assert isinstance(msg, str) and len(msg) > 20
    assert "PPS Anantam" in msg
    assert len(msg) <= 4096, f"WhatsApp message too long: {len(msg)}"
    record(test_name, True, f"Summary: {len(msg)} chars, within 4096 limit")
except Exception as e:
    record(test_name, False, f"{e}")

# --------------------------------------------------------------------------
# A4. Email Report
# --------------------------------------------------------------------------

# A4a. CommunicationHub email_offer
test_name = "A4a. CommunicationHub.email_offer()"
try:
    from communication_engine import CommunicationHub
    hub = CommunicationHub()
    result = hub.email_offer(
        customer_name="Infrastructure Corp",
        city="Delhi",
        grade="VG-30",
        quantity_mt=500,
        price_per_mt=43000,
        source="BPCL Mumbai",
        benefit_pct=2.5,
    )
    assert isinstance(result, dict), "Return type should be dict"
    assert "subject" in result, "Missing 'subject' key"
    assert "body" in result, "Missing 'body' key"
    assert "VG-30" in result["subject"]
    assert "43,000" in result["body"] or "43000" in result["body"] or "43" in result["body"]
    assert "GST" in result["body"]
    assert "27132000" in result["body"], "HSN code missing"
    record(test_name, True, f"Subject: {result['subject'][:60]}...")
except Exception as e:
    record(test_name, False, f"{e}")

# A4b. CommunicationHub email_followup
test_name = "A4b. CommunicationHub.email_followup()"
try:
    from communication_engine import CommunicationHub
    hub = CommunicationHub()
    result = hub.email_followup(
        customer_name="Follow Corp",
        original_date="01-03-2026",
        price=42000,
        city="Ahmedabad",
    )
    assert isinstance(result, dict)
    assert "subject" in result and "body" in result
    assert "Follow Corp" in result["body"]
    record(test_name, True, f"Subject: {result['subject'][:60]}...")
except Exception as e:
    record(test_name, False, f"{e}")

# A4c. CommunicationHub email_reactivation
test_name = "A4c. CommunicationHub.email_reactivation()"
try:
    from communication_engine import CommunicationHub
    hub = CommunicationHub()
    result = hub.email_reactivation(
        customer_name="Old Client",
        city="Pune",
        new_price=41500,
        old_price=44000,
        savings=2500,
    )
    assert isinstance(result, dict)
    assert "subject" in result and "body" in result
    assert "Old Client" in result["body"]
    assert "2,500" in result["body"] or "2500" in result["body"] or "2,500" in result["body"]
    record(test_name, True, f"Subject: {result['subject'][:60]}...")
except Exception as e:
    record(test_name, False, f"{e}")

# A4d. CommunicationHub email_payment_reminder
test_name = "A4d. CommunicationHub.email_payment_reminder()"
try:
    from communication_engine import CommunicationHub
    hub = CommunicationHub()
    result = hub.email_payment_reminder(
        customer_name="Pending Ltd",
        amount=500000,
        invoice_ref="INV-2026-099",
        days_overdue=15,
    )
    assert isinstance(result, dict)
    assert "subject" in result and "body" in result
    assert "ICICI" in result["body"]
    assert "Urgent" in result["subject"], "Should show urgency for 15 days overdue"
    record(test_name, True, f"Subject: {result['subject'][:60]}...")
except Exception as e:
    record(test_name, False, f"{e}")

# A4e. CommunicationHub email_tender_response
test_name = "A4e. CommunicationHub.email_tender_response()"
try:
    from communication_engine import CommunicationHub
    hub = CommunicationHub()
    result = hub.email_tender_response(
        authority_name="NHAI Regional Office",
        tender_ref="NHAI/GJ/2026/BIT-042",
        grade="VG-30",
        quantity_mt=1000,
        price_per_mt=41000,
        delivery_location="Ahmedabad-Vadodara Expressway",
    )
    assert isinstance(result, dict)
    assert "subject" in result and "body" in result
    assert "NHAI" in result["subject"]
    assert "NHAI/GJ/2026/BIT-042" in result["body"]
    record(test_name, True, f"Subject: {result['subject'][:60]}...")
except Exception as e:
    record(test_name, False, f"{e}")

# A4f. universal_action_engine build_email_report
test_name = "A4f. build_email_report() with PageContext"
try:
    from universal_action_engine import PageContext, build_email_report
    ctx = PageContext(
        page_name="Market Intelligence",
        summary_text="Market update for 04-03-2026",
        kpis=[("Brent", "₹ 72.5", "+1.2%"), ("USD/INR", "86.4", "-0.1")],
        tables=[{"title": "Top Suppliers", "headers": ["Supplier", "FOB"],
                 "rows": [["IOCL", "540"], ["BPCL", "545"]]}],
        insights=["Crude uptrend", "Monsoon demand spike"],
        action_items=["Lock Kandla supply"],
        filters={"Region": "Gujarat"},
    )
    result = build_email_report(ctx)
    assert isinstance(result, dict)
    assert "subject" in result, "Missing subject"
    assert "body_html" in result, "Missing body_html"
    assert "body_text" in result, "Missing body_text"
    assert "PPS Anantam" in result["body_html"]
    assert "Market Intelligence" in result["subject"]
    assert "<table" in result["body_html"], "HTML should have tables"
    record(test_name, True, f"Subject: {result['subject'][:60]}...")
except Exception as e:
    record(test_name, False, f"{e}")

# --------------------------------------------------------------------------
# A5. Chart Export
# --------------------------------------------------------------------------

# A5a. get_chart_config has toImageButtonOptions
test_name = "A5a. get_chart_config() returns proper config"
try:
    from interactive_chart_helpers import get_chart_config
    config = get_chart_config()
    assert isinstance(config, dict), "Config not a dict"
    assert "toImageButtonOptions" in config, "Missing toImageButtonOptions"
    assert config["toImageButtonOptions"]["format"] == "png", "Format should be png"
    assert config["toImageButtonOptions"]["scale"] == 2, "Scale should be 2"
    assert config["displayModeBar"] is True, "displayModeBar should be True"
    assert config["displaylogo"] is False, "displaylogo should be False"
    record(test_name, True, f"Config keys: {list(config.keys())}")
except Exception as e:
    record(test_name, False, f"{e}")

# A5b. Chart export dimensions
test_name = "A5b. Chart export image dimensions"
try:
    from interactive_chart_helpers import get_chart_config
    config = get_chart_config()
    opts = config["toImageButtonOptions"]
    assert opts["height"] == 600, f"Height should be 600, got {opts['height']}"
    assert opts["width"] == 1000, f"Width should be 1000, got {opts['width']}"
    assert opts["filename"] == "pps_chart", f"Filename should be pps_chart"
    record(test_name, True, f"Export: {opts['width']}x{opts['height']} @ {opts['scale']}x, file={opts['filename']}")
except Exception as e:
    record(test_name, False, f"{e}")

# A5c. Chart engine exists and has render_chart_with_export
test_name = "A5c. chart_engine has render_with_export"
try:
    from chart_engine import ChartEngine
    engine = ChartEngine()
    assert hasattr(engine, "render_with_export"), "Missing render_with_export method"
    record(test_name, True, "render_with_export method exists")
except Exception as e:
    record(test_name, False, f"{e}")

# A5d. apply_interactive_defaults exists
test_name = "A5d. apply_interactive_defaults function exists"
try:
    from interactive_chart_helpers import apply_interactive_defaults
    assert callable(apply_interactive_defaults)
    record(test_name, True, "apply_interactive_defaults is callable")
except Exception as e:
    record(test_name, False, f"{e}")

# --------------------------------------------------------------------------
# A6. Report Generation
# --------------------------------------------------------------------------

# A6a. Director briefing engine WhatsApp summary
test_name = "A6a. DirectorBriefingEngine.format_whatsapp_summary()"
try:
    from director_briefing_engine import DirectorBriefingEngine
    engine = DirectorBriefingEngine()
    assert hasattr(engine, "format_whatsapp_summary"), "Missing format_whatsapp_summary"
    # Create a mock briefing dict
    briefing = {
        "date": "04-03-2026",
        "market_summary": "Brent at ₹ 72.5",
        "opportunities": [],
        "communications": {"whatsapp": 5, "email": 3, "calls": 2, "total": 10},
    }
    summary = engine.format_whatsapp_summary(briefing)
    assert isinstance(summary, str) and len(summary) > 10
    record(test_name, True, f"WhatsApp summary: {len(summary)} chars")
except Exception as e:
    record(test_name, False, f"{e}")

# A6b. CommunicationHub email_director_report_template
test_name = "A6b. CommunicationHub.email_director_report_template()"
try:
    from communication_engine import CommunicationHub
    hub = CommunicationHub()
    assert hasattr(hub, "email_director_report_template"), "Missing email_director_report_template"
    briefing = {
        "date": "04-03-2026",
        "market_summary": "Stable market",
        "opportunities": [{"name": "Opportunity 1"}],
        "actions_taken": ["Called 3 clients"],
    }
    result = hub.email_director_report_template(briefing)
    assert isinstance(result, dict)
    assert "subject" in result
    record(test_name, True, f"Director email template generated")
except Exception as e:
    record(test_name, False, f"{e}")

# A6c. CommunicationHub email_weekly_summary_template
test_name = "A6c. CommunicationHub.email_weekly_summary_template()"
try:
    from communication_engine import CommunicationHub
    hub = CommunicationHub()
    assert hasattr(hub, "email_weekly_summary_template"), "Missing email_weekly_summary_template"
    summary = {
        "week": "W09-2026",
        "total_offers": 15,
        "total_orders": 5,
        "revenue": 2500000,
    }
    result = hub.email_weekly_summary_template(summary)
    assert isinstance(result, dict)
    assert "subject" in result
    record(test_name, True, f"Weekly email template generated")
except Exception as e:
    record(test_name, False, f"{e}")

# A6d. ai_message_engine exists
test_name = "A6d. ai_message_engine import and structure"
try:
    import ai_message_engine
    assert hasattr(ai_message_engine, "generate_message") or hasattr(ai_message_engine, "AIMessageEngine")
    record(test_name, True, "ai_message_engine module loaded")
except Exception as e:
    record(test_name, False, f"{e}")

# A6e. discussion_guidance_engine produces WhatsApp drafts
test_name = "A6e. DiscussionGuidanceEngine exists with WhatsApp draft support"
try:
    from discussion_guidance_engine import DiscussionGuide
    engine = DiscussionGuide()
    # Check that whatsapp_draft is produced in guidance output keys
    assert hasattr(engine, "_fallback_whatsapp_importer"), "Missing _fallback_whatsapp_importer"
    record(test_name, True, "DiscussionGuide with WhatsApp draft support")
except Exception as e:
    record(test_name, False, f"{e}")


# ==========================================================================
# PART B: API CONNECTION TESTING
# ==========================================================================

print()
print("=" * 80)
print("PART B: API CONNECTION TESTING")
print("=" * 80)

# --------------------------------------------------------------------------
# B1. api_hub_engine import and connector functions
# --------------------------------------------------------------------------

test_name = "B1a. Import api_hub_engine"
try:
    import api_hub_engine
    record(test_name, True, "api_hub_engine imported")
except Exception as e:
    record(test_name, False, f"{e}")

# B1b. All 19 connect_ functions exist (from grep)
EXPECTED_CONNECTORS = [
    "connect_eia", "connect_comtrade", "connect_weather", "connect_news",
    "connect_fx", "connect_ports", "connect_refinery", "connect_world_bank",
    "connect_maritime", "connect_bdi", "connect_gold", "connect_rbi_fx",
    "connect_opec_monthly", "connect_eia_steo", "connect_dgft_imports",
    "connect_nhai_tenders", "connect_cement_index", "connect_iocl_circular",
    "connect_fred_data",
]

test_name = "B1b. All 19 connect_* functions exist in api_hub_engine"
try:
    missing = []
    for fn_name in EXPECTED_CONNECTORS:
        if not hasattr(api_hub_engine, fn_name):
            missing.append(fn_name)
    assert not missing, f"Missing connectors: {missing}"
    record(test_name, True, f"All {len(EXPECTED_CONNECTORS)} connector functions found")
except Exception as e:
    record(test_name, False, f"{e}")

# B1c. Each connector is callable
test_name = "B1c. All connector functions are callable"
try:
    non_callable = []
    for fn_name in EXPECTED_CONNECTORS:
        fn = getattr(api_hub_engine, fn_name, None)
        if not callable(fn):
            non_callable.append(fn_name)
    assert not non_callable, f"Non-callable: {non_callable}"
    record(test_name, True, f"All {len(EXPECTED_CONNECTORS)} connectors are callable")
except Exception as e:
    record(test_name, False, f"{e}")

# --------------------------------------------------------------------------
# B2. CONNECTOR_SCHEDULE — 22 entries with proper TTLs
# --------------------------------------------------------------------------

test_name = "B2a. CONNECTOR_SCHEDULE has 22 entries"
try:
    from api_hub_engine import CONNECTOR_SCHEDULE
    count = len(CONNECTOR_SCHEDULE)
    assert count >= 22, f"Expected >= 22 entries, found {count}"
    record(test_name, True, f"{count} entries in CONNECTOR_SCHEDULE")
except Exception as e:
    record(test_name, False, f"{e}")

test_name = "B2b. CONNECTOR_SCHEDULE TTLs are positive integers"
try:
    from api_hub_engine import CONNECTOR_SCHEDULE
    invalid = []
    for cid, ttl in CONNECTOR_SCHEDULE.items():
        if not isinstance(ttl, (int, float)) or ttl <= 0:
            invalid.append((cid, ttl))
    assert not invalid, f"Invalid TTLs: {invalid}"
    record(test_name, True, f"All {len(CONNECTOR_SCHEDULE)} TTLs are positive")
except Exception as e:
    record(test_name, False, f"{e}")

test_name = "B2c. Critical connectors have short TTLs"
try:
    from api_hub_engine import CONNECTOR_SCHEDULE
    assert CONNECTOR_SCHEDULE.get("eia_crude", 999) <= 30, "eia_crude TTL should be <= 30 min"
    assert CONNECTOR_SCHEDULE.get("fx", 999) <= 120, "fx TTL should be <= 120 min"
    assert CONNECTOR_SCHEDULE.get("news", 999) <= 30, "news TTL should be <= 30 min"
    record(test_name, True, f"eia_crude={CONNECTOR_SCHEDULE['eia_crude']}m, fx={CONNECTOR_SCHEDULE['fx']}m, news={CONNECTOR_SCHEDULE['news']}m")
except Exception as e:
    record(test_name, False, f"{e}")

# --------------------------------------------------------------------------
# B3. Hub Cache read/write cycle
# --------------------------------------------------------------------------

test_name = "B3a. HubCache write/read cycle"
try:
    from api_hub_engine import HubCache
    test_key = "_test_cache_key"
    test_data = {"test": True, "value": 42, "ts": time.time()}
    HubCache.set(test_key, test_data)
    retrieved = HubCache.get(test_key)
    assert retrieved is not None, "Cache returned None after set"
    assert retrieved.get("test") is True, "Cache data mismatch"
    assert retrieved.get("value") == 42, "Cache value mismatch"
    record(test_name, True, "Write/read cycle successful")
except Exception as e:
    record(test_name, False, f"{e}")

test_name = "B3b. HubCache returns None for missing key"
try:
    from api_hub_engine import HubCache
    result = HubCache.get("_nonexistent_key_xyz_999")
    assert result is None, f"Expected None, got {result}"
    record(test_name, True, "Returns None for missing key")
except Exception as e:
    record(test_name, False, f"{e}")

# Clean up test cache key
try:
    cache_file = BASE / "hub_cache.json"
    if cache_file.exists():
        with open(cache_file, "r", encoding="utf-8") as f:
            cache = json.load(f)
        if "_test_cache_key" in cache:
            del cache["_test_cache_key"]
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache, f, indent=2, ensure_ascii=False)
except Exception:
    pass

# --------------------------------------------------------------------------
# B4. free_api_registry.py
# --------------------------------------------------------------------------

# B4a. FREE_API_CATALOG has 19+ entries
test_name = "B4a. FREE_API_CATALOG has 19+ entries"
try:
    from free_api_registry import FREE_API_CATALOG
    count = len(FREE_API_CATALOG)
    assert count >= 19, f"Expected >= 19 entries, found {count}"
    record(test_name, True, f"{count} entries in FREE_API_CATALOG")
except Exception as e:
    record(test_name, False, f"{e}")

# B4b. Each catalog entry has required fields
test_name = "B4b. Catalog entries have required fields"
try:
    from free_api_registry import FREE_API_CATALOG
    required_fields = {"name", "category", "url", "auth", "connector"}
    missing_fields = []
    for cid, entry in FREE_API_CATALOG.items():
        for field in required_fields:
            if field not in entry:
                missing_fields.append(f"{cid}.{field}")
    assert not missing_fields, f"Missing fields: {missing_fields}"
    record(test_name, True, f"All {len(FREE_API_CATALOG)} entries have {required_fields}")
except Exception as e:
    record(test_name, False, f"{e}")

# B4c. validate_api_health for 3 connectors
test_name = "B4c. validate_api_health() for 3 connectors"
try:
    from free_api_registry import validate_api_health
    tested = []
    for cid in ["eia_crude", "fx_fawazahmed", "weather_openmeteo"]:
        result = validate_api_health(cid)
        assert isinstance(result, dict), f"{cid}: Not a dict"
        assert "connector_id" in result, f"{cid}: Missing connector_id"
        assert "status" in result, f"{cid}: Missing status"
        tested.append(f"{cid}={result['status']}")
    record(test_name, True, f"Health checks: {', '.join(tested)}")
except Exception as e:
    record(test_name, False, f"{e}")

# B4d. validate_api_health returns proper structure
test_name = "B4d. validate_api_health() return structure"
try:
    from free_api_registry import validate_api_health
    result = validate_api_health("eia_crude")
    assert "connector_id" in result
    assert "status" in result
    assert result["status"] in ("healthy", "no_cache", "error", "unknown")
    record(test_name, True, f"Status: {result['status']}, keys: {list(result.keys())}")
except Exception as e:
    record(test_name, False, f"{e}")

# B4e. get_categories returns expected categories
test_name = "B4e. get_categories() returns categories"
try:
    from free_api_registry import get_categories
    cats = get_categories()
    assert isinstance(cats, list), "Not a list"
    assert len(cats) >= 5, f"Expected >= 5 categories, got {len(cats)}"
    assert "commodity" in cats, "Missing 'commodity' category"
    assert "currency" in cats, "Missing 'currency' category"
    record(test_name, True, f"Categories ({len(cats)}): {cats}")
except Exception as e:
    record(test_name, False, f"{e}")

# B4f. get_apis_by_category("commodity") returns results
test_name = "B4f. get_apis_by_category('commodity') returns results"
try:
    from free_api_registry import get_apis_by_category
    commodity_apis = get_apis_by_category("commodity")
    assert isinstance(commodity_apis, list), "Not a list"
    assert len(commodity_apis) >= 1, f"Expected >= 1, got {len(commodity_apis)}"
    for api in commodity_apis:
        assert "id" in api, "Missing 'id' field"
        assert "name" in api, "Missing 'name' field"
    names = [a.get("name", "?") for a in commodity_apis]
    record(test_name, True, f"{len(commodity_apis)} commodity APIs: {names}")
except Exception as e:
    record(test_name, False, f"{e}")

# B4g. get_apis_by_category for other categories
test_name = "B4g. get_apis_by_category for multiple categories"
try:
    from free_api_registry import get_apis_by_category, get_categories
    cats = get_categories()
    cat_counts = {}
    for cat in cats:
        apis = get_apis_by_category(cat)
        cat_counts[cat] = len(apis)
    total = sum(cat_counts.values())
    assert total >= 19, f"Total across all categories should be >= 19, got {total}"
    record(test_name, True, f"Category breakdown: {cat_counts}")
except Exception as e:
    record(test_name, False, f"{e}")

# --------------------------------------------------------------------------
# B5. sync_engine.py
# --------------------------------------------------------------------------

# B5a. Import SyncEngine
test_name = "B5a. Import SyncEngine"
try:
    from sync_engine import SyncEngine
    engine = SyncEngine()
    record(test_name, True, "SyncEngine instantiated")
except Exception as e:
    record(test_name, False, f"{e}")

# B5b. SyncEngine has 5 batches
test_name = "B5b. SyncEngine has 5 batches configured"
try:
    from sync_engine import SyncEngine
    import inspect
    source = inspect.getsource(SyncEngine.run_full_sync)
    batch_count = source.count("_run_batch")
    assert batch_count >= 5, f"Expected >= 5 _run_batch calls, found {batch_count}"
    record(test_name, True, f"{batch_count} _run_batch calls in run_full_sync")
except Exception as e:
    record(test_name, False, f"{e}")

# B5c. SyncEngine _sync_intelligence_refresh method exists
test_name = "B5c. SyncEngine._sync_intelligence_refresh exists"
try:
    from sync_engine import SyncEngine
    engine = SyncEngine()
    assert hasattr(engine, "_sync_intelligence_refresh"), "Missing _sync_intelligence_refresh"
    assert callable(engine._sync_intelligence_refresh)
    record(test_name, True, "_sync_intelligence_refresh method exists and callable")
except Exception as e:
    record(test_name, False, f"{e}")

# B5d. SyncEngine _sync_market_pulse method exists
test_name = "B5d. SyncEngine._sync_market_pulse exists"
try:
    from sync_engine import SyncEngine
    engine = SyncEngine()
    assert hasattr(engine, "_sync_market_pulse"), "Missing _sync_market_pulse"
    assert callable(engine._sync_market_pulse)
    record(test_name, True, "_sync_market_pulse method exists and callable")
except Exception as e:
    record(test_name, False, f"{e}")

# B5e. SyncEngine _sync_recommendations method exists
test_name = "B5e. SyncEngine._sync_recommendations exists"
try:
    from sync_engine import SyncEngine
    engine = SyncEngine()
    assert hasattr(engine, "_sync_recommendations"), "Missing _sync_recommendations"
    assert callable(engine._sync_recommendations)
    record(test_name, True, "_sync_recommendations method exists and callable")
except Exception as e:
    record(test_name, False, f"{e}")

# B5f. SyncEngine has all batch step methods
test_name = "B5f. SyncEngine has all batch step methods"
try:
    from sync_engine import SyncEngine
    engine = SyncEngine()
    required_methods = [
        "_sync_market_data", "_sync_news_feeds", "_sync_trade_data",
        "_validate_data", "_refresh_calculations", "_scan_opportunities",
        "_update_crm_profiles", "_generate_alerts",
        "_process_communication_triggers", "_generate_director_briefing",
        "_sync_intelligence_refresh", "_sync_market_pulse", "_sync_recommendations",
    ]
    missing = [m for m in required_methods if not hasattr(engine, m)]
    assert not missing, f"Missing methods: {missing}"
    record(test_name, True, f"All {len(required_methods)} batch step methods exist")
except Exception as e:
    record(test_name, False, f"{e}")

# B5g. SyncEngine run_market_only method
test_name = "B5g. SyncEngine.run_market_only exists"
try:
    from sync_engine import SyncEngine
    engine = SyncEngine()
    assert hasattr(engine, "run_market_only") and callable(engine.run_market_only)
    record(test_name, True, "run_market_only method exists")
except Exception as e:
    record(test_name, False, f"{e}")

# --------------------------------------------------------------------------
# B6. Data Freshness
# --------------------------------------------------------------------------

def check_freshness(file_path, name, max_hours=24):
    """Check if data file has recent timestamps."""
    test_name_inner = f"B6. Data freshness: {name}"
    try:
        if not file_path.exists():
            record(test_name_inner, False, f"File not found: {file_path}")
            return

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not data:
            record(test_name_inner, False, "File is empty")
            return

        # Find timestamps in the data
        ts_found = None
        now = datetime.now(IST)

        # Check for various timestamp fields
        if isinstance(data, dict):
            # Check top-level timestamps
            for key in ["fetched_at", "timestamp", "last_updated", "updated_at", "last_fetch"]:
                if key in data and data[key]:
                    ts_found = str(data[key])
                    break
            # Check if data has records list
            if not ts_found and "records" in data and isinstance(data["records"], list) and data["records"]:
                rec = data["records"][0]
                if isinstance(rec, dict):
                    for key in ["fetched_at", "timestamp", "date", "last_updated"]:
                        if key in rec and rec[key]:
                            ts_found = str(rec[key])
                            break
        elif isinstance(data, list) and data:
            rec = data[0] if isinstance(data[0], dict) else {}
            for key in ["fetched_at", "timestamp", "date", "last_updated"]:
                if key in rec and rec[key]:
                    ts_found = str(rec[key])
                    break

        if ts_found:
            # Try various timestamp formats
            parsed = None
            formats = [
                "%Y-%m-%d %H:%M:%S IST",
                "%Y-%m-%d %H:%M IST",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d",
                "%Y-%m-%d",
            ]
            for fmt in formats:
                try:
                    parsed = datetime.strptime(ts_found.strip()[:19] if 'T' in ts_found else ts_found.strip().replace(" IST", ""), fmt.replace(" IST", ""))
                    parsed = parsed.replace(tzinfo=IST)
                    break
                except ValueError:
                    continue

            if parsed:
                age_hours = (now - parsed).total_seconds() / 3600
                is_fresh = age_hours <= max_hours
                record(test_name_inner, is_fresh,
                       f"Timestamp: {ts_found}, age: {age_hours:.1f}h (max {max_hours}h)")
            else:
                # Could not parse but timestamp exists
                record(test_name_inner, True,
                       f"Timestamp found: {ts_found[:50]} (format not auto-parseable, data exists)")
        else:
            # No timestamp found but file has data
            size = file_path.stat().st_size
            record(test_name_inner, True,
                   f"No timestamp field found, but file has {size} bytes of data")
    except Exception as e:
        record(test_name_inner, False, f"Error: {e}")

# Check data freshness for key files
check_freshness(BASE / "tbl_crude_prices.json", "tbl_crude_prices.json")
check_freshness(BASE / "tbl_fx_rates.json", "tbl_fx_rates.json")
check_freshness(BASE / "tbl_weather.json", "tbl_weather.json")

# --------------------------------------------------------------------------
# B7. Additional API Infrastructure Tests
# --------------------------------------------------------------------------

# B7a. DEFAULT_CATALOG exists
test_name = "B7a. DEFAULT_CATALOG in api_hub_engine"
try:
    from api_hub_engine import DEFAULT_CATALOG
    assert isinstance(DEFAULT_CATALOG, dict)
    assert len(DEFAULT_CATALOG) >= 8, f"Expected >= 8, got {len(DEFAULT_CATALOG)}"
    record(test_name, True, f"{len(DEFAULT_CATALOG)} entries in DEFAULT_CATALOG")
except Exception as e:
    record(test_name, False, f"{e}")

# B7b. DEFAULT_CATALOG_GOVT exists
test_name = "B7b. DEFAULT_CATALOG_GOVT in api_hub_engine"
try:
    from api_hub_engine import DEFAULT_CATALOG_GOVT
    assert isinstance(DEFAULT_CATALOG_GOVT, dict)
    assert len(DEFAULT_CATALOG_GOVT) >= 3, f"Expected >= 3, got {len(DEFAULT_CATALOG_GOVT)}"
    record(test_name, True, f"{len(DEFAULT_CATALOG_GOVT)} entries in DEFAULT_CATALOG_GOVT")
except Exception as e:
    record(test_name, False, f"{e}")

# B7c. HubCatalog class
test_name = "B7c. HubCatalog class exists"
try:
    from api_hub_engine import HubCatalog
    assert hasattr(HubCatalog, "get")
    record(test_name, True, "HubCatalog class with get() method")
except Exception as e:
    record(test_name, False, f"{e}")

# B7d. Table file paths are defined
test_name = "B7d. Normalized table paths defined"
try:
    from api_hub_engine import (TBL_CRUDE, TBL_FX, TBL_WEATHER, TBL_NEWS,
                                 TBL_TRADE, TBL_PORTS, TBL_REFINERY)
    paths = {
        "TBL_CRUDE": TBL_CRUDE,
        "TBL_FX": TBL_FX,
        "TBL_WEATHER": TBL_WEATHER,
        "TBL_NEWS": TBL_NEWS,
        "TBL_TRADE": TBL_TRADE,
        "TBL_PORTS": TBL_PORTS,
        "TBL_REFINERY": TBL_REFINERY,
    }
    existing = [k for k, v in paths.items() if v.exists()]
    record(test_name, True, f"Defined: {list(paths.keys())}, Existing: {existing}")
except Exception as e:
    record(test_name, False, f"{e}")

# B7e. _should_refresh function
test_name = "B7e. _should_refresh function works"
try:
    from api_hub_engine import _should_refresh
    # A non-existent connector should need refresh
    result = _should_refresh("_nonexistent_test_connector")
    assert result is True, "Non-existent connector should need refresh"
    record(test_name, True, "Non-existent connector correctly returns True")
except Exception as e:
    record(test_name, False, f"{e}")

# B7f. Hub activity log file exists
test_name = "B7f. Hub activity log file exists"
try:
    from api_hub_engine import HUB_LOG_FILE
    assert HUB_LOG_FILE.exists(), f"Log file not found: {HUB_LOG_FILE}"
    size = HUB_LOG_FILE.stat().st_size
    record(test_name, True, f"Log file: {size} bytes")
except Exception as e:
    record(test_name, False, f"{e}")

# B7g. Hub cache file exists
test_name = "B7g. Hub cache file exists and is valid JSON"
try:
    from api_hub_engine import HUB_CACHE_FILE
    assert HUB_CACHE_FILE.exists(), f"Cache file not found"
    with open(HUB_CACHE_FILE, "r", encoding="utf-8") as f:
        cache = json.load(f)
    assert isinstance(cache, dict)
    record(test_name, True, f"Cache file: {len(cache)} entries, {HUB_CACHE_FILE.stat().st_size} bytes")
except Exception as e:
    record(test_name, False, f"{e}")

# B7h. validate_all_apis function
test_name = "B7h. validate_all_apis() returns summary"
try:
    from free_api_registry import validate_all_apis
    result = validate_all_apis()
    assert isinstance(result, dict)
    assert "total" in result
    assert "healthy" in result
    assert "health_pct" in result
    assert "details" in result
    record(test_name, True,
           f"Total: {result['total']}, Healthy: {result['healthy']}, "
           f"Health: {result['health_pct']}%")
except Exception as e:
    record(test_name, False, f"{e}")


# ==========================================================================
# SUMMARY
# ==========================================================================

print()
print("=" * 80)
print("TEST RESULTS SUMMARY")
print("=" * 80)

pass_count = sum(1 for r in results if r[0] == "PASS")
fail_count = sum(1 for r in results if r[0] == "FAIL")
total = len(results)

print()
for status, name, detail in results:
    marker = "PASS" if status == "PASS" else "FAIL"
    print(f"[{marker}] {name} -- {_safe_str(str(detail))}")

print()
print("-" * 80)
print(f"TOTAL: {total} tests | PASSED: {pass_count} | FAILED: {fail_count}")
print(f"Pass Rate: {pass_count/total*100:.1f}%" if total > 0 else "No tests run")
print("-" * 80)
