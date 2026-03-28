
import party_master
import json

# Define new service providers (Transporters)
new_transporters = [
    # --- NATIONAL / MULTI-REGION ---
    {
        "name": "Parashar Group of Transporters",
        "category": "Transporter - Bulk",
        "city": "Mumbai / Pan-India",
        "contact": "www.bitumentransporter.com",
        "details": "Major fleet owner since 1994. Serving IOCL, BPCL, HPCL, Essar, Hincol. All India Permit."
    },
    {
        "name": "India Golden Transport Company (IGTC)",
        "category": "Transporter - Bulk",
        "city": "Mathura / North India",
        "contact": "9411065880 / 9760466433",
        "details": "Govt authorized. Large fleet for bulk bitumen. Serving IOCL Mathura/Panipat, HPCL Bhatinda. Email: info@igtc.in"
    },
    
    # --- MUMBAI ---
    {
        "name": "Sanjivani Petrochem Pvt Ltd",
        "category": "Transporter - Bulk",
        "city": "Mumbai (Chembur)",
        "contact": "+91-8047845108",
        "details": "Leading bulk transporter. Branches in Baroda, Raipur."
    },
    {
        "name": "Shiv Malhar Enterprises",
        "category": "Transporter - Bulk",
        "city": "Mumbai",
        "contact": "8779743119 / 9892404991",
        "details": "Email: shivmalharenterprises02@gmail.com. Bulk Bitumen Transport."
    },
    {
        "name": "Lokmangal Logistics",
        "category": "Transporter - Bulk",
        "city": "Mumbai",
        "contact": "+91 9833136040",
        "details": "Email: lokmangallogistics@gmail.com"
    },
    {
        "name": "Brijda Roadline Pvt Ltd",
        "category": "Transporter - Bulk",
        "city": "Mumbai",
        "contact": "9820500726",
        "details": "Email: singhbrijesh@brijda.com"
    },
    {
        "name": "Riddhi Siddhi Petroleum",
        "category": "Transporter - Bulk",
        "city": "Mumbai",
        "contact": "+91-7949093032",
        "details": "Address: Chembur. 28 Ton Tankers Available."
    },

    # --- GUJARAT ---
    {
        "name": "Vansh Logistics & Co",
        "category": "Transporter - Bulk",
        "city": "Gujarat",
        "contact": "9898876000",
        "details": "Email: vijay@vanshlogistics.com"
    },
    {
        "name": "Rajeshree Tar Industries (Transport Div)",
        "category": "Transporter - Bulk",
        "city": "Vadodara",
        "contact": "9725040804",
        "details": "Email: rajeshree.roadlines@gmail.com"
    },
    {
        "name": "Harshit Logistics",
        "category": "Transporter - Bulk",
        "city": "Gujarat",
        "contact": "919925024190",
        "details": "Email: GANESHAM_MUNDRA@YAHOO.COM"
    },

    # --- DELHI NCR / NORTH ---
    {
        "name": "Aggarwal Cargo Transport",
        "category": "Transporter - Bulk",
        "city": "Ghaziabad / Delhi NCR",
        "contact": "Contact via Justdial",
        "details": "Specialized cargo movers."
    },
    {
        "name": "M/s Shri Ji Bitumen Traders (Logistics)",
        "category": "Transporter - Bulk",
        "city": "Mathura / UP",
        "contact": "www.shrijibitumen.in",
        "details": "Logistics support for IOCL Mathura/Panipat."
    },
    {
        "name": "AJIT TEMPO TRANSPORT SERVICE",
        "category": "Transporter - Bulk",
        "city": "New Delhi",
        "contact": "+91-7942963257",
        "details": "Bulk Bitumen Transportation Service."
    },

    # --- SOUTH INDIA ---
    {
        "name": "Bitumen Suppliers Transporters Hyderabad",
        "category": "Transporter - Bulk",
        "city": "Hyderabad",
        "contact": "093934 21122",
        "details": "Address: Kukatpally, Hyderabad."
    },
    {
        "name": "V. V. Carrierrs",
        "category": "Transporter - Bulk",
        "city": "Chennai",
        "contact": "8044464865",
        "details": "Specializes in Bitumen Transport. Address: Parrys, Chennai."
    },
    {
        "name": "Karthik Transporters",
        "category": "Transporter - Bulk",
        "city": "Chennai",
        "contact": "",
        "details": "Address: Manali, Chennai. Listed as Transporters For Bitumen."
    },
    {
        "name": "S S Enterprises",
        "category": "Transporter - Bulk",
        "city": "Bangalore",
        "contact": "",
        "details": "Address: Basavanagudi, Bangalore. Listed as Transporters For Bitumen."
    },
    
    # --- EAST / GUWAHATI ---
    {
        "name": "GWC Asphalt Logistics",
        "category": "Transporter - Bulk",
        "city": "Guwahati",
        "contact": "+91-75770 10777",
        "details": "Transport division of GWC Asphalt."
    }
]

# Load existing
try:
    current_services = party_master.load_services()
except Exception as e:
    print(f"Error loading services: {e}")
    current_services = []

# Update or Add
added_count = 0
updated_count = 0

for new_s in new_transporters:
    # Check if exists (by name)
    existing = next((s for s in current_services if s['name'] == new_s['name']), None)
    
    if existing:
        existing['city'] = new_s['city']
        existing['contact'] = new_s['contact']
        existing['details'] = new_s['details']
        updated_count += 1
    else:
        current_services.append(new_s)
        added_count += 1

# Save
try:
    party_master.save_services(current_services)
    print(f"SUCCESS: Added {added_count} new transporters and updated {updated_count} existing ones.")
    print("New total service providers:", len(current_services))
except Exception as e:
    print(f"Error saving: {e}")
