"""
Document PDF Engine — PPS Anantams Corporate Documents v2.0
============================================================

Generates professional PO, SO, and Payment Order PDFs using ReportLab Platypus.

Features v2.0:
- "Page X of Y" footer via two-pass build (_TotalPageCountDocTemplate)
- FY-based doc numbering (FY2526/PO/0001)
- Enhanced Payment PDF: payment mode, due dates, 3 signature blocks, transporter section
- LR No in logistics section
- Standardized footer: Page X of Y | Generated IST | User | Company | Computer Generated
"""

from __future__ import annotations

import io
import os
import datetime
from pathlib import Path

import pytz
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm, inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.pdfgen import canvas as pdfgen_canvas
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, HRFlowable, KeepTogether, PageBreak,
)

from company_config import COMPANY_PROFILE

# ── Paths ─────────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).parent
LOGO_PATH = BASE_DIR / "pps_logo.png"
EXPORT_DIR = BASE_DIR / "pdf_exports"
EXPORT_DIR.mkdir(exist_ok=True)

IST = pytz.timezone("Asia/Kolkata")

# ── Colors (Vastu Design System) ─────────────────────────────────────────

DARK_BLUE = colors.HexColor("#1e3a5f")
MID_BLUE = colors.HexColor("#2563eb")
LIGHT_BLUE = colors.HexColor("#dbeafe")
ORANGE = colors.HexColor("#ea580c")
GREEN = colors.HexColor("#16a34a")
RED = colors.HexColor("#dc2626")
GREY_LIGHT = colors.HexColor("#f1f5f9")
GREY_MED = colors.HexColor("#94a3b8")
GREY_DARK = colors.HexColor("#334155")
WHITE = colors.white
BLACK = colors.black

# ── Timestamps ────────────────────────────────────────────────────────────

def _now_ist() -> datetime.datetime:
    return datetime.datetime.now(IST)

def _ts_ist(fmt: str = "%Y-%m-%d %H:%M IST") -> str:
    return _now_ist().strftime(fmt)

def _ts_filename() -> str:
    return _now_ist().strftime("%Y-%m-%d_%H%MIST")

# ── INR Formatting ────────────────────────────────────────────────────────

def format_inr(amount, symbol: bool = True) -> str:
    """Indian number formatting: 48,302 → ₹ 48,302 / 1,23,45,678"""
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return str(amount)
    prefix = "\u20b9 " if symbol else ""
    if amount < 0:
        return f"-{prefix}{_indian_comma(-amount)}"
    return f"{prefix}{_indian_comma(amount)}"

def _indian_comma(n: float) -> str:
    s = f"{n:,.2f}"
    parts = s.split(".")
    integer = parts[0].replace(",", "")
    decimal = parts[1] if len(parts) > 1 else "00"
    if len(integer) <= 3:
        return f"{integer}.{decimal}"
    last3 = integer[-3:]
    rest = integer[:-3]
    groups = []
    while len(rest) > 2:
        groups.append(rest[-2:])
        rest = rest[:-2]
    if rest:
        groups.append(rest)
    groups.reverse()
    return ",".join(groups) + "," + last3 + "." + decimal


# ── Styles ────────────────────────────────────────────────────────────────

def _make_styles():
    base = getSampleStyleSheet()
    styles = {}
    styles["title"] = ParagraphStyle(
        "DocTitle", parent=base["Title"],
        fontSize=16, leading=20, textColor=DARK_BLUE, spaceAfter=2,
    )
    styles["subtitle"] = ParagraphStyle(
        "DocSubtitle", parent=base["Normal"],
        fontSize=9, leading=12, textColor=GREY_DARK, spaceAfter=2,
    )
    styles["section"] = ParagraphStyle(
        "DocSection", parent=base["Heading2"],
        fontSize=11, leading=14, textColor=DARK_BLUE,
        spaceBefore=8, spaceAfter=4, fontName="Helvetica-Bold",
    )
    styles["body"] = ParagraphStyle(
        "DocBody", parent=base["Normal"],
        fontSize=9, leading=13, textColor=GREY_DARK, spaceAfter=3,
    )
    styles["body_bold"] = ParagraphStyle(
        "DocBodyBold", parent=base["Normal"],
        fontSize=9, leading=13, textColor=GREY_DARK,
        fontName="Helvetica-Bold", spaceAfter=3,
    )
    styles["small"] = ParagraphStyle(
        "DocSmall", parent=base["Normal"],
        fontSize=7.5, leading=10, textColor=GREY_MED,
    )
    styles["table_header"] = ParagraphStyle(
        "DocTableHeader", parent=base["Normal"],
        fontSize=8, leading=10, textColor=WHITE, fontName="Helvetica-Bold",
    )
    styles["table_cell"] = ParagraphStyle(
        "DocTableCell", parent=base["Normal"],
        fontSize=8, leading=11, textColor=GREY_DARK,
    )
    styles["table_cell_right"] = ParagraphStyle(
        "DocTableCellR", parent=base["Normal"],
        fontSize=8, leading=11, textColor=GREY_DARK, alignment=TA_RIGHT,
    )
    styles["table_cell_bold"] = ParagraphStyle(
        "DocTableCellBold", parent=base["Normal"],
        fontSize=8, leading=11, textColor=GREY_DARK, fontName="Helvetica-Bold",
    )
    styles["company_name"] = ParagraphStyle(
        "DocCompanyName", parent=base["Normal"],
        fontSize=13, leading=16, textColor=WHITE, fontName="Helvetica-Bold",
    )
    styles["company_detail"] = ParagraphStyle(
        "DocCompanyDetail", parent=base["Normal"],
        fontSize=7.5, leading=10, textColor=colors.HexColor("#cbd5e1"),
    )
    return styles

