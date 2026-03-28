# Distance Matrix - Approximate road distances (KM) between major cities
# This is used for logistics cost calculation

import math

# --- 1. COORDINATES DATABASE (Lat, Lon) ---

# SOURCES (Refineries & Ports)
SOURCE_COORDS = {
    # Indian Refineries
    "IOCL Koyali": (22.31, 73.18),
    "IOCL Mathura": (27.49, 77.67),
    "IOCL Haldia": (22.03, 88.06),
    "IOCL Barauni": (25.47, 86.00),
    "IOCL Panipat": (29.39, 76.97),
    "IOCL Digboi": (27.39, 95.62),
    "IOCL Guwahati": (26.14, 91.74),
    "IOCL Bongaigaon": (26.47, 90.56),
    "BPCL Mumbai": (19.01, 72.85),
    "BPCL Kochi": (9.93, 76.26),
    "HPCL Mumbai": (19.01, 72.85),
    "HPCL Visakhapatnam": (17.69, 83.22),
    "CPCL Chennai": (13.08, 80.27),
    "MRPL Mangalore": (12.98, 74.81),
    "NRL Numaligarh": (26.63, 93.72),
    "ONGC Tatipaka": (16.58, 82.08),
    "HMEL Bhatinda": (30.21, 74.94),
    "BORL Bina": (24.17, 78.18),
    "RIL Jamnagar": (22.38, 69.84),
    "Nayara Vadinar": (22.39, 69.70),

    # Import Terminals
    "Mangalore Port Import": (12.98, 74.81),
    "Karwar Port Import": (14.81, 74.13),
    "Digi Port Import": (20.71, 70.98),
    "Taloja Terminal": (19.07, 73.12),
    "VVF Mumbai Terminal": (19.01, 72.85),
    "Kandla Port Import": (23.03, 70.22),
    "Mundra Port Import": (22.84, 69.72),
    "JNPT Import Terminal": (18.95, 72.95),
    "Haldia Port Import": (22.03, 88.06),
    "Ennore Port Import": (13.26, 80.33),
    
    # Private Decanters / Depots
    "Ahmedabad Decanter": (23.02, 72.57),
    "Vadodara Decanter": (22.31, 73.18),
    "Kutch Decanter": (23.24, 69.67),
    "Mathura Decanter": (27.49, 77.67),
    "Jaipur Decanter": (26.91, 75.79),
    "Indore Decanter": (22.72, 75.86),
    "Pune Decanter": (18.52, 73.86),
    "Hyderabad Decanter": (17.39, 78.49),
    "Nagpur Decanter": (21.15, 79.09),
    "Raipur Decanter": (21.25, 81.63),
}

