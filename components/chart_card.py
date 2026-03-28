"""
PPS Anantam — Chart Card Component v5.0
==========================================
Chart wrapper with download PNG + share buttons.
"""
import streamlit as st
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))


def render_chart_card(fig, title: str, page_name: str = "",
                      downloadable: bool = True, shareable: bool = True,
                      height: int = 400):
    """
    Chart wrapper with download PNG + share buttons.

    Args:
        fig: Plotly figure object
        title: Chart title text
        page_name: Page name for share context
        downloadable: Show download PNG button
        shareable: Show share button
        height: Chart height in pixels
    """
    # Title header
    col_title, col_actions = st.columns([8, 2])
    with col_title:
        st.markdown(
            f'<div class="pps-section-header">{title}</div>',
            unsafe_allow_html=True,
        )

    # Render chart
    st.plotly_chart(fig, use_container_width=True, config={
        "displayModeBar": False,
        "responsive": True,
    })

    # Action buttons
    if downloadable or shareable:
        action_cols = st.columns([1, 1, 6])

        if downloadable:
            with action_cols[0]:
                if st.button("📥 PNG", key=f"chart_dl_{title[:20]}", help="Download as PNG"):
                    try:
                        img_bytes = fig.to_image(format="png", width=1200, height=700, scale=2)
                        if img_bytes:
                            now = datetime.now(IST).strftime("%Y%m%d_%H%M")
                            safe_title = title.replace(" ", "_")[:30]
                            st.download_button(
                                "Download",
                                data=img_bytes,
                                file_name=f"PPS_{safe_title}_{now}.png",
                                mime="image/png",
                                key=f"chart_dl_btn_{title[:20]}",
                            )
                    except ImportError:
                        st.caption("Install `kaleido` for PNG export")
                    except Exception as e:
                        st.caption(f"Export failed: {e}")

        if shareable:
            with action_cols[1]:
                try:
                    from components.share_button import render_share_button
                    render_share_button(
                        page_name=page_name or title,
                        data_fn=lambda: {"summary": f"Chart: {title}"},
                    )
                except ImportError:
                    pass
