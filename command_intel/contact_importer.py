"""
Contact Importer UI Module
===========================
Streamlit UI for the Contact Importer feature.

Tabs:
  1. 📤 Import Contacts — upload, extract (AI or rules), preview, save
  2. 📋 Import History — view and clear past import batches

PPS Anantams Logistics AI — v3.3.3
"""

import streamlit as st
import pandas as pd

from contact_import_engine import (
    CATEGORY_TYPES,
    DESTINATION_OPTIONS,
    parse_file,
    extract_contacts_ai,
    extract_contacts_rules,
    check_duplicates,
    save_contacts,
    get_import_history,
    clear_import_history,
)


# ─── Preview columns (what's shown in the editable grid) ─────────────────────

_PREVIEW_COLS = [
    "company_name", "person_name", "mobile1", "email1",
    "city", "state", "gstin", "duplicate_status",
]

_DUP_COLORS = {
    "new":               "🟢 New",
    "possible_duplicate": "🟡 Possible Dup",
    "confirmed_dup":      "🔴 Confirmed Dup",
}


# ══════════════════════════════════════════════════════════════════════════════
# MAIN RENDER
# ══════════════════════════════════════════════════════════════════════════════

def render():
    st.subheader("📥 Contact Importer — Auto-Extract & CRM Fill")
    st.caption("Upload PDF, Excel, CSV, or images. AI auto-extracts contacts and fills CRM fields.")

    tab1, tab2 = st.tabs(["📤 Import Contacts", "📋 Import History"])

    with tab1:
        _render_import_tab()

    with tab2:
        _render_history_tab()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — IMPORT CONTACTS
# ══════════════════════════════════════════════════════════════════════════════

