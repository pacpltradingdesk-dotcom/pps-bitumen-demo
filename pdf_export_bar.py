"""
pdf_export_bar.py — Universal Print + PDF Export Bar
=====================================================
Drop-in component for every dashboard page.

Usage (top of any page's render() function):
    from pdf_export_bar import render_export_bar
    render_export_bar("Price Prediction", filters={"FY": "2025-26"})

Advanced usage with custom content:
    render_export_bar(
        "Historical Revisions",
        content_fn=lambda: [
            {"type": "section", "text": "Revision History"},
            {"type": "table",   "headers": headers, "rows": rows},
        ],
        filters={"Source": "IOCL", "Period": "2024-25"},
        kpis=[("Revisions", "240", "+12"), ("Avg Change", "₹ 420", "")],
        orientation="landscape",
    )
"""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components
from pdf_export_engine import (
    build_generic_pdf,
    _ts_filename,
    COMPANY_NAME,
)

# ── Print CSS (injected once per session) ────────────────────────────────────

_PRINT_CSS = """
@media print {
  /* Hide sidebar, header, toolbar, all buttons */
  [data-testid="stSidebar"],
  [data-testid="stHeader"],
  [data-testid="stToolbar"],
  [data-testid="stDecoration"],
  [data-testid="stStatusWidget"],
  .export-bar-container,
  .stButton > button,
  footer { display: none !important; }

  /* A4 page setup */
  @page { size: A4; margin: 15mm; }

  /* Remove padding from main content */
  .main .block-container {
    padding: 0.5rem !important;
    max-width: 100% !important;
  }

  /* Clean backgrounds and text */
  body, .main { background: #ffffff !important; color: #000000 !important; }

  /* Tables */
  table { border-collapse: collapse !important; width: 100% !important; }
  th, td {
    border: 1px solid #aaa !important;
    padding: 4px 6px !important;
    font-size: 10px !important;
    color: #000 !important;
  }
  th { background: #1e3a5f !important; color: #ffffff !important; }

  /* Page break control */
  table, .stDataFrame, .element-container { page-break-inside: avoid !important; }
  .js-plotly-plot { page-break-inside: avoid !important; }
  tr { page-break-inside: avoid !important; }
  orphans: 2;
  widows: 2;

  /* Exact color reproduction */
  * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }

  /* Section headings */
  h1, h2, h3 { color: #1e3a5f !important; page-break-after: avoid !important; }
}
"""

_CSS_INJECTED_KEY = "_pdf_bar_css_injected"


def _inject_print_css():
    if not st.session_state.get(_CSS_INJECTED_KEY):
        st.markdown(f"<style>{_PRINT_CSS}</style>", unsafe_allow_html=True)
        st.session_state[_CSS_INJECTED_KEY] = True


# ── Print Button (fires window.print() in browser) ──────────────────────────

def _render_print_js_button():
    """Tiny HTML+JS print button that calls window.print()."""
    components.html(
        """
        <button onclick="window.print()" title="Print this page"
         style="
          background:#1e3a5f; color:#ffffff; border:none;
          padding:5px 12px; border-radius:6px; cursor:pointer;
          font-size:13px; font-weight:600; letter-spacing:0.3px;
          display:inline-flex; align-items:center; gap:5px; margin:0;
         ">
         🖨 Print
        </button>
        """,
        height=38,
        scrolling=False,
    )


# ── Generic fallback PDF content ─────────────────────────────────────────────

def _default_sections(page_title: str, notes: str = "") -> list[dict]:
    from pdf_export_engine import _ts_ist
    return [
        {"type": "section",   "text": "Page Overview"},
        {"type": "paragraph", "text": f"This report was exported from the {page_title} page of the {COMPANY_NAME} Logistics AI Dashboard."},
        {"type": "paragraph", "text": f"Generated: {_ts_ist()}"},
        *([{"type": "paragraph", "text": notes}] if notes else []),
        {"type": "spacer"},
        {"type": "section",   "text": "Note"},
        {"type": "paragraph",
         "text": "For complete interactive data, charts, and filters please view this page in the dashboard."},
    ]


# ══════════════════════════════════════════════════════════════════════════════
# MAIN PUBLIC API
# ══════════════════════════════════════════════════════════════════════════════

