"""
PPS Bitumen Dashboard v5.0 — Data Table Component
Clean White Theme | Searchable, paginated, exportable data tables.
"""

import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime
import math

# ── Theme Colors ──────────────────────────────────────────────
BLUE_PRIMARY = "#2563eb"
BLUE_HOVER   = "#1d4ed8"
BLUE_LIGHT   = "#dbeafe"
GREEN        = "#059669"
RED          = "#dc2626"
AMBER        = "#f59e0b"
SLATE_50     = "#f8fafc"
SLATE_200    = "#e2e8f0"
SLATE_500    = "#64748b"
SLATE_700    = "#334155"
SLATE_900    = "#0f172a"
WHITE        = "#ffffff"


def _inject_table_css():
    """Inject CSS for data table styling."""
    st.markdown(f"""
    <style>
    .pps-table-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.75rem;
        flex-wrap: wrap;
        gap: 0.5rem;
    }}
    .pps-table-info {{
        font-size: 0.8rem;
        color: {SLATE_500};
        font-weight: 500;
    }}
    .pps-table-actions {{
        display: flex;
        gap: 0.5rem;
        align-items: center;
    }}
    .pps-table-container {{
        background: {WHITE};
        border: 1px solid {SLATE_200};
        border-radius: 0.75rem;
        padding: 1rem;
        margin-bottom: 1rem;
    }}
    .pps-table-pagination {{
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 1rem;
        margin-top: 0.75rem;
        padding-top: 0.75rem;
        border-top: 1px solid {SLATE_200};
    }}
    .pps-table-page-info {{
        font-size: 0.8rem;
        color: {SLATE_500};
        font-weight: 500;
    }}
    </style>
    """, unsafe_allow_html=True)


def _search_dataframe(df: pd.DataFrame, query: str) -> pd.DataFrame:
    """Filter DataFrame rows that match the search query across all columns."""
    if not query or not query.strip():
        return df

    query_lower = query.lower().strip()
    mask = pd.Series([False] * len(df), index=df.index)

    for col in df.columns:
        mask = mask | df[col].astype(str).str.lower().str.contains(
            query_lower, na=False
        )

    return df[mask]


def _to_csv_bytes(df: pd.DataFrame) -> bytes:
    """Convert DataFrame to CSV bytes for download."""
    return df.to_csv(index=False).encode("utf-8")


def _to_excel_bytes(df: pd.DataFrame) -> bytes:
    """Convert DataFrame to Excel bytes for download. Returns None if openpyxl unavailable."""
    try:
        import openpyxl  # noqa: F401
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Data")
        return buffer.getvalue()
    except ImportError:
        return None


