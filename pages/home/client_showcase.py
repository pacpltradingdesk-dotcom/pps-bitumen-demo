"""
PPS Anantam — Client Showcase (Digital Visiting Card)
======================================================
Shareable single-scroll page for customers.
Hero → Products → Today's Rates → Why PPS → Contact → Footer
"""

import streamlit as st
import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _load_json(filename):
    try:
        with open(os.path.join(BASE_DIR, filename), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _get_company():
    try:
        from company_config import COMPANY_PROFILE
        return COMPANY_PROFILE
    except Exception:
        return {
            "legal_name": "PPS Anantams Corporation Private Limited",
            "short_name": "PPS Anantams",
            "owner_name": "PRINCE P SHAH",
            "owner_mobile": "+91 7795242424",
            "owner_email": "princepshah@gmail.com",
            "experience_years": 24,
            "business_role": "Commission Agent + Logistics Arranger",
            "contact_database_size": 24000,
            "gst_no": "24AAHCV1611L2ZD",
            "pan_no": "AAHCV1611L",
            "cin_no": "U46632GJ2019PTC110676",
            "full_address": "04, Signet plaza Tower-B, Third floor, Kunal cross road, Gotri, Vadodara-390021, Gujarat",
            "city": "Vadodara",
            "state": "Gujarat",
            "bank_details": {
                "bank_name": "ICICI BANK",
                "ac_no": "184105001402",
                "ifsc": "ICIC0001841",
                "branch": "Vadodara",
            },
        }


def _get_products():
    try:
        from business_context import PRODUCTS
        return PRODUCTS
    except Exception:
        return {}


def _get_live_rates():
    lp = _load_json("live_prices.json")
    return {
        "VG30 Bulk (Mumbai)": lp.get("DRUM_MUMBAI_VG30", 37000) - 2000,
        "VG30 Drum (Mumbai)": lp.get("DRUM_MUMBAI_VG30", 37000),
        "VG30 Bulk (Kandla)": lp.get("DRUM_KANDLA_VG30", 35500) - 2000,
        "VG30 Drum (Kandla)": lp.get("DRUM_KANDLA_VG30", 35500),
        "VG10 Bulk (Mumbai)": lp.get("DRUM_MUMBAI_VG10", 38000) - 2000,
        "VG10 Drum (Mumbai)": lp.get("DRUM_MUMBAI_VG10", 38000),
    }


def _inject_showcase_css():
    st.markdown("""
    <style>
    .showcase-hero {
        background: linear-gradient(135deg, #1E1B4B 0%, #312E81 50%, #4F46E5 100%);
        color: white; padding: 48px 32px; border-radius: 16px;
        text-align: center; margin-bottom: 32px;
    }
    .showcase-hero h1 {
        font-size: 2rem; font-weight: 900; margin: 0; letter-spacing: -0.02em;
    }
    .showcase-hero .subtitle {
        font-size: 1.1rem; color: #C7D2FE; margin-top: 8px; font-weight: 500;
    }
    .showcase-hero .tagline {
        font-size: 0.9rem; color: #A5B4FC; margin-top: 4px;
    }
    .showcase-hero .badge-row {
        margin-top: 16px; display: flex; justify-content: center; gap: 12px; flex-wrap: wrap;
    }
    .showcase-hero .badge {
        background: rgba(255,255,255,0.15); padding: 6px 14px; border-radius: 20px;
        font-size: 0.8rem; font-weight: 600; backdrop-filter: blur(4px);
    }
    .showcase-section {
        margin-bottom: 32px;
    }
    .showcase-section h2 {
        font-size: 1.3rem; font-weight: 800; color: #111827;
        border-bottom: 2px solid #4F46E5; padding-bottom: 8px; margin-bottom: 16px;
    }
    .product-card {
        background: white; border: 1px solid #E5E7EB; border-radius: 12px;
        padding: 16px; text-align: center; height: 100%;
    }
    .product-card .grade { font-size: 1.1rem; font-weight: 800; color: #4F46E5; }
    .product-card .desc { font-size: 0.8rem; color: #6B7280; margin-top: 6px; }
    .rate-table {
        width: 100%; border-collapse: collapse; font-size: 0.9rem;
    }
    .rate-table th {
        background: #F9FAFB; padding: 10px 14px; text-align: left;
        font-weight: 700; color: #374151; border-bottom: 2px solid #E5E7EB;
    }
    .rate-table td {
        padding: 10px 14px; border-bottom: 1px solid #F3F4F6;
    }
    .rate-table tr:hover td { background: #F9FAFB; }
    .why-card {
        background: white; border: 1px solid #E5E7EB; border-radius: 12px;
        padding: 18px; text-align: center;
    }
    .why-card .number { font-size: 1.6rem; font-weight: 900; color: #4F46E5; }
    .why-card .text { font-size: 0.8rem; color: #6B7280; margin-top: 4px; }
    .contact-bar {
        background: #1E1B4B; color: white; border-radius: 12px;
        padding: 24px 32px; display: flex; justify-content: space-around;
        flex-wrap: wrap; gap: 16px; text-align: center;
    }
    .contact-bar a {
        color: #C7D2FE; text-decoration: none; font-weight: 600;
        font-size: 0.9rem; transition: color 0.2s;
    }
    .contact-bar a:hover { color: white; }
    .showcase-footer {
        background: #F9FAFB; border: 1px solid #E5E7EB; border-radius: 12px;
        padding: 20px; font-size: 0.75rem; color: #6B7280; text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)


def render():
    _inject_showcase_css()
    co = _get_company()

    # ── Hero ──────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="showcase-hero">
        <h1>🏛️ {co.get('legal_name', 'PPS Anantams Corporation Pvt Ltd')}</h1>
        <div class="subtitle">{co.get('business_role', 'Commission Agent + Logistics Arranger')}</div>
        <div class="tagline">{co.get('city', 'Vadodara')}, {co.get('state', 'Gujarat')} — India</div>
        <div class="badge-row">
            <span class="badge">🏆 {co.get('experience_years', 24)} Years in Bitumen</span>
            <span class="badge">📞 {co.get('contact_database_size', '24,000'):,}+ Contacts</span>
            <span class="badge">🇮🇳 Pan-India Network</span>
            <span class="badge">🚢 8 Import Terminals</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Products ──────────────────────────────────────────────────────────
    st.markdown('<div class="showcase-section"><h2>Our Products</h2></div>', unsafe_allow_html=True)
    products = _get_products()

    # Flatten all grades for display
    all_grades = []
    grade_info = {
        "VG-30": {"icon": "🛣️", "desc": "Highway paving — highest demand grade (~60% market share)"},
        "VG-10": {"icon": "🌧️", "desc": "Cold regions & surface dressing — spraying applications"},
        "VG-40": {"icon": "🔥", "desc": "Heavy traffic zones — premium durability"},
        "CRMB-55": {"icon": "♻️", "desc": "Crumb Rubber Modified — eco-friendly, crack resistant"},
        "CRMB-60": {"icon": "🏗️", "desc": "High-stress zones — bridges, expressways"},
        "PMB": {"icon": "⚡", "desc": "Polymer Modified — extreme weather performance"},
    }

    if products:
        for category, grades in products.items():
            for g_name in grades:
                all_grades.append(g_name)
    else:
        all_grades = list(grade_info.keys())

    # Show top 6 products in 3x2 grid
    display_grades = [g for g in grade_info if g in all_grades or True][:6]
    cols = st.columns(3)
    for i, g in enumerate(display_grades):
        info = grade_info.get(g, {"icon": "📦", "desc": ""})
        with cols[i % 3]:
            st.markdown(f"""<div class="product-card">
                <div style="font-size:1.5rem;">{info['icon']}</div>
                <div class="grade">{g}</div>
                <div class="desc">{info['desc']}</div>
            </div>""", unsafe_allow_html=True)
            st.markdown("")

    # ── Today's Indicative Rates ──────────────────────────────────────────
    st.markdown('<div class="showcase-section"><h2>Today\'s Indicative Rates</h2></div>',
                unsafe_allow_html=True)
    rates = _get_live_rates()

    rows = ""
    for grade_loc, price in rates.items():
        rows += f"<tr><td><strong>{grade_loc}</strong></td><td style='text-align:right; font-weight:700; color:#059669;'>₹{price:,.0f}/MT</td></tr>"

    st.markdown(f"""
    <table class="rate-table">
        <thead><tr><th>Grade & Location</th><th style="text-align:right;">Rate (₹/MT)</th></tr></thead>
        <tbody>{rows}</tbody>
    </table>
    <div style="font-size:0.75rem; color:#6B7280; margin-top:8px;">
        * Rates are indicative. Final pricing depends on quantity, destination & payment terms.
        Ex-Terminal/Warehouse. GST 18% extra. 100% advance. 24hr validity.
    </div>
    """, unsafe_allow_html=True)

    st.markdown("")

    # ── Why PPS Anantams ──────────────────────────────────────────────────
    st.markdown('<div class="showcase-section"><h2>Why PPS Anantams?</h2></div>',
                unsafe_allow_html=True)

    w1, w2, w3, w4 = st.columns(4)
    why_items = [
        (w1, "24+", "Years Experience", "Deep market knowledge since 2002"),
        (w2, "24K+", "Industry Contacts", "Refineries, importers, contractors, govt"),
        (w3, "8", "Import Terminals", "Direct access to all major ports"),
        (w4, "50+", "Source Points", "PSU Refineries + Import + Decanters"),
    ]
    for col, num, title, sub in why_items:
        with col:
            st.markdown(f"""<div class="why-card">
                <div class="number">{num}</div>
                <div style="font-weight:700; color:#111827; font-size:0.85rem;">{title}</div>
                <div class="text">{sub}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("")

    # More reasons
    reasons = [
        "PSU + Import + Decanter — all source types covered",
        "Real-time AI-powered pricing for best landed cost",
        "Pan-India delivery network — bulk tankers & drum trucks",
        "Transparent billing — GST compliant, proper documentation",
        "NHAI/MoRTH project experience — highway-grade bitumen",
        "24/7 price quotes — call or WhatsApp anytime",
    ]
    for r in reasons:
        st.markdown(f"- {r}")

    st.markdown("")

    # ── Contact ───────────────────────────────────────────────────────────
    st.markdown('<div class="showcase-section"><h2>Get in Touch</h2></div>',
                unsafe_allow_html=True)

    phone = co.get("owner_mobile", "+91 7795242424")
    email = co.get("owner_email", "princepshah@gmail.com")
    phone_clean = phone.replace(" ", "").replace("+", "")

    st.markdown(f"""
    <div class="contact-bar">
        <div>
            <div style="font-size:0.75rem; color:#A5B4FC;">Call Us</div>
            <a href="tel:{phone}">{phone}</a>
        </div>
        <div>
            <div style="font-size:0.75rem; color:#A5B4FC;">WhatsApp</div>
            <a href="https://wa.me/{phone_clean}" target="_blank">Chat Now</a>
        </div>
        <div>
            <div style="font-size:0.75rem; color:#A5B4FC;">Email</div>
            <a href="mailto:{email}">{email}</a>
        </div>
        <div>
            <div style="font-size:0.75rem; color:#A5B4FC;">Office</div>
            <span style="font-size:0.85rem;">{co.get('city', 'Vadodara')}, {co.get('state', 'Gujarat')}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("")

    # Full address
    st.markdown(f"**Office Address:** {co.get('full_address', '')}")

    st.markdown("")

    # ── Footer ────────────────────────────────────────────────────────────
    bank = co.get("bank_details", {})
    st.markdown(f"""
    <div class="showcase-footer">
        <div style="margin-bottom:8px;">
            <strong>{co.get('legal_name', 'PPS Anantams Corporation Pvt Ltd')}</strong>
        </div>
        <div>
            GST: {co.get('gst_no', '')} | PAN: {co.get('pan_no', '')} | CIN: {co.get('cin_no', '')}
        </div>
        <div style="margin-top:6px;">
            Bank: {bank.get('bank_name', 'ICICI')} | A/C: {bank.get('ac_no', '')} |
            IFSC: {bank.get('ifsc', '')} | Branch: {bank.get('branch', '')}
        </div>
        <div style="margin-top:6px;">
            HSN: 27132000 | Terms: 100% Advance | Validity: 24 Hours | Ex-Terminal/Warehouse
        </div>
        <div style="margin-top:10px; color:#9CA3AF;">
            © {co.get('short_name', 'PPS Anantams')} — Powered by AI
        </div>
    </div>
    """, unsafe_allow_html=True)
