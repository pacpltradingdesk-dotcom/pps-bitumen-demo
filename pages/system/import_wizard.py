"""Import Wizard — 5-step flow for Excel/CSV → DB.

Steps:
  1  Upload        (file picker)
  2  Map columns   (auto-suggested, user-overridable)
  3  Classify      (target table + category tag)
  4  Preview       (validation + dedupe + first 20 rows)
  5  Commit        (progress + summary)

State lives in st.session_state["_iw"] — a dict keyed by step number.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

from contact_import_engine import (
    parse_spreadsheet, suggest_column_mapping,
    validate_rows, dedupe_against_db, commit_import,
)

TARGETS = [
    ("customers", "Customer — Contractor / Buyer"),
    ("suppliers", "Supplier — Refinery / Importer"),
    ("contacts",  "Contact — General directory"),
    ("customer_profiles", "Customer profile — WhatsApp data"),
]
TARGET_SCHEMAS = {
    "customers":         ["name", "phone", "city", "state", "gstin",
                          "address", "category"],
    "suppliers":         ["name", "phone", "city", "state", "gstin",
                          "category"],
    "contacts":          ["name", "phone", "email", "city", "state",
                          "category"],
    "customer_profiles": ["name", "company", "phone", "email", "city",
                          "state", "category", "notes"],
}


def _iw() -> dict:
    return st.session_state.setdefault("_iw", {"step": 1})


def _set_step(n: int):
    _iw()["step"] = n


def render():
    st.markdown("## 📥 Import Wizard")
    st.caption("Excel / CSV → SQLite. Dedupe, preview, commit, revert — all inside.")

    step = _iw()["step"]
    cols = st.columns(5)
    for i, label in enumerate(["Upload", "Map", "Classify", "Preview", "Commit"]):
        with cols[i]:
            active = i + 1 == step
            color = "#4F46E5" if active else "#9CA3AF"
            st.markdown(
                f"<div style='text-align:center;color:{color};font-weight:"
                f"{'700' if active else '400'};font-size:0.9rem;'>"
                f"{'●' if active else '○'} {i+1}. {label}</div>",
                unsafe_allow_html=True,
            )
    st.markdown("---")

    if step == 1:
        _step1_upload()
    elif step == 2:
        _step2_map()
    elif step == 3:
        _step3_classify()
    elif step == 4:
        _step4_preview()
    elif step == 5:
        _step5_commit()


# ── Step 1: Upload ─────────────────────────────────────────────────

def _step1_upload():
    st.subheader("Step 1 — Upload Excel or CSV")
    up = st.file_uploader("Drop a .xlsx or .csv file",
                          type=["xlsx", "xls", "csv"],
                          key="_iw_file")
    if up is None:
        st.info("Tip: first row must be column headers.")
        return

    suffix = Path(up.name).suffix
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(up.getvalue())
    tmp.close()

    try:
        df = parse_spreadsheet(tmp.name)
    except ValueError as e:
        st.error(str(e))
        return

    st.success(f"✅ Loaded `{up.name}` — **{len(df)} rows × {len(df.columns)} cols**")
    with st.expander("Preview first 5 rows"):
        st.dataframe(df.head(5), use_container_width=True)

    _iw().update({
        "file_name": up.name,
        "tmp_path":  tmp.name,
        "source_cols": list(df.columns),
    })
    if st.button("Next → Map columns", type="primary"):
        _set_step(2)
        st.rerun()


# ── Step 2: Map columns ────────────────────────────────────────────

def _step2_map():
    st.subheader("Step 2 — Map columns")
    state = _iw()
    source_cols = state.get("source_cols", [])
    if not source_cols:
        st.error("No file loaded — restart from Step 1.")
        if st.button("← Back to Upload"):
            _set_step(1)
            st.rerun()
        return

    target_table = state.get("target_table", "customers")
    schema = TARGET_SCHEMAS[target_table]
    suggested = suggest_column_mapping(source_cols, schema)

    st.caption(f"Target table: **{target_table}** — assign a source column to each field.")
    chosen: dict[str, str] = {}
    _map_cols = st.columns(2)
    for _i, field in enumerate(schema):
        with _map_cols[_i % 2]:
            default = suggested.get(field, "")
            options = [""] + source_cols
            idx = options.index(default) if default in options else 0
            chosen[field] = st.selectbox(
                f"**{field}**"
                + ("  _(required)_" if field == "name" else ""),
                options, index=idx, key=f"_iw_map_{field}"
            )

    c1, c2 = st.columns(2)
    with c1:
        if st.button("← Back"):
            _set_step(1)
            st.rerun()
    with c2:
        if st.button("Next → Classify", type="primary"):
            if not chosen.get("name"):
                st.warning("`name` is required — pick a source column.")
            else:
                state["mapping"] = {k: v for k, v in chosen.items() if v}
                _set_step(3)
                st.rerun()


# ── Step 3: Classify (target + category) ───────────────────────────

def _step3_classify():
    st.subheader("Step 3 — Classify")
    state = _iw()

    current = state.get("target_table", "customers")
    labels = [lbl for _, lbl in TARGETS]
    keys   = [k   for k, _   in TARGETS]
    idx    = keys.index(current) if current in keys else 0

    picked_label = st.radio("Import these rows as", labels, index=idx)
    picked_key   = keys[labels.index(picked_label)]

    category = st.text_input(
        "Default category tag (optional)",
        value=state.get("category", ""),
        placeholder="e.g. Contractor, Trader, Refinery",
        help="Applied to rows whose category column is blank.",
    )
    dedupe_strategy = st.radio(
        "If a row already exists in the DB (same name + phone)",
        ["skip", "overwrite", "merge"],
        index=["skip", "overwrite", "merge"].index(
            state.get("dedupe_strategy", "skip")
        ),
        horizontal=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        if st.button("← Back"):
            _set_step(2)
            st.rerun()
    with c2:
        if st.button("Next → Preview", type="primary"):
            state.update({
                "target_table": picked_key,
                "category": category.strip(),
                "dedupe_strategy": dedupe_strategy,
            })
            _set_step(4)
            st.rerun()


# ── Step 4: Preview ────────────────────────────────────────────────

def _step4_preview():
    st.subheader("Step 4 — Preview & clean")
    state = _iw()
    try:
        df = parse_spreadsheet(state["tmp_path"])
    except Exception as e:
        st.error(f"Could not re-read file: {e}")
        return

    inverse = {src: tgt for tgt, src in state["mapping"].items()}
    df = df.rename(columns=inverse)[list(state["mapping"].keys())]

    if state.get("category") and "category" in df.columns:
        df["category"] = df["category"].replace("", state["category"])

    valid, invalid = validate_rows(df, state["target_table"])
    fresh = dedupe_against_db(
        valid, state["target_table"], strategy=state["dedupe_strategy"]
    )

    m1, m2, m3 = st.columns(3)
    m1.metric("Valid", len(valid))
    m2.metric("Invalid", len(invalid))
    m3.metric("Fresh (after dedupe)", len(fresh))

    with st.expander(f"Preview first 20 of {len(fresh)} rows to insert",
                     expanded=True):
        st.dataframe(fresh.head(20), use_container_width=True)

    if len(invalid):
        with st.expander(f"⚠️ {len(invalid)} invalid row(s)"):
            st.dataframe(invalid, use_container_width=True)

    state["fresh_count"] = len(fresh)
    state["invalid_count"] = len(invalid)
    fresh_path = Path(state["tmp_path"]).with_suffix(".fresh.parquet")
    fresh.to_parquet(fresh_path)
    state["fresh_path"] = str(fresh_path)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("← Back"):
            _set_step(3)
            st.rerun()
    with c2:
        disabled = len(fresh) == 0
        if st.button("Commit import →", type="primary", disabled=disabled):
            _set_step(5)
            st.rerun()
    if disabled:
        st.caption("Nothing to commit — change dedupe strategy or upload a different file.")


# ── Step 5: Commit ─────────────────────────────────────────────────

def _step5_commit():
    st.subheader("Step 5 — Commit import")
    state = _iw()

    import pandas as pd
    fresh = pd.read_parquet(state["fresh_path"])
    with st.spinner(f"Inserting {len(fresh)} rows into "
                    f"{state['target_table']}…"):
        try:
            result = commit_import(
                fresh, state["target_table"],
                source_file=state["file_name"],
            )
        except Exception as e:
            st.error(f"Import failed — rolled back. Reason: {e}")
            if st.button("← Back to Preview"):
                _set_step(4)
                st.rerun()
            return

    st.success(f"✅ Inserted **{result['inserted']}** rows "
               f"(import_history id = {result['import_history_id']})")
    st.balloons()

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Open Contacts Directory"):
            try:
                from navigation_engine import navigate_to
                navigate_to("contacts_directory_dashboard")
            except Exception:
                pass
    with c2:
        if st.button("Start another import"):
            st.session_state.pop("_iw", None)
            _set_step(1)
            st.rerun()
