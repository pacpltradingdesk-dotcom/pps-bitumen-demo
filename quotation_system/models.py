from typing import Optional, List
from datetime import date
from sqlmodel import SQLModel, Field, Relationship
from pydantic import BaseModel

# --- Shared Schemas (Pydantic) ---

class QuotationBase(SQLModel):
    quote_number: str = Field(index=True, unique=True)
    quote_date: date
    valid_until: date
    
    # Seller Details (Snapshot)
    seller_name: str
    seller_address: str
    seller_gstin: str
    seller_email: Optional[str] = None
    seller_phone: Optional[str] = None
    
    # Buyer Details
    buyer_name: str
    buyer_address: str
    buyer_gstin: Optional[str] = None
    buyer_contact_person: Optional[str] = None
    project_name: Optional[str] = None
    
    # Commercial Terms
    delivery_terms: str  # e.g. "FOR Vadodara"
    payment_terms: str   # e.g. "100% Advance"
    dispatch_mode: str   # e.g. "By Road"
    
    # Totals
    subtotal: float = 0.0
    total_tax: float = 0.0
    freight_total: float = 0.0
    other_charges: float = 0.0
    grand_total: float = 0.0
    
    # Status
    status: str = "DRAFT" # DRAFT, FINAL, SENT

class Quotation(QuotationBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    items: List["QuotationItem"] = Relationship(back_populates="quotation")

class QuotationItemBase(SQLModel):
    product_name: str # e.g. "Bitumen VG-30"
    description: Optional[str] = None
    hsn_code: str = "27132000"
    
    quantity: float
    unit: str = "MT"
    
    rate: float
    
    # Taxes & Extras per item
    tax_rate: float = 18.0
    freight_rate: float = 0.0
    packing_rate: float = 0.0
    
    total_amount: float # Calculated

class QuotationItem(QuotationItemBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    quotation_id: Optional[int] = Field(default=None, foreign_key="quotation.id")
    quotation: Optional[Quotation] = Relationship(back_populates="items")

# --- API Models ---

class QuotationCreate(QuotationBase):
    items: List[QuotationItemBase]

class QuotationRead(QuotationBase):
    id: int
    items: List[QuotationItemBase]
