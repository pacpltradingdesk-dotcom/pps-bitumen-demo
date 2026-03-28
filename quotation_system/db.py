from sqlmodel import SQLModel, create_engine, Session
import os

# SQLite Database File
DATABASE_FILE = "quotations.db"
DATABASE_URL = f"sqlite:///{DATABASE_FILE}"

engine = create_engine(DATABASE_URL, echo=False)

def create_db_and_tables():
    from .models import Quotation, QuotationItem
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
