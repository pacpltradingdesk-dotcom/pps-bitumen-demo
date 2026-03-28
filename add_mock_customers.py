
import party_master

# Add Dummy Customers for Demo
customers = [
    {
        "name": "L&T Construction (Hyderabad)",
        "category": "Contractor - NHAI",
        "city": "Hyderabad",
        "state": "Telangana",
        "contact": "9876543210",
        "gstin": "36AAACL1234A1Z5",
        "address": "Hi-Tech City Road, Madhapur, Hyderabad"
    },
    {
        "name": "Dilip Buildcon (Bhopal)",
        "category": "Contractor - NHAI",
        "city": "Bhopal",
        "state": "Madhya Pradesh",
        "contact": "9988776655",
        "gstin": "23AAACD5678B1Z2",
        "address": "Chuna Bhatti, Kolar Road, Bhopal"
    },
    {
        "name": "Tata Projects (Pune)",
        "category": "Contractor - State/PWD",
        "city": "Pune",
        "state": "Maharashtra",
        "contact": "9123456789",
        "gstin": "27AAACT9012C1Z8",
        "address": "Yerwada, Pune"
    }
]

added = 0
for c in customers:
    # Check if exists
    try:
        current = party_master.load_customers()
        if not any(curr['name'] == c['name'] for curr in current):
            party_master.add_customer(
                c['name'], c['category'], c['city'], c['state'], 
                c['contact'], c['gstin'], c['address']
            )
            added += 1
    except:
        pass

print(f"Added {added} mock customers.")