# DESTINATIONS (Customer Locations)
# Format: "CityName": (Lat, Lon)
DESTINATION_COORDS = {
    # Gujarat
    "Ahmedabad": (23.02, 72.57), "Vadodara": (22.31, 73.18), "Surat": (21.17, 72.83), 
    "Rajkot": (22.30, 70.80), "Bhavnagar": (21.76, 72.15), "Jamnagar": (22.47, 70.05),
    "Gandhinagar": (23.21, 72.63), "Junagadh": (21.52, 70.45), "Gandhidham": (23.07, 70.13),
    "Anand": (22.56, 72.92), "Navsari": (20.94, 72.95), "Morbi": (22.81, 70.83),
    "Bharuch": (21.70, 72.99), "Palanpur": (24.17, 72.43), "Valsad": (20.59, 72.93),
    "Vapi": (20.38, 72.91), "Mehsana": (23.58, 72.36), "Bhuj": (23.24, 69.66),
    "Porbandar": (21.64, 69.60), "Godhra": (22.77, 73.61), "Veraval": (20.91, 70.35),
    "Surendranagar": (22.72, 71.63), "Patan": (23.84, 72.12), "Amreli": (21.60, 71.22),

    # Maharashtra
    "Mumbai": (19.07, 72.87), "Pune": (18.52, 73.85), "Nagpur": (21.14, 79.08),
    "Nashik": (19.99, 73.78), "Aurangabad": (19.87, 75.34), "Solapur": (17.65, 75.90),
    "Thane": (19.21, 72.97), "Amravati": (20.93, 77.75), "Kolhapur": (16.70, 74.24),
    "Sangli": (16.85, 74.58), "Jalgaon": (21.00, 75.56), "Akola": (20.70, 77.00),
    "Latur": (18.40, 76.56), "Dhule": (20.90, 74.77), "Ahmednagar": (19.09, 74.74),
    "Chandrapur": (19.96, 79.29), "Parbhani": (19.26, 76.77), "Jalna": (19.83, 75.88),
    "Bhiwandi": (19.28, 73.06), "Ratnagiri": (16.99, 73.31), "Wardha": (20.74, 78.60),
    "Satara": (17.68, 73.99), "Beed": (18.98, 75.76), "Yavatmal": (20.38, 78.12),

    # Rajasthan
    "Jaipur": (26.91, 75.78), "Jodhpur": (26.23, 73.02), "Kota": (25.21, 75.86),
    "Bikaner": (28.02, 73.31), "Ajmer": (26.44, 74.63), "Udaipur": (24.58, 73.68),
    "Bhilwara": (25.34, 74.63), "Alwar": (27.55, 76.63), "Bharatpur": (27.21, 77.48),
    "Sikar": (27.60, 75.13), "Pali": (25.77, 73.32), "Sri Ganganagar": (29.90, 73.87),
    "Barmer": (25.75, 71.41), "Hanumangarh": (29.58, 74.31), "Chittorgarh": (24.88, 74.62),
    
    # Madhya Pradesh
    "Indore": (22.71, 75.85), "Bhopal": (23.25, 77.41), "Jabalpur": (23.18, 79.94),
    "Gwalior": (26.21, 78.17), "Ujjain": (23.17, 75.78), "Sagar": (23.83, 78.73),
    "Dewas": (22.96, 76.05), "Satna": (24.60, 80.83), "Ratlam": (23.33, 75.03),
    "Rewa": (24.53, 81.30), "Murwara (Katni)": (23.83, 80.39), "Singrauli": (24.19, 82.66),
    "Burhanpur": (21.31, 76.21), "Khandwa": (21.83, 76.36), "Morena": (26.49, 78.00),

    # Uttar Pradesh
    "Lucknow": (26.84, 80.94), "Kanpur": (26.44, 80.33), "Ghaziabad": (28.66, 77.45),
    "Agra": (27.17, 78.00), "Varanasi": (25.31, 82.97), "Meerut": (28.98, 77.70),
    "Prayagraj (Allahabad)": (25.43, 81.84), "Bareilly": (28.36, 79.43), "Aligarh": (27.89, 78.08),
    "Moradabad": (28.83, 78.77), "Saharanpur": (29.96, 77.55), "Gorakhpur": (26.76, 83.37),
    "Noida": (28.53, 77.39), "Firozabad": (27.15, 78.39), "Jhansi": (25.44, 78.56),
    "Muzaffarnagar": (29.46, 77.70), "Mathura": (27.49, 77.67), "Ayodhya": (26.79, 82.19),
    "Rampur": (28.80, 79.02), "Shahjahanpur": (27.88, 79.91), "Farrukhabad": (27.38, 79.59),

    # Punjab & Chandigarh
    "Ludhiana": (30.90, 75.85), "Amritsar": (31.63, 74.87), "Jalandhar": (31.32, 75.57),
    "Patiala": (30.33, 76.38), "Bathinda": (30.21, 74.94), "Mohali": (30.70, 76.71),
    "Hoshiarpur": (31.51, 75.91), "Batala": (31.81, 75.20), "Pathankot": (32.26, 75.64),
    "Chandigarh": (30.73, 76.77),

    # Haryana
    "Faridabad": (28.40, 77.31), "Gurgaon": (28.45, 77.02), "Panipat": (29.39, 76.96),
    "Ambala": (30.37, 76.77), "Yamunanagar": (30.12, 77.26), "Rohtak": (28.89, 76.60),
    "Hisar": (29.14, 75.71), "Karnal": (29.68, 76.99), "Sonipat": (28.99, 77.01),
    "Panchkula": (30.69, 76.86),

    # Delhi
    "Delhi": (28.70, 77.10), "New Delhi": (28.61, 77.20),

    # Karnataka
    "Bangalore": (12.97, 77.59), "Hubli": (15.36, 75.12), "Mysore": (12.29, 76.63),
    "Gulbarga": (17.32, 76.83), "Mangalore": (12.91, 74.85), "Belgaum": (15.84, 74.49),
    "Davangere": (14.46, 75.92), "Bellary": (15.13, 76.92), "Bijapur": (16.83, 75.71),
    "Shimoga": (13.92, 75.56), "Tumkur": (13.33, 77.11), "Raichur": (16.20, 77.36),
    "Bidar": (17.91, 77.50), "Hospet": (15.26, 76.38), "Udupi": (13.34, 74.74),

    # Telangana
    "Hyderabad": (17.38, 78.48), "Warangal": (17.96, 79.59), "Nizamabad": (18.67, 78.09),
    "Karimnagar": (18.43, 79.12), "Ramagundam": (18.75, 79.51), "Khammam": (17.24, 80.15),
    "Mahbubnagar": (16.74, 78.00), "Nalgonda": (17.05, 79.26), "Adilabad": (19.66, 78.52),

    # Andhra Pradesh
    "Visakhapatnam": (17.68, 83.21), "Vijayawada": (16.50, 80.64), "Guntur": (16.30, 80.43),
    "Nellore": (14.44, 79.98), "Kurnool": (15.82, 78.03), "Rajahmundry": (16.98, 81.78),
    "Kakinada": (16.98, 82.24), "Tirupati": (13.62, 79.41), "Anantapur": (14.68, 77.60),
    "Kadapa": (14.46, 78.82), "Vizianagaram": (18.10, 83.39), "Eluru": (16.71, 81.09),

    # Tamil Nadu
    "Chennai": (13.08, 80.27), "Coimbatore": (11.01, 76.95), "Madurai": (9.92, 78.11),
    "Tiruchirappalli": (10.79, 78.70), "Salem": (11.66, 78.14), "Tirunelveli": (8.71, 77.75),
    "Tiruppur": (11.10, 77.34), "Erode": (11.34, 77.71), "Vellore": (12.91, 79.13),
    "Thoothukudi": (8.76, 78.13), "Dindigul": (10.36, 77.98), "Thanjavur": (10.78, 79.13),
    "Hosur": (12.74, 77.82), "Nagercoil": (8.18, 77.41), "Kanchipuram": (12.83, 79.70),

    # Kerala
    "Thiruvananthapuram": (8.52, 76.93), "Kochi": (9.93, 76.26), "Kozhikode": (11.25, 75.78),
    "Kollam": (8.89, 76.61), "Thrissur": (10.52, 76.21), "Kannur": (11.87, 75.37),
    "Alappuzha": (9.49, 76.33), "Palakkad": (10.78, 76.65), "Malappuram": (11.07, 76.07),
    "Kottayam": (9.59, 76.52),

    # West Bengal
    "Kolkata": (22.57, 88.36), "Asansol": (23.67, 86.95), "Siliguri": (26.72, 88.39),
    "Durgapur": (23.52, 87.31), "Bardhaman": (23.23, 87.86), "Malda": (25.01, 88.14),
    "Baharampur": (24.10, 88.25), "Habra": (22.84, 88.66), "Kharagpur": (22.34, 87.23),
    "Haldia": (22.06, 88.06),

    # Bihar
    "Patna": (25.59, 85.13), "Gaya": (24.79, 85.00), "Bhagalpur": (25.24, 87.01),
    "Muzaffarpur": (26.11, 85.39), "Purnia": (25.77, 87.47), "Darbhanga": (26.15, 85.89),
    "Bihar Sharif": (25.19, 85.51), "Arrah": (25.55, 84.66), "Begusarai": (25.41, 86.12),
    "Katihar": (25.54, 87.57),

    # Jharkhand
    "Ranchi": (23.34, 85.30), "Jamshedpur": (22.80, 86.20), "Dhanbad": (23.79, 86.43),
    "Bokaro Steel City": (23.66, 86.15), "Deoghar": (24.48, 86.69), "Phusro": (23.76, 85.99),
    "Hazaribagh": (23.99, 85.36), "Giridih": (24.19, 86.29), "Ramgarh": (23.63, 85.51),

    # Odisha
    "Bhubaneswar": (20.29, 85.82), "Cuttack": (20.46, 85.87), "Rourkela": (22.26, 84.85),
    "Berhampur": (19.31, 84.79), "Sambalpur": (21.46, 83.98), "Puri": (19.81, 85.83),
    "Balasore": (21.49, 86.93), "Bhadrak": (21.05, 86.49), "Baripada": (21.93, 86.72),

    # Chhattisgarh
    "Raipur": (21.25, 81.62), "Bhilai": (21.19, 81.38), "Bilaspur": (22.07, 82.14),
    "Korba": (22.35, 82.68), "Durg": (21.19, 81.28), "Rajnandgaon": (21.10, 81.03),
    "Raigarh": (21.89, 83.39), "Jagdalpur": (19.07, 82.01), "Ambikapur": (23.11, 83.19),

    # Assam
    "Guwahati": (26.14, 91.73), "Silchar": (24.83, 92.77), "Dibrugarh": (27.47, 94.91),
    "Jorhat": (26.75, 94.20), "Nagaon": (26.34, 92.68), "Tinsukia": (27.48, 95.38),
    "Tezpur": (26.65, 92.79),

    # Uttarakhand
    "Dehradun": (30.31, 78.03), "Haridwar": (29.94, 78.16), "Roorkee": (29.85, 77.88),
    "Haldwani": (29.21, 79.51), "Rudrapur": (28.98, 79.40), "Kashipur": (29.21, 78.96),

    # Himachal Pradesh
    "Shimla": (31.10, 77.17), "Solan": (30.90, 77.09), "Dharamshala": (32.21, 76.32),
    "Mandi": (31.58, 76.91), "Baddi": (30.95, 76.79),
}

