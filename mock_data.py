import os
import pandas as pd
import numpy as np

# EXTRACTED DATA FROM IMAGE
# We create a Cartesian product: Every Source calculates a price for Every Destination (Dummy logic)
# This simulates the "Pan-India" matrix.

# EXTRACTED DATA FROM USER INPUT (Today's Prices)
sources = [
    {"name": "Barauni (IOCL)", "city": "Barauni", "state": "Bihar", "base_bulk": 48372, "base_drum": 51372, "disc": 0},
    {"name": "Bathinda (HMEL)", "city": "Bathinda", "state": "Punjab", "base_bulk": 46830, "base_drum": 49830, "disc": 0},
    {"name": "Chennai (CPCL)", "city": "Chennai", "state": "Tamil Nadu", "base_bulk": 48842, "base_drum": 51842, "disc": 0},
    {"name": "Kochi (BPCL)", "city": "Kochi", "state": "Kerala", "base_bulk": 49560, "base_drum": 52560, "disc": 0},
    {"name": "Guwahati (IOCL)", "city": "Guwahati", "state": "Assam", "base_bulk": 53285, "base_drum": 56285, "disc": 0},
    {"name": "Haldia (IOCL)", "city": "Haldia", "state": "West Bengal", "base_bulk": 47542, "base_drum": 50542, "disc": 0},
    {"name": "Hyderabad Depot", "city": "Hyderabad", "state": "Telangana", "base_bulk": 51437, "base_drum": 54437, "disc": 0},
    {"name": "Indore Depot", "city": "Indore", "state": "Madhya Pradesh", "base_bulk": 50377, "base_drum": 53377, "disc": 0},
    {"name": "Jabalpur", "city": "Jabalpur", "state": "Madhya Pradesh", "base_bulk": 55672, "base_drum": 58672, "disc": 0},
    {"name": "Jamnagar (RIL/NEL)", "city": "Jamnagar", "state": "Gujarat", "base_bulk": 49625, "base_drum": 52625, "disc": 0},
    {"name": "Koyali (IOCL)", "city": "Vadodara", "state": "Gujarat", "base_bulk": 48380, "base_drum": 51380, "disc": 0},
    {"name": "Karwar (Various)", "city": "Karwar", "state": "Karnataka", "base_bulk": 48660, "base_drum": 51660, "disc": 0},
    {"name": "Mangalore (MRPL)", "city": "Mangalore", "state": "Karnataka", "base_bulk": 48660, "base_drum": 51660, "disc": 0},
    {"name": "Mathura (IOCL)", "city": "Mathura", "state": "Uttar Pradesh", "base_bulk": 46342, "base_drum": 49342, "disc": 0},
    {"name": "Mumbai/JNPT (BPCL)", "city": "Mumbai", "state": "Maharashtra", "base_bulk": 50140, "base_drum": 53140, "disc": 0},
    {"name": "Mundra", "city": "Mundra", "state": "Gujarat", "base_bulk": 47820, "base_drum": 50820, "disc": 0},
    {"name": "Mysore", "city": "Mysore", "state": "Karnataka", "base_bulk": 52776, "base_drum": 55776, "disc": 0},
    {"name": "Nippani", "city": "Nippani", "state": "Karnataka", "base_bulk": 53797, "base_drum": 56797, "disc": 0},
    {"name": "Panipat (IOCL)", "city": "Panipat", "state": "Haryana", "base_bulk": 46342, "base_drum": 49342, "disc": 0},
    {"name": "Raipur", "city": "Raipur", "state": "Chhattisgarh", "base_bulk": 49477, "base_drum": 52477, "disc": 0},
    {"name": "Vapi", "city": "Vapi", "state": "Gujarat", "base_bulk": 48664, "base_drum": 51664, "disc": 0},
    {"name": "Vizag (HPCL)", "city": "Visakhapatnam", "state": "Andhra Pradesh", "base_bulk": 47830, "base_drum": 50830, "disc": 0}
]

