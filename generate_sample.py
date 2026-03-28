from quotation_system.models import Quotation, QuotationItem
from quotation_system.pdf_maker import generate_pdf
import datetime

# Create a sample quote
quote = Quotation(
    quote_number="PPS/GUJ/SAMPLE/001",
    quote_date=datetime.date.today(),
    valid_until=datetime.date.today() + datetime.timedelta(days=1),
    seller_name="PPS Anantams Corporation Pvt. Ltd.",
    seller_address="04, Signet plaza Tower- B, Vadodara-390021",
    seller_gstin="24AAHCV1611L2ZD",
    buyer_name="Demo Client Constructions",
    buyer_address="123 Business Park, Ahmedabad",
    delivery_terms="FOR Ahmedabad",
    payment_terms="100% Advance",
    dispatch_mode="Road",
    subtotal=100000.0,
    total_tax=18000.0,
    grand_total=118000.0,
    status="DRAFT"
)

quote.items = [
    QuotationItem(
        product_name="Bitumen VG30 (Bulk)",
        description="Source: Koyali Refinery",
        quantity=20.0,
        rate=5000.0,
        total_amount=100000.0
    )
]

# Generate
filename = "Sample_Showcase_Quote.pdf"
generate_pdf(quote, filename)
print(f"Generated {filename}")