# Combine maps
DESTINATIONS = sorted(list(DESTINATION_COORDS.keys()))

# --- 2. CITY TO STATE MAPPING ---

CITY_STATE_MAP = {
    # Gujarat
    "Ahmedabad": "Gujarat", "Vadodara": "Gujarat", "Surat": "Gujarat",
    "Rajkot": "Gujarat", "Bhavnagar": "Gujarat", "Jamnagar": "Gujarat",
    "Gandhinagar": "Gujarat", "Junagadh": "Gujarat", "Gandhidham": "Gujarat",
    "Anand": "Gujarat", "Navsari": "Gujarat", "Morbi": "Gujarat",
    "Bharuch": "Gujarat", "Palanpur": "Gujarat", "Valsad": "Gujarat",
    "Vapi": "Gujarat", "Mehsana": "Gujarat", "Bhuj": "Gujarat",
    "Porbandar": "Gujarat", "Godhra": "Gujarat", "Veraval": "Gujarat",
    "Surendranagar": "Gujarat", "Patan": "Gujarat", "Amreli": "Gujarat",

    # Maharashtra
    "Mumbai": "Maharashtra", "Pune": "Maharashtra", "Nagpur": "Maharashtra",
    "Nashik": "Maharashtra", "Aurangabad": "Maharashtra", "Solapur": "Maharashtra",
    "Thane": "Maharashtra", "Amravati": "Maharashtra", "Kolhapur": "Maharashtra",
    "Sangli": "Maharashtra", "Jalgaon": "Maharashtra", "Akola": "Maharashtra",
    "Latur": "Maharashtra", "Dhule": "Maharashtra", "Ahmednagar": "Maharashtra",
    "Chandrapur": "Maharashtra", "Parbhani": "Maharashtra", "Jalna": "Maharashtra",
    "Bhiwandi": "Maharashtra", "Ratnagiri": "Maharashtra", "Wardha": "Maharashtra",
    "Satara": "Maharashtra", "Beed": "Maharashtra", "Yavatmal": "Maharashtra",

    # Rajasthan
    "Jaipur": "Rajasthan", "Jodhpur": "Rajasthan", "Kota": "Rajasthan",
    "Bikaner": "Rajasthan", "Ajmer": "Rajasthan", "Udaipur": "Rajasthan",
    "Bhilwara": "Rajasthan", "Alwar": "Rajasthan", "Bharatpur": "Rajasthan",
    "Sikar": "Rajasthan", "Pali": "Rajasthan", "Sri Ganganagar": "Rajasthan",
    "Barmer": "Rajasthan", "Hanumangarh": "Rajasthan", "Chittorgarh": "Rajasthan",

    # Madhya Pradesh
    "Indore": "Madhya Pradesh", "Bhopal": "Madhya Pradesh", "Jabalpur": "Madhya Pradesh",
    "Gwalior": "Madhya Pradesh", "Ujjain": "Madhya Pradesh", "Sagar": "Madhya Pradesh",
    "Dewas": "Madhya Pradesh", "Satna": "Madhya Pradesh", "Ratlam": "Madhya Pradesh",
    "Rewa": "Madhya Pradesh", "Murwara (Katni)": "Madhya Pradesh", "Singrauli": "Madhya Pradesh",
    "Burhanpur": "Madhya Pradesh", "Khandwa": "Madhya Pradesh", "Morena": "Madhya Pradesh",

    # Uttar Pradesh
    "Lucknow": "Uttar Pradesh", "Kanpur": "Uttar Pradesh", "Ghaziabad": "Uttar Pradesh",
    "Agra": "Uttar Pradesh", "Varanasi": "Uttar Pradesh", "Meerut": "Uttar Pradesh",
    "Prayagraj (Allahabad)": "Uttar Pradesh", "Bareilly": "Uttar Pradesh", "Aligarh": "Uttar Pradesh",
    "Moradabad": "Uttar Pradesh", "Saharanpur": "Uttar Pradesh", "Gorakhpur": "Uttar Pradesh",
    "Noida": "Uttar Pradesh", "Firozabad": "Uttar Pradesh", "Jhansi": "Uttar Pradesh",
    "Muzaffarnagar": "Uttar Pradesh", "Mathura": "Uttar Pradesh", "Ayodhya": "Uttar Pradesh",
    "Rampur": "Uttar Pradesh", "Shahjahanpur": "Uttar Pradesh", "Farrukhabad": "Uttar Pradesh",

    # Punjab
    "Ludhiana": "Punjab", "Amritsar": "Punjab", "Jalandhar": "Punjab",
    "Patiala": "Punjab", "Bathinda": "Punjab", "Mohali": "Punjab",
    "Hoshiarpur": "Punjab", "Batala": "Punjab", "Pathankot": "Punjab",
    "Chandigarh": "Chandigarh", # UT

    # Haryana
    "Faridabad": "Haryana", "Gurgaon": "Haryana", "Panipat": "Haryana",
    "Ambala": "Haryana", "Yamunanagar": "Haryana", "Rohtak": "Haryana",
    "Hisar": "Haryana", "Karnal": "Haryana", "Sonipat": "Haryana",
    "Panchkula": "Haryana",

    # Delhi
    "Delhi": "Delhi", "New Delhi": "Delhi",

    # Karnataka
    "Bangalore": "Karnataka", "Hubli": "Karnataka", "Mysore": "Karnataka",
    "Gulbarga": "Karnataka", "Mangalore": "Karnataka", "Belgaum": "Karnataka",
    "Davangere": "Karnataka", "Bellary": "Karnataka", "Bijapur": "Karnataka",
    "Shimoga": "Karnataka", "Tumkur": "Karnataka", "Raichur": "Karnataka",
    "Bidar": "Karnataka", "Hospet": "Karnataka", "Udupi": "Karnataka",

    # Telangana
    "Hyderabad": "Telangana", "Warangal": "Telangana", "Nizamabad": "Telangana",
    "Karimnagar": "Telangana", "Ramagundam": "Telangana", "Khammam": "Telangana",
    "Mahbubnagar": "Telangana", "Nalgonda": "Telangana", "Adilabad": "Telangana",

    # Andhra Pradesh
    "Visakhapatnam": "Andhra Pradesh", "Vijayawada": "Andhra Pradesh", "Guntur": "Andhra Pradesh",
    "Nellore": "Andhra Pradesh", "Kurnool": "Andhra Pradesh", "Rajahmundry": "Andhra Pradesh",
    "Kakinada": "Andhra Pradesh", "Tirupati": "Andhra Pradesh", "Anantapur": "Andhra Pradesh",
    "Kadapa": "Andhra Pradesh", "Vizianagaram": "Andhra Pradesh", "Eluru": "Andhra Pradesh",

    # Tamil Nadu
    "Chennai": "Tamil Nadu", "Coimbatore": "Tamil Nadu", "Madurai": "Tamil Nadu",
    "Tiruchirappalli": "Tamil Nadu", "Salem": "Tamil Nadu", "Tirunelveli": "Tamil Nadu",
    "Tiruppur": "Tamil Nadu", "Erode": "Tamil Nadu", "Vellore": "Tamil Nadu",
    "Thoothukudi": "Tamil Nadu", "Dindigul": "Tamil Nadu", "Thanjavur": "Tamil Nadu",
    "Hosur": "Tamil Nadu", "Nagercoil": "Tamil Nadu", "Kanchipuram": "Tamil Nadu",

    # Kerala
    "Thiruvananthapuram": "Kerala", "Kochi": "Kerala", "Kozhikode": "Kerala",
    "Kollam": "Kerala", "Thrissur": "Kerala", "Kannur": "Kerala",
    "Alappuzha": "Kerala", "Palakkad": "Kerala", "Malappuram": "Kerala",
    "Kottayam": "Kerala",

    # West Bengal
    "Kolkata": "West Bengal", "Asansol": "West Bengal", "Siliguri": "West Bengal",
    "Durgapur": "West Bengal", "Bardhaman": "West Bengal", "Malda": "West Bengal",
    "Baharampur": "West Bengal", "Habra": "West Bengal", "Kharagpur": "West Bengal",
    "Haldia": "West Bengal",

    # Bihar
    "Patna": "Bihar", "Gaya": "Bihar", "Bhagalpur": "Bihar",
    "Muzaffarpur": "Bihar", "Purnia": "Bihar", "Darbhanga": "Bihar",
    "Bihar Sharif": "Bihar", "Arrah": "Bihar", "Begusarai": "Bihar",
    "Katihar": "Bihar",

    # Jharkhand
    "Ranchi": "Jharkhand", "Jamshedpur": "Jharkhand", "Dhanbad": "Jharkhand",
    "Bokaro Steel City": "Jharkhand", "Deoghar": "Jharkhand", "Phusro": "Jharkhand",
    "Hazaribagh": "Jharkhand", "Giridih": "Jharkhand", "Ramgarh": "Jharkhand",

    # Odisha
    "Bhubaneswar": "Odisha", "Cuttack": "Odisha", "Rourkela": "Odisha",
    "Berhampur": "Odisha", "Sambalpur": "Odisha", "Puri": "Odisha",
    "Balasore": "Odisha", "Bhadrak": "Odisha", "Baripada": "Odisha",

    # Chhattisgarh
    "Raipur": "Chhattisgarh", "Bhilai": "Chhattisgarh", "Bilaspur": "Chhattisgarh",
    "Korba": "Chhattisgarh", "Durg": "Chhattisgarh", "Rajnandgaon": "Chhattisgarh",
    "Raigarh": "Chhattisgarh", "Jagdalpur": "Chhattisgarh", "Ambikapur": "Chhattisgarh",

    # Assam
    "Guwahati": "Assam", "Silchar": "Assam", "Dibrugarh": "Assam",
    "Jorhat": "Assam", "Nagaon": "Assam", "Tinsukia": "Assam",
    "Tezpur": "Assam",

    # Uttarakhand
    "Dehradun": "Uttarakhand", "Haridwar": "Uttarakhand", "Roorkee": "Uttarakhand",
    "Haldwani": "Uttarakhand", "Rudrapur": "Uttarakhand", "Kashipur": "Uttarakhand",

    # Himachal Pradesh
    "Shimla": "Himachal Pradesh", "Solan": "Himachal Pradesh", "Dharamshala": "Himachal Pradesh",
    "Mandi": "Himachal Pradesh", "Baddi": "Himachal Pradesh",
}

