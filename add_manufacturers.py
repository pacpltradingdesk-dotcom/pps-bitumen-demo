
import party_master
import json

# Define the new suppliers to add
new_suppliers = [
    # --- PSU REFINERIES (Classified as Bulk Suppliers) ---
    {
        "name": "Indian Oil Corporation Ltd (IOCL)",
        "type": "Indian Importer - Bulk",
        "city": "New Delhi (HQ) / Panipat",
        "contact": "1800-2333-555",
        "gstin": "06AAACI1681G1Z0", 
        "details": "Major PSU Refinery. Locations: Panipat, Mathura, Koyali, Haldia, Paradip, Barauni, Guwahati, Digboi, Bongaigaon, Chennai. Email: customercare@indianoilcgd.com",
        "marked_for_purchase": True,
        "qty_mt": 1000000
    },
    {
        "name": "Bharat Petroleum Corporation Ltd (BPCL)",
        "type": "Indian Importer - Bulk",
        "city": "Mumbai (HQ) / Kochi",
        "contact": "1800 22 4344",
        "gstin": "27AAACB2902M1Z6",
        "details": "Major PSU Refinery. Locations: Mumbai, Kochi, Bina. Website: bharatpetroleum.in",
        "marked_for_purchase": True,
        "qty_mt": 800000
    },
    {
        "name": "Hindustan Petroleum Corporation Ltd (HPCL)",
        "type": "Indian Importer - Bulk",
        "city": "Mumbai (HQ) / Visakhapatnam",
        "contact": "1800 2333 555",
        "gstin": "27AAACH1118B1ZC",
        "details": "Major PSU Refinery. Locations: Mumbai, Visakhapatnam, Bhatinda (HMEL).",
        "marked_for_purchase": True,
        "qty_mt": 750000
    },
    {
        "name": "Mangalore Refinery (MRPL)",
        "type": "Indian Importer - Bulk",
        "city": "Mangalore",
        "contact": "0824-2882000",
        "gstin": "29AAACM3560G1Z5",
        "details": "ONGC Subsidiary. Major Bitumen Producer in South.",
        "marked_for_purchase": True,
        "qty_mt": 300000
    },
    {
        "name": "Nayara Energy (formerly Essar Oil)",
        "type": "Indian Importer - Bulk",
        "city": "Vadinar, Gujarat",
        "contact": "(+91) 22 71320000",
        "gstin": "24AAACE5648E1Z2",
        "details": "Private Refinery. India's second largest single-site refinery.",
        "marked_for_purchase": True,
        "qty_mt": 400000
    },

    # --- DOWNSTREAM MANUFACTURERS (Emulsion/PMB) ---
    {
        "name": "HINCOL (Hindustan Colas Ltd)",
        "type": "Indian Mfg (Emulsion/CRMB/PMB)",
        "city": "Mumbai (HQ)",
        "contact": "022-2302 3250",
        "gstin": "27AAACH2861H1Z9",
        "details": "Address: B-601, Marathon Futurex, Lower Parel, Mumbai. Locations: Mumbai, Vizag, Mangalore, Bhatinda. Email: corporate@dustasidehincol.in",
        "marked_for_purchase": True,
        "qty_mt": 50000
    },
    {
        "name": "Tiki Tar Industries",
        "type": "Indian Mfg (Emulsion/CRMB/PMB)",
        "city": "Vadodara",
        "contact": "0265-2331185",
        "gstin": "24AAACT4996F1Z8",
        "details": "Address: 8th Floor, Neptune Tower, Alkapuri, Vadodara. Major PMB supplier. Email: nidhi@tikitar.com",
        "marked_for_purchase": True,
        "qty_mt": 30000
    },
    {
        "name": "Agarwal Industrial Corporation Ltd (AICL)",
        "type": "Indian Mfg (Emulsion/CRMB/PMB)",
        "city": "Mumbai (Chembur)",
        "contact": "+91-22-25291149",
        "gstin": "27AAACA3996G1Z5",
        "details": "Address: Eastern Court, Unit 201-202, Chembur, Mumbai. Logistics & Bitumen Mfg.",
        "marked_for_purchase": True,
        "qty_mt": 45000
    },
    {
        "name": "RoadStar Bitumen",
        "type": "Indian Mfg (Emulsion/CRMB/PMB)",
        "city": "New Delhi",
        "contact": "+91 9871855136",
        "gstin": "",
        "details": "Address: E 45/6, Okhla Phase-2, New Delhi. Offices in Mumbai, Chennai, Kolkata. Email: corporate@roadstarbitumen.com",
        "marked_for_purchase": True,
        "qty_mt": 15000
    },
    {
        "name": "Classic Bitumen (CGOC)",
        "type": "Indian Mfg (Emulsion/CRMB/PMB)",
        "city": "Mohali / Chandigarh",
        "contact": "+91 80 41011570",
        "gstin": "",
        "details": "Address: Plot No 1567, Sector 82, JLPL Mohali, Punjab.",
        "marked_for_purchase": True,
        "qty_mt": 12000
    },

    # --- MAJOR IMPORTERS ---
    {
        "name": "Bitumen Corporation India (BITCOL)",
        "type": "Indian Importer - Bulk",
        "city": "Mumbai (Nariman Point)",
        "contact": "info@bitcol.in",
        "gstin": "27AACCA6654J1Z8",
        "details": "Address: 27/28 A, Nariman Bhavan, Nariman Point, Mumbai. Terminals: Mundra, Karwar, Haldia.",
        "marked_for_purchase": True,
        "qty_mt": 60000
    },
    {
        "name": "Kotak Petroleum LLP",
        "type": "Indian Importer - Bulk",
        "city": "Jamnagar",
        "contact": "+91-9824850777",
        "gstin": "24AAHFK4298J1Z6",
        "details": "Address: 2nd Floor, Standard House, Jamnagar, Gujarat. Email: kotak.hemal@gmail.com",
        "marked_for_purchase": True,
        "qty_mt": 38000
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

for new_p in new_suppliers:
    # Check if exists (by name)
    existing = next((p for p in current_parties if p['name'] == new_p['name']), None)
    
    if existing:
        # Update details explicitly if needed, but let's just update empty fields or overwrite key info
        # User said "ADD ... ALL INFO", so updating is good.
        existing['city'] = new_p['city']
        existing['contact'] = new_p['contact']
        existing['details'] = new_p['details']
        if new_p['gstin']:
             existing['gstin'] = new_p['gstin']
        
        # Ensure type matches one of the valid categories
        # If existing type is usable, keep it, else update.
        if existing['type'] not in party_master.SUPPLIER_CATEGORIES:
             existing['type'] = new_p['type']
             
        updated_count += 1
    else:
        current_parties.append(new_p)
        added_count += 1

# Save
try:
    party_master.save_suppliers(current_parties)
    print(f"SUCCESS: Added {added_count} new suppliers and updated {updated_count} existing ones.")
    print("New total suppliers:", len(current_parties))
except Exception as e:
    print(f"Error saving: {e}")