def _render_import_tab():
    # ── Step 1: Upload + Category ─────────────────────────────────────────────
    col_up, col_cat = st.columns([2, 1])

    with col_up:
        uploaded_file = st.file_uploader(
            "📂 Upload File",
            type=["xlsx", "xls", "csv", "pdf", "jpg", "jpeg", "png"],
            help="Supports Excel, CSV, PDF, and scanned images (JPG/PNG).",
        )

    with col_cat:
        category_type = st.selectbox(
            "Category Type",
            CATEGORY_TYPES,
            index=0,
            help="Select the contact category for proper field mapping.",
        )

    # ── Step 2: Extract ───────────────────────────────────────────────────────
    if uploaded_file:
        extract_btn = st.button("🔍 Extract Contacts", type="primary", use_container_width=True)

        if extract_btn:
            with st.spinner("Parsing file and extracting contacts..."):
                # Parse file
                pre_contacts, raw_text, parse_warning = parse_file(uploaded_file, category_type)
                source_name = uploaded_file.name

                if parse_warning:
                    st.warning(f"⚠️ {parse_warning}")

                contacts = []
                extraction_mode = "rules"

                if pre_contacts:
                    # Structured file (Excel/CSV) — already extracted
                    contacts = pre_contacts
                    extraction_mode = "rules"
                    st.info(f"📊 Structured file detected — {len(contacts)} rows parsed directly.")

                elif raw_text.strip():
                    # Unstructured (PDF/image/text) — try AI then rules
                    with st.spinner("🤖 Asking AI to extract contacts..."):
                        ai_contacts, ai_mode = extract_contacts_ai(raw_text, category_type)

                    if ai_contacts:
                        contacts = ai_contacts
                        extraction_mode = "ai"
                    else:
                        st.info("🤖 AI extraction unavailable or returned no results — using rule-based extraction.")
                        contacts = extract_contacts_rules(raw_text, category_type)
                        extraction_mode = "rules"

                else:
                    if not parse_warning:
                        st.warning("Could not extract any text from the file. Please try a different format.")

                if contacts:
                    # Duplicate check
                    contacts = check_duplicates(contacts)

                    # Store in session state
                    st.session_state["ci_contacts"]       = contacts
                    st.session_state["ci_source_name"]    = source_name
                    st.session_state["ci_extraction_mode"] = extraction_mode

    # ── Step 3: Preview & Edit ────────────────────────────────────────────────
    contacts = st.session_state.get("ci_contacts", [])
    ext_mode = st.session_state.get("ci_extraction_mode", "rules")
    src_name = st.session_state.get("ci_source_name", "")

    if contacts:
        # Extraction mode badge
        mode_badge = "🤖 AI Extraction" if ext_mode == "ai" else "📐 Rule-Based Extraction"
        dup_new    = sum(1 for c in contacts if c.get("duplicate_status") == "new")
        dup_warn   = sum(1 for c in contacts if c.get("duplicate_status") != "new")

        met1, met2, met3 = st.columns(3)
        with met1:
            st.metric("Contacts Found", len(contacts))
        with met2:
            st.metric("New", dup_new)
        with met3:
            st.metric("Duplicates / Warnings", dup_warn)

        st.caption(f"Extraction mode: **{mode_badge}**")

        # Build preview dataframe
        preview_rows = []
        for c in contacts:
            row = {col: c.get(col, "") for col in _PREVIEW_COLS}
            row["duplicate_status"] = _DUP_COLORS.get(
                c.get("duplicate_status", "new"), c.get("duplicate_status", "")
            )
            preview_rows.append(row)

        df_preview = pd.DataFrame(preview_rows, columns=_PREVIEW_COLS)
        df_preview.index = df_preview.index + 1   # 1-based row numbers

        st.markdown("**Preview — Edit fields below before saving:**")
        edited_df = st.data_editor(
            df_preview,
            use_container_width=True,
            num_rows="fixed",
            column_config={
                "duplicate_status": st.column_config.TextColumn("Dup Status", width="medium"),
                "mobile1":          st.column_config.TextColumn("Mobile", width="medium"),
                "email1":           st.column_config.TextColumn("Email", width="large"),
                "gstin":            st.column_config.TextColumn("GSTIN", width="medium"),
            },
            height=min(400, 40 + 35 * len(contacts)),
        )

        # Merge edits back into contacts list
        for i, c in enumerate(contacts):
            if i < len(edited_df):
                row = edited_df.iloc[i]
                for col in _PREVIEW_COLS:
                    if col != "duplicate_status":
                        c[col] = str(row.get(col, "")).strip()

        # ── Step 4: Destination + Save ────────────────────────────────────────
        st.divider()
        save_col1, save_col2 = st.columns([2, 1])

        with save_col1:
            destination = st.selectbox(
                "💾 Save To",
                DESTINATION_OPTIONS,
                index=0,
                help="Choose where to route the extracted contacts.",
            )

        with save_col2:
            st.write("")  # spacer
            st.write("")
            save_btn = st.button(
                f"💾 Save {len(contacts)} Contacts",
                type="primary",
                use_container_width=True,
            )

        if save_btn:
            with st.spinner(f"Saving {len(contacts)} contacts to {destination}..."):
                result = save_contacts(contacts, destination, source_file=src_name)

            saved  = result.get("saved", 0)
            errors = result.get("errors", [])

            if saved > 0:
                st.success(f"✅ {saved} contact(s) saved to **{destination}** successfully.")
                # Clear session state after successful save
                for key in ("ci_contacts", "ci_source_name", "ci_extraction_mode"):
                    st.session_state.pop(key, None)

            if errors:
                with st.expander(f"⚠️ {len(errors)} error(s) during save"):
                    for err in errors[:20]:
                        st.write(f"• {err}")

    elif uploaded_file and not st.session_state.get("ci_contacts"):
        st.info("Click **🔍 Extract Contacts** to begin extraction.")
    else:
        st.info("Upload a file above and click **🔍 Extract Contacts** to start.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — IMPORT HISTORY
# ══════════════════════════════════════════════════════════════════════════════

def _render_history_tab():
    st.subheader("📋 Import History")

    history = get_import_history()

    if not history:
        st.info("No import history yet. Upload and save contacts to see records here.")
        return

    # Display metrics
    total_batches = len(history)
    total_saved   = sum(r.get("saved", 0) for r in history)
    total_errors  = sum(r.get("errors", 0) for r in history)

    h1, h2, h3 = st.columns(3)
    with h1:
        st.metric("Total Batches", total_batches)
    with h2:
        st.metric("Total Contacts Saved", total_saved)
    with h3:
        st.metric("Total Errors", total_errors)

    # History table
    df_hist = pd.DataFrame(history)
    display_cols = [c for c in [
        "batch_id", "timestamp", "source_file", "category_type",
        "extraction_mode", "total", "saved", "errors", "destination"
    ] if c in df_hist.columns]

    st.dataframe(
        df_hist[display_cols],
        use_container_width=True,
        height=min(500, 50 + 35 * len(history)),
    )

    # Clear history
    st.divider()
    confirm_clear = st.checkbox("Confirm clear all import history")
    if st.button("🗑️ Clear Import History", disabled=not confirm_clear):
        clear_import_history()
        st.success("Import history cleared.")
        st.rerun()
