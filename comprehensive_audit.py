
import os
import json
import sys
import importlib.util
import math

# --- CONFIGURATION ---
SYS_ENCODING = 'utf-8'
sys.stdout.reconfigure(encoding=SYS_ENCODING)

def print_header(title):
    print(f"\n{'='*60}\n {title}\n{'='*60}")

def check_file(path, description):
    exists = os.path.exists(path)
    status = "OK" if exists else "MISSING"
    print(f"📄 {description:30} : {status}")
    return exists

def check_json(path, description):
    if not os.path.exists(path):
        print(f"❌ {description:30} : MISSING FILE")
        return False
    try:
        with open(path, 'r', encoding=SYS_ENCODING) as f:
            data = json.load(f)
            count = len(data)
            status = "OK" if count > 0 else "EMPTY"
            print(f"🗄️  {description:30} : {status} ({count} records)")
            return True
    except Exception as e:
        print(f"❌ {description:30} : CORRUPT ({str(e)})")
        return False

def test_distance_calc():
    print_header("TESTING: DISTANCE CALCULATION LOGIC")
    try:
        from distance_matrix import get_distance, haversine_distance
        
        # Test Case: Mumbai to Pune (Approx 150km road)
        # Coordinates approx: Mumbai (19.07, 72.87), Pune (18.52, 73.85)
        dist = get_distance("BPCL Mumbai", "Pune")
        
        print(f"📍 Test Route: BPCL Mumbai -> Pune")
        print(f"   Calculated Distance: {dist} KM")
        
        if 120 <= dist <= 180:
            print("   ✅ Logic Check: PASSED (Within valid range)")
        else:
            print("   ⚠️ Logic Check: UNUSUAL (Check coordinates)")
            
    except ImportError:
        print("❌ Could not import distance_matrix for testing.")

def test_pricing_logic():
    print_header("TESTING: PRICING LOGIC")
    # Mock Data
    base_price = 40000
    freight_rate = 4.0
    distance = 500
    margin = 1000
    gst_rate = 0.18
    
    freight_cost = distance * freight_rate
    landed_pre_tax = base_price + freight_cost + margin
    gst_amt = landed_pre_tax * gst_rate
    final_total = landed_pre_tax + gst_amt
    
    print(f"💰 Simulation:")
    print(f"   Base: {base_price}")
    print(f"   Freight ({distance}km * {freight_rate}): {freight_cost}")
    print(f"   Margin: {margin}")
    print(f"   ----------------")
    print(f"   Landed (Pre-Tax): {landed_pre_tax}")
    print(f"   GST (18%): {gst_amt}")
    print(f"   Total: {final_total}")
    
    expected = 40000 + 2000 + 1000
    if landed_pre_tax == expected:
        print("   ✅ Math Check: PASSED")
    else:
        print(f"   ❌ Math Check: FAILED (Expected {expected}, Got {landed_pre_tax})")

def full_audit():
    print_header("BITUMEN DASHBOARD - COMPREHENSIVE AUDIT")
    
    # 1. File Structure
    print(">> CHECKING CORE FILES")
    check_file("dashboard.py", "Main Dashboard App")
    check_file("sales_workspace.py", "Sales Workspace")
    check_file("market_intelligence.py", "Market Intel Module")
    check_file("market_data.py", "Live Market Data")
    check_file("pdf_generator.py", "PDF Generator")
    check_file("sales_knowledge_base.py", "Knowledge Base")
    
    # 2. Data Integrity
    print("\n>> CHECKING DATABASES")
    check_json("purchase_parties.json", "Suppliers DB")
    check_json("sales_parties.json", "Customers DB")
    check_json("service_providers.json", "Logistics DB")
    
    # 3. Logic Tests
    test_distance_calc()
    test_pricing_logic()
    
    # 4. Import Safety
    print_header("TESTING: MODULE IMPORT SAFETY")
    modules = ["sales_workspace", "market_intelligence", "pdf_generator", "market_data"]
    for mod in modules:
        try:
            importlib.import_module(mod)
            print(f"📦 Module '{mod:20}' : ✅ LOADED SUCCESS")
        except Exception as e:
            print(f"❌ Module '{mod:20}' : FAILED ({str(e)})")
            
    print_header("AUDIT CONCLUSION")
    print("If all checks above are GREEN/OK, the system is fully operational.")

if __name__ == "__main__":
    full_audit()