STYLES = _make_styles()


# ═══════════════════════════════════════════════════════════════════════════
# NUMBERED CANVAS — "Page X of Y" via deferred rendering
# ═══════════════════════════════════════════════════════════════════════════

class _NumberedCanvas(pdfgen_canvas.Canvas):
    """Canvas subclass that supports 'Page X of Y' by deferring page output."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_page_total(total)
            super().showPage()
        super().save()

    def _draw_page_total(self, total: int):
        """Overwrite the page number placeholder with 'Page X of Y'."""
        # Draw over the footer area where we left a placeholder
        self.saveState()
        self.setFillColor(colors.white)
        # White out the placeholder area (left side of footer)
        self.rect(14 * mm, 12.5 * mm, 80 * mm, 5 * mm, fill=1, stroke=0)
        self.setFillColor(GREY_MED)
        self.setFont("Helvetica", 7)
        page_num = self._pageNumber
        self.drawString(
            15 * mm, 14 * mm,
            f"Page {page_num} of {total}  |  Generated: {_ts_ist()}  |  User: {getattr(self, '_doc_username', 'Admin')}",
        )
        self.restoreState()


# ═══════════════════════════════════════════════════════════════════════════
# DOCUMENT PDF ENGINE
# ═══════════════════════════════════════════════════════════════════════════

class DocumentPDFEngine:
    """Generate corporate PO, SO, and Payment Order PDFs."""

    def __init__(self, doc_type: str, doc_number: str,
                 reference: str = "", username: str = "Admin"):
        self.doc_type = doc_type          # "PURCHASE ORDER", "SALES ORDER", etc.
        self.doc_number = doc_number      # "FY2526/PO/0001"
        self.reference = reference        # Optional deal reference
        self.username = username
        self.doc_date = _ts_ist()

    # ── PUBLIC API ─────────────────────────────────────────────────────────

    def generate_po_pdf(self, po_data: dict) -> bytes:
        """Generate a Purchase Order PDF. Returns PDF bytes."""
        elements = []
        elements.extend(self._document_header_block())
        elements.append(Spacer(1, 4 * mm))
        elements.extend(self._party_info_box(po_data.get("supplier", {}), "SUPPLIER"))
        elements.append(Spacer(1, 4 * mm))
        elements.extend(self._items_table(po_data.get("items", [])))
        elements.append(Spacer(1, 4 * mm))
        logistics = po_data.get("logistics", {})
        if logistics:
            elements.extend(self._logistics_section(logistics))
            elements.append(Spacer(1, 4 * mm))
        elements.extend(self._terms_and_bank_section(po_data.get("terms", [])))
        elements.append(Spacer(1, 6 * mm))
        elements.extend(self._declaration_section())
        elements.append(Spacer(1, 8 * mm))
        elements.extend(self._signature_block())
        return self._build_pdf(elements)

    def generate_so_pdf(self, so_data: dict) -> bytes:
        """Generate a Sales Order PDF. Returns PDF bytes."""
        elements = []
        elements.extend(self._document_header_block())
        elements.append(Spacer(1, 4 * mm))
        elements.extend(self._party_info_box(so_data.get("customer", {}), "CUSTOMER"))
        elements.append(Spacer(1, 4 * mm))
        elements.extend(self._items_table(so_data.get("items", [])))
        elements.append(Spacer(1, 4 * mm))
        logistics = so_data.get("logistics", {})
        if logistics:
            elements.extend(self._logistics_section(logistics))
            elements.append(Spacer(1, 4 * mm))
        elements.extend(self._terms_and_bank_section(so_data.get("terms", [])))
        elements.append(Spacer(1, 6 * mm))
        elements.extend(self._declaration_section())
        elements.append(Spacer(1, 8 * mm))
        elements.extend(self._signature_block())
        return self._build_pdf(elements)

    def generate_payment_pdf(self, pay_data: dict) -> bytes:
        """Generate an enhanced Payment Order PDF. Returns PDF bytes."""
        elements = []
        elements.extend(self._document_header_block())
        elements.append(Spacer(1, 4 * mm))

        # Payment mode + PO/SO references
        elements.extend(self._payment_meta_section(pay_data))
        elements.append(Spacer(1, 4 * mm))

        # Purchase Payable + Sales Receivable side by side
        elements.extend(self._payment_summary_section(pay_data))
        elements.append(Spacer(1, 4 * mm))

        # Transport section
        transport = pay_data.get("transport", {})
        if transport and transport.get("name"):
            elements.extend(self._transport_section(transport))
            elements.append(Spacer(1, 4 * mm))

        # Profit Summary
        elements.extend(self._profit_summary_section(pay_data))
        elements.append(Spacer(1, 6 * mm))

        # Bank details
        elements.extend(self._bank_section())
        elements.append(Spacer(1, 8 * mm))

        # 3-column signature block: Prepared / Approved / Payment By
        elements.extend(self._payment_signature_block(pay_data))
        return self._build_pdf(elements)

    # ── INTERNAL: PDF Builder ──────────────────────────────────────────────

    def _build_pdf(self, elements: list) -> bytes:
        """Build PDF with 'Page X of Y' via _NumberedCanvas deferred rendering."""
        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf, pagesize=A4,
            rightMargin=15 * mm, leftMargin=15 * mm,
            topMargin=38 * mm, bottomMargin=22 * mm,
        )
        # Store username on doc so _NumberedCanvas can access it
        doc._doc_username = self.username
        doc.build(elements, onFirstPage=self._header_footer_placeholder,
                  onLaterPages=self._header_footer_placeholder,
                  canvasmaker=_NumberedCanvas)
        return buf.getvalue()

    def _header_footer_placeholder(self, canvas, doc):
        """Draw corporate header and placeholder footer on every page.
        The _NumberedCanvas.save() will overwrite the page number with 'Page X of Y'."""
        # Pass username to canvas for _NumberedCanvas
        canvas._doc_username = self.username
        canvas.saveState()
        W, H = doc.pagesize

        # ── HEADER STRIP ──────────────────────────────────────────────────
        header_h = 32 * mm
        canvas.setFillColor(DARK_BLUE)
        canvas.rect(0, H - header_h, W, header_h, fill=1, stroke=0)

        # Logo
        lp = str(LOGO_PATH)
        x_text = 10 * mm
        if os.path.exists(lp):
            try:
                canvas.drawImage(lp, 10 * mm, H - 28 * mm,
                                 width=20 * mm, height=20 * mm,
                                 preserveAspectRatio=True, mask="auto")
                x_text = 35 * mm
            except Exception:
                pass

        # Company name
        canvas.setFillColor(WHITE)
        canvas.setFont("Helvetica-Bold", 13)
        canvas.drawString(x_text, H - 14 * mm, COMPANY_PROFILE["legal_name"])

        # Company details line
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#cbd5e1"))
        detail = (
            f"GSTIN: {COMPANY_PROFILE['gst_no']}  |  "
            f"CIN: {COMPANY_PROFILE['cin_no']}  |  "
            f"PAN: {COMPANY_PROFILE['pan_no']}"
        )
        canvas.drawString(x_text, H - 20 * mm, detail)
        canvas.drawString(x_text, H - 25 * mm, COMPANY_PROFILE["full_address"])

        # ── DOCUMENT TYPE BAR ─────────────────────────────────────────────
        bar_y = H - header_h - 6 * mm
        canvas.setFillColor(ORANGE)
        canvas.rect(0, bar_y - 1 * mm, W, 7 * mm, fill=1, stroke=0)

        canvas.setFillColor(WHITE)
        canvas.setFont("Helvetica-Bold", 10)
        canvas.drawString(15 * mm, bar_y + 1 * mm, self.doc_type)

        canvas.setFont("Helvetica-Bold", 9)
        canvas.drawRightString(W - 15 * mm, bar_y + 1 * mm, self.doc_number)

        # Date + reference line below bar
        canvas.setFillColor(GREY_DARK)
        canvas.setFont("Helvetica", 7.5)
        info_y = bar_y - 5 * mm
        canvas.drawString(15 * mm, info_y, f"Date: {self.doc_date}")
        if self.reference:
            canvas.drawRightString(W - 15 * mm, info_y, f"Ref: {self.reference}")

        # ── FOOTER (placeholder — NumberedCanvas overwrites left side with Page X of Y)
        canvas.setStrokeColor(GREY_MED)
        canvas.setLineWidth(0.5)
        canvas.line(15 * mm, 18 * mm, W - 15 * mm, 18 * mm)

        canvas.setFillColor(GREY_MED)
        canvas.setFont("Helvetica", 7)
        # Left side: placeholder (overwritten by _NumberedCanvas._draw_page_total)
        canvas.drawString(
            15 * mm, 14 * mm,
            f"Page {canvas.getPageNumber()}  |  Generated: {_ts_ist()}  |  User: {self.username}",
        )
        # Right side: company name (not overwritten)
        canvas.drawRightString(
            W - 15 * mm, 14 * mm,
            "PPS Anantams Corporation Pvt Ltd  |  Computer Generated Document",
        )

        canvas.restoreState()

    # ── INTERNAL: Content Blocks ───────────────────────────────────────────

    def _document_header_block(self) -> list:
        """Spacer after the canvas-drawn header."""
        return [Spacer(1, 8 * mm)]

    def _party_info_box(self, party: dict, label: str) -> list:
        """Formatted box for supplier/customer details."""
        if not party:
            return []

        name = party.get("name", "N/A")
        gstin = party.get("gstin", "N/A")
        pan = party.get("pan", "")
        address = party.get("address", "")
        city = party.get("city", "")
        state = party.get("state", "")
        contact = party.get("contact", "")

        full_addr = address
        if city:
            full_addr += f", {city}" if full_addr else city
        if state:
            full_addr += f", {state}" if full_addr else state

        rows = [
            [Paragraph(f"<b>{label} DETAILS</b>", STYLES["table_header"]), ""],
            [Paragraph("<b>Name:</b>", STYLES["table_cell"]),
             Paragraph(str(name), STYLES["table_cell_bold"])],
            [Paragraph("<b>GSTIN:</b>", STYLES["table_cell"]),
             Paragraph(str(gstin), STYLES["table_cell"])],
        ]
        if pan:
            rows.append([
                Paragraph("<b>PAN:</b>", STYLES["table_cell"]),
                Paragraph(str(pan), STYLES["table_cell"]),
            ])
        if full_addr:
            rows.append([
                Paragraph("<b>Address:</b>", STYLES["table_cell"]),
                Paragraph(str(full_addr), STYLES["table_cell"]),
            ])
        if contact:
            rows.append([
                Paragraph("<b>Contact:</b>", STYLES["table_cell"]),
                Paragraph(str(contact), STYLES["table_cell"]),
            ])

        t = Table(rows, colWidths=[35 * mm, 140 * mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), DARK_BLUE),
            ("SPAN", (0, 0), (-1, 0)),
            ("BOX", (0, 0), (-1, -1), 0.5, GREY_MED),
            ("LINEBELOW", (0, 0), (-1, 0), 1, DARK_BLUE),
            ("GRID", (0, 1), (-1, -1), 0.25, GREY_LIGHT),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        return [t]

    def _items_table(self, items: list) -> list:
        """Material table: Sn | Product | HSN | Packing | Qty MT | Rate/MT | GST | Amount."""
        if not items:
            return [Paragraph("No items specified.", STYLES["body"])]

        header = [
            Paragraph("Sn", STYLES["table_header"]),
            Paragraph("Product", STYLES["table_header"]),
            Paragraph("HSN", STYLES["table_header"]),
            Paragraph("Packing", STYLES["table_header"]),
            Paragraph("Qty (MT)", STYLES["table_header"]),
            Paragraph("Rate/MT", STYLES["table_header"]),
            Paragraph("GST @18%", STYLES["table_header"]),
            Paragraph("Amount", STYLES["table_header"]),
        ]

        data = [header]
        subtotal = 0.0
        total_gst = 0.0

        for i, item in enumerate(items):
            qty = float(item.get("quantity", 0))
            rate = float(item.get("rate", 0))
            gst_rate = float(item.get("gst_rate", 18)) / 100
            line_subtotal = qty * rate
            line_gst = line_subtotal * gst_rate
            line_total = line_subtotal + line_gst
            subtotal += line_subtotal
            total_gst += line_gst

            data.append([
                Paragraph(str(i + 1), STYLES["table_cell"]),
                Paragraph(str(item.get("product", "BITUMEN VG30")), STYLES["table_cell_bold"]),
                Paragraph(str(item.get("hsn", "27132000")), STYLES["table_cell"]),
                Paragraph(str(item.get("packing", "BULK")), STYLES["table_cell"]),
                Paragraph(f"{qty:.3f}", STYLES["table_cell_right"]),
                Paragraph(format_inr(rate), STYLES["table_cell_right"]),
                Paragraph(format_inr(line_gst), STYLES["table_cell_right"]),
                Paragraph(format_inr(line_total), STYLES["table_cell_right"]),
            ])

        # Totals rows
        grand_total = subtotal + total_gst
        data.append([
            "", "", "", "",
            Paragraph("<b>Subtotal:</b>", STYLES["table_cell_right"]),
            "", "",
            Paragraph(f"<b>{format_inr(subtotal)}</b>", STYLES["table_cell_right"]),
        ])
        data.append([
            "", "", "", "",
            Paragraph("<b>GST @18%:</b>", STYLES["table_cell_right"]),
            "", "",
            Paragraph(f"<b>{format_inr(total_gst)}</b>", STYLES["table_cell_right"]),
        ])
        data.append([
            "", "", "", "",
            Paragraph("<b>GRAND TOTAL:</b>", STYLES["table_cell_right"]),
            "", "",
            Paragraph(f"<b>{format_inr(grand_total)}</b>", STYLES["table_cell_right"]),
        ])

        col_widths = [8*mm, 38*mm, 18*mm, 18*mm, 20*mm, 25*mm, 25*mm, 28*mm]
        t = Table(data, colWidths=col_widths)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), DARK_BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("GRID", (0, 0), (-1, len(items)), 0.5, GREY_MED),
            ("ROWBACKGROUNDS", (0, 1), (-1, len(items)), [WHITE, GREY_LIGHT]),
            ("LINEABOVE", (4, len(items) + 1), (-1, len(items) + 1), 1, DARK_BLUE),
            ("LINEABOVE", (4, len(items) + 3), (-1, len(items) + 3), 1.5, DARK_BLUE),
            ("BACKGROUND", (4, len(items) + 3), (-1, len(items) + 3), LIGHT_BLUE),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))

        return [
            Paragraph("MATERIAL DETAILS", STYLES["section"]),
            t,
        ]

    def _logistics_section(self, logistics: dict) -> list:
        """Vehicle, transporter, loading point, delivery point, LR No."""
        rows = [
            [Paragraph("<b>LOGISTICS DETAILS</b>", STYLES["table_header"]), "", "", ""],
        ]
        row1 = [
            Paragraph("<b>Vehicle No:</b>", STYLES["table_cell"]),
            Paragraph(str(logistics.get("vehicle_no", "N/A")), STYLES["table_cell"]),
            Paragraph("<b>Transporter:</b>", STYLES["table_cell"]),
            Paragraph(str(logistics.get("transporter", "N/A")), STYLES["table_cell"]),
        ]
        row2 = [
            Paragraph("<b>Loading Point:</b>", STYLES["table_cell"]),
            Paragraph(str(logistics.get("loading_point", "N/A")), STYLES["table_cell"]),
            Paragraph("<b>Delivery Point:</b>", STYLES["table_cell"]),
            Paragraph(str(logistics.get("delivery_point", "N/A")), STYLES["table_cell"]),
        ]
        rows.extend([row1, row2])

        # LR Number
        lr_no = logistics.get("lr_no", "")
        if lr_no:
            rows.append([
                Paragraph("<b>LR No:</b>", STYLES["table_cell"]),
                Paragraph(str(lr_no), STYLES["table_cell"]),
                Paragraph("<b>LR Status:</b>", STYLES["table_cell"]),
                Paragraph("Issued", STYLES["table_cell"]),
            ])

        if logistics.get("driver_name"):
            rows.append([
                Paragraph("<b>Driver:</b>", STYLES["table_cell"]),
                Paragraph(str(logistics["driver_name"]), STYLES["table_cell"]),
                Paragraph("<b>Driver Phone:</b>", STYLES["table_cell"]),
                Paragraph(str(logistics.get("driver_phone", "")), STYLES["table_cell"]),
            ])

        t = Table(rows, colWidths=[30*mm, 57*mm, 30*mm, 57*mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), DARK_BLUE),
            ("SPAN", (0, 0), (-1, 0)),
            ("BOX", (0, 0), (-1, -1), 0.5, GREY_MED),
            ("GRID", (0, 1), (-1, -1), 0.25, GREY_LIGHT),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        return [t]

    def _terms_and_bank_section(self, terms: list | None = None) -> list:
        """Terms & conditions + bank details side by side."""
        if not terms:
            try:
                from database import get_connection, _rows_to_list
                with get_connection() as conn:
                    term_rows = _rows_to_list(
                        conn.execute(
                            "SELECT term_text FROM terms_master "
                            "WHERE is_active = 1 AND category != 'clause' ORDER BY sort_order"
                        ).fetchall()
                    )
                terms = [t["term_text"] for t in term_rows]
            except Exception:
                terms = COMPANY_PROFILE.get("terms", [])

        terms_content = [Paragraph("<b>Terms &amp; Conditions:</b>", STYLES["body_bold"])]
        for term in terms:
            terms_content.append(Paragraph(str(term), STYLES["small"]))

        bd = COMPANY_PROFILE.get("bank_details", {})
        bank_content = [
            Paragraph("<b>Bank Details for Payment:</b>", STYLES["body_bold"]),
            Paragraph(f"Bank: {bd.get('bank_name', '')}", STYLES["body"]),
            Paragraph(f"A/c No: {bd.get('ac_no', '')}", STYLES["body"]),
            Paragraph(f"IFSC: {bd.get('ifsc', '')}", STYLES["body"]),
            Paragraph(f"Branch: {bd.get('branch', '')}", STYLES["body"]),
        ]

        t = Table([[terms_content, bank_content]], colWidths=[110 * mm, 65 * mm])
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOX", (0, 0), (-1, -1), 0.5, GREY_MED),
            ("GRID", (0, 0), (-1, -1), 0.25, GREY_LIGHT),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        return [t]

    def _bank_section(self) -> list:
        """Standalone bank details box."""
        bd = COMPANY_PROFILE.get("bank_details", {})
        rows = [
            [Paragraph("<b>BANK DETAILS FOR PAYMENT</b>", STYLES["table_header"]), ""],
            [Paragraph("<b>Bank:</b>", STYLES["table_cell"]),
             Paragraph(str(bd.get("bank_name", "")), STYLES["table_cell"])],
            [Paragraph("<b>A/c No:</b>", STYLES["table_cell"]),
             Paragraph(str(bd.get("ac_no", "")), STYLES["table_cell"])],
            [Paragraph("<b>IFSC:</b>", STYLES["table_cell"]),
             Paragraph(str(bd.get("ifsc", "")), STYLES["table_cell"])],
            [Paragraph("<b>Branch:</b>", STYLES["table_cell"]),
             Paragraph(str(bd.get("branch", "")), STYLES["table_cell"])],
        ]
        t = Table(rows, colWidths=[30 * mm, 80 * mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), DARK_BLUE),
            ("SPAN", (0, 0), (-1, 0)),
            ("BOX", (0, 0), (-1, -1), 0.5, GREY_MED),
            ("GRID", (0, 1), (-1, -1), 0.25, GREY_LIGHT),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        return [t]

    def _declaration_section(self) -> list:
        """Declaration text."""
        decl = COMPANY_PROFILE.get(
            "declaration",
            "We declare that this document shows the actual details of the goods "
            "described and that the particulars given above are true and correct.",
        )
        return [
            Paragraph("<b>Declaration:</b>", STYLES["body_bold"]),
            Paragraph(decl, STYLES["small"]),
        ]

    def _signature_block(self) -> list:
        """'For PPS Anantams Corporation Pvt Ltd' + Authorized Signatory."""
        sig_data = [
            [Paragraph(
                f"For, <b>{COMPANY_PROFILE['legal_name']}</b>",
                STYLES["body_bold"],
            )],
            [Spacer(1, 20 * mm)],
            [Paragraph("Authorized Signatory", STYLES["body"])],
        ]
        t = Table(sig_data, colWidths=[80 * mm], hAlign="RIGHT")
        return [t]

    # ── PAYMENT-SPECIFIC SECTIONS ─────────────────────────────────────────

    def _payment_meta_section(self, pay_data: dict) -> list:
        """Payment mode + PO/SO references."""
        mode = pay_data.get("payment_mode", "NEFT")
        po_num = pay_data.get("po_number", "")
        so_num = pay_data.get("so_number", "")

        rows = [
            [Paragraph("<b>PAYMENT DETAILS</b>", STYLES["table_header"]), "", "", ""],
            [
                Paragraph("<b>Payment Mode:</b>", STYLES["table_cell"]),
                Paragraph(str(mode), STYLES["table_cell_bold"]),
                Paragraph("<b>PO Reference:</b>", STYLES["table_cell"]),
                Paragraph(str(po_num) if po_num else "N/A", STYLES["table_cell"]),
            ],
            [
                Paragraph("<b>Prepared By:</b>", STYLES["table_cell"]),
                Paragraph(str(pay_data.get("prepared_by", "Admin")), STYLES["table_cell"]),
                Paragraph("<b>SO Reference:</b>", STYLES["table_cell"]),
                Paragraph(str(so_num) if so_num else "N/A", STYLES["table_cell"]),
            ],
        ]

        t = Table(rows, colWidths=[30*mm, 57*mm, 30*mm, 57*mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), DARK_BLUE),
            ("SPAN", (0, 0), (-1, 0)),
            ("BOX", (0, 0), (-1, -1), 0.5, GREY_MED),
            ("GRID", (0, 1), (-1, -1), 0.25, GREY_LIGHT),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        return [t]

    def _payment_summary_section(self, pay_data: dict) -> list:
        """Purchase Payable + Sales Receivable side by side with due dates and status."""
        purchase = pay_data.get("purchase", {})
        sales = pay_data.get("sales", {})

        def _make_side(data: dict, label: str) -> list:
            content = [Paragraph(f"<b>{label}</b>", STYLES["body_bold"])]
            content.append(Paragraph(
                f"Party: <b>{data.get('party_name', 'N/A')}</b>", STYLES["body"]
            ))
            content.append(Paragraph(
                f"Material: {data.get('product', 'VG30')} {data.get('packing', 'BULK')}",
                STYLES["body"],
            ))
            content.append(Paragraph(
                f"Qty: {data.get('quantity', 0):.3f} MT", STYLES["body"]
            ))
            content.append(Paragraph(
                f"Rate: {format_inr(data.get('rate', 0))}/MT", STYLES["body"]
            ))
            subtotal = float(data.get("quantity", 0)) * float(data.get("rate", 0))
            gst = subtotal * 0.18
            total = subtotal + gst
            content.append(Paragraph(f"Subtotal: {format_inr(subtotal)}", STYLES["body"]))
            content.append(Paragraph(f"GST @18%: {format_inr(gst)}", STYLES["body"]))
            content.append(Paragraph(
                f"<b>Total: {format_inr(total)}</b>", STYLES["body_bold"]
            ))
            # Due date and status
            due = data.get("due_date") or data.get("expected_date", "")
            status = data.get("status", "")
            if due:
                content.append(Paragraph(f"Due/Expected: {due}", STYLES["body"]))
            if status:
                content.append(Paragraph(f"Status: <b>{status}</b>", STYLES["body_bold"]))
            return content

        left = _make_side(purchase, "PURCHASE PAYABLE")
        right = _make_side(sales, "SALES RECEIVABLE")

        t = Table([[left, right]], colWidths=[87 * mm, 87 * mm])
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOX", (0, 0), (0, 0), 0.5, GREY_MED),
            ("BOX", (1, 0), (1, 0), 0.5, GREY_MED),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        return [t]

    def _transport_section(self, transport: dict) -> list:
        """Transport details section for payment orders."""
        rows = [
            [Paragraph("<b>TRANSPORT DETAILS</b>", STYLES["table_header"]), "", "", ""],
            [
                Paragraph("<b>Transporter:</b>", STYLES["table_cell"]),
                Paragraph(str(transport.get("name", "N/A")), STYLES["table_cell_bold"]),
                Paragraph("<b>Amount:</b>", STYLES["table_cell"]),
                Paragraph(format_inr(transport.get("amount", 0)), STYLES["table_cell_right"]),
            ],
            [
                Paragraph("<b>Status:</b>", STYLES["table_cell"]),
                Paragraph(str(transport.get("status", "N/A")), STYLES["table_cell"]),
                "", "",
            ],
        ]

        t = Table(rows, colWidths=[30*mm, 57*mm, 30*mm, 57*mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), DARK_BLUE),
            ("SPAN", (0, 0), (-1, 0)),
            ("BOX", (0, 0), (-1, -1), 0.5, GREY_MED),
            ("GRID", (0, 1), (-1, -1), 0.25, GREY_LIGHT),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        return [t]

    def _profit_summary_section(self, pay_data: dict) -> list:
        """Profit summary table."""
        purchase = pay_data.get("purchase", {})
        sales = pay_data.get("sales", {})
        transport = pay_data.get("transport", {})
        transport_cost = float(transport.get("amount", 0)) if isinstance(transport, dict) else float(pay_data.get("transport_cost", 0))

        buy_qty = float(purchase.get("quantity", 0))
        buy_rate = float(purchase.get("rate", 0))
        sell_qty = float(sales.get("quantity", 0))
        sell_rate = float(sales.get("rate", 0))

        revenue = sell_qty * sell_rate
        cost = buy_qty * buy_rate
        net_profit = revenue - cost - transport_cost
        qty = max(sell_qty, buy_qty, 0.001)
        margin_per_mt = net_profit / qty if qty else 0
        margin_pct = (net_profit / revenue * 100) if revenue else 0

        rows = [
            [Paragraph("<b>PROFIT SUMMARY</b>", STYLES["table_header"]), ""],
            [Paragraph("Revenue (Sales):", STYLES["table_cell"]),
             Paragraph(f"<b>{format_inr(revenue)}</b>", STYLES["table_cell_right"])],
            [Paragraph("Purchase Cost:", STYLES["table_cell"]),
             Paragraph(f"- {format_inr(cost)}", STYLES["table_cell_right"])],
            [Paragraph("Transport Cost:", STYLES["table_cell"]),
             Paragraph(f"- {format_inr(transport_cost)}", STYLES["table_cell_right"])],
            [Paragraph("<b>Net Profit:</b>", STYLES["table_cell_bold"]),
             Paragraph(f"<b>{format_inr(net_profit)}</b>", STYLES["table_cell_right"])],
            [Paragraph("Margin per MT:", STYLES["table_cell"]),
             Paragraph(f"{format_inr(margin_per_mt)}", STYLES["table_cell_right"])],
            [Paragraph("Margin %:", STYLES["table_cell"]),
             Paragraph(f"{margin_pct:.2f}%", STYLES["table_cell_right"])],
        ]

        t = Table(rows, colWidths=[80 * mm, 60 * mm])
        profit_color = GREEN if net_profit >= 0 else RED
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), DARK_BLUE),
            ("SPAN", (0, 0), (-1, 0)),
            ("BOX", (0, 0), (-1, -1), 0.5, GREY_MED),
            ("GRID", (0, 1), (-1, -1), 0.25, GREY_LIGHT),
            ("LINEABOVE", (0, 4), (-1, 4), 1.5, DARK_BLUE),
            ("BACKGROUND", (0, 4), (-1, 4), LIGHT_BLUE),
            ("TEXTCOLOR", (1, 4), (1, 4), profit_color),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        return [t]

    def _payment_signature_block(self, pay_data: dict) -> list:
        """3-column signature block: Prepared By / Approved By / Payment By."""
        prepared = pay_data.get("prepared_by", "Admin")
        approved = pay_data.get("approved_by", "")

        def _sig_col(label: str, name: str) -> list:
            return [
                Paragraph(f"<b>{label}</b>", STYLES["body_bold"]),
                Spacer(1, 10 * mm),
                Paragraph(name if name else "________________", STYLES["body"]),
                Paragraph("Signature &amp; Date", STYLES["small"]),
            ]

        col1 = _sig_col("Prepared By:", prepared)
        col2 = _sig_col("Approved By:", approved)
        col3 = _sig_col("Payment By:", "")

        t = Table([[col1, col2, col3]], colWidths=[58 * mm, 58 * mm, 58 * mm])
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOX", (0, 0), (-1, -1), 0.5, GREY_MED),
            ("GRID", (0, 0), (-1, -1), 0.25, GREY_LIGHT),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        return [
            Paragraph(
                f"For, <b>{COMPANY_PROFILE['legal_name']}</b>",
                STYLES["body_bold"],
            ),
            Spacer(1, 4 * mm),
            t,
        ]


# ═══════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def generate_po_pdf(po_data: dict, po_number: str = "",
                    reference: str = "", username: str = "Admin") -> bytes:
    """Convenience: generate PO PDF bytes."""
    if not po_number:
        from database import get_next_doc_number
        po_number = get_next_doc_number("PO")
    engine = DocumentPDFEngine("PURCHASE ORDER", po_number, reference, username)
    return engine.generate_po_pdf(po_data)


def generate_so_pdf(so_data: dict, so_number: str = "",
                    reference: str = "", username: str = "Admin") -> bytes:
    """Convenience: generate SO PDF bytes."""
    if not so_number:
        from database import get_next_doc_number
        so_number = get_next_doc_number("SO")
    engine = DocumentPDFEngine("SALES ORDER", so_number, reference, username)
    return engine.generate_so_pdf(so_data)


def generate_payment_pdf(pay_data: dict, pay_number: str = "",
                         reference: str = "", username: str = "Admin") -> bytes:
    """Convenience: generate Payment Order PDF bytes."""
    if not pay_number:
        from database import get_next_doc_number
        pay_number = get_next_doc_number("PAY")
    engine = DocumentPDFEngine("PAYMENT ORDER", pay_number, reference, username)
    return engine.generate_payment_pdf(pay_data)


def save_pdf_to_archive(pdf_bytes: bytes, doc_type: str, doc_number: str) -> str:
    """Save PDF bytes to archive and return the file path."""
    safe_number = doc_number.replace("/", "_")
    filename = f"{doc_type}_{safe_number}_{_ts_filename()}.pdf"
    filepath = EXPORT_DIR / filename
    with open(filepath, "wb") as f:
        f.write(pdf_bytes)
    return str(filepath)
