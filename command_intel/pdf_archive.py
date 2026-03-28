"""
command_intel/pdf_archive.py — PDF Export Archive Viewer
=========================================================
Lists all PDFs saved to pdf_exports/, with download and delete controls.
Nav: "📁 PDF Archive" under TECHNOLOGY & SYSTEMS
"""

from __future__ import annotations

import streamlit as st
import sys
import os
from pathlib import Path

# ── Import from parent dir ────────────────────────────────────────────────────
_HERE = Path(__file__).parent
_ROOT = _HERE.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    from pdf_export_engine import (
        list_archived_pdfs,
        delete_archived_pdf,
        delete_all_archived_pdfs,
        read_archived_pdf,
        get_archive_stats,
        EXPORT_DIR,
    )
    _ENGINE_OK = True
except Exception as _e:
    _ENGINE_OK = False
    _ENGINE_ERR = str(_e)

try:
    from india_localization import format_datetime_ist
    def _fmt_dt(s): return s  # already formatted strings from engine
except Exception:
    def _fmt_dt(s): return s


# ══════════════════════════════════════════════════════════════════════════════
# RENDER
# ══════════════════════════════════════════════════════════════════════════════

def render():
    st.title("📁 PDF Export Archive")
    st.caption("All PDFs generated from dashboard pages — download, preview info, or delete")

    if not _ENGINE_OK:
        st.error(f"PDF engine not available: {_ENGINE_ERR}")
        return

    # ── Stats row ─────────────────────────────────────────────────────────────
    stats = get_archive_stats()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total PDFs", stats["total_files"])
    c2.metric("Total Size", f"{stats['total_size_mb']} MB")
    c3.metric("Archive Folder", "pdf_exports/")
    c4.metric("Storage Path", "Local Disk")

    st.divider()

    # ── Action bar ────────────────────────────────────────────────────────────
    act1, act2, act3 = st.columns([2, 2, 4])
    with act1:
        if st.button("🔄 Refresh List", use_container_width=True):
            st.rerun()
    with act2:
        if st.button("🗑️ Clear ALL PDFs", use_container_width=True, type="secondary"):
            st.session_state["_pdf_arch_confirm_clear"] = True

    # Confirm clear all
    if st.session_state.get("_pdf_arch_confirm_clear"):
        st.warning("⚠️ This will permanently delete ALL archived PDFs. Are you sure?")
        y, n, _ = st.columns([1, 1, 5])
        with y:
            if st.button("✅ Yes, Delete All", type="primary"):
                count = delete_all_archived_pdfs()
                st.success(f"Deleted {count} files from archive.")
                st.session_state["_pdf_arch_confirm_clear"] = False
                st.rerun()
        with n:
            if st.button("❌ Cancel"):
                st.session_state["_pdf_arch_confirm_clear"] = False
                st.rerun()

    # ── File list ─────────────────────────────────────────────────────────────
    pdfs = list_archived_pdfs()

    if not pdfs:
        st.info(
            "📭 No PDFs in archive yet.\n\n"
            "Click **⬇ PDF** on any dashboard page to generate and save a PDF here."
        )
        return

    st.markdown(f"**{len(pdfs)} PDF{'s' if len(pdfs) != 1 else ''} in archive** — newest first")
    st.markdown("---")

    # ── Per-file cards ────────────────────────────────────────────────────────
    for i, pdf in enumerate(pdfs):
        fname       = pdf["filename"]
        page_title  = pdf.get("page_title", fname)
        generated   = pdf.get("generated_at", "—")
        role        = pdf.get("role", "—")
        size_kb     = pdf.get("size_kb", 0)

        with st.container():
            st.markdown(
                f"""<div style="background:#0d1b2e;border:1px solid #2563eb;
                    border-radius:8px;padding:10px 16px;margin-bottom:8px;">""",
                unsafe_allow_html=True,
            )

            # Top row: icon + title + meta
            row1, row2 = st.columns([4, 2])
            with row1:
                st.markdown(
                    f"**📄 {page_title}**  "
                    f"<span style='color:#94a3b8;font-size:12px;'>{fname}</span>",
                    unsafe_allow_html=True,
                )
                st.caption(
                    f"🕐 Generated: {generated} &nbsp;|&nbsp; "
                    f"👤 Role: {role} &nbsp;|&nbsp; "
                    f"📦 {size_kb} KB"
                )
            with row2:
                btn_dl, btn_del = st.columns(2)
                with btn_dl:
                    pdf_bytes = read_archived_pdf(fname)
                    if pdf_bytes:
                        st.download_button(
                            label="📥 Download",
                            data=pdf_bytes,
                            file_name=fname,
                            mime="application/pdf",
                            key=f"_arch_dl_{i}",
                            use_container_width=True,
                        )
                    else:
                        st.button("❌ Missing", disabled=True, key=f"_arch_miss_{i}",
                                  use_container_width=True)
                with btn_del:
                    if st.button(
                        "🗑️ Delete",
                        key=f"_arch_del_{i}",
                        use_container_width=True,
                    ):
                        if delete_archived_pdf(fname):
                            st.success(f"Deleted: {fname}")
                            st.rerun()
                        else:
                            st.error("Delete failed.")

            st.markdown("</div>", unsafe_allow_html=True)

    # ── Footer ────────────────────────────────────────────────────────────────
    st.divider()
    st.caption(
        f"📂 Archive location: `{EXPORT_DIR}`  |  "
        "PDFs auto-saved when generated via any ⬇ PDF button on dashboard pages."
    )
