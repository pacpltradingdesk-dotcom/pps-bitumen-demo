from fpdf import FPDF
import datetime
import os
from company_config import COMPANY_PROFILE

LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pps_logo.png")

class QuoteGenerator(FPDF):
    def header(self):
        # Logo on left
        if os.path.exists(LOGO_PATH):
            self.image(LOGO_PATH, 10, 8, 25)
        
        # Title on right
        self.set_xy(40, 10)
        self.set_font('Arial', 'B', 14)
        self.set_fill_color(46, 64, 83)  # Dark blue
        self.set_text_color(255, 255, 255)  # White text
        self.cell(160, 10, 'OFFICIAL QUOTATION / PROFORMA', 0, 1, 'C', 1)
        self.set_text_color(0, 0, 0)  # Reset to black
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}  |  PPS Anantams Corporation Pvt Ltd  |  Computer Generated Document', 0, 0, 'C')

def get_next_quote_number():
    counter_file = "quote_counter.txt"
    if not os.path.exists(counter_file):
        with open(counter_file, "w") as f:
            f.write("100") 
    
    with open(counter_file, "r") as f:
        try:
            current = int(f.read().strip())
        except:
            current = 100
            
    next_current = current + 1
    
    with open(counter_file, "w") as f:
        f.write(str(next_current))
        
    return f"PPS/GUJARAT/25-26/{next_current:03d}"

