"""
PPS Anantam — PDF Brochure Generator
=======================================
Generates a professional A4 company brochure PDF.
Pages: Cover → About → Products → Rates → Why PPS → Contact
"""
import os
import json
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


def _get_live_rates():
    try:
        with open(os.path.join(BASE_DIR, "live_prices.json"), "r") as f:
            lp = json.load(f)
        return {
            "VG30 Bulk (Mumbai)": lp.get("DRUM_MUMBAI_VG30", 37000) - 2000,
            "VG30 Drum (Mumbai)": lp.get("DRUM_MUMBAI_VG30", 37000),
            "VG30 Bulk (Kandla)": lp.get("DRUM_KANDLA_VG30", 35500) - 2000,
            "VG30 Drum (Kandla)": lp.get("DRUM_KANDLA_VG30", 35500),
            "VG10 Bulk (Mumbai)": lp.get("DRUM_MUMBAI_VG10", 38000) - 2000,
            "VG10 Drum (Mumbai)": lp.get("DRUM_MUMBAI_VG10", 38000),
        }
    except Exception:
        return {"VG30 Bulk": 34000, "VG30 Drum": 36000, "VG10 Bulk": 35000, "VG10 Drum": 37000}


def generate_brochure(output_path=None):
    """Generate the company brochure PDF. Returns the file path."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm, cm
        from reportlab.lib.colors import HexColor
        from reportlab.pdfgen import canvas
        from reportlab.lib.styles import getSampleStyleSheet
    except ImportError:
        return None

    if not output_path:
        output_path = os.path.join(BASE_DIR, "pdf_exports", "PPS_Company_Brochure.pdf")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    co = _get_company()
    rates = _get_live_rates()
    today = datetime.date.today().strftime("%d %b %Y")
    w, h = A4

    c = canvas.Canvas(output_path, pagesize=A4)

    # Colors
    INDIGO = HexColor("#4F46E5")
    DARK = HexColor("#1E1B4B")
    WHITE = HexColor("#FFFFFF")
    GRAY = HexColor("#6B7280")
    GREEN = HexColor("#059669")
    LIGHT_BG = HexColor("#F8FAFC")

    # ── Page 1: Cover ──
    c.setFillColor(DARK)
    c.rect(0, 0, w, h, fill=1, stroke=0)

    # Gradient-like effect with overlay rectangle
    c.setFillColor(INDIGO)
    c.rect(0, h * 0.3, w, h * 0.4, fill=1, stroke=0)

    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(w / 2, h * 0.6, co.get("short_name", "PPS Anantams"))

    c.setFont("Helvetica", 14)
    c.drawCentredString(w / 2, h * 0.55, "Corporation Private Limited")

    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(w / 2, h * 0.45, "India's Trusted Bitumen Trading Partner")

    c.setFont("Helvetica", 11)
    c.drawCentredString(w / 2, h * 0.38, f"{co.get('city', 'Vadodara')}, {co.get('state', 'Gujarat')} | Since 2002")

    c.setFont("Helvetica", 10)
    c.drawCentredString(w / 2, h * 0.15, f"Brochure Date: {today}")
    c.drawCentredString(w / 2, h * 0.12, f"Contact: {co.get('owner_mobile', '+91 7795242424')}")

    c.showPage()

    # ── Page 2: About Us ──
    c.setFillColor(DARK)
    c.rect(0, h - 60, w, 60, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(30, h - 40, "About PPS Anantams")

    y = h - 100
    c.setFillColor(HexColor("#111827"))
    c.setFont("Helvetica-Bold", 12)
    c.drawString(30, y, co.get("legal_name", ""))
    y -= 25

    about_lines = [
        f"Owner: {co.get('owner_name', 'PRINCE P SHAH')}",
        f"Experience: {co.get('experience_years', 24)}+ years in bitumen trading",
        f"Contact Database: {co.get('contact_database_size', '24,000'):,}+ industry contacts",
        f"Role: {co.get('business_role', 'Commission Agent + Logistics Arranger')}",
        "",
        "We connect buyers with the best bitumen sources across India —",
        "PSU Refineries (IOCL, HPCL, BPCL), Import Terminals (8 major ports),",
        "and Decanter Plants. Our AI-powered platform ensures you get",
        "the best landed cost for every delivery.",
        "",
        f"Office: {co.get('full_address', '')}",
    ]

    c.setFont("Helvetica", 10)
    for line in about_lines:
        c.drawString(30, y, line)
        y -= 18

    # Stats boxes
    y -= 20
    stats = [("24+", "Years"), ("24K+", "Contacts"), ("8", "Terminals"), ("50+", "Sources")]
    box_w = (w - 80) / 4
    for i, (num, label) in enumerate(stats):
        x = 30 + i * (box_w + 10)
        c.setFillColor(LIGHT_BG)
        c.roundRect(x, y - 50, box_w, 60, 8, fill=1, stroke=0)
        c.setFillColor(INDIGO)
        c.setFont("Helvetica-Bold", 20)
        c.drawCentredString(x + box_w / 2, y - 15, num)
        c.setFillColor(GRAY)
        c.setFont("Helvetica", 9)
        c.drawCentredString(x + box_w / 2, y - 35, label)

    c.showPage()

    # ── Page 3: Products & Rates ──
    c.setFillColor(DARK)
    c.rect(0, h - 60, w, 60, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(30, h - 40, "Products & Today's Rates")

    y = h - 90
    products = [
        ("VG-30", "Highway paving — highest demand grade (~60% market share)"),
        ("VG-10", "Cold regions & surface dressing — spraying applications"),
        ("VG-40", "Heavy traffic zones — premium durability"),
        ("CRMB-55", "Crumb Rubber Modified — eco-friendly, crack resistant"),
        ("CRMB-60", "High-stress zones — bridges, expressways"),
        ("PMB", "Polymer Modified — extreme weather performance"),
    ]

    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(HexColor("#111827"))
    c.drawString(30, y, "Bitumen Grades We Supply:")
    y -= 25

    for grade, desc in products:
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(INDIGO)
        c.drawString(40, y, grade)
        c.setFont("Helvetica", 9)
        c.setFillColor(GRAY)
        c.drawString(110, y, desc)
        y -= 20

    y -= 20
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(HexColor("#111827"))
    c.drawString(30, y, f"Indicative Rates ({today}):")
    y -= 25

    # Rates table
    c.setFillColor(LIGHT_BG)
    c.roundRect(30, y - len(rates) * 22 - 10, w - 60, len(rates) * 22 + 35, 8, fill=1, stroke=0)

    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(HexColor("#374151"))
    c.drawString(45, y, "Grade & Location")
    c.drawRightString(w - 45, y, "Rate (₹/MT)")
    y -= 18

    c.setFont("Helvetica", 9)
    for grade, price in rates.items():
        c.setFillColor(HexColor("#374151"))
        c.drawString(45, y, grade)
        c.setFillColor(GREEN)
        c.drawRightString(w - 45, y, f"₹{price:,}/MT")
        y -= 20

    y -= 10
    c.setFont("Helvetica", 8)
    c.setFillColor(GRAY)
    c.drawString(30, y, "* Ex-Terminal/Warehouse. GST 18% extra. 100% advance. 24hr validity. HSN: 27132000")

    c.showPage()

    # ── Page 4: Contact & Bank Details ──
    c.setFillColor(DARK)
    c.rect(0, h - 60, w, 60, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(30, h - 40, "Contact & Banking")

    y = h - 100
    c.setFillColor(HexColor("#111827"))

    contact_lines = [
        ("Contact Person:", co.get("owner_name", "")),
        ("Phone:", co.get("owner_mobile", "")),
        ("Email:", co.get("owner_email", "")),
        ("Office:", co.get("full_address", "")),
        ("", ""),
        ("GST No:", co.get("gst_no", "")),
        ("PAN:", co.get("pan_no", "")),
        ("CIN:", co.get("cin_no", "")),
    ]

    for label, value in contact_lines:
        if label:
            c.setFont("Helvetica-Bold", 10)
            c.drawString(30, y, label)
            c.setFont("Helvetica", 10)
            c.drawString(150, y, str(value))
        y -= 20

    # Bank details
    bank = co.get("bank_details", {})
    y -= 10
    c.setFont("Helvetica-Bold", 12)
    c.drawString(30, y, "Bank Details:")
    y -= 25

    bank_lines = [
        ("Bank:", bank.get("bank_name", "ICICI BANK")),
        ("A/C No:", bank.get("ac_no", "184105001402")),
        ("IFSC:", bank.get("ifsc", "ICIC0001841")),
        ("Branch:", bank.get("branch", "Vadodara")),
    ]

    for label, value in bank_lines:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(30, y, label)
        c.setFont("Helvetica", 10)
        c.drawString(150, y, str(value))
        y -= 20

    # Footer
    y -= 30
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(INDIGO)
    c.drawCentredString(w / 2, y, "Thank you for your interest in PPS Anantams!")
    y -= 20
    c.setFont("Helvetica", 9)
    c.setFillColor(GRAY)
    c.drawCentredString(w / 2, y, f"Call {co.get('owner_mobile', '')} for best rates | WhatsApp available")

    c.save()
    return output_path
