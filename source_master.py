# Master Data for Sources - Categorized by Type
# This file defines all loading points with their categories

SOURCE_CATEGORIES = {
    "INDIAN_REFINERY": "🏭 Indian Refinery (PSU)",
    "IMPORT_TERMINAL": "🚢 Import Terminal",
    "PRIVATE_DECANTER": "🔄 Private Decanter"
}

# Indian Refineries (PSU - Public Sector Undertakings)
INDIAN_REFINERIES = [
    {"name": "IOCL Koyali", "city": "Vadodara", "state": "Gujarat", "category": "INDIAN_REFINERY"},
    {"name": "IOCL Mathura", "city": "Mathura", "state": "Uttar Pradesh", "category": "INDIAN_REFINERY"},
    {"name": "IOCL Haldia", "city": "Haldia", "state": "West Bengal", "category": "INDIAN_REFINERY"},
    {"name": "IOCL Barauni", "city": "Barauni", "state": "Bihar", "category": "INDIAN_REFINERY"},
    {"name": "IOCL Panipat", "city": "Panipat", "state": "Haryana", "category": "INDIAN_REFINERY"},
    {"name": "IOCL Digboi", "city": "Digboi", "state": "Assam", "category": "INDIAN_REFINERY"},
    {"name": "IOCL Guwahati", "city": "Guwahati", "state": "Assam", "category": "INDIAN_REFINERY"},
    {"name": "IOCL Bongaigaon", "city": "Bongaigaon", "state": "Assam", "category": "INDIAN_REFINERY"},
    {"name": "BPCL Mumbai", "city": "Mumbai", "state": "Maharashtra", "category": "INDIAN_REFINERY"},
    {"name": "BPCL Kochi", "city": "Kochi", "state": "Kerala", "category": "INDIAN_REFINERY"},
    {"name": "HPCL Mumbai", "city": "Mumbai", "state": "Maharashtra", "category": "INDIAN_REFINERY"},
    {"name": "HPCL Visakhapatnam", "city": "Visakhapatnam", "state": "Andhra Pradesh", "category": "INDIAN_REFINERY"},
    {"name": "CPCL Chennai", "city": "Chennai", "state": "Tamil Nadu", "category": "INDIAN_REFINERY"},
    {"name": "MRPL Mangalore", "city": "Mangalore", "state": "Karnataka", "category": "INDIAN_REFINERY"},
    {"name": "NRL Numaligarh", "city": "Numaligarh", "state": "Assam", "category": "INDIAN_REFINERY"},
    {"name": "ONGC Tatipaka", "city": "Tatipaka", "state": "Andhra Pradesh", "category": "INDIAN_REFINERY"},
]

# Import Terminals (Bulk Import Ports)
IMPORT_TERMINALS = [
    {"name": "Mangalore Port Import", "city": "Mangalore", "state": "Karnataka", "category": "IMPORT_TERMINAL"},
    {"name": "Karwar Port Import", "city": "Karwar", "state": "Karnataka", "category": "IMPORT_TERMINAL"},
    {"name": "Digi Port Import", "city": "Digi Port", "state": "Gujarat", "category": "IMPORT_TERMINAL"},
    {"name": "Taloja Terminal", "city": "Taloja", "state": "Maharashtra", "category": "IMPORT_TERMINAL"},
    {"name": "VVF Mumbai Terminal", "city": "Mumbai", "state": "Maharashtra", "category": "IMPORT_TERMINAL"},
    {"name": "Kandla Port Import", "city": "Kandla", "state": "Gujarat", "category": "IMPORT_TERMINAL"},
    {"name": "Mundra Port Import", "city": "Mundra", "state": "Gujarat", "category": "IMPORT_TERMINAL"},
    {"name": "JNPT Import Terminal", "city": "Nhava Sheva", "state": "Maharashtra", "category": "IMPORT_TERMINAL"},
]

# Private Decanters (Drum to Bulk Conversion)
PRIVATE_DECANTERS = [
    {"name": "Ahmedabad Decanter", "city": "Ahmedabad", "state": "Gujarat", "category": "PRIVATE_DECANTER"},
    {"name": "Vadodara Decanter", "city": "Vadodara", "state": "Gujarat", "category": "PRIVATE_DECANTER"},
    {"name": "Kutch Decanter", "city": "Kutch", "state": "Gujarat", "category": "PRIVATE_DECANTER"},
    {"name": "Mathura Decanter", "city": "Mathura", "state": "Uttar Pradesh", "category": "PRIVATE_DECANTER"},
    {"name": "Jaipur Decanter", "city": "Jaipur", "state": "Rajasthan", "category": "PRIVATE_DECANTER"},
    {"name": "Indore Decanter", "city": "Indore", "state": "Madhya Pradesh", "category": "PRIVATE_DECANTER"},
    {"name": "Pune Decanter", "city": "Pune", "state": "Maharashtra", "category": "PRIVATE_DECANTER"},
    {"name": "Hyderabad Decanter", "city": "Hyderabad", "state": "Telangana", "category": "PRIVATE_DECANTER"},
]

# Combined Master List
ALL_SOURCES = INDIAN_REFINERIES + IMPORT_TERMINALS + PRIVATE_DECANTERS

def get_sources_by_category(category):
    """Returns list of sources for a given category."""
    return [s for s in ALL_SOURCES if s['category'] == category]

def get_all_source_names():
    """Returns list of all source names."""
    return [s['name'] for s in ALL_SOURCES]

def get_source_category(source_name):
    """Returns category of a source."""
    for s in ALL_SOURCES:
        if s['name'] == source_name:
            return s['category']
    return "UNKNOWN"

def get_category_label(category_key):
    """Returns display label for category."""
    return SOURCE_CATEGORIES.get(category_key, category_key)
