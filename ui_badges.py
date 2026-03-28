import streamlit as st

def display_badge(data_type: str):
    """
    Renders a unified data badge.
    data_type can be: 'real-time', 'calculated', 'historical'
    """
    if data_type == "real-time":
        icon, bg_col, text_col, label = "🟢", "#dcfce7", "#166534", "Real-Time Data"
    elif data_type == "calculated":
        icon, bg_col, text_col, label = "🟡", "#fef9c3", "#854d0e", "Auto-Calculated Output"
    elif data_type == "historical":
        icon, bg_col, text_col, label = "⚪", "#f1f5f9", "#475569", "Historical / Static Data"
    else:
        icon, bg_col, text_col, label = "🔵", "#e0f2fe", "#075985", "Information"

    st.markdown(
        f"""
<div style="
            display: inline-flex;
            align-items: center;
            background-color: {bg_col};
            color: {text_col};
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.8rem;
            font-weight: 600;
            margin-bottom: 10px;
            border: 1px solid rgba(0,0,0,0.05);
        ">
<span style="margin-right: 5px;">{icon}</span> {label}
</div>
        """,
        unsafe_allow_html=True
    )