# Get unique states
ALL_STATES = sorted(list(set(CITY_STATE_MAP.values())))

# --- 3. HELPER FUNCTIONS ---

def get_cities_by_state(state):
    """Get all cities in a given state."""
    return sorted([city for city, st in CITY_STATE_MAP.items() if st == state])

def get_state_by_city(city):
    """Get state for a given city."""
    return CITY_STATE_MAP.get(city, "Unknown")

def get_clean_state(raw_city):
    """
    Robust state lookup that handles formatted city names like 'Mumbai (Chembur)'.
    """
    if not raw_city: return "Unknown"
    
    # Cleaning city name (e.g. "Mumbai (Chembur)" -> "Mumbai")
    clean_city = raw_city.split('(')[0].strip()
    
    # Check exact map first
    state = CITY_STATE_MAP.get(clean_city)
    if state: return state

    # Manual Mapping for specific cases common in supply chain
    if 'Navi Mumbai' in raw_city: return 'Maharashtra'
    if 'Chembur' in raw_city: return 'Maharashtra'
    if 'Taloja' in raw_city: return 'Maharashtra'
    if 'Kandla' in raw_city or 'Mundra' in raw_city: return 'Gujarat'
    if 'Haldia' in raw_city: return 'West Bengal'
    if 'Bhatinda' in raw_city: return 'Punjab'
    if 'Mangalore' in raw_city: return 'Karnataka'
    
    # Fallback for capitals if needed
    if clean_city in ['Delhi', 'New Delhi']: return 'Delhi'
    if clean_city == 'Guwahati': return 'Assam'
    if clean_city == 'Bhubaneswar': return 'Odisha'
    if clean_city == 'Kolkata': return 'West Bengal'
    
    return "Unknown"

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points using Haversine formula."""
    R = 6371  # Earth's radius in km
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    # Road distance is typically 1.3x straight line distance
    return round(R * c * 1.3, 0)

def get_distance(source_name, destination_name):
    """Get road distance between source and destination."""
    if source_name not in SOURCE_COORDS:
        return 0
    if destination_name not in DESTINATION_COORDS:
        return 0
    
    src = SOURCE_COORDS[source_name]
    dst = DESTINATION_COORDS[destination_name]
    
    return haversine_distance(src[0], src[1], dst[0], dst[1])

def get_all_distances_for_destination(destination_name):
    """Get distances from all sources to a destination."""
    distances = {}
    for source in SOURCE_COORDS:
        distances[source] = get_distance(source, destination_name)
    return distances

def get_nearest_sources(destination_name, n=3):
    """Get n nearest sources to a destination."""
    distances = get_all_distances_for_destination(destination_name)
    sorted_sources = sorted(distances.items(), key=lambda x: x[1])
    return sorted_sources[:n]

# Pre-calculate common routes
DISTANCE_MATRIX = {}
for dest in DESTINATIONS:
    DISTANCE_MATRIX[dest] = get_all_distances_for_destination(dest)
