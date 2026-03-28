"""
PPS Anantam — Subscription Pricing Page
==========================================
SaaS pricing tiers for the Bitumen Trading Dashboard.
"""
import streamlit as st
import datetime
import os
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TIERS = [
    {
        "name": "Essential",
        "price": 14999,
        "period": "year",
        "icon": "🟢",
        "color": "#10B981",
        "tag": "Start Here",
        "features": [
            "Live Market Prices (Brent, WTI, USD/INR)",
            "Basic Pricing Calculator",
            "VG30 Grade Support",
            "5 Quotes/Day",
            "Email Support",
            "Basic CRM (50 contacts)",
            "PDF Quote Generation",
            "Market News Feed",
        ],
    },
    {
        "name": "Plus",
        "price": 34999,
        "period": "year",
        "icon": "🔵",
        "color": "#4F46E5",
        "tag": "Most Popular",
        "recommended": True,
        "features": [
            "Everything in Essential +",
            "All Grades (VG10, VG30, VG40, CRMB, PMB)",
            "Import Cost Model",
            "AI Price Prediction",
            "Unlimited Quotes",
            "WhatsApp Integration",
            "CRM Automation (500 contacts)",
            "Negotiation Assistant",
            "Sales Calendar",
            "Director Briefing",
            "5 User Accounts",
        ],
    },
    {
        "name": "Premium",
        "price": 64999,
        "period": "year",
        "icon": "🟣",
        "color": "#8B5CF6",
        "tag": "Full Power",
        "features": [
            "Everything in Plus +",
            "10-Signal Market Intelligence",
            "Competitor Price Tracker",
            "NHAI Tender Feed",
            "Tanker Tracking",
            "E-Way Bill Management",
            "Credit & Aging Dashboard",
            "Profitability Analytics",
            "Telegram Integration",
            "API Access",
            "15 User Accounts",
            "Priority Support",
        ],
    },
    {
        "name": "Ultimate",
        "price": 89999,
        "period": "year",
        "icon": "👑",
        "color": "#D97706",
        "tag": "Enterprise",
        "features": [
            "Everything in Premium +",
            "White-Label Branding",
            "Custom Domain",
            "Dedicated Server",
            "AI Chatbot (Custom Trained)",
            "Custom Reports",
            "SRE Monitoring",
            "Unlimited Users",
            "24/7 Phone Support",
            "On-site Training",
            "Data Migration",
            "Custom Integrations",
        ],
    },
]


def _save_inquiry(data):
    """Save inquiry to database."""
    try:
        import sqlite3
        db_path = os.path.join(BASE_DIR, "bitumen_dashboard.db")
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS inquiries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT, company TEXT, phone TEXT, email TEXT,
                tier TEXT, message TEXT, created_at TEXT, status TEXT DEFAULT 'new'
            )
        """)
        conn.execute(
            "INSERT INTO inquiries (name, company, phone, email, tier, message, created_at) VALUES (?,?,?,?,?,?,?)",
            (data.get("name"), data.get("company"), data.get("phone"), data.get("email"),
             data.get("tier"), data.get("message"), datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def render():
    # ── Hero ──
    st.markdown("""
<div style="background:linear-gradient(135deg,#1E1B4B 0%,#312E81 50%,#4F46E5 100%);
            color:white;padding:48px 32px;border-radius:16px;text-align:center;margin-bottom:32px;">
