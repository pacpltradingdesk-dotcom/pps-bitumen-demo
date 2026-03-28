
# Supplier/Party Master - Extensive Category Support
import pandas as pd
import json
import os

# ============ CATEGORY DEFINITIONS ============

SUPPLIER_CATEGORIES = [
    "Exporter of Gulf",
    "Importer of India",
    "India Mfg (Refinery/Plant)",
    "Big Trader",
    "Smaller Trader", # Changed from 'Small Trader' to match existing if needed, but 'Small Trader' is fine. sticking to user request.
    "Decanter Owner"
]

CUSTOMER_CATEGORIES = [
    "Big Trader",
    "Small Trader",
    "Big Contractor",
    "Small Contractor", 
    "Local Trader",
    "Commission Agent",
    "Decanter Owner"
]

SERVICE_CATEGORIES = [
    "Tank Terminal",
    "Port CFS",
    "Bitumen Decanter",
    "Transporter - Bulk",
    "Transporter - Drum/Truck", 
    "CHA / Clearing Agent",
    "Loading Contact"
]

# ============ EXISTING DATA (migrated) ============
# Keeping these for backward compatibility initialization
BULK_IMPORTERS = [
    {"name": "KOTAK PETROLEUM LLP", "qty_mt": 38343, "type": "Indian Importer - Bulk", "city": "Mumbai", "contact": "", "gstin": "", "marked_for_purchase": True},
    {"name": "AGARWAL INDUSTRIAL CORPORATION LTD", "qty_mt": 27600, "type": "Indian Importer - Bulk", "city": "Mumbai", "contact": "", "gstin": "", "marked_for_purchase": True},
    {"name": "NEPTUNE PETROCHEMICALS LTD", "qty_mt": 21877, "type": "Indian Importer - Bulk", "city": "Mumbai", "contact": "", "gstin": "", "marked_for_purchase": True},
    {"name": "PREMIUM PETRO AND INFRA PROJECTS PVT LTD", "qty_mt": 14054, "type": "Indian Importer - Bulk", "city": "Kandla", "contact": "", "gstin": "", "marked_for_purchase": True},
    {"name": "SADASHIVA OVERSEAS LTD", "qty_mt": 11788, "type": "Indian Importer - Bulk", "city": "Kandla", "contact": "", "gstin": "", "marked_for_purchase": True},
    {"name": "INDIAN OIL CORPORATION LTD", "qty_mt": 10282, "type": "Indian Importer - Bulk", "city": "Multiple", "contact": "", "gstin": "", "marked_for_purchase": True},
]

DRUM_IMPORTERS_LEGACY = [
    {"name": "FINE LUBRICANTS", "qty_mt": 9853, "type": "Indian Importer - Drum", "city": "Mumbai"},
    {"name": "PRAKRUTEES INFRA IMPEX INDIA PVT LTD", "qty_mt": 8837, "type": "Indian Importer - Drum", "city": "Mumbai"},
    {"name": "CHER LIFE HEALTHCARE PVT LTD", "qty_mt": 8345, "type": "Indian Importer - Drum", "city": "Mumbai"},
    {"name": "TOTAL VENTURE SOLUTIONS", "qty_mt": 8205, "type": "Indian Importer - Drum", "city": "Mumbai"},
    {"name": "FUTURE UNIVERSAL PETROCHEM PVT LTD", "qty_mt": 7752, "type": "Indian Importer - Drum", "city": "Kandla"},
]
# Mapping legacy "Drum" type to new category for existing functions
def map_legacy_type(p_type):
    if p_type == "Bulk" or p_type == "Bulk/PSU": return "Indian Importer - Bulk"
    if p_type == "Drum": return "Indian Importer - Drum"
    return p_type

# ============ FILE PATHS ============
PURCHASE_PARTY_FILE = "purchase_parties.json" # Suppliers
SALES_PARTY_FILE = "sales_parties.json"       # Customers
SERVICE_PARTY_FILE = "service_providers.json" # Logistics & Services

# ============ GENERIC IO FUNCTIONS ============

def load_json_file(filepath, default_data=[]):
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except:
            return default_data
    return default_data

def save_json_file(filepath, data):
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

# ============ SPECIFIC LOAD/SAVE FUNCTIONS ============

def load_suppliers():
    data = load_json_file(PURCHASE_PARTY_FILE)
    if not data:
        # Initialize with legacy data if empty
        data = BULK_IMPORTERS + DRUM_IMPORTERS_LEGACY
        # Ensure types are updated
        for p in data:
            if p['type'] == 'Bulk' or p['type'] == 'Bulk/PSU': p['type'] = "Indian Importer - Bulk"
            if p['type'] == 'Drum': p['type'] = "Indian Importer - Drum"
    return data

def save_suppliers(parties):
    save_json_file(PURCHASE_PARTY_FILE, parties)

def load_customers():
    return load_json_file(SALES_PARTY_FILE)

def save_customers(parties):
    save_json_file(SALES_PARTY_FILE, parties)

