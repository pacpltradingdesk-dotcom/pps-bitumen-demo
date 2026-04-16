"""
PDF Export Engine — PPS Anantams Logistics AI
=============================================
Universal ReportLab-based PDF generator for all dashboard pages.

Features:
- A4 paper, portrait + landscape
- Company header every page
- Footer: page X of Y + CONFIDENTIAL + data source
- INR formatting (₹ with Indian comma grouping)
- IST timestamps (DD-MM-YYYY HH:MM IST)
- Auto-wrapping tables with column spanning
- Chart images (Plotly PNG via kaleido)
- PDF archive: saves to pdf_exports/ with IST filename
- Role-based: never includes restricted fields

Filename convention: <PageName>_DD-MM-YYYY_HHmmIST.pdf
"""

from __future__ import annotations

try:
    from india_localization import format_inr, format_inr_short, format_date, format_datetime_ist, get_financial_year, get_fy_quarter
except ImportError:
    import sys as _sys
    import os as _os
    _sys.path.append(_os.path.dirname(_os.path.dirname(__file__)))
    try:
        from india_localization import format_inr, format_inr_short, format_date, format_datetime_ist, get_financial_year, get_fy_quarter
    except Exception:
        pass

import io
import json
import os
import datetime
from pathlib import Path
from typing import Optional

import pytz
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame,
    Paragraph, Spacer, Table, TableStyle,
    Image, HRFlowable, KeepTogether, PageBreak,
    NextPageTemplate,
)
from reportlab.platypus.flowables import BalancedColumns
from reportlab.lib.utils import ImageReader

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR      = Path(__file__).parent
EXPORT_DIR    = BASE_DIR / "pdf_exports"
LOGO_PATH     = BASE_DIR / "pps_logo.png"
EXPORT_DIR.mkdir(exist_ok=True)

IST = pytz.timezone("Asia/Kolkata")

# ── India Formatting ───────────────────────────────────────────────────────────

def _now_ist() -> datetime.datetime:
    return datetime.datetime.now(IST)

def _ts_ist(fmt: str = "%Y-%m-%d %H:%M IST") -> str:
    return _now_ist().strftime(fmt)

def _ts_filename() -> str:
    return _now_ist().strftime("%Y-%m-%d_%H%MIST")

# format_inr() comes from india_localization (imported above) — single source
# of truth for INR formatting across engines.

# ── Colour Palette ─────────────────────────────────────────────────────────────

DARK_BLUE   = colors.HexColor("#1e3a5f")
MID_BLUE    = colors.HexColor("#2563eb")
LIGHT_BLUE  = colors.HexColor("#dbeafe")
ORANGE      = colors.HexColor("#ea580c")
GREEN       = colors.HexColor("#16a34a")
RED         = colors.HexColor("#dc2626")
AMBER       = colors.HexColor("#d97706")
GREY_LIGHT  = colors.HexColor("#f1f5f9")
GREY_MED    = colors.HexColor("#94a3b8")
GREY_DARK   = colors.HexColor("#334155")
WHITE       = colors.white
BLACK       = colors.black

# ── Styles ─────────────────────────────────────────────────────────────────────

