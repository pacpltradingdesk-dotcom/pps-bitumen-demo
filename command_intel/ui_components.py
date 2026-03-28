"""
PPS Anantam — Premium UI Components Toolkit
Injects raw HTML/CSS for advanced UI blocks (bento grids, animated metrics) that Streamlit doesn't support natively.
"""
import streamlit as st

def render_bento_metric(title: str, value: str, delta: str = None, icon: str = "📈", is_featured: bool = False) -> None:
    """
    Renders a crisp, minimalist metric card using raw HTML.
    Supports 'featured' styling which adds subtle indigo accents.
    """
    delta_html = ""
    if delta:
        color = "var(--text-muted)"
        bg_color = "#F3F4F6" # Gray 100
        if delta.strip().startswith("+"):
            color = "#059669" # Emerald 600
            bg_color = "#D1FAE5" # Emerald 100
        elif delta.strip().startswith("-"):
            color = "#DC2626" # Red 600
            bg_color = "#FEE2E2" # Red 100
        
        delta_html = f"""
        <div style="font-size: 0.75rem; font-weight: 700; color: {color}; background-color: {bg_color};
                    padding: 4px 10px; border-radius: 6px; display: inline-flex; align-items: center; gap: 4px; margin-top: 12px;
                    border: 1px solid rgba(0,0,0,0.05);">
            {delta}
        </div>
        """

    base_card_style = """
        background: var(--bg-surface);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-md);
        padding: 24px;
        box-shadow: var(--shadow-sm);
        transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
        position: relative;
        overflow: hidden;
        z-index: 1;
    """

    # If featured, add the glow card CSS class
    extra_style = "border-top: 3px solid var(--text-blue); box-shadow: var(--shadow-md);" if is_featured else ""

    html = f"""
    <div style="{base_card_style} {extra_style}" 
       onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='var(--shadow-md)'; this.style.borderColor='var(--border-hover)';" 
       onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='var(--shadow-sm)'; this.style.borderColor='var(--border-subtle)';">
        <div style="
            position: absolute;
            top: -20px;
            right: -20px;
            font-size: 100px;
            opacity: 0.03;
            transform: rotate(15deg);
            pointer-events: none;
            filter: grayscale(100%);
            transition: opacity 0.3s ease, transform 0.3s ease;
        " onmouseover="this.style.opacity='0.06'; this.style.transform='rotate(10deg) scale(1.1)';">{icon}</div>
        
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
            <span style="font-size: 1.2rem;">{icon}</span>
            <span style="font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted);">
                {title}
            </span>
        </div>
        
        <div style="font-size: 2.2rem; font-weight: 800; letter-spacing: -0.03em; color: var(--text-main); line-height: 1.1; display:flex; align-items:baseline; gap:4px;">
            {value}
        </div>
        
        {delta_html}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_animated_progress(title: str, percentage: int, color: str = "var(--text-blue)") -> None:
    """
    Renders an sleek progress bar inside a minimalist container.
    """
    html = f"""
    <div style="background: #FFFFFF; padding: 20px; border-radius: var(--radius-md); border: 1px solid var(--border-subtle); margin-bottom: 16px; box-shadow: var(--shadow-sm);">
        <div style="display: flex; justify-content: space-between; margin-bottom: 8px; align-items: center;">
            <span style="font-size: 0.8rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em;">{title}</span>
            <span style="font-size: 0.9rem; font-weight: 800; color: var(--text-main);">{percentage}%</span>
        </div>
        <div style="width: 100%; background: #F3F4F6; border-radius: 8px; height: 8px; overflow: hidden; border: 1px solid rgba(0,0,0,0.02);">
            <div style="width: 0%; height: 100%; background: {color}; border-radius: 8px; transition: width 1.5s cubic-bezier(0.25, 1, 0.5, 1);" id="prog_{title.replace(' ', '')}"></div>
        </div>
    </div>
    <script>
        setTimeout(() => {{
            document.getElementById('prog_{title.replace(' ', '')}').style.width = '{percentage}%';
        }}, 100);
    </script>
    """
    st.markdown(html, unsafe_allow_html=True)

def render_glass_container_start(title: str = "", subtitle: str = "", icon: str = "") -> None:
    """
    Start a crisp light container. Only use if strictly mapping HTML blocks.
    In Streamlit, it is usually better to rely on the CSS targeting [data-testid="stVerticalBlock"] (already done in theme.py).
    """
    header_html = ""
    if title:
        sub_html = f"<div style='font-size:0.85rem; color:var(--text-muted); font-weight:500; margin-top:4px;'>{subtitle}</div>" if subtitle else ""
        icon_html = f"<span style='margin-right:8px;'>{icon}</span>" if icon else ""
        header_html = f"""
        <div style="margin-bottom: 24px; padding-bottom: 16px; border-bottom: 1px solid var(--border-subtle);">
            <h3 style="margin:0; display:flex; align-items:center; color: var(--text-main); font-weight: 800; letter-spacing: -0.02em;">{icon_html}{title}</h3>
            {sub_html}
        </div>
        """
        
    html = f"""
    <div style="
        background: var(--bg-surface);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-md);
        padding: 32px;
        box-shadow: var(--shadow-sm);
        margin-bottom: 24px;
    ">
    {header_html}
    """
    st.markdown(html, unsafe_allow_html=True)

def render_glass_container_end() -> None:
    st.markdown("</div>", unsafe_allow_html=True)
