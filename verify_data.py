
import json
import os
import pandas as pd
import sys

# Force UTF-8 for output
sys.stdout.reconfigure(encoding='utf-8')

# Files
PURCHASE_FILE = 'purchase_parties.json'
SERVICE_FILE = 'service_providers.json'
SALES_FILE = 'sales_parties.json'

def verify_file(filename, label):
    print(f"\n--- VERIFYING {label} ({filename}) ---")
    if not os.path.exists(filename):
        print(f"[MISSING] File {filename} not found.")
        return
    
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
        
        count = len(data)
        print(f"[OK] File loaded successfully. Total Entries: {count}")
        
        if count > 0:
            df = pd.DataFrame(data)
            
            # Check for name duplicates
            if 'name' in df.columns:
                duplicates = df[df.duplicated(subset=['name'], keep=False)]
                if not duplicates.empty:
                    print(f"[WARN] {len(duplicates)} duplicate names found:")
                    print(duplicates['name'].unique())
                else:
                    print("[OK] No duplicates found.")
            
            # Show breakdown by 'type' or 'category'
            if 'type' in df.columns:
                print("\nBreakdown by Type:")
                print(df['type'].value_counts().to_string())
            elif 'category' in df.columns:
                print("\nBreakdown by Category:")
                print(df['category'].value_counts().to_string())
            
            # Show City coverage
            if 'city' in df.columns:
                unique_cities = df['city'].nunique()
                print(f"\nCities Covered: {unique_cities}")
                print("Top 5 Cities:")
                print(df['city'].value_counts().head(5).to_string())

    except Exception as e:
        print(f"[ERROR] JSON Error: {e}")

# Run Verifications
verify_file(PURCHASE_FILE, "SUPPLIERS (Manufacturers & Importers)")
verify_file(SERVICE_FILE, "SERVICE PROVIDERS (Transporters)")
verify_file(SALES_FILE, "CUSTOMERS (Sales Parties)")