def _make_styles():
    base = getSampleStyleSheet()
    styles = {}

    styles["title"] = ParagraphStyle(
        "PDFTitle", parent=base["Title"],
        fontSize=18, leading=22, textColor=DARK_BLUE,
        spaceAfter=4,
    )
    styles["subtitle"] = ParagraphStyle(
        "PDFSubtitle", parent=base["Normal"],
        fontSize=10, leading=14, textColor=GREY_DARK,
        spaceAfter=2,
    )
    styles["section"] = ParagraphStyle(
        "PDFSection", parent=base["Heading2"],
        fontSize=12, leading=16, textColor=DARK_BLUE,
        spaceBefore=10, spaceAfter=4,
        borderPad=4,
    )
    styles["body"] = ParagraphStyle(
        "PDFBody", parent=base["Normal"],
        fontSize=9, leading=13, textColor=GREY_DARK,
        spaceAfter=4,
    )
    styles["small"] = ParagraphStyle(
        "PDFSmall", parent=base["Normal"],
        fontSize=7.5, leading=11, textColor=GREY_MED,
    )
    styles["caption"] = ParagraphStyle(
        "PDFCaption", parent=base["Normal"],
        fontSize=8, leading=11, textColor=GREY_MED,
        alignment=TA_CENTER, spaceAfter=4,
    )
    styles["table_header"] = ParagraphStyle(
        "PDFTableHeader", parent=base["Normal"],
        fontSize=8, leading=10, textColor=WHITE,
        fontName="Helvetica-Bold",
    )
    styles["table_cell"] = ParagraphStyle(
        "PDFTableCell", parent=base["Normal"],
        fontSize=8, leading=11, textColor=GREY_DARK,
    )
    styles["table_cell_right"] = ParagraphStyle(
        "PDFTableCellR", parent=base["Normal"],
        fontSize=8, leading=11, textColor=GREY_DARK,
        alignment=TA_RIGHT,
    )
    styles["filter_key"] = ParagraphStyle(
        "PDFFilterKey", parent=base["Normal"],
        fontSize=7.5, leading=10, textColor=GREY_DARK,
        fontName="Helvetica-Bold",
    )
    styles["filter_val"] = ParagraphStyle(
        "PDFFilterVal", parent=base["Normal"],
        fontSize=7.5, leading=10, textColor=GREY_DARK,
    )
    return styles

STYLES = _make_styles()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE TEMPLATE — header + footer on every page
# ══════════════════════════════════════════════════════════════════════════════

COMPANY_NAME   = "PPS Anantam Agentic AI Eco System"
COMPANY_GST    = "GST: 24AAHCV1611L2ZD"
COMPANY_CITY   = "Vadodara, Gujarat"
DASHBOARD_NAME = "GST: 24AAHCV1611L2ZD  |  Vadodara, Gujarat"


def _build_header_footer(canvas, doc):
    """Called for every page — draws header strip and footer line."""
    canvas.saveState()
    W, H = doc.pagesize

    # ── Header strip ────────────────────────────────────────────────────────
    canvas.setFillColor(DARK_BLUE)
    canvas.rect(0, H - 32*mm, W, 32*mm, fill=1, stroke=0)

    # Logo (if exists)
    lp = str(LOGO_PATH)
    if os.path.exists(lp):
        try:
            canvas.drawImage(lp, 10*mm, H - 28*mm, width=20*mm, height=20*mm,
                             preserveAspectRatio=True, mask="auto")
        except Exception:
            pass
    x_text = 35*mm if os.path.exists(lp) else 10*mm

    # Company name
    canvas.setFont("Helvetica-Bold", 13)
    canvas.setFillColor(WHITE)
    canvas.drawString(x_text, H - 14*mm, COMPANY_NAME)

    # Sub info
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#93c5fd"))
    canvas.drawString(x_text, H - 21*mm, f"{COMPANY_CITY}  |  {COMPANY_GST}  |  {DASHBOARD_NAME}")

    # Page title (right-aligned in header)
    canvas.setFont("Helvetica-Bold", 11)
    canvas.setFillColor(colors.HexColor("#fbbf24"))
    title = getattr(doc, "_page_title", "Report")
    canvas.drawRightString(W - 10*mm, H - 14*mm, title)

    # Generated timestamp
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#93c5fd"))
    ts = getattr(doc, "_generated_at", _ts_ist())
    canvas.drawRightString(W - 10*mm, H - 21*mm, f"Generated: {ts}")

    # ── Footer line ─────────────────────────────────────────────────────────
    canvas.setStrokeColor(DARK_BLUE)
    canvas.setLineWidth(0.5)
    canvas.line(10*mm, 16*mm, W - 10*mm, 16*mm)

    # Page number
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(GREY_DARK)
    total = getattr(doc, "_total_pages", "?")
    canvas.drawString(10*mm, 10*mm, f"Page {canvas.getPageNumber()} of {total}")
    ts_footer = getattr(doc, "_generated_at", _ts_ist())
    canvas.drawCentredString(
        W / 2, 10*mm,
        f"PPS Anantam Agentic AI Eco System  |  GST: 24AAHCV1611L2ZD  |  "
        f"v3.2.1  |  {ts_footer}"
    )
    canvas.drawRightString(W - 10*mm, 10*mm, "CONFIDENTIAL")

    canvas.restoreState()