<h1 style="font-size:2rem;font-weight:900;margin:0;">India's Smartest Bitumen Trading Platform</h1>
<p style="font-size:1.1rem;color:#C7D2FE;margin-top:8px;">AI-powered pricing, market intelligence, and sales automation</p>
<div style="margin-top:16px;display:flex;justify-content:center;gap:12px;flex-wrap:wrap;">
<span style="background:rgba(255,255,255,0.15);padding:6px 14px;border-radius:20px;font-size:0.8rem;font-weight:600;">25% Below Market Rates</span>
<span style="background:rgba(255,255,255,0.15);padding:6px 14px;border-radius:20px;font-size:0.8rem;font-weight:600;">No Setup Fee</span>
<span style="background:rgba(255,255,255,0.15);padding:6px 14px;border-radius:20px;font-size:0.8rem;font-weight:600;">Cancel Anytime</span>
</div>
</div>""", unsafe_allow_html=True)

    # ── Tier Cards ──
    cols = st.columns(4)
    for i, tier in enumerate(TIERS):
        with cols[i]:
            recommended = tier.get("recommended", False)
            border = f"2px solid {tier['color']}" if recommended else "1px solid #E2E8F0"
            badge = f'<div style="background:{tier["color"]};color:#fff;text-align:center;padding:4px;border-radius:12px 12px 0 0;font-size:0.7rem;font-weight:700;">{tier["tag"]}</div>' if recommended else ""

            features_html = ""
            for f in tier["features"]:
                features_html += f'<div style="font-size:0.78rem;color:#374151;padding:4px 0;border-bottom:1px solid #F3F4F6;">✓ {f}</div>'

            st.markdown(f"""
{badge}
<div style="background:#fff;border:{border};border-radius:{'0 0 12px 12px' if recommended else '12px'};padding:24px 16px;text-align:center;height:100%;">
<div style="font-size:1.5rem;">{tier['icon']}</div>
<div style="font-size:1.1rem;font-weight:800;color:#111827;margin-top:4px;">{tier['name']}</div>
<div style="margin:12px 0;">
<span style="font-size:1.8rem;font-weight:900;color:{tier['color']};">₹{tier['price']:,}</span>
<span style="font-size:0.8rem;color:#6B7280;">/{tier['period']}</span>
</div>
<div style="font-size:0.72rem;color:#9CA3AF;margin-bottom:12px;">₹{tier['price']//12:,}/month</div>
{features_html}
</div>""", unsafe_allow_html=True)

    st.markdown("")

    # ── Feature Comparison Table ──
    with st.expander("📊 Detailed Feature Comparison", expanded=False):
        all_features = [
            ("Live Market Prices", True, True, True, True),
            ("Pricing Calculator", True, True, True, True),
            ("All Bitumen Grades", False, True, True, True),
            ("Import Cost Model", False, True, True, True),
            ("AI Price Prediction", False, True, True, True),
            ("WhatsApp Integration", False, True, True, True),
            ("CRM Automation", "50", "500", "Unlimited", "Unlimited"),
            ("Negotiation Assistant", False, True, True, True),
            ("10-Signal Intelligence", False, False, True, True),
            ("Competitor Tracker", False, False, True, True),
            ("NHAI Tender Feed", False, False, True, True),
            ("Tanker Tracking", False, False, True, True),
            ("E-Way Bill Mgmt", False, False, True, True),
            ("Profitability Analytics", False, False, True, True),
            ("Telegram Integration", False, False, True, True),
            ("API Access", False, False, True, True),
            ("White-Label Branding", False, False, False, True),
            ("Custom Domain", False, False, False, True),
            ("AI Chatbot (Custom)", False, False, False, True),
            ("Users", "1", "5", "15", "Unlimited"),
            ("Support", "Email", "Email+Chat", "Priority", "24/7 Phone"),
        ]

        header = "| Feature | Essential | Plus | Premium | Ultimate |\n|---------|-----------|------|---------|----------|\n"
        rows = ""
        for feat in all_features:
            name = feat[0]
            vals = []
            for v in feat[1:]:
                if v is True:
                    vals.append("✅")
                elif v is False:
                    vals.append("—")
                else:
                    vals.append(str(v))
            rows += f"| {name} | {' | '.join(vals)} |\n"
        st.markdown(header + rows)

    # ── FAQ ──
    with st.expander("❓ Frequently Asked Questions", expanded=False):
        faqs = [
            ("Can I upgrade later?", "Yes! Upgrade anytime. You only pay the difference for the remaining period."),
            ("Is there a free trial?", "We offer a 7-day free demo of the Plus tier. Contact us to get started."),
            ("What payment methods?", "Bank transfer, UPI, credit/debit cards. Annual billing only."),
            ("Can I cancel anytime?", "Yes, cancel anytime. No refunds for unused period."),
            ("Do you offer custom plans?", "Yes! For enterprises with specific needs, contact us for a custom quote."),
            ("Is my data secure?", "Yes. All data is encrypted (Fernet), stored locally, with role-based access control."),
            ("What about updates?", "All plans include free updates and new features for the subscription period."),
            ("How many users?", "Essential: 1, Plus: 5, Premium: 15, Ultimate: Unlimited."),
        ]
        for q, a in faqs:
            st.markdown(f"**{q}**")
            st.markdown(a)
            st.markdown("")

    # ── Inquiry Form ──
    st.markdown("---")
    st.subheader("📞 Get Started — Request a Demo")

    fc1, fc2 = st.columns(2)
    with fc1:
        name = st.text_input("Your Name", key="sub_name")
        company = st.text_input("Company Name", key="sub_company")
        phone = st.text_input("Phone", key="sub_phone", placeholder="+91 98765 43210")
    with fc2:
        email = st.text_input("Email", key="sub_email")
        tier = st.selectbox("Interested In", ["Essential ₹14,999", "Plus ₹34,999", "Premium ₹64,999", "Ultimate ₹89,999"], index=1, key="sub_tier")
        message = st.text_area("Message (optional)", key="sub_msg", height=80)

    if st.button("Submit Inquiry", type="primary", use_container_width=True):
        if name and phone:
            saved = _save_inquiry({
                "name": name, "company": company, "phone": phone,
                "email": email, "tier": tier.split(" ")[0], "message": message,
            })
            if saved:
                st.success("Thank you! We'll contact you within 24 hours.")
                st.balloons()
            else:
                st.success("Thank you! Please call +91 7795242424 for immediate assistance.")
        else:
            st.warning("Please enter your name and phone number.")

    st.markdown("")
    st.markdown("""
<div style="text-align:center;font-size:0.8rem;color:#6B7280;padding:16px;">
Need help choosing? Call <strong>+91 7795242424</strong> | Email: princepshah@gmail.com<br>
PPS Anantams Corporation Pvt Ltd, Vadodara, Gujarat
</div>""", unsafe_allow_html=True)
