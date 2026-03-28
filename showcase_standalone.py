"""
PPS Anantam — Standalone Showcase Generator
==============================================
Generates a self-contained HTML page for sharing via URL or file.
Includes Open Graph meta tags for WhatsApp/LinkedIn previews.
"""
import json
import os
import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


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
            "city": "Vadodara",
            "state": "Gujarat",
            "full_address": "04, Signet plaza Tower-B, Third floor, Kunal cross road, Gotri, Vadodara-390021, Gujarat",
        }


def _get_live_rates():
    try:
        with open(os.path.join(BASE_DIR, "live_prices.json"), "r") as f:
            lp = json.load(f)
        return {
            "VG30 Bulk (Mumbai)": lp.get("DRUM_MUMBAI_VG30", 37000) - 2000,
            "VG30 Drum (Mumbai)": lp.get("DRUM_MUMBAI_VG30", 37000),
            "VG30 Bulk (Kandla)": lp.get("DRUM_KANDLA_VG30", 35500) - 2000,
            "VG30 Drum (Kandla)": lp.get("DRUM_KANDLA_VG30", 35500),
        }
    except Exception:
        return {"VG30 Bulk": 34000, "VG30 Drum": 36000, "VG10 Bulk": 35000, "VG10 Drum": 37000}


def generate_showcase_html():
    """Generate a complete standalone HTML showcase page."""
    co = _get_company()
    rates = _get_live_rates()
    today = datetime.date.today().strftime("%d %b %Y")
    phone = co.get("owner_mobile", "+91 7795242424")
    phone_clean = phone.replace(" ", "").replace("+", "")

    rates_rows = ""
    for grade, price in rates.items():
        rates_rows += f'<tr><td>{grade}</td><td style="text-align:right;font-weight:700;color:#059669;">₹{price:,}/MT</td></tr>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{co.get('short_name', 'PPS Anantams')} — Bitumen Trading</title>
