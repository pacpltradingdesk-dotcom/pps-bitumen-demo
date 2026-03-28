"""
system_requirements_dashboard.py — Dependencies & System Health Checker
========================================================================
Shows installed packages, environment health, and worker module status.
"""

from __future__ import annotations
import streamlit as st
import sys
import os
import platform
from pathlib import Path
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))
BASE = Path(__file__).parent.parent
NAVY = "#1e3a5f"
GOLD = "#c9a84c"
GREEN = "#2d6a4f"
FIRE = "#b85c38"


def render():
    """Main render function for System Requirements page."""
    from ui_badges import display_badge
    display_badge("information")

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#334155,{NAVY});padding:18px 24px;
                border-radius:10px;margin-bottom:16px;">
      <div style="font-size:1.2rem;font-weight:700;color:#ffffff;">📦 System Requirements</div>
      <div style="font-size:0.8rem;color:{GOLD};margin-top:4px;">
        Installed packages, environment health, and worker module status
      </div>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs([
        "Dependencies", "Environment", "Worker Modules",
    ])

    with tab1:
        _render_dependencies()
    with tab2:
        _render_environment()
    with tab3:
        _render_worker_modules()


# ── Tab 1: Dependencies ──────────────────────────────────────────────────────

def _render_dependencies():
    st.subheader("Python Package Dependencies")

    # Required packages (from requirements.txt)
    required = [
        ("streamlit", "1.31.0"),
        ("pandas", "2.1.4"),
        ("numpy", "1.26.3"),
        ("reportlab", "4.0.8"),
        ("fpdf2", "2.7.6"),
        ("yfinance", "0.2.35"),
        ("openpyxl", "3.1.2"),
        ("xlrd", "2.0.1"),
        ("plotly", "5.18.0"),
        ("pytz", "2023.3"),
        ("requests", "2.31.0"),
    ]

    optional = [
        ("kaleido", "Chart image export"),
        ("ollama", "Local AI inference (FREE)"),
        ("gpt4all", "Offline AI model (FREE)"),
        ("pdfplumber", "PDF text extraction"),
        ("pytesseract", "OCR for images"),
    ]

    # Check installed versions
    rows_html = []
    ok_count = 0
    for pkg_name, min_version in required:
        installed = _get_pkg_version(pkg_name)
        if installed:
            status = f'<span style="color:{GREEN};font-weight:700;">OK</span>'
            ok_count += 1
        else:
            status = f'<span style="color:{FIRE};font-weight:700;">MISSING</span>'

        rows_html.append(f"""
        <tr style="border-bottom:1px solid #1e293b;">
          <td style="padding:6px 12px;color:#e2e8f0;font-weight:600;">{pkg_name}</td>
          <td style="padding:6px 12px;color:#94a3b8;">&ge; {min_version}</td>
          <td style="padding:6px 12px;color:#e2e8f0;">{installed or 'N/A'}</td>
          <td style="padding:6px 12px;">{status}</td>
        </tr>
        """)

    # KPI
    kc1, kc2, kc3 = st.columns(3)
    kc1.metric("Required Packages", len(required))
    kc2.metric("Installed", ok_count)
    kc3.metric("Missing", len(required) - ok_count)

    st.markdown(f"""
    <table style="width:100%;border-collapse:collapse;background:#0d1b2e;border-radius:8px;overflow:hidden;">
      <thead>
        <tr style="background:{NAVY};">
          <th style="padding:6px 12px;text-align:left;color:#fff;font-size:0.8rem;">Package</th>
          <th style="padding:6px 12px;text-align:left;color:#fff;font-size:0.8rem;">Required</th>
          <th style="padding:6px 12px;text-align:left;color:#fff;font-size:0.8rem;">Installed</th>
          <th style="padding:6px 12px;text-align:left;color:#fff;font-size:0.8rem;">Status</th>
        </tr>
      </thead>
      <tbody>{''.join(rows_html)}</tbody>
    </table>
    """, unsafe_allow_html=True)

    # Optional packages
    st.markdown("---")
    st.markdown("**Optional Packages**")
    for pkg_name, purpose in optional:
        installed = _get_pkg_version(pkg_name)
        icon = "🟢" if installed else "⚪"
        ver = installed or "not installed"
        st.markdown(f"{icon} **{pkg_name}** — {purpose} — `{ver}`")


def _get_pkg_version(pkg_name: str) -> str:
    """Get installed version of a package, or empty string if not installed."""
    try:
        from importlib.metadata import version
        return version(pkg_name)
    except Exception:
        # Some packages have different import names
        alt_names = {"fpdf2": "fpdf", "pytesseract": "pytesseract"}
        alt = alt_names.get(pkg_name)
        if alt:
            try:
                from importlib.metadata import version
                return version(alt)
            except Exception:
                pass
        return ""


# ── Tab 2: Environment ───────────────────────────────────────────────────────