# ══════════════════════════════════════════════════════════════════════════════
# PDF DOCUMENT BUILDER
# ══════════════════════════════════════════════════════════════════════════════

class PDFExportEngine:
    """
    Build a structured PDF with header/footer on every page.
    Usage:
        engine = PDFExportEngine("Price Prediction", orientation="portrait")
        engine.add_section("Market Overview")
        engine.add_paragraph("Brent Crude is at ₹ 72.87...")
        engine.add_table(headers, rows)
        pdf_bytes = engine.build()
    """

    def __init__(
        self,
        page_title: str,
        orientation: str = "portrait",   # "portrait" or "landscape"
        filters_summary: dict = None,
        include_filters: bool = True,
        data_source: str = "Dashboard internal tables + Live APIs",
        role: str = "Admin",
    ):
        self.page_title    = page_title
        self.orientation   = orientation
        self.filters       = filters_summary or {}
        self.include_filters = include_filters
        self.data_source   = data_source
        self.role          = role
        self._story: list  = []
        self._generated_at = _ts_ist()
        self._buf          = io.BytesIO()

        if orientation == "landscape":
            self.pagesize = landscape(A4)
        else:
            self.pagesize = A4

        W, H = self.pagesize
        margin = 15*mm
        self._frame = Frame(
            margin, 20*mm,
            W - 2*margin, H - 40*mm,
            leftPadding=0, rightPadding=0,
            topPadding=4, bottomPadding=4,
        )

    # ── Flowable builders ──────────────────────────────────────────────────

    def add_title(self, text: str):
        self._story.append(Paragraph(text, STYLES["title"]))
        self._story.append(Spacer(1, 2*mm))

    def add_subtitle(self, text: str):
        self._story.append(Paragraph(text, STYLES["subtitle"]))
        self._story.append(Spacer(1, 1*mm))

    def add_section(self, text: str):
        self._story.append(Spacer(1, 3*mm))
        self._story.append(HRFlowable(width="100%", thickness=0.5, color=DARK_BLUE))
        self._story.append(Paragraph(text, STYLES["section"]))

    def add_paragraph(self, text: str):
        self._story.append(Paragraph(text, STYLES["body"]))
        self._story.append(Spacer(1, 1*mm))

    def add_spacer(self, mm_height: float = 4):
        self._story.append(Spacer(1, mm_height * mm))

    def add_page_break(self):
        self._story.append(PageBreak())

    def add_filters_box(self):
        """Render applied filters as a light-background summary box."""
        if not self.filters:
            return
        items = []
        for k, v in self.filters.items():
            items.append([
                Paragraph(str(k), STYLES["filter_key"]),
                Paragraph(str(v), STYLES["filter_val"]),
            ])
        if not items:
            return
        tbl = Table(items, colWidths=["35%", "65%"])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), GREY_LIGHT),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [GREY_LIGHT, WHITE]),
            ("BOX",       (0, 0), (-1, -1), 0.5, GREY_MED),
            ("INNERGRID", (0, 0), (-1, -1), 0.3, GREY_MED),
            ("TOPPADDING",    (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING",   (0, 0), (-1, -1), 6),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
        ]))
        self._story.append(Paragraph("Applied Filters", STYLES["section"]))
        self._story.append(tbl)
        self._story.append(Spacer(1, 3*mm))

    def add_kpi_row(self, kpis: list[tuple]):
        """
        kpis = [("Label", "Value", "delta"), ...]  — max 5 per row
        """
        if not kpis:
            return
        data = []
        for label, value, delta in kpis[:5]:
            delta_str = f"▲ {delta}" if str(delta).startswith("+") else (
                        f"▼ {delta}" if str(delta).startswith("-") else str(delta))
            cell = [
                Paragraph(str(label), STYLES["small"]),
                Paragraph(f"<b>{value}</b>", STYLES["body"]),
                Paragraph(delta_str, STYLES["small"]),
            ]
            data.append(cell)

        # Lay KPIs in a single row table
        col_w = (self.pagesize[0] - 30*mm) / max(len(kpis), 1)
        row = [[k[0], k[1], k[2]] for k in kpis]
        tbl_data = [
            [Paragraph(str(label), STYLES["small"]) for label, _, _ in kpis],
            [Paragraph(f"<b>{val}</b>", STYLES["body"]) for _, val, _ in kpis],
            [Paragraph(str(dlt), STYLES["small"]) for _, _, dlt in kpis],
        ]
        col_widths = [col_w] * len(kpis)
        tbl = Table(tbl_data, colWidths=col_widths, rowHeights=[8*mm, 10*mm, 6*mm])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), LIGHT_BLUE),
            ("BACKGROUND", (0, 1), (-1, 1), WHITE),
            ("BACKGROUND", (0, 2), (-1, 2), GREY_LIGHT),
            ("BOX",       (0, 0), (-1, -1), 0.8, DARK_BLUE),
            ("INNERGRID", (0, 0), (-1, -1), 0.3, GREY_MED),
            ("ALIGN",     (0, 0), (-1, -1), "CENTER"),
            ("VALIGN",    (0, 0), (-1, -1), "MIDDLE"),
            ("FONTNAME",  (0, 1), (-1, 1), "Helvetica-Bold"),
            ("FONTSIZE",  (0, 1), (-1, 1), 12),
        ]))
        self._story.append(tbl)
        self._story.append(Spacer(1, 3*mm))

    def add_table(
        self,
        headers: list[str],
        rows: list[list],
        col_widths: list = None,
        highlight_cols: list[int] = None,
        zebra: bool = True,
        title: str = "",
    ):
        """
        Add a data table.
        headers: list of column names
        rows: list of lists (strings or numbers; INR auto-formatted if float)
        col_widths: list of mm values or None (auto)
        highlight_cols: column indices to highlight in orange
        """
        if not rows:
            self._story.append(Paragraph("No data available.", STYLES["body"]))
            return

        if title:
            self._story.append(Paragraph(title, STYLES["section"]))

        usable_width = self.pagesize[0] - 30*mm
        n_cols = len(headers)

        if col_widths:
            cw = [c * mm for c in col_widths]
        else:
            cw = [usable_width / n_cols] * n_cols

        # Build header row
        hdr = [Paragraph(str(h), STYLES["table_header"]) for h in headers]

        # Build data rows
        tbl_data = [hdr]
        for row in rows:
            tbl_row = []
            for i, cell in enumerate(row):
                # Auto-format numbers
                if isinstance(cell, float) and cell > 1000:
                    txt = format_inr(cell)
                    style = STYLES["table_cell_right"]
                elif isinstance(cell, (int, float)):
                    txt = f"{cell:,.2f}" if isinstance(cell, float) else str(cell)
                    style = STYLES["table_cell_right"]
                else:
                    txt = str(cell) if cell is not None else "—"
                    style = STYLES["table_cell"]
                tbl_row.append(Paragraph(txt, style))
            tbl_data.append(tbl_row)

        tbl = Table(tbl_data, colWidths=cw, repeatRows=1)

        style_cmds = [
            # Header
            ("BACKGROUND",    (0, 0), (-1, 0), DARK_BLUE),
            ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
            ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, 0), 8),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, GREY_LIGHT] if zebra else [WHITE]),
            ("GRID",          (0, 0), (-1, -1), 0.3, GREY_MED),
            ("BOX",           (0, 0), (-1, -1), 0.8, DARK_BLUE),
            ("ALIGN",         (0, 0), (-1, 0), "CENTER"),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING",   (0, 0), (-1, -1), 5),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 5),
        ]

        if highlight_cols:
            for ci in highlight_cols:
                style_cmds.append(("TEXTCOLOR", (ci, 1), (ci, -1), ORANGE))
                style_cmds.append(("FONTNAME",  (ci, 1), (ci, -1), "Helvetica-Bold"))

        tbl.setStyle(TableStyle(style_cmds))
        self._story.append(KeepTogether([tbl, Spacer(1, 3*mm)]))

    def add_chart_image(
        self,
        fig,
        caption: str = "",
        width_mm: float = 160,
        height_mm: float = 90,
    ):
        """
        Embed a Plotly figure as a PNG image.
        Requires kaleido installed.
        """
        try:
            img_bytes = fig.to_image(format="png", width=1200, height=700, scale=2)
            img_buf = io.BytesIO(img_bytes)
            img = Image(img_buf, width=width_mm*mm, height=height_mm*mm)
            if caption:
                self._story.append(KeepTogether([
                    img,
                    Spacer(1, 1*mm),
                    Paragraph(caption, STYLES["caption"]),
                    Spacer(1, 3*mm),
                ]))
            else:
                self._story.append(img)
                self._story.append(Spacer(1, 3*mm))
        except Exception as e:
            self._story.append(Paragraph(
                f"[Chart could not be embedded: {str(e)[:80]}]", STYLES["small"]
            ))

    def add_alert_table(self, alerts: list[dict]):
        """Specialized formatter for alert data."""
        if not alerts:
            self.add_paragraph("No active alerts.")
            return
        headers = ["ID", "Severity", "Category", "Title", "Time (IST)", "Acknowledged"]
        rows = []
        for a in alerts:
            rows.append([
                a.get("id", "—"),
                a.get("severity", "—").upper(),
                a.get("category", "—"),
                a.get("title", "—")[:60],
                a.get("time", "—").strftime("%Y-%m-%d %H:%M") if hasattr(a.get("time"), "strftime") else str(a.get("time", "—"))[:16],
                "Yes" if a.get("acknowledged") else "No",
            ])
        self.add_table(headers, rows, col_widths=[12, 16, 22, 60, 32, 18])

    def add_log_table(self, logs: list[dict], columns: list[str], title: str = ""):
        """Generic log/audit table."""
        if not logs:
            self.add_paragraph("No log entries.")
            return
        headers = [c.replace("_", " ").title() for c in columns]
        rows = []
        for entry in logs[:200]:  # Max 200 rows per export
            rows.append([str(entry.get(c, "—"))[:60] for c in columns])
        self.add_table(headers, rows, title=title)

    # ── Build & Save ───────────────────────────────────────────────────────

    def build(self, save_to_archive: bool = True) -> bytes:
        """
        Compile all flowables into PDF bytes.
        Optionally saves a copy to pdf_exports/.
        Returns raw bytes for st.download_button().
        """
        doc = BaseDocTemplate(
            self._buf,
            pagesize=self.pagesize,
            leftMargin=15*mm, rightMargin=15*mm,
            topMargin=35*mm, bottomMargin=22*mm,
            title=self.page_title,
            author=COMPANY_NAME,
            subject=f"PPS Anantam Agentic AI Eco System — {self.page_title}",
            creator="PPS Anantam Agentic AI Eco System v3.2",
        )
        doc._page_title    = self.page_title
        doc._generated_at  = self._generated_at

        template = PageTemplate(
            id="pps_template",
            frames=[self._frame],
            onPage=_build_header_footer,
        )
        doc.addPageTemplates([template])

        # Prepend title block + filters if needed
        story_full = []

        # Page title block
        story_full.append(Paragraph(self.page_title, STYLES["title"]))
        story_full.append(Paragraph(
            f"PPS Anantam Agentic AI Eco System  |  Generated: {self._generated_at}  |  "
            f"Role: {self.role}",
            STYLES["subtitle"],
        ))
        story_full.append(Spacer(1, 2*mm))
        story_full.append(HRFlowable(width="100%", thickness=1, color=DARK_BLUE))
        story_full.append(Spacer(1, 3*mm))

        # Filters box
        if self.include_filters and self.filters:
            self.add_filters_box()

        story_full.extend(self._story)

        # Two-pass build: first pass counts pages, second pass renders with total
        counting_buf = io.BytesIO()
        counting_doc = BaseDocTemplate(
            counting_buf, pagesize=self.pagesize,
            leftMargin=15*mm, rightMargin=15*mm,
            topMargin=35*mm, bottomMargin=22*mm,
        )
        counting_doc._page_title = self.page_title
        counting_doc._generated_at = self._generated_at
        counting_doc._total_pages = "?"
        count_template = PageTemplate(
            id="count_template",
            frames=[Frame(15*mm, 20*mm, self.pagesize[0]-30*mm, self.pagesize[1]-55*mm,
                          leftPadding=0, rightPadding=0, topPadding=4, bottomPadding=4)],
            onPage=_build_header_footer,
        )
        counting_doc.addPageTemplates([count_template])
        page_count = [0]
        _orig_afterPage = counting_doc.afterPage
        def _track_pages():
            page_count[0] = counting_doc.page
            if _orig_afterPage:
                _orig_afterPage()
        counting_doc.afterPage = _track_pages
        try:
            counting_doc.build(list(story_full))
            page_count[0] = max(page_count[0], counting_doc.page)
        except Exception:
            page_count[0] = 1

        # Second pass with total page count
        doc._total_pages = page_count[0]
        doc.build(story_full)
        pdf_bytes = self._buf.getvalue()

        if save_to_archive:
            self._archive(pdf_bytes)

        return pdf_bytes

    def _archive(self, pdf_bytes: bytes):
        """Save PDF to pdf_exports/ with IST filename."""
        safe_title = "".join(c if c.isalnum() or c in "-_ " else "_" for c in self.page_title)
        safe_title = safe_title.replace(" ", "_")[:40]
        filename   = f"{safe_title}_{_ts_filename()}.pdf"
        path       = EXPORT_DIR / filename
        path.write_bytes(pdf_bytes)
        # Write metadata sidecar
        meta_path = EXPORT_DIR / (filename + ".json")
        meta_path.write_text(json.dumps({
            "filename":     filename,
            "page_title":   self.page_title,
            "generated_at": self._generated_at,
            "role":         self.role,
            "size_bytes":   len(pdf_bytes),
        }, indent=2, ensure_ascii=False), encoding="utf-8")
        return path


