
import party_master
import json

# Define specific plant locations to add as distinct sources
# This allows for precise logistics planning from specific loading points.

new_plants = [
    # --- HINCOL PLANTS ---
    {
        "name": "HINCOL (Vizag Plant)",
        "type": "Indian Mfg (Emulsion/CRMB/PMB)",
        "city": "Visakhapatnam",
        "contact": "022-2302 3250",
        "details": "Plant Address: Gajuwaka - Scindia Rd, Malkapuram, Visakhapatnam, Andhra Pradesh 530011",
        "marked_for_purchase": True,
        "qty_mt": 10000
    },
    {
        "name": "HINCOL (Mangalore Plant)",
        "type": "Indian Mfg (Emulsion/CRMB/PMB)",
        "city": "Mangalore",
        "contact": "022-2302 3250",
        "details": "Plant Address: Plot No P1, Near KK Gate, New Mangalore Port Authority, Panambur, Mangalore.",
        "marked_for_purchase": True,
        "qty_mt": 10000
    },
    {
        "name": "HINCOL (Haldia Plant)",
        "type": "Indian Mfg (Emulsion/CRMB/PMB)",
        "city": "Haldia",
        "contact": "022-2302 3250",
        "details": "Plant Address: JL-168, Mouza-Chiranjibpur, Haldia Purba Medinipur, West Bengal.",
        "marked_for_purchase": True,
        "qty_mt": 10000
    },
    {
        "name": "HINCOL (Savli Plant)",
        "type": "Indian Mfg (Emulsion/CRMB/PMB)",
        "city": "Vadodara",
        "contact": "022-2302 3250",
        "details": "Plant Address: 426, Savli GIDC Rd, Manjusar, Zumkal, Gujarat 391775.",
        "marked_for_purchase": True,
        "qty_mt": 10000
    },
    {
        "name": "HINCOL (Chennai Plant)",
        "type": "Indian Mfg (Emulsion/CRMB/PMB)",
        "city": "Chennai",
        "contact": "022-2302 3250",
        "details": "Plant Address: A-9, SIPCOT Industrial Park, Irungattukottai, Tamil Nadu.",
        "marked_for_purchase": True,
        "qty_mt": 10000
    },

    # --- TIKI TAR INDUSTRIES ---
    {
        "name": "Tiki Tar (Taloja Plant)",
        "type": "Indian Mfg (Emulsion/CRMB/PMB)",
        "city": "Mumbai",
        "contact": "022-2302 3250",
        "details": "Plant Address: G-13/3, MIDC Industrial area, Taloja, Dist. Raigad, Maharashtra.",
        "marked_for_purchase": True,
        "qty_mt": 8000
    },
    {
        "name": "Tiki Tar (Halol Plant)",
        "type": "Indian Mfg (Emulsion/CRMB/PMB)",
        "city": "Vadodara",
        "contact": "0265-2331185",
        "details": "Plant Address: Halol GIDC, Pratappura, Panchmahal, Gujarat.",
        "marked_for_purchase": True,
        "qty_mt": 8000
    },

    # --- AGARWAL INDUSTRIAL CORPORATION (AICL) ---
    {
        "name": "AICL (Karwar Terminal)",
        "type": "Indian Importer - Bulk",
        "city": "Karwar",
        "contact": "+91-22-25291149",
        "details": "Bulk Bitumen Terminal at Karwar Port.",
        "marked_for_purchase": True,
        "qty_mt": 15000
    },
    {
        "name": "AICL (Mangalore Terminal)",
        "type": "Indian Importer - Bulk",
        "city": "Mangalore",
        "contact": "+91-22-25291149",
        "details": "Bulk Bitumen Terminal at Mangalore.",
        "marked_for_purchase": True,
        "qty_mt": 15000
    },
    {
        "name": "AICL (Hazira/Dahej Terminal)",
        "type": "Indian Importer - Bulk",
        "city": "Surat",
        "contact": "+91-22-25291149",
        "details": "Bulk Bitumen Terminal at Hazira/Dahej.",
        "marked_for_purchase": True,
        "qty_mt": 15000
    },
    {
        "name": "AICL (Kakinada Terminal)",
        "type": "Indian Importer - Bulk",
        "city": "Kakinada",
        "contact": "+91-22-25291149",
        "details": "Bulk Bitumen Terminal at Kakinada Port.",
        "marked_for_purchase": True,
        "qty_mt": 15000
    },

    # --- BITCOL ---
    {
        "name": "BITCOL (Mathura Plant)",
        "type": "Indian Mfg (Emulsion/CRMB/PMB)",
        "city": "Mathura",
        "contact": "info@bitcol.in",
        "details": "Plant Address: Plot H-38, UPSIDC Industrial Area Ext. 1, Kosi Kotwan, Mathura.",
        "marked_for_purchase": True,
        "qty_mt": 5000
    },
    {
        "name": "BITCOL (Dindigul Plant)",
        "type": "Indian Mfg (Emulsion/CRMB/PMB)",
        "city": "Dindigul",
        "contact": "info@bitcol.in",
        "details": "Plant: Plot C-21, SIPCOT Industrial Complex, Village Pallapatti, Nilakottai, Dindigul, TN.",
        "marked_for_purchase": True,
        "qty_mt": 5000
    },
    
    # --- VENKATESHWARA BITUMENS ---
    {
        "name": "Venkateshwara Bitumens (Uppal Plant)",
        "type": "Indian Mfg (Emulsion/CRMB/PMB)",
        "city": "Hyderabad",
        "contact": "9731742757",
        "details": "Factory: Plot No. 2/6b, Uppal Ida Uppal, Hyderabad.",
        "marked_for_purchase": True,
        "qty_mt": 3000
    }
]

# Load existing
try:
    current_parties = party_master.load_suppliers()
except Exception as e:
    print(f"Error loading suppliers: {e}")
    current_parties = []

# Update or Add
added_count = 0
updated_count = 0

for new_p in new_plants:
    # Check if exists (by name)
    existing = next((p for p in current_parties if p['name'] == new_p['name']), None)
    
    if existing:
        # Update details explicitly
        existing['city'] = new_p['city']
        existing['contact'] = new_p['contact']
        existing['details'] = new_p['details']
        updated_count += 1
    else:
        current_parties.append(new_p)
        added_count += 1

# Save
try:
    party_master.save_suppliers(current_parties)
    print(f"SUCCESS: Added {added_count} new plant locations and updated {updated_count} existing ones.")
except Exception as e:
    print(f"Error saving: {e}")