<meta property="og:title" content="{co.get('short_name', 'PPS Anantams')} — India's Bitumen Experts">
<meta property="og:description" content="{co.get('experience_years', 24)} years | {co.get('contact_database_size', '24000'):,}+ contacts | Pan-India bitumen supply">
<meta property="og:type" content="website">
<meta name="description" content="PPS Anantams Corporation — Leading bitumen trading platform. VG30, VG10, CRMB, PMB. Best rates across India.">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:Inter,-apple-system,Segoe UI,sans-serif;background:#F8FAFC;color:#1E293B}}
.hero{{background:linear-gradient(135deg,#1E1B4B 0%,#312E81 50%,#4F46E5 100%);color:#fff;padding:48px 24px;text-align:center}}
.hero h1{{font-size:1.8rem;font-weight:900}}
.hero .sub{{color:#C7D2FE;margin-top:8px;font-size:1rem}}
.hero .loc{{color:#A5B4FC;font-size:0.85rem;margin-top:4px}}
.badges{{margin-top:16px;display:flex;justify-content:center;gap:10px;flex-wrap:wrap}}
.badge{{background:rgba(255,255,255,0.15);padding:6px 14px;border-radius:20px;font-size:0.8rem;font-weight:600}}
.container{{max-width:800px;margin:0 auto;padding:24px}}
.section{{margin-bottom:32px}}
.section h2{{font-size:1.3rem;font-weight:800;border-bottom:2px solid #4F46E5;padding-bottom:8px;margin-bottom:16px}}
.products{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}}
.prod{{background:#fff;border:1px solid #E5E7EB;border-radius:12px;padding:16px;text-align:center}}
.prod .name{{font-size:1rem;font-weight:800;color:#4F46E5}}
.prod .desc{{font-size:0.78rem;color:#6B7280;margin-top:4px}}
table{{width:100%;border-collapse:collapse}}
th{{background:#F9FAFB;padding:10px 14px;text-align:left;font-weight:700;font-size:0.85rem;border-bottom:2px solid #E5E7EB}}
td{{padding:10px 14px;border-bottom:1px solid #F3F4F6;font-size:0.85rem}}
.stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}}
.stat{{background:#fff;border:1px solid #E5E7EB;border-radius:12px;padding:18px;text-align:center}}
.stat .num{{font-size:1.5rem;font-weight:900;color:#4F46E5}}
.stat .lbl{{font-size:0.78rem;color:#6B7280;margin-top:4px}}
.contact{{background:#1E1B4B;color:#fff;border-radius:12px;padding:24px;display:flex;justify-content:space-around;flex-wrap:wrap;gap:16px;text-align:center}}
.contact a{{color:#C7D2FE;text-decoration:none;font-weight:600}}
.contact a:hover{{color:#fff}}
.footer{{background:#F9FAFB;border:1px solid #E5E7EB;border-radius:12px;padding:20px;font-size:0.75rem;color:#6B7280;text-align:center;margin-top:24px}}
.cta{{display:inline-block;background:#4F46E5;color:#fff;padding:12px 32px;border-radius:8px;font-weight:700;text-decoration:none;margin-top:16px}}
.cta:hover{{background:#4338CA}}
@media(max-width:768px){{.products,.stats{{grid-template-columns:repeat(2,1fr)}}.contact{{flex-direction:column}}}}
</style>
</head>
<body>
<div class="hero">
<h1>{co.get('legal_name', 'PPS Anantams Corporation Pvt Ltd')}</h1>
<div class="sub">{co.get('business_role', 'Commission Agent + Logistics Arranger')}</div>
<div class="loc">{co.get('city', 'Vadodara')}, {co.get('state', 'Gujarat')} — India</div>
<div class="badges">
<span class="badge">🏆 {co.get('experience_years', 24)} Years</span>
<span class="badge">📞 {co.get('contact_database_size', '24,000'):,}+ Contacts</span>
<span class="badge">🇮🇳 Pan-India</span>
<span class="badge">🚢 8 Terminals</span>
</div>
<a href="https://wa.me/{phone_clean}?text=Hi%20PPS%20Anantams%2C%20I%20need%20a%20bitumen%20quote" class="cta" style="margin-top:20px;">Request Quote on WhatsApp</a>
</div>

<div class="container">
<div class="section">
<h2>Our Products</h2>
<div class="products">
<div class="prod"><div style="font-size:1.3rem">🛣️</div><div class="name">VG-30</div><div class="desc">Highway paving — highest demand</div></div>
<div class="prod"><div style="font-size:1.3rem">🌧️</div><div class="name">VG-10</div><div class="desc">Cold regions & surface dressing</div></div>
<div class="prod"><div style="font-size:1.3rem">🔥</div><div class="name">VG-40</div><div class="desc">Heavy traffic zones</div></div>
<div class="prod"><div style="font-size:1.3rem">♻️</div><div class="name">CRMB-55</div><div class="desc">Crumb Rubber Modified</div></div>
<div class="prod"><div style="font-size:1.3rem">🏗️</div><div class="name">CRMB-60</div><div class="desc">Bridges & expressways</div></div>
<div class="prod"><div style="font-size:1.3rem">⚡</div><div class="name">PMB</div><div class="desc">Polymer Modified</div></div>
</div>
</div>

<div class="section">
<h2>Today's Indicative Rates ({today})</h2>
<table>
<thead><tr><th>Grade & Location</th><th style="text-align:right">Rate</th></tr></thead>
<tbody>{rates_rows}</tbody>
</table>
<p style="font-size:0.75rem;color:#6B7280;margin-top:8px;">* Ex-Terminal/Warehouse. GST 18% extra. 100% advance. 24hr validity.</p>
</div>

<div class="section">
<h2>Why PPS Anantams?</h2>
<div class="stats">
<div class="stat"><div class="num">{co.get('experience_years', 24)}+</div><div class="lbl">Years Experience</div></div>
<div class="stat"><div class="num">24K+</div><div class="lbl">Industry Contacts</div></div>
<div class="stat"><div class="num">8</div><div class="lbl">Import Terminals</div></div>
<div class="stat"><div class="num">50+</div><div class="lbl">Source Points</div></div>
</div>
</div>

<div class="section">
<h2>Get in Touch</h2>
<div class="contact">
<div><div style="font-size:0.75rem;color:#A5B4FC;">Call</div><a href="tel:{phone}">{phone}</a></div>
<div><div style="font-size:0.75rem;color:#A5B4FC;">WhatsApp</div><a href="https://wa.me/{phone_clean}">Chat Now</a></div>
<div><div style="font-size:0.75rem;color:#A5B4FC;">Email</div><a href="mailto:{co.get('owner_email', '')}">{co.get('owner_email', '')}</a></div>
<div><div style="font-size:0.75rem;color:#A5B4FC;">Office</div><span style="font-size:0.85rem;">{co.get('city', 'Vadodara')}, {co.get('state', 'Gujarat')}</span></div>
</div>
</div>

<div class="footer">
<strong>{co.get('legal_name', 'PPS Anantams Corporation Pvt Ltd')}</strong><br>
GST: {co.get('gst_no', '')} | HSN: 27132000 | Terms: 100% Advance | 24hr Validity<br>
<span style="margin-top:6px;display:inline-block;">© {co.get('short_name', 'PPS Anantams')} — Powered by AI</span>
</div>
</div>
</body>
</html>"""
    return html


def save_showcase_html(filepath=None):
    """Save showcase HTML to a file."""
    if not filepath:
        filepath = os.path.join(BASE_DIR, "showcase_page.html")
    html = generate_showcase_html()
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    return filepath


def generate_qr_code(url, filepath=None):
    """Generate a QR code PNG for the given URL."""
    if not filepath:
        filepath = os.path.join(BASE_DIR, "showcase_qr.png")
    try:
        import qrcode
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#1E1B4B", back_color="white")
        img.save(filepath)
        return filepath
    except ImportError:
        return None