# ══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE BUILDERS — quick one-call PDF for each page type
# ══════════════════════════════════════════════════════════════════════════════

def build_table_pdf(
    page_title: str,
    headers: list[str],
    rows: list[list],
    filters: dict = None,
    kpis: list[tuple] = None,
    notes: str = "",
    role: str = "Admin",
) -> bytes:
    """Generic table PDF — one title, optional KPI row, one table."""
    eng = PDFExportEngine(page_title, filters_summary=filters, role=role)
    if kpis:
        eng.add_section("Key Metrics")
        eng.add_kpi_row(kpis)
    if notes:
        eng.add_paragraph(notes)
    eng.add_table(headers, rows)
    return eng.build()


def build_generic_pdf(
    page_title: str,
    sections: list[dict],
    filters: dict = None,
    role: str = "Admin",
    orientation: str = "portrait",
) -> bytes:
    """
    Build a multi-section PDF.
    sections = [
        {"type": "section",   "text": "..."},
        {"type": "paragraph", "text": "..."},
        {"type": "table",     "headers": [...], "rows": [[...]]},
        {"type": "kpis",      "items": [("Label","Value","delta")]},
        {"type": "chart",     "fig": plotly_fig, "caption": "..."},
        {"type": "spacer"},
        {"type": "page_break"},
    ]
    """
    eng = PDFExportEngine(page_title, filters_summary=filters, role=role,
                          orientation=orientation)
    for sec in sections:
        t = sec.get("type", "paragraph")
        if t == "section":
            eng.add_section(sec.get("text", ""))
        elif t == "paragraph":
            eng.add_paragraph(sec.get("text", ""))
        elif t == "table":
            eng.add_table(
                sec.get("headers", []),
                sec.get("rows", []),
                col_widths=sec.get("col_widths"),
                highlight_cols=sec.get("highlight_cols"),
                title=sec.get("title", ""),
            )
        elif t == "kpis":
            eng.add_kpi_row(sec.get("items", []))
        elif t == "chart":
            eng.add_chart_image(
                sec["fig"],
                caption=sec.get("caption", ""),
                width_mm=sec.get("width_mm", 160),
                height_mm=sec.get("height_mm", 90),
            )
        elif t == "spacer":
            eng.add_spacer(sec.get("mm", 4))
        elif t == "page_break":
            eng.add_page_break()
        elif t == "alerts":
            eng.add_alert_table(sec.get("alerts", []))
        elif t == "log":
            eng.add_log_table(sec.get("logs", []), sec.get("columns", []),
                              title=sec.get("title", ""))
    return eng.build()