# Major Destinations to simulate (Pan-India Cross Calculation)
destinations_map = {
    "Maharashtra": ["Mumbai", "Pune", "Nagpur", "Nashik", "Aurangabad", "Solapur", "Kolhapur", "Amravati", "Nanded", "Jalgaon", "Akola", "Latur", "Dhule", "Ahmednagar", "Chandrapur"],
    "Gujarat": ["Ahmedabad", "Surat", "Vadodara", "Rajkot", "Bhavnagar", "Jamnagar", "Junagadh", "Gandhinagar", "Anand", "Bharuch", "Morbi", "Vapi"],
    "Karnataka": ["Bangalore", "Mysore", "Hubli", "Dharwad", "Mangalore", "Belgaum", "Gulbarga", "Davangere", "Bellary", "Shimoga"],
    "Tamil Nadu": ["Chennai", "Coimbatore", "Madurai", "Trichy", "Salem", "Tirunelveli", "Erode", "Vellore", "Thoothukudi"],
    "Uttar Pradesh": ["Lucknow", "Kanpur", "Ghaziabad", "Agra", "Varanasi", "Meerut", "Prayagraj", "Bareilly", "Aligarh", "Moradabad", "Gorakhpur", "Noida"],
    "Rajasthan": ["Jaipur", "Jodhpur", "Kota", "Bikaner", "Ajmer", "Udaipur", "Bhilwara", "Alwar", "Sikar", "Sri Ganganagar"],
    "Madhya Pradesh": ["Indore", "Bhopal", "Jabalpur", "Gwalior", "Ujjain", "Sagar", "Dewas", "Satna", "Ratlam"],
    "West Bengal": ["Kolkata", "Asansol", "Siliguri", "Durgapur", "Bardhaman", "Malda", "Kharagpur", "Haldia"],
    "Bihar": ["Patna", "Gaya", "Bhagalpur", "Muzaffarpur", "Purnia", "Darbhanga", "Begusarai"],
    "Andhra Pradesh": ["Visakhapatnam", "Vijayawada", "Guntur", "Nellore", "Kurnool", "Rajahmundry", "Tirupati", "Kakinada"],
    "Telangana": ["Hyderabad", "Warangal", "Nizamabad", "Karimnagar", "Khammam"],
    "Punjab": ["Ludhiana", "Amritsar", "Jalandhar", "Patiala", "Bathinda", "Mohali", "Pathankot"],
    "Haryana": ["Faridabad", "Gurgaon", "Panipat", "Ambala", "Yamunanagar", "Rohtak", "Hisar", "Karnal", "Sonipat"],
    "Kerala": ["Kochi", "Thiruvananthapuram", "Kozhikode", "Thrissur", "Kollam", "Kannur"],
    "Odisha": ["Bhubaneswar", "Cuttack", "Rourkela", "Berhampur", "Sambalpur", "Puri"],
    "Assam": ["Guwahati", "Silchar", "Dibrugarh", "Jorhat"],
    "Jharkhand": ["Ranchi", "Jamshedpur", "Dhanbad", "Bokaro"],
    "Chhattisgarh": ["Raipur", "Bhilai", "Bilaspur", "Korba"],
    "Uttarakhand": ["Dehradun", "Haridwar", "Roorkee", "Haldwani"],
    "Himachal Pradesh": ["Shimla", "Manali", "Dharamshala", "Solan"],
    "Goa": ["Panaji", "Margao", "Vasco da Gama"],
    "Delhi": ["Delhi", "New Delhi"]
}

rows = []

print("Generating Pan-India Cross-Calculation Matrix...")
# Create a flat list of dests
for state, cities in destinations_map.items():
    for city in cities:
        dest = city
        dest_state = state
        
        for src in sources:
            # Smart Transport Logic based on Distance Approximation and KM
            # 1. Calculate approximate distance (Simulated)
            
            distance_km = 0
            rate_per_km_bulk = 4.5 # Average market rate per ton per km
            rate_per_km_drum = 5.2
            
            if src['city'] == dest:
                distance_km = np.random.randint(10, 50) # Local
            elif src['state'] == dest_state:
                distance_km = np.random.randint(100, 450) # Intra-state
            else:
                # Inter-state Logic
                # Check region proximity again
                north_states = ["Punjab", "Haryana", "Delhi", "Uttar Pradesh", "Rajasthan", "Uttarakhand", "Himachal Pradesh"]
                west_states = ["Maharashtra", "Gujarat", "Madhya Pradesh", "Goa", "Rajasthan"]
                south_states = ["Karnataka", "Tamil Nadu", "Kerala", "Andhra Pradesh", "Telangana"]
                east_states = ["West Bengal", "Bihar", "Odisha", "Jharkhand", "Assam"]
                
                is_nearby = False
                if src['state'] in north_states and dest_state in north_states: is_nearby = True
                if src['state'] in west_states and dest_state in west_states: is_nearby = True
                if src['state'] in south_states and dest_state in south_states: is_nearby = True
                if src['state'] in east_states and dest_state in east_states: is_nearby = True
                
                if is_nearby:
                    distance_km = np.random.randint(400, 900)
                else:
                    distance_km = np.random.randint(1000, 2500) # Long haul

            # Calculate Transport Cost based on KM
            # Min freight logic
            min_freight = 800
            
            transport_bulk = max(min_freight, int(distance_km * rate_per_km_bulk))
            transport_drum = max(min_freight + 300, int(distance_km * rate_per_km_drum))

            row = {
                'destination': dest,
                'customer_name': f"Client in {dest}",
                'source_location': src['name'],
                'port': src['city'],
                'state': src['state'],
                'destination_state': dest_state,
                'distance_km': distance_km, # Added KM
                'rate_per_km': rate_per_km_bulk,
                'base_price': src['base_bulk'], 
                'discount': src['disc'],
                'transport_bulk': transport_bulk,
                'transport_drum': transport_drum,
                'base_bulk': src['base_bulk'],
                'base_drum': src['base_drum'],
                'disc_bulk': src['disc'],
                'disc_drum': src['disc']
            }
            rows.append(row)

df = pd.DataFrame(rows)
print(f"Generated {len(df)} pricing combinations.")
output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logistics_data.parquet")
df.to_parquet(output_path)
print(f"Saved to {output_path}")
print("Mock Data Updated with Real Refineries!")