def render_export_bar(
    page_title: str,
    content_fn=None,
    filters: dict = None,
    kpis: list[tuple] = None,
    role: str = "Admin",
    orientation: str = "portrait",
    notes: str = "",
) -> bytes | None:
    """
    Render the universal Print + PDF bar at the top of any page.

    Parameters
    ----------
    page_title  : str  — page name shown in PDF header and used in filename
    content_fn  : callable | None — zero-arg function returning list[dict] sections
                  (see pdf_export_engine.build_generic_pdf for section format).
                  If None, a generic summary PDF is generated.
    filters     : dict | None — applied filters shown in PDF filters box
    kpis        : list of (label, value, delta) tuples for KPI row in PDF
    role        : str — current user role (for role-sensitive data)
    orientation : "portrait" | "landscape"
    notes       : str — extra paragraph added to generic fallback PDF

    Returns
    -------
    bytes | None  — PDF bytes if user clicked Generate, else None
    """
    _inject_print_css()

    # Unique session keys for this page
    sk = f"_exportbar_{page_title.replace(' ', '_')}"
    if sk not in st.session_state:
        st.session_state[sk] = {"show": False, "pdf_bytes": None}

    # ── Button row ───────────────────────────────────────────────────────────
    st.markdown(
        '<div class="export-bar-container" style="display:flex;justify-content:flex-end;gap:8px;margin-bottom:6px;">',
        unsafe_allow_html=True,
    )

    col_gap, col_print, col_pdf = st.columns([7, 1, 1])

    with col_print:
        _render_print_js_button()

    with col_pdf:
        if st.button("⬇ PDF", key=f"{sk}_btn", use_container_width=True,
                     help="Download this page as PDF"):
            st.session_state[sk]["show"] = not st.session_state[sk]["show"]
            st.session_state[sk]["pdf_bytes"] = None  # reset previous

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Options panel ────────────────────────────────────────────────────────
    if not st.session_state[sk]["show"]:
        return None

    with st.container():
        st.markdown(
            """<div style="background:#0d1b2e;border:1px solid #2563eb;border-radius:8px;
                          padding:14px 18px;margin-bottom:10px;">""",
            unsafe_allow_html=True,
        )
        st.markdown("**📄 PDF Export Options**")

        opt1, opt2, opt3 = st.columns([2, 2, 2])

        with opt1:
            paper = st.selectbox(
                "Paper",
                ["A4 Portrait", "A4 Landscape"],
                key=f"{sk}_paper",
            )
            inc_filters = st.checkbox(
                "Include Filters Summary", value=bool(filters), key=f"{sk}_ifilter"
            )

        with opt2:
            inc_charts = st.checkbox("Include Charts", value=True, key=f"{sk}_ichart",
                                     help="Requires kaleido (may be slow)")
            inc_tables = st.checkbox("Include Data Tables", value=True, key=f"{sk}_itable")

        with opt3:
            st.caption(f"**Page:** {page_title}")
            st.caption(f"**Company:** PPS Anantam Agentic AI Eco System")
            st.caption(f"**Role:** {role}")
            st.caption("**Footer:** CONFIDENTIAL | Page X of Y")

        btn_col, dl_col = st.columns([2, 3])
        with btn_col:
            generate = st.button(
                "🔄 Generate PDF",
                key=f"{sk}_gen",
                type="primary",
                use_container_width=True,
            )

        if generate:
            orient = "landscape" if "Landscape" in paper else "portrait"
            with st.spinner("Building PDF…"):
                try:
                    # Build content
                    if content_fn is not None:
                        raw_sections = content_fn()
                    else:
                        raw_sections = _default_sections(page_title, notes)

                    # Inject KPI row at top if provided
                    if kpis:
                        raw_sections = [{"type": "kpis", "items": kpis}] + raw_sections

                    # Filter by user options
                    sections = []
                    for s in raw_sections:
                        t = s.get("type", "")
                        if t == "chart" and not inc_charts:
                            continue
                        if t in ("table", "log") and not inc_tables:
                            continue
                        sections.append(s)

                    pdf_bytes = build_generic_pdf(
                        page_title=page_title,
                        sections=sections,
                        filters=filters if inc_filters else None,
                        role=role,
                        orientation=orient,
                    )
                    st.session_state[sk]["pdf_bytes"] = pdf_bytes
                    st.success(f"✅ PDF ready — {len(pdf_bytes)//1024} KB — saved to archive")

                except Exception as exc:
                    st.error(f"PDF generation failed: {exc}")

        # ── Download button ──────────────────────────────────────────────────
        pdf_bytes = st.session_state[sk].get("pdf_bytes")
        if pdf_bytes:
            safe = page_title.replace(" ", "_").replace("/", "-")[:40]
            filename = f"{safe}_{_ts_filename()}.pdf"
            with dl_col:
                st.download_button(
                    label="📥 Download PDF",
                    data=pdf_bytes,
                    file_name=filename,
                    mime="application/pdf",
                    key=f"{sk}_dl",
                    use_container_width=True,
                )

        st.markdown("</div>", unsafe_allow_html=True)

    return pdf_bytes if st.session_state[sk].get("pdf_bytes") else None


# ── Convenience: inject print CSS only (no buttons) ──────────────────────────

def inject_print_css():
    """Call once at app start to make all pages printable."""
    _inject_print_css()
