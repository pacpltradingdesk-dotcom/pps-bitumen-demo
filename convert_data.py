import pandas as pd
import os
import sys

# Configuration
SOURCE_FILE = r"C:\Users\HP\Desktop\Sales VG30 Dashboard all india prising.xlsx"
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logistics_data.parquet")

def convert_excel_to_parquet():
    print("="*60)
    print("LOGISTICS DATA CONVERTER")
    print("="*60)
    
    if not os.path.exists(SOURCE_FILE):
        print(f"[ERROR] Source file not found: {SOURCE_FILE}")
        print("Please check the file name and path.")
        return

    print(f"Reading Excel file: {SOURCE_FILE}")
    print("This may take 2-5 minutes because the file is 1GB...")
    print("Please wait...")

    try:
        # 1. READ RAW (Skip empty top rows)
        print("Reading raw file to find headers...")
        df_raw = pd.read_excel(SOURCE_FILE, header=None, nrows=20)
        
        # Find Header Row
        header_idx = 0
        for i, row in df_raw.iterrows():
            row_vals = [str(x).lower() for x in row.values]
            if "particulars" in row_vals and "names" in row_vals:
                header_idx = i
                print(f"[INFO] Found Header at Row {i}")
                break
        
        # 2. READ PROPERLY
        print(f"Loading full data with header={header_idx}...")
        df = pd.read_excel(SOURCE_FILE, header=header_idx)
        print(f"[SUCCESS] Excel loaded. Rows: {len(df)}, Columns: {len(df.columns)}")
        
        # 3. CLEANING
        # Rename columns to standard keys
        # We need to map 'Particulars' -> 'source_location', etc.
        # But first, clean names
        df.columns = [str(c).strip() for c in df.columns]
        
        # Map common names from the file to our internal keys
        rename_map = {
            'Names': 'source_location',
            'Particulars': 'source_name',
            'Major City': 'port',
            'State': 'state_name',
            'Base Rate For Bulk': 'base_bulk',
            'Discount For Bulk': 'disc_bulk',
            'Base Rate For Drum': 'base_drum',
            'Discount For Drum': 'disc_drum',
            'Transportation Charges (Bulk)': 'transport_bulk',
            'Transportation Charges (Drum)': 'transport_drum'
        }
        
        # Flexible renaming (case insensitive match)
        new_cols = {}
        for col in df.columns:
            for key, val in rename_map.items():
                if key.lower() in col.lower():
                    new_cols[col] = val
                    
        df.rename(columns=new_cols, inplace=True)
        print("Columns standardized:", list(df.columns[:5]))

        # Fix "Mixed Types" for Parquet (e.g. some cells are numbers, some are strings)
        for col in df.columns:
            df[col] = df[col].astype(str)

        # Save as Parquet
        print(f"Saving to optimized format: {OUTPUT_FILE}...")
        df.to_parquet(OUTPUT_FILE, index=False)
        print("[SUCCESS] Conversion complete!")
        print("You can now run the dashboard instantly.")
        
    except Exception as e:
        print(f"[ERROR] Failed to convert: {e}")

if __name__ == "__main__":
    convert_excel_to_parquet()