# ══════════════════════════════════════════════════════════════════════════════
# PDF ARCHIVE MANAGER
# ══════════════════════════════════════════════════════════════════════════════

def list_archived_pdfs() -> list[dict]:
    """Return list of archived PDFs sorted newest first."""
    results = []
    for p in sorted(EXPORT_DIR.glob("*.pdf"), key=lambda x: x.stat().st_mtime, reverse=True):
        meta_path = EXPORT_DIR / (p.name + ".json")
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception:
                meta = {}
        else:
            meta = {}
        results.append({
            "filename":     p.name,
            "path":         str(p),
            "size_kb":      round(p.stat().st_size / 1024, 1),
            "page_title":   meta.get("page_title", p.stem),
            "generated_at": meta.get("generated_at", "—"),
            "role":         meta.get("role", "—"),
        })
    return results


def delete_archived_pdf(filename: str) -> bool:
    """Delete a PDF and its sidecar from the archive."""
    p = EXPORT_DIR / filename
    meta = EXPORT_DIR / (filename + ".json")
    try:
        if p.exists():
            p.unlink()
        if meta.exists():
            meta.unlink()
        return True
    except Exception:
        return False


def delete_all_archived_pdfs() -> int:
    """Delete ALL PDFs from archive. Returns count deleted."""
    count = 0
    for p in list(EXPORT_DIR.glob("*.pdf")) + list(EXPORT_DIR.glob("*.pdf.json")):
        try:
            p.unlink()
            count += 1
        except Exception:
            pass
    return count


def read_archived_pdf(filename: str) -> Optional[bytes]:
    """Return bytes of an archived PDF for download."""
    p = EXPORT_DIR / filename
    if p.exists():
        return p.read_bytes()
    return None


def get_archive_stats() -> dict:
    """Return archive usage stats."""
    files = list(EXPORT_DIR.glob("*.pdf"))
    total_size = sum(f.stat().st_size for f in files)
    return {
        "total_files": len(files),
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "archive_path": str(EXPORT_DIR),
    }
