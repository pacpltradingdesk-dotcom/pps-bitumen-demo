from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import inch, mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

import os

LOGO_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pps_logo.png")

def generate_pdf(quotation, filename):
    """
    Generates a professional PDF quotation using ReportLab Platypus.
    quotation: Instance of Quotation model (with items)
    filename: Output path
    """
    
    doc = SimpleDocTemplate(filename, pagesize=A4,
                            rightMargin=15*mm, leftMargin=15*mm,
                            topMargin=15*mm, bottomMargin=15*mm)
    
    elements = []
    
    styles = getSampleStyleSheet()
    
    # Custom Styles
    style_title = ParagraphStyle('Title', parent=styles['Heading1'], alignment=TA_CENTER, fontSize=16, spaceAfter=20)
    style_normal = styles['Normal']
    style_bold = ParagraphStyle('Bold', parent=styles['Normal'], fontName='Helvetica-Bold')
    style_right = ParagraphStyle('Right', parent=styles['Normal'], alignment=TA_RIGHT)
    
    # --- HEADER WITH LOGO ---
    if os.path.exists(LOGO_PATH):
        logo = Image(LOGO_PATH, width=40*mm, height=20*mm)
        elements.append(logo)
    
    elements.append(Paragraph("QUOTATION / PROFORMA INVOICE", style_title))
    
    # Supplier & Buyer Box
    
    # Seller Text
    seller_text = [
        Paragraph(f"<b>{quotation.seller_name}</b>", style_normal),
        Paragraph(quotation.seller_address, style_normal),
        Paragraph(f"GSTIN: {quotation.seller_gstin}", style_normal),
        Paragraph(f"Email: {quotation.seller_email or ''}", style_normal),
    ]
    
    # Buyer Text
    buyer_text = [
        Paragraph(f"<b>To: {quotation.buyer_name}</b>", style_normal),
        Paragraph(quotation.buyer_address, style_normal),
        Paragraph(f"GSTIN: {quotation.buyer_gstin or 'N/A'}", style_normal),
        Paragraph(f"Attn: {quotation.buyer_contact_person or ''}", style_normal),
    ]
    
    # Meta Data
    meta_text = [
        Paragraph(f"<b>Quote No:</b> {quotation.quote_number}", style_normal),
        Paragraph(f"<b>Date:</b> {quotation.quote_date}", style_normal),
        Paragraph(f"<b>Valid Until:</b> {quotation.valid_until}", style_normal),
    ]
    
    # Layout Table
    data = [
        ["SUPPLIER", "BUYER", "DETAILS"],
        [seller_text, buyer_text, meta_text]
    ]
    
    t = Table(data, colWidths=[2.3*inch, 2.3*inch, 2.3*inch])
    t.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 6),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
    ]))
    
    elements.append(t)
    elements.append(Spacer(1, 20))
    
    # --- ITEMS TABLE ---
    item_header = ["Sn", "Description", "HSN", "Qty", "Rate", "Tax%", "Amount"]
    
    item_data = [item_header]
    
    for idx, item in enumerate(quotation.items):
        row = [
            str(idx+1),
            Paragraph(f"<b>{item.product_name}</b><br/>{item.description or ''}", style_normal),
            item.hsn_code,
            f"{item.quantity} {item.unit}",
            f"{item.rate:,.2f}",
            f"{item.tax_rate}%",
            f"{item.total_amount:,.2f}"
        ]
        item_data.append(row)
    
    # Totals
    item_data.append(["", "", "", "", "Subtotal:", "", f"{quotation.subtotal:,.2f}"])
    item_data.append(["", "", "", "", "Tax Total:", "", f"{quotation.total_tax:,.2f}"])
    item_data.append(["", "", "", "", "Grand Total:", "", f"{quotation.grand_total:,.2f}"])
    
    col_widths = [0.4*inch, 2.5*inch, 0.8*inch, 0.8*inch, 1.0*inch, 0.6*inch, 1.2*inch]
    
    t_items = Table(item_data, colWidths=col_widths)
    t_items.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-2), 0.5, colors.grey),
        ('BOX', (0,0), (-1,-1), 1, colors.black),
        ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('ALIGN', (3,0), (-1,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LINEABOVE', (-3,-3), (-1,-1), 1, colors.black),
        ('FONTNAME', (-3,-1), (-1,-1), 'Helvetica-Bold'),
    ]))
    
    elements.append(t_items)
    elements.append(Spacer(1, 20))
    
    # --- TERMS & BANK ---
    
    terms_content = [
        Paragraph("<b>Terms & Conditions:</b>", style_bold),
        Paragraph(f"1. Delivery: {quotation.delivery_terms}", style_normal),
        Paragraph(f"2. Payment: {quotation.payment_terms}", style_normal),
        Paragraph(f"3. Dispatch: {quotation.dispatch_mode}", style_normal),
        Paragraph("4. Taxes: As applicable at time of supply.", style_normal),
        Paragraph("5. Disputes: Subject to Vadodara Jurisdiction.", style_normal),
    ]
    
    bank_content = [
        Paragraph("<b>Bank Details:</b>", style_bold),
        Paragraph("Bank: ICICI BANK", style_normal),
        Paragraph("A/c: 184105001402", style_normal),
        Paragraph("IFSC: ICIC0001841", style_normal),
        Paragraph("Branch: Vadodara", style_normal),
    ]
    
    term_table = Table([[terms_content, bank_content]], colWidths=[4*inch, 3*inch])
    term_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('PADDING', (0,0), (-1,-1), 10),
    ]))
    
    elements.append(term_table)
    elements.append(Spacer(1, 30))
    
    # --- SIGNATURE ---
    sig_data = [[Paragraph("For, PPS Anantams Corporation Pvt Ltd", style_bold)],
                [Spacer(1, 40)],
                [Paragraph("Authorized Signatory", style_normal)]]
    
    sig_table = Table(sig_data, colWidths=[3*inch], hAlign='RIGHT')
    elements.append(sig_table)
    
    # Build
    doc.build(elements)
    return filename