def load_services():
    return load_json_file(SERVICE_PARTY_FILE)

def save_services(parties):
    save_json_file(SERVICE_PARTY_FILE, parties)

# ============ ADD FUNCTIONS ============

def add_supplier(name, category, city, contact="", gstin="", details="",
                  email="", whatsapp_number=""):
    parties = load_suppliers()
    new_party = {
        "name": name,
        "type": category,
        "city": city,
        "contact": contact,
        "gstin": gstin,
        "details": details, # For extra info like loading person
        "marked_for_purchase": True,
        "qty_mt": 0, # Default
        "email": email,
        "whatsapp_number": whatsapp_number,
    }
    parties.append(new_party)
    save_suppliers(parties)
    return new_party

def add_customer(name, category, city, state, contact="", gstin="", address="",
                 email="", whatsapp_number=""):
    parties = load_customers()

    # Check if exists
    existing = next((p for p in parties if p['name'].lower() == name.lower().strip()), None)

    if existing:
        # Update existing
        existing['category'] = category
        existing['city'] = city
        existing['state'] = state
        if contact: existing['contact'] = contact
        if gstin: existing['gstin'] = gstin
        if address: existing['address'] = address
        if email: existing['email'] = email
        if whatsapp_number: existing['whatsapp_number'] = whatsapp_number
        save_customers(parties)
        return existing
    else:
        # Create new
        new_party = {
            "name": name,
            "category": category,
            "city": city,
            "state": state,
            "contact": contact,
            "gstin": gstin,
            "address": address,
            "email": email,
            "whatsapp_number": whatsapp_number,
            "active": True
        }
        parties.append(new_party)
        save_customers(parties)
        return new_party

def add_service_provider(name, category, city, contact="", details=""):
    parties = load_services()
    new_party = {
        "name": name,
        "category": category,
        "city": city,
        "contact": contact,
        "details": details 
    }
    parties.append(new_party)
    save_services(parties)
    return new_party

# ============ ACCESSOR FUNCTIONS (COMPATIBILITY) ============

def get_bulk_purchase_options():
    """Get only bulk importers marked for purchase."""
    parties = load_suppliers()
    # Match both legacy and new category names for safety
    return [p for p in parties if p['type'] in ['Bulk', 'Bulk/PSU', 'Indian Importer - Bulk'] and p.get('marked_for_purchase', True)]

def get_drum_purchase_options():
    """Get all drum importers."""
    parties = load_suppliers()
    return [p for p in parties if p['type'] in ['Drum', 'Indian Importer - Drum'] and p.get('marked_for_purchase', True)]

def import_sales_from_excel(file_path, default_category="Contractor - City/Municipal"):
    """Import customers from Excel with Smart Merge (Update existing)."""
    try:
        df = pd.read_excel(file_path)
        parties = load_customers()
        
        added_count = 0
        updated_count = 0
        
        for _, row in df.iterrows():
            name = str(row.get('Company Name', row.get('Name', ''))).strip()
            if not name or name.lower() == 'nan': continue
            
            # Determine Category
            category = default_category
            if 'Category' in df.columns and pd.notna(row['Category']):
                category = str(row['Category']).strip()
                
            # Prepare new data
            new_data = {
                "name": name,
                "category": category,
                "city": str(row.get('City', '')).strip(),
                "state": str(row.get('State', '')).strip(),
                "contact": str(row.get('Contact', row.get('Phone', row.get('Mobile', '')))).strip(),
                "gstin": str(row.get('GSTIN', row.get('GST', ''))).strip(),
                "address": str(row.get('Address', '')).strip(),
                "active": True
            }
            
            # Check if exists
            existing_party = next((p for p in parties if p['name'].lower() == name.lower()), None)
            
            if existing_party:
                # MERGE LOGIC: Update fields if new data is present
                updated = False
                if new_data['contact'] and new_data['contact'] != 'nan':
                     existing_party['contact'] = new_data['contact']
                     updated = True
                if new_data['gstin'] and new_data['gstin'] != 'nan':
                     existing_party['gstin'] = new_data['gstin']
                     updated = True
                if new_data['address'] and new_data['address'] != 'nan':
                     existing_party['address'] = new_data['address']
                     updated = True
                if new_data['city'] and new_data['city'] != 'nan':
                     existing_party['city'] = new_data['city']
                     updated = True
                if 'Category' in df.columns: # Only update category if explicitly provided in file
                     existing_party['category'] = new_data['category']
                     updated = True
                     
                if updated: updated_count += 1
            else:
                parties.append(new_data)
                added_count += 1
        
        save_customers(parties)
        return f"{added_count} Added, {updated_count} Updated", "Success"
    except Exception as e:
        return 0, str(e)

def toggle_purchase_party(party_name, marked):
    parties = load_suppliers()
    for p in parties:
        if p['name'] == party_name:
            p['marked_for_purchase'] = marked
            break
    save_suppliers(parties)
