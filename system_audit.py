
import os
import json
import sys
import importlib.util

# Set encoding to handle symbols
sys.stdout.reconfigure(encoding='utf-8')

def check_file(path, description):
    exists = os.path.exists(path)
    status = "OK" if exists else "MISSING"
    print(f"{description:30} : {status} ({path})")
    return exists

def check_json_data(path, description):
    if not os.path.exists(path):
        print(f"{description:30} : MISSING")
        return False
    try:
        with open(path, 'r') as f:
            data = json.load(f)
            count = len(data)
            print(f"{description:30} : OK (Entries: {count})")
            return True
    except json.JSONDecodeError:
        print(f"{description:30} : CORRUPT/INVALID JSON")
        return False

print("--- BITUMEN DASHBOARD SYSTEM AUDIT ---\n")

# 1. CORE FILES
print(">> CHECKING CORE MODULES")
check_file("dashboard.py", "Main Dashboard App")
check_file("sales_workspace.py", "Sales Workspace Module")
check_file("party_master.py", "Party Management Module")
check_file("distance_matrix.py", "Distance/Map Module")
check_file("feasibility_engine.py", "Costing Engine")
check_file("sales_calendar.py", "Calendar Module")

# 2. DATA FILES
print("\n>> CHECKING DATABASE")
check_json_data("purchase_parties.json", "Suppliers Database")
check_json_data("sales_parties.json", "Customers Database")
check_json_data("service_providers.json", "Transporters Database")

# 3. INTEGRATION CHECK
print("\n>> CHECKING INTEGRATIONS")
# Verify sales_workspace has the main render function
try:
    import sales_workspace
    if hasattr(sales_workspace, 'render_deal_room'):
        print(f"{'Sales Workspace Function':30} : FOUND")
    else:
        print(f"{'Sales Workspace Function':30} : MISSING 'render_deal_room'")
except ImportError:
    print(f"{'Sales Workspace Module':30} : IMPORT FAILED")

# 4. ENVIRONMENT
print("\n>> ENVIRONMENT")
cwd = os.getcwd()
print(f"Working Directory: {cwd}")

print("\n--- AUDIT COMPLETE ---")
