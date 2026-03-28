import streamlit as st
import os
from dotenv import load_dotenv
from brain import analyze_charts
from PIL import Image

# Load environment variables
load_dotenv()

# Page Configuration
st.set_page_config(
    page_title="Strategic Nifty Vision",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for the Dashboard
st.markdown("""
<style>
    .big-font {
        font-size: 24px !important;
        font-weight: bold;
    }
    .metric-card {
        background-color: #1E1E1E;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #333;
        text-align: center;
    }
    .bullish {
        color: #00FF00;
    }
    .bearish {
        color: #FF0000;
    }
    .neutral {
        color: #FFFF00;
    }
</style>
""", unsafe_allow_html=True)

def main():
    st.title("Strategic Nifty Vision 🦅")
    st.markdown("### AI-Powered Constituent Analysis System")

    # Sidebar for API Key
    with st.sidebar:
        st.header("Configuration")
        api_key = st.text_input("Enter Google API Key", type="password")
        if not api_key:
            api_key = os.getenv("GOOGLE_API_KEY")
        
        st.info("Upload the 12 charts in the specific order below.")

    # 12 Slots - Grid Layout
    st.header("1. Upload Charts")
    
    col1, col2, col3, col4 = st.columns(4)
    
    uploaded_files = {}
    
    with col1:
        uploaded_files['slot1'] = st.file_uploader("1. Nifty 50 (Index)", type=['png', 'jpg', 'jpeg'])
        uploaded_files['slot5'] = st.file_uploader("5. ICICI Bank", type=['png', 'jpg', 'jpeg'])
        uploaded_files['slot9'] = st.file_uploader("9. Axis Bank", type=['png', 'jpg', 'jpeg'])

    with col2:
        uploaded_files['slot2'] = st.file_uploader("2. Bank Nifty (Sector)", type=['png', 'jpg', 'jpeg'])
        uploaded_files['slot6'] = st.file_uploader("6. Infosys", type=['png', 'jpg', 'jpeg'])
        uploaded_files['slot10'] = st.file_uploader("10. Kotak Bank", type=['png', 'jpg', 'jpeg'])

    with col3:
        uploaded_files['slot3'] = st.file_uploader("3. HDFC Bank (CRITICAL)", type=['png', 'jpg', 'jpeg'])
        uploaded_files['slot7'] = st.file_uploader("7. ITC", type=['png', 'jpg', 'jpeg'])
        uploaded_files['slot11'] = st.file_uploader("11. SBI", type=['png', 'jpg', 'jpeg'])

    with col4:
        uploaded_files['slot4'] = st.file_uploader("4. Reliance (CRITICAL)", type=['png', 'jpg', 'jpeg'])
        uploaded_files['slot8'] = st.file_uploader("8. L&T", type=['png', 'jpg', 'jpeg'])
        uploaded_files['slot12'] = st.file_uploader("12. TCS", type=['png', 'jpg', 'jpeg'])

    # Analysis Button
    if st.button("🚀 Analyze Market Structure", use_container_width=True):
        if not api_key:
            st.error("Please provide a Google API Key.")
            return
        
        # Validation: Check if all critical slots are filled
        missing_critical = []
        if not uploaded_files['slot1']: missing_critical.append("Slot 1 (Nifty)")
        if not uploaded_files['slot3']: missing_critical.append("Slot 3 (HDFC)")
        if not uploaded_files['slot4']: missing_critical.append("Slot 4 (Reliance)")
        
        if missing_critical:
            st.warning(f"Missing Critical Charts: {', '.join(missing_critical)}. Analysis may be less accurate.")
        
        # Collect images in order
        images = []
        # We need to maintain the order 1-12. If a slot is empty, we handle it (e.g., skip or send None)
        # For simplicity, we send a list of tuples (slot_name, file)
        for i in range(1, 13):
            key = f"slot{i}"
            if uploaded_files[key]:
                images.append(uploaded_files[key])
            else:
                # Add placeholder or handle missing? 
                # The SRS implies 12 slots are expected. We'll skip missing but the prompt assumes 12.
                # Let's simple append None and handle in brain
                images.append(None)

        with st.spinner("AI is analyzing Market Structure & Constituents..."):
            try:
                result = analyze_charts(images, api_key)
                
                if result:
                    display_dashboard(result, images)
                else:
                    st.error("Analysis failed. Please check the logs.")
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")

def display_dashboard(data, images):
    st.divider()
    
    # --- Vastu/Sober Colors CSS ---
    st.markdown("""
    <style>
        .vastu-card {
            background-color: #0e1117; 
            border: 1px solid #262730;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 10px;
        }
        .vastu-header {
            color: #FFD700; /* Gold for Wealth */
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 5px;
        }
        .vastu-text {
            color: #e0e0e0;
            font-size: 14px;
        }
    </style>
    """, unsafe_allow_html=True)
    
    st.header("📊 Strategic Trade Dashboard")
    
    # 1. Image Reference Strip (Collapsible)
    with st.expander("📸 View Analyzed Charts (Verification)", expanded=False):
        # We need to filter out None values from images list if any, but we kept them aligned in main
        # Let's assume images list has filtered valid files or we filter here
        cols = st.columns(6)
        # Display first 6
        for idx in range(min(6, len(images))):
            with cols[idx]:
                if images[idx]:
                    st.image(images[idx], caption=f"Slot {idx+1}", use_container_width=True)
        
        cols2 = st.columns(6)
        # Display next 6
        for idx in range(6, min(12, len(images))):
            with cols2[idx-6]:
                if images[idx]:
                    st.image(images[idx], caption=f"Slot {idx+1}", use_container_width=True)

    # Visual cues for decision
    decision = data.get('decision', 'WAIT').upper()
    
    # Sober/Vastu Color Palette
    # Green (Emerald) for Buy, Red (muted) for Sell, Gold/Blue for Wait
    if 'BUY' in decision:
        status_color = "#10B981" # Emerald Green
    elif 'SELL' in decision:
        status_color = "#EF4444" # Muted Red
    else:
        status_color = "#3B82F6" # Royal Blue
    
    # 2. Top Level Status
    st.markdown(f"""
    <div style="background-color: {status_color}; padding: 20px; border-radius: 10px; text-align: center; color: white; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <h1 style="margin:0; text-shadow: 1px 1px 2px black;">{decision}</h1>
        <h3 style="margin:0; opacity: 0.9;">Probability: {data.get('confidence_score', '0%')}</h3>
        <p style="margin:0; font-style: italic; opacity: 0.8;">{data.get('market_status', '')}</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.write("") # Spacer

    # 3. Key Metrics Board (Gold Accents for Wealth)
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown(f"""
        <div class="metric-card" style="border-top: 3px solid #FFD700;">
            <h4 style="margin:0; color: #aaa;">🎯 ENTRY</h4>
            <h2 style="margin:5px 0; color: white;">{data.get('entry_trigger', 'N/A')}</h2>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="metric-card" style="border-top: 3px solid #EF4444;">
            <h4 style="margin:0; color: #aaa;">🛑 STOP LOSS</h4>
            <h2 style="margin:5px 0; color: #ff9999;">{data.get('exit_price', 'N/A')}</h2>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="metric-card" style="border-top: 3px solid #10B981;">
            <h4 style="margin:0; color: #aaa;">🏁 TARGET</h4>
            <h2 style="margin:5px 0; color: #6ee7b7;">{data.get('target', 'N/A')}</h2>
        </div>
        """, unsafe_allow_html=True)

    # 4. Strategic Reasoning (The 6 Drivers)
    st.subheader("🧠 Strategic Analysis (6-Point Check)")
    
    factors = data.get('factors', {})
    
    row1_c1, row1_c2, row1_c3 = st.columns(3)
    row2_c1, row2_c2, row2_c3 = st.columns(3)

    # Helper for card
    def reason_card(title, content):
        return f"""
        <div class="vastu-card">
            <div class="vastu-header">{title}</div>
            <div class="vastu-text">{content}</div>
        </div>
        """

    with row1_c1: st.markdown(reason_card("1. Nifty View (Market)", factors.get('Nifty_View', '-')), unsafe_allow_html=True)
    with row1_c2: st.markdown(reason_card("2. Bank Nifty (Sector)", factors.get('BankNifty_View', '-')), unsafe_allow_html=True)
    with row1_c3: st.markdown(reason_card("3. HDFC Bank (General)", factors.get('HDFC_Bank', '-')), unsafe_allow_html=True)
    
    with row2_c1: st.markdown(reason_card("4. Reliance (General)", factors.get('Reliance', '-')), unsafe_allow_html=True)
    with row2_c2: st.markdown(reason_card("5. Soldier Stocks", factors.get('Overall_Constituents', '-')), unsafe_allow_html=True)
    with row2_c3: st.markdown(reason_card("6. Confluence Check", factors.get('Technical_Confluence', '-')), unsafe_allow_html=True)


if __name__ == "__main__":
    main()
