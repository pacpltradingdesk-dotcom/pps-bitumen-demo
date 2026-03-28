try:
    from india_localization import format_inr, format_inr_short, format_date, format_datetime_ist, get_financial_year, get_fy_quarter
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    try:
        from india_localization import format_inr, format_inr_short, format_date, format_datetime_ist, get_financial_year, get_fy_quarter
    except:
        pass
# Feasibility Assessment Engine - Updated
# Includes: PSU Refineries, Import Bulk, Local Decanters, and Drum Pricing

from source_master import INDIAN_REFINERIES, IMPORT_TERMINALS, PRIVATE_DECANTERS, ALL_SOURCES
from distance_matrix import get_distance, DESTINATION_COORDS
import os
import json
from pathlib import Path

# --- LIVE PRICE CONFIG FILE ---
PRICE_CONFIG_FILE = Path(__file__).parent / "live_prices.json"

def get_live_prices():
    """Load live prices from config file."""
    default_prices = {
        # PSU Refineries (VG30 Bulk)
        "IOCL Koyali": 42000,
        "IOCL Mathura": 42500,
        "IOCL Haldia": 41800,
        "IOCL Barauni": 41500,
        "IOCL Panipat": 42200,
        "BPCL Mumbai": 43000,
        "BPCL Kochi": 42800,
        "HPCL Mumbai": 42900,
        "HPCL Visakhapatnam": 41600,
        "CPCL Chennai": 42100,
        "MRPL Mangalore": 41900,
        "IOCL Digboi": 41000,
        "IOCL Guwahati": 41200,
        "IOCL Bongaigaon": 41100,
        "NRL Numaligarh": 41300,
        "ONGC Tatipaka": 41500,
        
        # Import Bulk Terminals
        "Mangalore Port Import": 38500,
        "Karwar Port Import": 38800,
        "Digi Port Import": 39000,
        "Taloja Terminal": 39500,
        "VVF Mumbai Terminal": 39200,
        "Kandla Port Import": 38000,
        "Mundra Port Import": 37800,
        "JNPT Import Terminal": 39800,
        
        # DRUM BITUMEN PRICES (Only 2 locations)
        "DRUM_MUMBAI_VG30": 37000,
        "DRUM_KANDLA_VG30": 35500,
        "DRUM_MUMBAI_VG10": 38000,
        "DRUM_KANDLA_VG10": 36500,
        
        # Decanter Conversion Cost
        "DECANTER_CONVERSION_COST": 500,
        
        # Transport Rates
        "BULK_RATE_PER_KM": 5.5,
        "DRUM_RATE_PER_KM": 6.0,
    }
    
    if os.path.exists(PRICE_CONFIG_FILE):
        try:
            with open(PRICE_CONFIG_FILE, 'r') as f:
                saved = json.load(f)
                default_prices.update(saved)
        except:
            pass
    
    return default_prices

def save_live_prices(prices):
    """Save live prices to config file."""
    with open(PRICE_CONFIG_FILE, 'w') as f:
        json.dump(prices, f, indent=2)
    return True

# Load prices
LIVE_PRICES = get_live_prices()

# --- NORTH INDIA STATES (Kandla serves these for Drum) ---
KANDLA_DRUM_STATES = [
    "Gujarat", "Rajasthan", "Madhya Pradesh", "Uttar Pradesh", "Delhi",
    "Haryana", "Punjab", "Himachal Pradesh", "Jammu & Kashmir", "Uttarakhand",
    "Bihar", "Jharkhand", "Chhattisgarh", "West Bengal", "Odisha"
]

# Cities served by Kandla for Drum
KANDLA_DRUM_CITIES = [
    "Ahmedabad", "Vadodara", "Surat", "Rajkot", "Kutch", "Jaipur", "Udaipur",
    "Delhi", "Lucknow", "Agra", "Kanpur", "Patna", "Ranchi", "Kolkata",
    "Bhopal", "Indore", "Gwalior", "Chandigarh", "Ludhiana", "Amritsar",
    "Nagpur", "Nashik", "Aurangabad"  # Parts of Maharashtra
]

# Cities served by Mumbai for Drum
MUMBAI_DRUM_CITIES = [
    "Mumbai", "Pune", "Bangalore", "Chennai", "Hyderabad", "Kochi",
    "Mysore", "Mangalore", "Visakhapatnam", "Coimbatore", "Goa"
]

# Distance from Kandla to major cities (for drum transport)
KANDLA_COORDS = (23.03, 70.22)
MUMBAI_COORDS = (19.08, 72.88)

