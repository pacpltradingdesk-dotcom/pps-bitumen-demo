
import json
import os
import datetime
import uuid
from datetime import timedelta

# --- CONFIGURATION ---
SOS_FILE = "sos_opportunities.json"

# --- CORE SOS LOGIC ---

def load_sos_data():
    if os.path.exists(SOS_FILE):
        try:
            with open(SOS_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_sos_data(data):
    with open(SOS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def create_sos_opportunity(location, product, old_price, new_price):
    """
    Creates a new SOS Opportunity if price drop > threshold.
    """
    saving = old_price - new_price
    if saving < 200: return None # Threshold rule
    
    opp = {
        "id": str(uuid.uuid4())[:8],
        "location": location,
        "product": product,
        "old_price": old_price,
        "new_price": new_price,
        "saving": saving,
        "valid_until": (datetime.datetime.now() + timedelta(hours=48)).strftime("%Y-%m-%d %H:%M"),
        "status": "Active",
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "target_customers": find_matching_customers(location, product)
    }
    
    data = load_sos_data()
    data.append(opp)
    save_sos_data(data)
    return opp

def find_matching_customers(location, product):
    """
    Finds customers in the specific location/city.
    """
    from party_master import load_customers
    all_c = load_customers()
    
    matches = []
    # Normalize comparison to lower case strip
    target_loc = location.lower().strip()
    
    for c in all_c:
        # Strict match on City
        c_city = c.get('city', '').lower().strip()
        
        # Include if city contains target (e.g. "Ahmedabad" in "Ahmedabad GIDC")
        if target_loc in c_city or c_city in target_loc:
             matches.append({
                 "name": c['name'],
                 "city": c.get('city', location), # Store city for display
                 "contact": c['contact'],
                 "last_price": 42500, # Still mocked as we don't have order history DB yet
                 "priority": "High" if "Big" in c.get('category', '') else "Medium"
             })
    
    return matches

def get_active_sos():
    data = load_sos_data()
    return [d for d in data if d['status'] == "Active"]

def generate_sos_script(cust_name, saving, new_price, valid_until):
    return {
        "call_script": f"Hi {cust_name}, quick update. Rates dropped by {saving} just now for your location. Current landing cost is {new_price}. This is valid only till {valid_until}. Should I book 1 tanker?",
        "whatsapp": f"🚨 *PRICE DROP ALERT* 🚨\n\nHi {cust_name},\n\nGood news! Bitumen rates down by *{saving}/MT*.\n\n📉 New Price: *{new_price}*\n⏳ Valid until: {valid_until}\n\nStrictly limited slots. Reply YES to block.",
        "email_subject": f"URGENT: Price Drop Alert - Save {saving}/MT Today"
    }

# --- MOCK DATA ---
def init_mock_sos():
    if not os.path.exists(SOS_FILE):
        mock = [
            {
                "id": "SOS-101",
                "location": "Ahmedabad",
                "product": "VG30",
                "old_price": 42500,
                "new_price": 41800,
                "saving": 700,
                "valid_until": (datetime.datetime.now() + timedelta(hours=24)).strftime("%Y-%m-%d %H:%M"),
                "status": "Active",
                "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "target_customers": [
                   {"name": "Patel Infra", "contact": "9898012345", "last_price": 42400, "priority": "High"},
                   {"name": "Ganesh Construction", "contact": "9825012345", "last_price": 42500, "priority": "Medium"}
                ]
            }
        ]
        save_sos_data(mock)

init_mock_sos()