def render_data_table(
    df: pd.DataFrame,
    key: str,
    searchable: bool = True,
    exportable: bool = True,
    page_size: int = 25,
    title: str = None,
):
    """
    Filterable, searchable data table with export options.

    Args:
        df:         pandas DataFrame to display.
        key:        Unique key for widgets (must be unique per table).
        searchable: Whether to show a search box above the table.
        exportable: Whether to show CSV/Excel export buttons.
        page_size:  Number of rows per page (default 25).
        title:      Optional title displayed above the table.
    """
    if df is None or df.empty:
        st.info("No data to display.")
        return

    _inject_table_css()

    # ── Title ─────────────────────────────────────────────────
    if title:
        st.markdown(
            f'<p style="font-size:1rem;font-weight:600;color:{SLATE_900};'
            f'margin-bottom:0.5rem;">{title}</p>',
            unsafe_allow_html=True,
        )

    working_df = df.copy()

    # ── Search ────────────────────────────────────────────────
    search_query = ""
    if searchable:
        search_col, info_col = st.columns([3, 1])
        with search_col:
            search_query = st.text_input(
                "\U0001f50d Search",
                value="",
                placeholder="Search across all columns...",
                key=f"{key}_search",
                label_visibility="collapsed",
            )
        working_df = _search_dataframe(working_df, search_query)

        with info_col:
            total = len(df)
            filtered = len(working_df)
            if search_query:
                st.markdown(
                    f'<p class="pps-table-info">'
                    f'Showing {filtered} of {total} rows</p>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<p class="pps-table-info">{total} rows</p>',
                    unsafe_allow_html=True,
                )

    # ── Pagination ────────────────────────────────────────────
    total_rows = len(working_df)
    total_pages = max(1, math.ceil(total_rows / page_size))
    page_key = f"{key}_page"

    if page_key not in st.session_state:
        st.session_state[page_key] = 1

    # Reset to page 1 when search changes
    search_state_key = f"{key}_prev_search"
    if search_state_key not in st.session_state:
        st.session_state[search_state_key] = ""
    if st.session_state[search_state_key] != search_query:
        st.session_state[page_key] = 1
        st.session_state[search_state_key] = search_query

    current_page = st.session_state[page_key]
    current_page = min(current_page, total_pages)
    st.session_state[page_key] = current_page

    start_idx = (current_page - 1) * page_size
    end_idx = min(start_idx + page_size, total_rows)
    page_df = working_df.iloc[start_idx:end_idx]

    # ── Display Table ─────────────────────────────────────────
    st.dataframe(
        page_df,
        use_container_width=True,
        hide_index=True,
        key=f"{key}_dataframe",
    )

    # ── Pagination Controls ───────────────────────────────────
    if total_pages > 1:
        pag_cols = st.columns([1, 1, 2, 1, 1])

        with pag_cols[0]:
            if st.button(
                "\u25c0\u25c0 First",
                key=f"{key}_first",
                disabled=(current_page == 1),
                use_container_width=True,
            ):
                st.session_state[page_key] = 1
                st.rerun()

        with pag_cols[1]:
            if st.button(
                "\u25c0 Prev",
                key=f"{key}_prev",
                disabled=(current_page == 1),
                use_container_width=True,
            ):
                st.session_state[page_key] = current_page - 1
                st.rerun()

        with pag_cols[2]:
            st.markdown(
                f'<p style="text-align:center;color:{SLATE_500};'
                f'font-size:0.85rem;font-weight:500;margin-top:0.5rem;">'
                f'Page {current_page} of {total_pages} '
                f'({start_idx + 1}\u2013{end_idx} of {total_rows})</p>',
                unsafe_allow_html=True,
            )

        with pag_cols[3]:
            if st.button(
                "Next \u25b6",
                key=f"{key}_next",
                disabled=(current_page == total_pages),
                use_container_width=True,
            ):
                st.session_state[page_key] = current_page + 1
                st.rerun()

        with pag_cols[4]:
            if st.button(
                "Last \u25b6\u25b6",
                key=f"{key}_last",
                disabled=(current_page == total_pages),
                use_container_width=True,
            ):
                st.session_state[page_key] = total_pages
                st.rerun()

    # ── Export Buttons ────────────────────────────────────────
    if exportable:
        exp_cols = st.columns([1, 1, 4])
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")

        with exp_cols[0]:
            csv_bytes = _to_csv_bytes(working_df)
            st.download_button(
                "\u2b07\ufe0f CSV",
                data=csv_bytes,
                file_name=f"PPS_export_{key}_{timestamp}.csv",
                mime="text/csv",
                key=f"{key}_csv_dl",
                use_container_width=True,
            )

        with exp_cols[1]:
            xlsx_bytes = _to_excel_bytes(working_df)
            if xlsx_bytes:
                st.download_button(
                    "\u2b07\ufe0f Excel",
                    data=xlsx_bytes,
                    file_name=f"PPS_export_{key}_{timestamp}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"{key}_xlsx_dl",
                    use_container_width=True,
                )
            else:
                st.button(
                    "\u2b07\ufe0f Excel",
                    key=f"{key}_xlsx_na",
                    disabled=True,
                    help="Install openpyxl: pip install openpyxl",
                    use_container_width=True,
                )
