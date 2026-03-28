
import party_master
import json

# Define the new suppliers to add from extensive city-by-city search
new_suppliers = [
    # --- AHMEDABAD ---
    {
        "name": "Maruti Bitumen Pvt Ltd",
        "type": "Indian Mfg (Emulsion/CRMB/PMB)",
        "city": "Ahmedabad",
        "contact": "http://www.marutigroup.in",
        "gstin": "",
        "details": "Address: 21, 4D Square, Motera, Ahmedabad. Products: Bitumen Emulsions, PMB.",
        "marked_for_purchase": True,
        "qty_mt": 10000
    },
    {
        "name": "Atlas Engineering",
        "type": "Indian Mfg (Emulsion/CRMB/PMB)",
        "city": "Ahmedabad",
        "contact": "9825073095",
        "gstin": "",
        "details": "Address: Plot 397/398, Kathwada GIDC, Ahmedabad. Products: Manufacturers of Bitumen plants and machinery.",
        "marked_for_purchase": True,
        "qty_mt": 5000
    },
    {
        "name": "Aaspa Equipment Pvt Ltd",
        "type": "Indian Mfg (Emulsion/CRMB/PMB)",
        "city": "Ahmedabad",
        "contact": "",
        "gstin": "",
        "details": "Address: SF 223, Arth Business Center, Nikol, Ahmedabad. Products: Bitumen Emulsions, PMB.",
        "marked_for_purchase": True,
        "qty_mt": 5000
    },
    
    # --- MUMBAI ---
    {
        "name": "Krish Impex",
        "type": "Indian Importer - Drum",
        "city": "Mumbai",
        "contact": "Contact via IndiaMart",
        "gstin": "",
        "details": "Address: Ghatkopar East, Mumbai.",
        "marked_for_purchase": True,
        "qty_mt": 2000
    },
    {
        "name": "Floatantide Commodities",
        "type": "Indian Importer - Bulk",
        "city": "Mumbai",
        "contact": "",
        "gstin": "",
        "details": "Address: Khar West, Mumbai.",
        "marked_for_purchase": True,
        "qty_mt": 8000
    },
    {
        "name": "Blue Jay Petro Pvt Ltd",
        "type": "Indian Importer - Drum",
        "city": "Mumbai",
        "contact": "",
        "gstin": "",
        "details": "Address: Andheri East, Mumbai.",
        "marked_for_purchase": True,
        "qty_mt": 3000
    },
    {
        "name": "Jay Ambe Petro Chem",
        "type": "Indian Importer - Drum",
        "city": "Navi Mumbai",
        "contact": "022-49797074",
        "gstin": "",
        "details": "Address: Vashi, Navi Mumbai.",
        "marked_for_purchase": True,
        "qty_mt": 4000
    },
    
    # --- CHENNAI ---
    {
        "name": "Cauvery Bituchem Pvt Ltd",
        "type": "Indian Mfg (Emulsion/CRMB/PMB)",
        "city": "Chennai",
        "contact": "",
        "gstin": "",
        "details": "Address: Pycrofts Road, Royapettah, Chennai.",
        "marked_for_purchase": True,
        "qty_mt": 5000
    },
    {
        "name": "Muthoos Enterprises",
        "type": "Indian Mfg (Emulsion/CRMB/PMB)",
        "city": "Chennai",
        "contact": "+918044566500",
        "gstin": "",
        "details": "Address: Anna Nagar, Chennai. Plant in Thiruvallur.",
        "marked_for_purchase": True,
        "qty_mt": 6000
    },
    {
        "name": "IWL India Limited",
        "type": "Indian Mfg (Emulsion/CRMB/PMB)",
        "city": "Chennai",
        "contact": "",
        "gstin": "",
        "details": "Address: Anna Nagar West, Chennai. Products: CRMB, PMB.",
        "marked_for_purchase": True,
        "qty_mt": 7000
    },
    
    # --- DELHI NCR / MATHURA ---
    {
        "name": "KM Chemicals",
        "type": "Indian Mfg (Emulsion/CRMB/PMB)",
        "city": "Mathura",
        "contact": "",
        "gstin": "",
        "details": "Address: 110 KM Stone, Delhi Mathura Road.",
        "marked_for_purchase": True,
        "qty_mt": 5000
    },
    {
        "name": "DRG Bitumen",
        "type": "Indian Mfg (Emulsion/CRMB/PMB)",
        "city": "Mathura",
        "contact": "+91 9910558183",
        "gstin": "",
        "details": "Address: Chhata, Mathura. Products: Bitumen processing.",
        "marked_for_purchase": True,
        "qty_mt": 6000
    },
    {
        "name": "Shiv Sons",
        "type": "Indian Importer - Drum",
        "city": "Delhi",
        "contact": "www.shivson.com",
        "gstin": "",
        "details": "Address: GB Road, New Delhi.",
        "marked_for_purchase": True,
        "qty_mt": 3000
    },
    
    # --- KOLKATA ---
    {
        "name": "Bitchem Asphalt Technologies",
        "type": "Indian Mfg (Emulsion/CRMB/PMB)",
        "city": "Kolkata",
        "contact": "",
        "gstin": "",
        "details": "Address: Ganesh Chandra Avenue, Kolkata.",
        "marked_for_purchase": True,
        "qty_mt": 8000
    },
    {
        "name": "SAPCO Bitumen Company Ltd",
        "type": "Indian Importer - Bulk",
        "city": "Kolkata",
        "contact": "s.agarwal@sapco.in",
        "gstin": "",
        "details": "Address: Rabindra Sarani, Kolkata.",
        "marked_for_purchase": True,
        "qty_mt": 10000
    },
    {
        "name": "Choudhary Bitumen & Allied Products",
        "type": "Indian Mfg (Emulsion/CRMB/PMB)",
        "city": "Kolkata",
        "contact": "contact@cbap.co.in",
        "gstin": "",
        "details": "Address: C.R. Avenue, Kolkata. Plant in Howrah.",
        "marked_for_purchase": True,
        "qty_mt": 7000
    },
    
    # --- VADODARA ---
    {
        "name": "Shiv Shakti Tar Chem Products",
        "type": "Indian Importer - Drum",
        "city": "Vadodara",
        "contact": "",
        "gstin": "",
        "details": "Address: Lakodara, Vadodara.",
        "marked_for_purchase": True,
        "qty_mt": 2000
    },
    {
        "name": "Swastik Tar Industries",
        "type": "Indian Mfg (Emulsion/CRMB/PMB)",
        "city": "Vadodara",
        "contact": "",
        "gstin": "",
        "details": "Address: Nandesari Industrial Estate, Vadodara.",
        "marked_for_purchase": True,
        "qty_mt": 3000
    },
    {
        "name": "Rajeshree Tar Industries",
        "type": "Indian Mfg (Emulsion/CRMB/PMB)",
        "city": "Vadodara",
        "contact": "9725040804",
        "gstin": "",
        "details": "Address: Nandesari, Vadodara. Email: rajeshreetarind@gmail.com",
        "marked_for_purchase": True,
        "qty_mt": 4000
    },
    
    # --- SURAT ---
    {
        "name": "Spectrum Dyes And Chemicals",
        "type": "Indian Mfg (Emulsion/CRMB/PMB)",
        "city": "Surat",
        "contact": "",
        "gstin": "",
        "details": "Address: Palsana, Surat.",
        "marked_for_purchase": True,
        "qty_mt": 5000
    },
    
    # --- HYDERABAD ---
    {
        "name": "Venkateshwara Bitumens",
        "type": "Indian Mfg (Emulsion/CRMB/PMB)",
        "city": "Hyderabad",
        "contact": "9731742757",
        "gstin": "",
        "details": "Address: IDA Uppal, Hyderabad.",
        "marked_for_purchase": True,
        "qty_mt": 3000
    },
    {
        "name": "Rinkey Enterprises",
        "type": "Indian Importer - Drum",
        "city": "Hyderabad",
        "contact": "08046054733",
        "gstin": "",
        "details": "Address: Sriven Enclave, Hyderabad.",
        "marked_for_purchase": True,
        "qty_mt": 2000
    },
    
    # --- BANGALORE ---
    {
        "name": "Shree Sai Chemicals",
        "type": "Indian Importer - Drum",
        "city": "Bangalore",
        "contact": "08046061090",
        "gstin": "",
        "details": "Address: Marathahalli, Bangalore.",
        "marked_for_purchase": True,
        "qty_mt": 2000
    },
    {
        "name": "Krush Tar Industries",
        "type": "Indian Mfg (Emulsion/CRMB/PMB)",
        "city": "Bangalore",
        "contact": "www.krushtarindustries.com",
        "gstin": "",
        "details": "Address: Jayanagar, Bangalore.",
        "marked_for_purchase": True,
        "qty_mt": 3000
    },
    
    # --- GUWAHATI ---
    {
        "name": "BitChem Asphalt Technologies (Guwahati)",
        "type": "Indian Mfg (Emulsion/CRMB/PMB)",
        "city": "Guwahati",
        "contact": "+91 88769 20128",
        "gstin": "",
        "details": "Address: Anil Plaza, GS Road, Guwahati.",
        "marked_for_purchase": True,
        "qty_mt": 5000
    },
    {
        "name": "GWC Asphalt",
        "type": "Indian Mfg (Emulsion/CRMB/PMB)",
        "city": "Guwahati",
        "contact": "+91-75770 10777",
        "gstin": "",
        "details": "Address: Anil Plaza-II, Guwahati. Plant in Goalpara.",
        "marked_for_purchase": True,
        "qty_mt": 4000
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
        # Update details explicitly if needed
        existing['city'] = new_p['city']
        existing['contact'] = new_p['contact']
        existing['details'] = new_p['details']
        if new_p['gstin']:
             existing['gstin'] = new_p['gstin']
        
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