import math

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points."""
    R = 6371
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return round(R * c * 1.3, 0)  # 1.3x for road distance

def get_drum_source_for_city(city):
    """Determine which drum loading point serves this city."""
    if city in KANDLA_DRUM_CITIES:
        return "Kandla"
    elif city in MUMBAI_DRUM_CITIES:
        return "Mumbai"
    else:
        # Default based on distance
        if city in DESTINATION_COORDS:
            dest = DESTINATION_COORDS[city]
            dist_kandla = haversine_distance(KANDLA_COORDS[0], KANDLA_COORDS[1], dest[0], dest[1])
            dist_mumbai = haversine_distance(MUMBAI_COORDS[0], MUMBAI_COORDS[1], dest[0], dest[1])
            return "Kandla" if dist_kandla < dist_mumbai else "Mumbai"
        return "Kandla"

def calculate_landed_cost(source_name, destination, base_price=None, rate_per_km=None):
    """Calculate landed cost for bulk from any source."""
    prices = get_live_prices()
    
    if base_price is None:
        base_price = prices.get(source_name, 42000)
    
    if rate_per_km is None:
        rate_per_km = prices.get("BULK_RATE_PER_KM", 5.5)
    
    distance = get_distance(source_name, destination)
    transport = distance * rate_per_km
    
    # GST 18%
    ex_refinery = base_price * 1.18
    landed = ex_refinery + transport
    
    return {
        "source": source_name,
        "destination": destination,
        "distance_km": distance,
        "base_price": base_price,
        "ex_refinery": round(ex_refinery, 2),
        "transport": round(transport, 2),
        "landed_cost": round(landed, 2)
    }

def calculate_decanter_cost(destination, grade="VG30"):
    """
    Calculate decanter bulk cost for a city.
    Decanters are 30km from city center, charge ₹500 conversion.
    Drum comes from Kandla or Mumbai.
    """
    prices = get_live_prices()
    
    # Get drum source
    drum_source = get_drum_source_for_city(destination)
    
    # Get drum base price
    if drum_source == "Kandla":
        drum_price = prices.get(f"DRUM_KANDLA_{grade}", 35500)
        drum_coords = KANDLA_COORDS
    else:
        drum_price = prices.get(f"DRUM_MUMBAI_{grade}", 37000)
        drum_coords = MUMBAI_COORDS
    
    # Distance from drum source to destination
    if destination in DESTINATION_COORDS:
        dest_coords = DESTINATION_COORDS[destination]
        drum_transport_dist = haversine_distance(drum_coords[0], drum_coords[1], dest_coords[0], dest_coords[1])
    else:
        drum_transport_dist = 500  # Default
    
    drum_rate = prices.get("DRUM_RATE_PER_KM", 6.0)
    drum_transport = drum_transport_dist * drum_rate
    
    # Decanter is 30km from city, conversion cost
    decanter_distance = 30
    conversion_cost = prices.get("DECANTER_CONVERSION_COST", 500)
    local_transport = decanter_distance * prices.get("BULK_RATE_PER_KM", 5.5)
    
    # Total calculation
    # Drum reaches decanter (near city) + conversion + local transport to site
    drum_with_gst = drum_price * 1.18
    total_landed = drum_with_gst + drum_transport + conversion_cost + local_transport
    
    return {
        "source": f"Local Decanter ({destination})",
        "destination": destination,
        "drum_source": drum_source,
        "drum_base_price": drum_price,
        "drum_transport": round(drum_transport, 2),
        "conversion_cost": conversion_cost,
        "local_transport": round(local_transport, 2),
        "distance_km": decanter_distance,
        "landed_cost": round(total_landed, 2),
        "category": "LOCAL_DECANTER"
    }

def calculate_drum_direct_cost(destination, grade="VG30"):
    """Calculate drum bitumen cost delivered directly (no decanting)."""
    prices = get_live_prices()
    
    drum_source = get_drum_source_for_city(destination)
    
    if drum_source == "Kandla":
        base_price = prices.get(f"DRUM_KANDLA_{grade}", 35500)
        source_coords = KANDLA_COORDS
        source_name = "Kandla Drum Import"
    else:
        base_price = prices.get(f"DRUM_MUMBAI_{grade}", 37000)
        source_coords = MUMBAI_COORDS
        source_name = "Mumbai Drum Import"
    
    if destination in DESTINATION_COORDS:
        dest_coords = DESTINATION_COORDS[destination]
        distance = haversine_distance(source_coords[0], source_coords[1], dest_coords[0], dest_coords[1])
    else:
        distance = 500
    
    drum_rate = prices.get("DRUM_RATE_PER_KM", 6.0)
    transport = distance * drum_rate
    
    base_with_gst = base_price * 1.18
    total = base_with_gst + transport
    
    return {
        "source": source_name,
        "destination": destination,
        "distance_km": distance,
        "base_price": base_price,
        "transport": round(transport, 2),
        "landed_cost": round(total, 2),
        "category": "DRUM"
    }

def get_feasibility_assessment(destination, top_n=2, grade="VG30"):
    """
    Get full feasibility assessment including:
    - Top N PSU Refineries
    - Top N Import Bulk Terminals
    - Local Decanter option (drum to bulk)
    - Direct Drum option
    """
    
    if destination not in DESTINATION_COORDS:
        return None
    
    prices = get_live_prices()
    
    # Calculate for all refineries
    refinery_options = []
    for r in INDIAN_REFINERIES:
        result = calculate_landed_cost(r['name'], destination)
        result['category'] = "REFINERY"
        result['city'] = r['city']
        refinery_options.append(result)
    
    # Calculate for all import terminals
    import_options = []
    for r in IMPORT_TERMINALS:
        result = calculate_landed_cost(r['name'], destination)
        result['category'] = "IMPORT"
        result['city'] = r['city']
        import_options.append(result)
    
    # Local Decanter option (drum to bulk conversion)
    local_decanter = calculate_decanter_cost(destination, grade)
    
    # Direct Drum option
    drum_direct = calculate_drum_direct_cost(destination, grade)
    
    # Sort by landed cost
    refinery_options.sort(key=lambda x: x['landed_cost'])
    import_options.sort(key=lambda x: x['landed_cost'])
    
    # Best overall (only bulk options)
    all_bulk_options = refinery_options[:1] + import_options[:1] + [local_decanter]
    best_overall = min(all_bulk_options, key=lambda x: x['landed_cost']) if all_bulk_options else None
    
    return {
        "destination": destination,
        "grade": grade,
        "refineries": refinery_options[:top_n],
        "imports": import_options[:top_n],
        "local_decanter": local_decanter,
        "drum_direct": drum_direct,
        "best_overall": best_overall,
        "live_prices": {
            "drum_mumbai": prices.get(f"DRUM_MUMBAI_{grade}"),
            "drum_kandla": prices.get(f"DRUM_KANDLA_{grade}"),
            "decanter_cost": prices.get("DECANTER_CONVERSION_COST")
        }
    }

def get_comparison_table(destination):
    """Get a comparison table of all options."""
    assessment = get_feasibility_assessment(destination, top_n=2)
    
    if not assessment:
        return None
    
    rows = []
    
    # Add refineries
    for i, opt in enumerate(assessment['refineries']):
        rows.append({
            "Rank": i + 1,
            "Category": "🏭 Refinery",
            "Source": opt['source'],
            "Distance (KM)": f"{opt['distance_km']:,.0f}",
            "Base Price": f"{format_inr(opt['base_price'])}",
            "Transport": f"{format_inr(opt['transport'])}",
            "Landed Cost": f"{format_inr(opt['landed_cost'])}"
        })
    
    # Add imports
    for i, opt in enumerate(assessment['imports']):
        rows.append({
            "Rank": i + 1,
            "Category": "🚢 Import Bulk",
            "Source": opt['source'],
            "Distance (KM)": f"{opt['distance_km']:,.0f}",
            "Base Price": f"{format_inr(opt['base_price'])}",
            "Transport": f"{format_inr(opt['transport'])}",
            "Landed Cost": f"{format_inr(opt['landed_cost'])}"
        })
    
    # Add local decanter
    dec = assessment['local_decanter']
    rows.append({
        "Rank": 1,
        "Category": "🔄 Local Decanter",
        "Source": dec['source'],
        "Distance (KM)": f"{dec['distance_km']:,.0f} (local)",
        "Base Price": f"{format_inr(dec['drum_base_price'])} + {dec['conversion_cost']}",
        "Transport": f"{format_inr(dec['drum_transport'])} + {format_inr(dec['local_transport'])}",
        "Landed Cost": f"{format_inr(dec['landed_cost'])}"
    })
    
    # Add drum direct
    drum = assessment['drum_direct']
    rows.append({
        "Rank": 1,
        "Category": "🛢️ Drum Direct",
        "Source": drum['source'],
        "Distance (KM)": f"{drum['distance_km']:,.0f}",
        "Base Price": f"{format_inr(drum['base_price'])}",
        "Transport": f"{format_inr(drum['transport'])}",
        "Landed Cost": f"{format_inr(drum['landed_cost'])}"
    })
    
    return rows

# Quick test
if __name__ == "__main__":
    result = get_feasibility_assessment("Ahmedabad")
    print(f"Best options for Ahmedabad:")
    print(f"Refineries: {[r['source'] for r in result['refineries']]}")
    print(f"Imports: {[r['source'] for r in result['imports']]}")
    print(f"Local Decanter: {result['local_decanter']['landed_cost']}")
    print(f"Drum Direct: {result['drum_direct']['landed_cost']}")
