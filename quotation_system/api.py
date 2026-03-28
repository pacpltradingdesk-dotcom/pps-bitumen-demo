from fastapi import FastAPI, HTTPException, Depends
from sqlmodel import Session, select
from typing import List
from .models import Quotation, QuotationCreate, QuotationRead, QuotationItem
from .db import get_session, create_db_and_tables, engine
from .pdf_maker import generate_pdf
import os

app = FastAPI(title="Bitumen Quotation System", version="1.0")

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

@app.post("/quotations/", response_model=QuotationRead)
def create_quotation(quotation: QuotationCreate, session: Session = Depends(get_session)):
    # 1. Convert Pydantic to SQLModel
    db_quote = Quotation.from_orm(quotation)
    
    # 2. Add Items
    for item in quotation.items:
        db_item = QuotationItem.from_orm(item)
        db_quote.items.append(db_item) # Check relationship handling
    
    # 3. Calculate Totals (Server-side validation)
    subtotal = sum(i.quantity * i.rate + i.freight_rate + i.packing_rate for i in quotation.items)
    # simplified logic for demo, ideally we calc item.total_amount first
    
    session.add(db_quote)
    session.commit()
    session.refresh(db_quote)
    return db_quote

@app.get("/quotations/{qt_id}", response_model=QuotationRead)
def read_quotation(qt_id: int, session: Session = Depends(get_session)):
    quote = session.get(Quotation, qt_id)
    if not quote:
        raise HTTPException(status_code=404, detail="Quotation not found")
    return quote

@app.get("/quotations/{qt_id}/pdf")
def get_quotation_pdf(qt_id: int, session: Session = Depends(get_session)):
    quote = session.get(Quotation, qt_id)
    if not quote:
        raise HTTPException(status_code=404, detail="Quotation not found")
        
    filename = f"Quote_{quote.quote_number}.pdf"
    full_path = os.path.abspath(filename)
    
    generate_pdf(quote, full_path)
    
    from fastapi.responses import FileResponse
    return FileResponse(full_path, media_type='application/pdf', filename=filename)

@app.get("/quotations/latest-number")
def get_latest_number(session: Session = Depends(get_session)):
    # Logic to find max number
    # Simple query
    statement = select(Quotation).order_by(Quotation.id.desc()).limit(1)
    result = session.exec(statement).first()
    if result:
        return {"latest_quote_no": result.quote_number}
    return {"latest_quote_no": "None"}


# ── Share Link Routes ─────────────────────────────────────────────────────

@app.get("/share/{token}")
def serve_shared_content(token: str):
    """Serve content for a shareable link token."""
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from shareable_links_engine import get_share_link, render_shared_content

        link = get_share_link(token)
        if not link:
            from fastapi.responses import HTMLResponse
            return HTMLResponse(
                content="<html><body style='font-family:Inter,sans-serif;text-align:center;padding:60px;'>"
                        "<h1>Link Expired or Not Found</h1>"
                        "<p>This shared link is no longer active.</p>"
                        "<p><a href='https://wa.me/917795242424'>Contact PPS Anantams</a></p>"
                        "</body></html>",
                status_code=404
            )

        html = render_shared_content(link)
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=html)

    except ImportError:
        raise HTTPException(status_code=500, detail="Share engine not available")


@app.post("/share/create")
def create_share(page_name: str, content: dict = None, expiry_hours: int = 48):
    """Create a new shareable link."""
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from shareable_links_engine import create_share_link, generate_share_url

        token = create_share_link(page_name, content_json=content, expiry_hours=expiry_hours)
        url = generate_share_url(token)
        return {"token": token, "url": url, "expires_in_hours": expiry_hours}

    except ImportError:
        raise HTTPException(status_code=500, detail="Share engine not available")
