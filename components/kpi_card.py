"""
PPS Bitumen Dashboard v5.0 — KPI Card Component
Clean White Theme | Metric cards with change indicators.
"""

import streamlit as st

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

# Map color names to hex values
_COLOR_MAP = {
    "green": GREEN,
    "red": RED,
    "amber": AMBER,
    "blue": BLUE_PRIMARY,
    "slate": SLATE_500,
}


def _inject_kpi_css():
    """Inject CSS for KPI card styling."""
    st.markdown(f"""
    <style>
    .pps-kpi-container {{
        display: flex;
        gap: 1rem;
        flex-wrap: wrap;
        margin-bottom: 1rem;
    }}
    .pps-kpi-card {{
        background: {WHITE};
        border: 1px solid {SLATE_200};
        border-radius: 0.75rem;
        padding: 1.25rem 1.5rem;
        flex: 1;
        min-width: 180px;
        transition: box-shadow 0.2s, border-color 0.2s;
    }}
    .pps-kpi-card:hover {{
        box-shadow: 0 4px 12px rgba(0,0,0,0.06);
        border-color: {BLUE_LIGHT};
    }}
    .pps-kpi-icon {{
        font-size: 1.5rem;
        margin-bottom: 0.25rem;
    }}
    .pps-kpi-label {{
        font-size: 0.7rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: {SLATE_500};
        margin: 0 0 0.35rem 0;
        line-height: 1.2;
    }}
    .pps-kpi-value {{
        font-size: 1.75rem;
        font-weight: 700;
        color: {SLATE_900};
        margin: 0 0 0.3rem 0;
        line-height: 1.1;
    }}
    .pps-kpi-change {{
        font-size: 0.8rem;
        font-weight: 600;
        margin: 0;
        line-height: 1.3;
    }}
    .pps-kpi-change-up {{
        color: {GREEN};
    }}
    .pps-kpi-change-down {{
        color: {RED};
    }}
    .pps-kpi-change-neutral {{
        color: {SLATE_500};
    }}
    </style>
    """, unsafe_allow_html=True)


def _resolve_color(color: str) -> str:
    """Resolve a color name or hex code to hex value."""
    if color is None:
        return SLATE_500
    color_lower = color.lower().strip()
    return _COLOR_MAP.get(color_lower, color)


def _get_change_arrow(change: str, color: str) -> str:
    """Determine arrow indicator based on change value."""
    if change is None:
        return ""
    change_stripped = change.strip().lstrip("+-")
    color_lower = color.lower().strip() if color else ""
    if color_lower == "green" or change.strip().startswith("+"):
        return "\u25b2 "  # up arrow
    elif color_lower == "red" or change.strip().startswith("-"):
        return "\u25bc "  # down arrow
    return ""


def _get_change_css_class(color: str) -> str:
    """Get CSS class for change indicator."""
    if color is None:
        return "pps-kpi-change-neutral"
    color_lower = color.lower().strip()
    if color_lower == "green":
        return "pps-kpi-change-up"
    elif color_lower == "red":
        return "pps-kpi-change-down"
    return "pps-kpi-change-neutral"


def render_kpi_card(
    label: str,
    value: str,
    change: str = None,
    change_color: str = "green",
    icon: str = "",
):
    """
    Renders a single KPI metric card using HTML with theme styling.

    Args:
        label:        Small-caps label text (e.g. "Total Revenue").
        value:        Large value text (e.g. "₹24.5 Cr").
        change:       Optional change indicator (e.g. "+12.3%").
        change_color: Color for change text — "green", "red", "amber", or hex.
        icon:         Optional emoji icon shown above the label.
    """
    _inject_kpi_css()

    icon_html = (
        f'<div class="pps-kpi-icon">{icon}</div>' if icon else ""
    )

    change_html = ""
    if change:
        arrow = _get_change_arrow(change, change_color)
        css_class = _get_change_css_class(change_color)
        resolved_color = _resolve_color(change_color)
        change_html = (
            f'<p class="pps-kpi-change" style="color:{resolved_color};">'
            f'{arrow}{change}</p>'
        )

    html = f"""
    <div class="pps-kpi-card">
        {icon_html}
        <p class="pps-kpi-label">{label}</p>
        <p class="pps-kpi-value">{value}</p>
        {change_html}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_kpi_row(cards: list):
    """
    Renders multiple KPI cards in a responsive row using st.columns.

    Args:
        cards: List of dicts, each with keys:
               - label (str): Card label
               - value (str): Card value
               - change (str, optional): Change indicator
               - color (str, optional): Change color (default "green")
               - icon (str, optional): Emoji icon
    """
    if not cards:
        return

    _inject_kpi_css()

    cols = st.columns(len(cards))

    for col, card in zip(cols, cards):
        with col:
            icon_html = ""
            icon = card.get("icon", "")
            if icon:
                icon_html = f'<div class="pps-kpi-icon">{icon}</div>'

            change = card.get("change")
            change_color = card.get("color", "green")
            change_html = ""
            if change:
                arrow = _get_change_arrow(change, change_color)
                resolved_color = _resolve_color(change_color)
                change_html = (
                    f'<p class="pps-kpi-change" style="color:{resolved_color};">'
                    f'{arrow}{change}</p>'
                )

            html = f"""
            <div class="pps-kpi-card">
                {icon_html}
                <p class="pps-kpi-label">{card.get("label", "")}</p>
                <p class="pps-kpi-value">{card.get("value", "")}</p>
                {change_html}
            </div>
            """
            st.markdown(html, unsafe_allow_html=True)
