import pandas as pd

SOURCE_FILE = r"C:\Users\HP\Desktop\Sales VG30 Dashboard all india prising.xlsx"

print(f"Inspecting {SOURCE_FILE}...")
try:
    # Read first 10 rows to find header
    df = pd.read_excel(SOURCE_FILE, nrows=10, header=None)
    print("Raw Data (First 10 rows):")
    print(df.to_string())
    
    # Simple logic to find header: Look for row containing "Particulars" or "Base"
    header_row = -1
    for i, row in df.iterrows():
        row_str = str(row.values).lower()
        if "names" in row_str and "sector" in row_str:
            header_row = i
            print(f"\n[FOUND] Potential Header at Row Index: {i}")
            break
            
    if header_row != -1:
        print(f"Reading file with header={header_row}...")
        df_real = pd.read_excel(SOURCE_FILE, nrows=5, header=header_row)
        print("Correct columns detected:")
        print(list(df_real.columns))
    else:
        print("[WARNING] Could not auto-detect header row.")

except Exception as e:
    print(f"Error: {e}")