def create_price_pdf(customer_name, product_type, source, price_pmt, filename="Quote.pdf", qty=1, quote_no="DRAFT", why_us_points=None):
    if why_us_points is None:
        why_us_points = [
            "Verified GPS-Tracked Fleet for 100% Quantity Assurance",
            "Sourced directly from PSU Refinery (No Re-processed Material)",
            "Guaranteed Dispatch within 24 Hours of Payment"
        ]

    pdf = QuoteGenerator()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    # --- BOX 1: SUPPLIER ---
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(95, 6, "SUPPLIER / CONSIGNOR:", 1, 0)
    # --- BOX 2: BUYER ---
    pdf.cell(95, 6, "BUYER / CONSIGNEE:", 1, 1)
    
    y_start = pdf.get_y()
    
    # LEFT COLUMN
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(95, 6, COMPANY_PROFILE['legal_name'], "LR", 1)
    pdf.set_font("Arial", '', 9)
    pdf.cell(95, 5, COMPANY_PROFILE['address_line1'], "LR", 1)
    pdf.cell(95, 5, COMPANY_PROFILE['address_line2'], "LR", 1)
    pdf.cell(95, 5, f"{COMPANY_PROFILE['city']} - {COMPANY_PROFILE['pincode']}, {COMPANY_PROFILE['state']}", "LR", 1)
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(95, 6, f"GSTIN: {COMPANY_PROFILE['gst_no']}", "LR", 1)
    pdf.cell(95, 6, f"CIN: {COMPANY_PROFILE['cin_no']}", "LRB", 0)
    
    # RIGHT COLUMN
    pdf.set_xy(105, y_start)
    
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(95, 6, customer_name, "R", 1)
    pdf.set_font("Arial", '', 9)
    pdf.set_x(105)
    pdf.cell(95, 5, "(Billing Address to be provided)", "R", 1)
    pdf.set_x(105)
    pdf.cell(95, 5, "State: ____________ Code: __", "R", 1)
    pdf.set_x(105)
    pdf.cell(95, 5, "Contact: Purchase Manager", "R", 1)
    pdf.set_x(105)
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(95, 6, f"GSTIN: _______________________", "R", 1)
    
    pdf.set_x(105)
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(95, 6, f"Quote No: {quote_no}", "R", 1) 
    pdf.set_x(105)
    pdf.set_font("Arial", '', 9)
    pdf.cell(95, 6, f"Date: {datetime.date.today().strftime('%d-%b-%Y')}", "R", 1)
    
    # VALIDITY BOX
    pdf.set_x(105)
    pdf.set_fill_color(255, 204, 204) # Light red
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(95, 6, "⚠️ RATE VALID FOR 24 HOURS ONLY", "RB", 1, 'C', 1)
    
    pdf.ln(5)

    # 2. Table Header
    pdf.set_fill_color(44, 62, 80) # Dark Blue
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(10, 8, "Sn", 1, 0, 'C', 1)
    pdf.cell(80, 8, "Description of Goods", 1, 0, 'C', 1)
    pdf.cell(25, 8, "HSN", 1, 0, 'C', 1)
    pdf.cell(25, 8, "Qty (MT)", 1, 0, 'C', 1)
    pdf.cell(25, 8, "Rate", 1, 0, 'C', 1)
    pdf.cell(25, 8, "Amount", 1, 1, 'C', 1)
    pdf.set_text_color(0, 0, 0) # Reset

    # 3. Table Rows
    pdf.set_font("Arial", '', 10)
    
    base_val = qty * price_pmt
    tax_amt = base_val * 0.18
    total_amt = base_val + tax_amt
    
    pdf.cell(10, 10, "1", 1, 0, 'C')
    pdf.cell(80, 10, f"{product_type} (Source: {source})", 1, 0, 'L')
    pdf.cell(25, 10, COMPANY_PROFILE['hsn_code'], 1, 0, 'C')
    pdf.cell(25, 10, f"{qty:.3f}", 1, 0, 'C')
    pdf.cell(25, 10, f"{price_pmt:,.2f}", 1, 0, 'R')
    pdf.cell(25, 10, f"{base_val:,.2f}", 1, 1, 'R')
    
    # Tax Row
    pdf.cell(10, 10, "", 1, 0, 'C')
    pdf.cell(80, 10, "IGST @ 18% (Applicable)", 1, 0, 'R')
    pdf.cell(25, 10, "", 1, 0, 'C')
    pdf.cell(25, 10, "", 1, 0, 'C')
    pdf.cell(25, 10, "18%", 1, 0, 'R')
    pdf.cell(25, 10, f"{tax_amt:,.2f}", 1, 1, 'R')

    # Total Row
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(165, 10, "TOTAL LANDED COST (INR)", 1, 0, 'R')
    pdf.cell(25, 10, f"{total_amt:,.2f}", 1, 1, 'R')

    pdf.ln(5)
    
    # --- SALES PERSUASION SECTION ---
    pdf.set_fill_color(230, 240, 255) # Light Blue
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 7, " Why Choose PPS Anantams? (Our Promise)", 1, 1, 'L', 1)
    pdf.set_font("Arial", '', 10)
    for point in why_us_points:
         pdf.cell(5, 6, chr(149), 0, 0) # Bullet
         pdf.cell(0, 6, point, 0, 1)
         
    pdf.ln(5)

    # 4. Bank Details
    y_before_bank = pdf.get_y()
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(90, 6, "Bank Details for RTGS/NEFT:", 0, 1)
    pdf.set_font("Arial", '', 10)
    pdf.cell(30, 6, "Bank Name:", 0, 0)
    pdf.cell(60, 6, COMPANY_PROFILE['bank_details']['bank_name'], 0, 1)
    
    pdf.cell(30, 6, "A/C No.:", 0, 0)
    pdf.cell(60, 6, COMPANY_PROFILE['bank_details']['ac_no'], 0, 1)
    
    pdf.cell(30, 6, "IFSC Code:", 0, 0)
    pdf.cell(60, 6, COMPANY_PROFILE['bank_details']['ifsc'], 0, 1)
    
    pdf.cell(30, 6, "Company PAN:", 0, 0)
    pdf.cell(60, 6, COMPANY_PROFILE['pan_no'], 0, 1)

    # 5. Terms
    pdf.set_xy(110, y_before_bank)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(80, 6, "Terms & Conditions:", 0, 1)
    pdf.set_font("Arial", '', 8)
    for term in COMPANY_PROFILE['terms']:
        pdf.set_x(110)
        pdf.multi_cell(80, 4, term, 0, 'L')

    try:
        pdf.output(filename)
        return True
    except Exception as e:
        print(f"PDF Error: {e}")
        return False

if __name__ == "__main__":
    create_price_pdf("Test Client", "Bitumen VG10", "Haldia", 41200)
