"""Import History — view past imports, revert the most recent."""
from __future__ import annotations
import sqlite3
from pathlib import Path

import streamlit as st
import pandas as pd

from contact_import_engine import revert_import

DB = Path(__file__).resolve().parent.parent.parent / "bitumen_dashboard.db"


def _load() -> pd.DataFrame:
    conn = sqlite3.connect(DB)
    try:
        return pd.read_sql_query(
            "SELECT id, imported_at, file_name, target_table, "
            "rows_inserted, rows_skipped, rows_errored, reverted "
            "FROM import_history ORDER BY id DESC LIMIT 50",
            conn,
        )
    finally:
        conn.close()


def render():
    st.markdown("## 🗂️ Import History")
    st.caption("Last 50 imports. Revert removes the rows inserted by that import.")

    df = _load()
    if df.empty:
        st.info("No imports yet — try the Import Wizard.")
        return

    for _, r in df.iterrows():
        with st.container(border=True):
            c1, c2, c3 = st.columns([5, 2, 1])
            with c1:
                reverted_badge = " · 🔁 reverted" if r["reverted"] else ""
                st.markdown(
                    f"**{r['file_name']}** → `{r['target_table']}`{reverted_badge}"
                )
                st.caption(f"{r['imported_at']} · id={r['id']}")
            with c2:
                st.metric("Inserted", int(r["rows_inserted"]))
            with c3:
                disabled = bool(r["reverted"])
                if st.button("Revert", key=f"_rev_{r['id']}",
                             disabled=disabled, type="secondary"):
                    with st.spinner("Reverting…"):
                        try:
                            n = revert_import(int(r["id"]))
                            st.success(f"Removed {n} row(s)")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))
