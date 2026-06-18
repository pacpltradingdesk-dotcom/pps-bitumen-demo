"""
Generate premium PDF demo samples — one of each type.
Run: python generate_pdf_demos.py
Outputs to demo_pdfs/ and opens them.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from share_formatter import (
    build_quote_pdf,
    build_invoice_pdf,
    build_purchase_order_pdf,
    build_director_brief_pdf,
    build_sales_order_pdf,
    build_payment_receipt_pdf,
    build_delivery_note_pdf,
)

OUT = Path("demo_pdfs")
OUT.mkdir(exist_ok=True)


def _save(name: str, data: bytes) -> Path:
    p = OUT / name
    p.write_bytes(data)
    print(f"  [OK] {p}  ({len(data):,} bytes)")
    return p


def demo_quote() -> Path:
    pdf = build_quote_pdf(
        customer_name="Shree Ganesh Infra Pvt Ltd",
        city="Pune, Maharashtra",
        grade="VG-30",
        qty_mt=120,
        price_per_mt=78260,
        source="Vadinar Terminal",
        quote_no="FY2526/QT/0142",
    )
    return _save("01_Premium_Quote.pdf", pdf)


def demo_invoice() -> Path:
    pdf = build_invoice_pdf(
        customer_name="Highway Builders Pvt Ltd",
        customer_gst="27AABCH1234C1Z5",
        customer_address="Plot 42, MIDC Phase-II, Pune — 411019",
        customer_state="Maharashtra",
        invoice_no="FY2526/INV/0078",
        invoice_date="14-04-2026",
        place_of_supply="Maharashtra",
        items=[
            {"desc": "Bitumen VG-30 (Bulk)", "qty": 80, "rate": 48500},
            {"desc": "Bitumen VG-10 (Drum)", "qty": 20, "rate": 51200},
        ],
    )
    return _save("02_Premium_Invoice.pdf", pdf)


def demo_po() -> Path:
    pdf = build_purchase_order_pdf(
        supplier_name="Indian Oil Corporation Ltd",
        supplier_address="IOCL Refinery, Vadinar, Gujarat — 361010",
        supplier_gst="24AAACI1681G1Z0",
        po_no="FY2526/PO/0031",
        po_date="14-04-2026",
        delivery_date="22-04-2026",
        delivery_address="PPS Warehouse, Vadodara, Gujarat — 390007",
        items=[
            {"desc": "Bitumen VG-30 Bulk (tanker)", "qty": 150, "rate": 46200},
            {"desc": "Bitumen VG-10 Drum (210kg)", "qty": 48, "rate": 49100},
        ],
    )
    return _save("03_Premium_Purchase_Order.pdf", pdf)


def demo_director_brief() -> Path:
    kpis = [
        {"label": "Brent Crude", "value": "$84.20", "delta": "+1.8%",
         "color": "#16A34A", "direction": "up"},
        {"label": "USD / INR", "value": "83.42", "delta": "-0.12",
         "color": "#16A34A", "direction": "down"},
        {"label": "VG-30 Landed", "value": "Rs.48,500", "delta": "+2.1%",
         "color": "#DC2626", "direction": "up"},
        {"label": "Active Deals", "value": "14", "delta": "+3",
         "color": "#16A34A", "direction": "up"},
        {"label": "Pending AR", "value": "Rs.1.82 Cr", "delta": "-8%",
         "color": "#16A34A", "direction": "down"},
        {"label": "AI Signal", "value": "BUY", "delta": "78% urgency",
         "color": "#16A34A", "direction": "up"},
    ]
    sections = [
        {"title": "Yesterday",
         "icon": "■", "accent": "#6B7280",
         "bullets": [
             "Closed Shree Ganesh deal — 120 MT @ Rs.48,500/MT (margin Rs.2,400/MT)",
             "IOCL circular: VG-30 ex-Vadinar up Rs.450/MT effective 15-Apr",
             "Received 62% of pending AR from Highway Builders (Rs.1.12 Cr)",
         ]},
        {"title": "Today",
         "icon": "▲", "accent": "#4F46E5",
         "bullets": [
             "Call L&T, NHAI Pune PKG-3 — VG-30 requirement 400 MT next 2 weeks",
             "Send reactivation offer to 12 dormant contractors (Q1 no orders)",
             "Lock freight rate with Vadinar-Pune fleet before next IOCL revision",
         ]},
        {"title": "15-Day Outlook",
         "icon": "♦", "accent": "#c9a84c",
         "bullets": [
             "Brent expected Rs.85-88 band; IOCL likely revise upward 15/22-Apr",
             "Monsoon onset Kerala 28-May — north/west demand peaks through 10-May",
             "Govt tender pipeline: 3 NHAI + 2 MoRTH closings by 30-Apr (Rs.12 Cr)",
         ]},
        {"title": "Risks",
         "icon": "●", "accent": "#DC2626",
         "bullets": [
             "Sundarpur Transport overdue Rs.38 L — legal notice if unpaid by 20-Apr",
             "Vadodara refinery shutdown risk 18-Apr (unconfirmed): lock alt source",
         ]},
    ]
    pdf = build_director_brief_pdf(
        date_str="14 April 2026, Tuesday",
        kpis=kpis,
        sections=sections,
        overall_status="WATCH",
        top_action="Lock 400 MT VG-30 with IOCL before 15-Apr circular revision (est +Rs.450/MT exposure)",
        mood="Margins tight, opportunities real — execute with discipline",
    )
    return _save("04_Premium_Director_Brief.pdf", pdf)


def demo_sales_order() -> Path:
    pdf = build_sales_order_pdf(
        customer_name="Highway Builders Pvt Ltd",
        customer_address="Plot 42, MIDC Phase-II, Pune — 411019",
        customer_gst="27AABCH1234C1Z5",
        so_no="FY2526/SO/0091",
        so_date="14-04-2026",
        dispatch_date="18-04-2026",
        dispatch_from="PPS Warehouse, Vadodara",
        items=[
            {"desc": "Bitumen VG-30 Bulk (tanker)", "qty": 60, "rate": 48500},
            {"desc": "Bitumen VG-10 Drum (210kg)", "qty": 20, "rate": 51200},
        ],
    )
    return _save("05_Premium_Sales_Order.pdf", pdf)


def demo_payment_receipt() -> Path:
    pdf = build_payment_receipt_pdf(
        party_name="Highway Builders Pvt Ltd",
        party_address="Plot 42, MIDC Phase-II, Pune — 411019",
        receipt_no="FY2526/RCP/0048",
        receipt_date="14-04-2026",
        amount=1125000,
        mode="RTGS / NEFT",
        reference_no="ICIC8942631045",
        against_invoice="FY2526/INV/0078",
        direction="received",
    )
    return _save("06_Premium_Payment_Receipt.pdf", pdf)


def demo_delivery_note() -> Path:
    pdf = build_delivery_note_pdf(
        customer_name="Highway Builders Pvt Ltd",
        delivery_address="Plot 42, MIDC Phase-II, Pune — 411019, Maharashtra",
        dn_no="FY2526/DN/0112",
        dn_date="18-04-2026",
        dispatch_from="PPS Warehouse, Vadodara, Gujarat",
        vehicle_no="GJ-06-BW-4821",
        driver_name="Rameshbhai Patel",
        driver_phone="+91 94272 88910",
        so_ref="FY2526/SO/0091",
        invoice_ref="FY2526/INV/0078",
        items=[
            {"desc": "Bitumen VG-30 Bulk", "qty": 40.000, "batch": "VAD-0418-A"},
            {"desc": "Bitumen VG-30 Bulk", "qty": 20.000, "batch": "VAD-0418-B"},
            {"desc": "Bitumen VG-10 Drum (210kg)", "qty": 20.000, "batch": "DRM-240418"},
        ],
    )
    return _save("07_Premium_Delivery_Note.pdf", pdf)


def _open(p: Path) -> None:
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(p))
        elif sys.platform == "darwin":
            os.system(f"open '{p}'")
        else:
            os.system(f"xdg-open '{p}'")
    except Exception as e:
        print(f"  (could not auto-open {p.name}: {e})")


if __name__ == "__main__":
    print("Generating premium PDF demos...")
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["new", "all"], default="all",
                    help="'new' = only 05/06/07 (SO / Payment / Delivery Note)")
    args = ap.parse_args()

    all_builders = [
        demo_quote,
        demo_invoice,
        demo_po,
        demo_director_brief,
        demo_sales_order,
        demo_payment_receipt,
        demo_delivery_note,
    ]
    builders = all_builders[-3:] if args.only == "new" else all_builders
    paths = [b() for b in builders]
    print("\nOpening PDFs...")
    for p in paths:
        _open(p)
    print(f"\nDone. Files in: {OUT.resolve()}")