def _render_environment():
    st.subheader("System Environment")

    # Python info
    ec1, ec2, ec3 = st.columns(3)
    ec1.metric("Python Version", platform.python_version())
    ec2.metric("Platform", platform.system())
    ec3.metric("Architecture", platform.machine())

    st.markdown("---")

    # Disk space
    try:
        import shutil
        disk = shutil.disk_usage(str(BASE))
        dc1, dc2, dc3 = st.columns(3)
        dc1.metric("Disk Total", f"{disk.total // (1024**3)} GB")
        dc2.metric("Disk Used", f"{disk.used // (1024**3)} GB")
        dc3.metric("Disk Free", f"{disk.free // (1024**3)} GB")
    except Exception:
        st.caption("Disk usage information not available.")

    st.markdown("---")

    # Database size
    db_path = BASE / "bitumen_dashboard.db"
    if db_path.exists():
        db_size = db_path.stat().st_size
        st.metric("Database Size", f"{db_size / (1024*1024):.1f} MB")

    # JSON files
    json_files = list(BASE.glob("*.json"))
    json_total = sum(f.stat().st_size for f in json_files if f.exists())
    jc1, jc2 = st.columns(2)
    jc1.metric("JSON Files", len(json_files))
    jc2.metric("JSON Total Size", f"{json_total / (1024*1024):.1f} MB")

    # PDF exports
    pdf_dir = BASE / "pdf_exports"
    if pdf_dir.exists():
        pdf_files = list(pdf_dir.glob("*.pdf"))
        pdf_total = sum(f.stat().st_size for f in pdf_files if f.exists())
        pc1, pc2 = st.columns(2)
        pc1.metric("PDF Exports", len(pdf_files))
        pc2.metric("PDF Total Size", f"{pdf_total / (1024*1024):.1f} MB")

    # Python path
    st.markdown("---")
    st.markdown("**Python Executable**")
    st.code(sys.executable, language=None)
    st.markdown("**Working Directory**")
    st.code(str(BASE), language=None)


# ── Tab 3: Worker Modules ────────────────────────────────────────────────────

def _render_worker_modules():
    st.subheader("Engine Module Status")

    modules = [
        ("email_engine", "Email Engine — SMTP send + queue processing"),
        ("whatsapp_engine", "WhatsApp Engine — 360dialog integration"),
        ("sre_engine", "SRE Engine — Self-healing + auto bug fixing"),
        ("sync_engine", "Sync Engine — 13-step data orchestration"),
        ("api_hub_engine", "API Hub — Central data integration"),
        ("api_manager", "API Manager — Health checks + retry logic"),
        ("news_engine", "News Engine — RSS + API aggregation"),
        ("ai_fallback_engine", "AI Fallback — Multi-provider chain (FREE)"),
        ("ai_learning_engine", "AI Learning — Daily/weekly/monthly cycles"),
        ("ai_assistant_engine", "AI Assistant — Query interface"),
        ("director_briefing_engine", "Director Briefing — Executive reports"),
        ("communication_engine", "Communication Hub — Template rendering"),
        ("chart_engine", "Chart Engine — Plotly + Vastu design"),
        ("pdf_export_engine", "PDF Export — ReportLab universal builder"),
        ("calculation_engine", "Calculation Engine — Margin + cost analysis"),
        ("forward_strategy_engine", "Forward Strategy — Demand scoring"),
        ("infra_demand_engine", "Infra Demand — GDELT + budget cross-check"),
        ("correlation_engine", "Correlation Engine — Market correlations"),
        ("crm_engine", "CRM Engine — Task automation + pipeline"),
        ("universal_action_engine", "Universal Action — Send/export from any page"),
        ("role_engine", "Role Engine — RBAC access control"),
    ]

    ok_count = 0
    rows_html = []
    for mod_name, description in modules:
        can_import = False
        file_size = ""
        try:
            mod_path = BASE / f"{mod_name}.py"
            if mod_path.exists():
                file_size = f"{mod_path.stat().st_size / 1024:.0f} KB"
            __import__(mod_name)
            can_import = True
            ok_count += 1
        except Exception:
            pass

        badge = (
            f'<span style="color:{GREEN};font-weight:700;">OK</span>'
            if can_import
            else f'<span style="color:{FIRE};font-weight:700;">FAIL</span>'
        )

        rows_html.append(f"""
        <tr style="border-bottom:1px solid #1e293b;">
          <td style="padding:6px 12px;color:#e2e8f0;font-weight:600;">{mod_name}</td>
          <td style="padding:6px 12px;color:#94a3b8;font-size:0.8rem;">{description}</td>
          <td style="padding:6px 12px;color:#94a3b8;">{file_size}</td>
          <td style="padding:6px 12px;">{badge}</td>
        </tr>
        """)

    # KPI
    kc1, kc2, kc3 = st.columns(3)
    kc1.metric("Total Modules", len(modules))
    kc2.metric("Import OK", ok_count)
    kc3.metric("Import Failed", len(modules) - ok_count)

    st.markdown(f"""
    <table style="width:100%;border-collapse:collapse;background:#0d1b2e;border-radius:8px;overflow:hidden;">
      <thead>
        <tr style="background:{NAVY};">
          <th style="padding:6px 12px;text-align:left;color:#fff;font-size:0.8rem;">Module</th>
          <th style="padding:6px 12px;text-align:left;color:#fff;font-size:0.8rem;">Description</th>
          <th style="padding:6px 12px;text-align:left;color:#fff;font-size:0.8rem;">Size</th>
          <th style="padding:6px 12px;text-align:left;color:#fff;font-size:0.8rem;">Status</th>
        </tr>
      </thead>
      <tbody>{''.join(rows_html)}</tbody>
    </table>
    """, unsafe_allow_html=True)
