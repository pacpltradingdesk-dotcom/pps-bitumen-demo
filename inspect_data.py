import pandas as pd
import os

file_path = r"C:\Users\HP\Desktop\Sales VG30 Dashboard all india prising.xlsx"

try:
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        exit()

    print("Reading first 5 rows of the Excel file...")
    # Read only the first 5 rows to be fast
    df = pd.read_excel(file_path, nrows=5)
    
    print("\nColumns found:")
    for col in df.columns:
        print(f"- {col}")
        
    print("\nSample Data (First 2 rows):")
    print(df.head(2).to_string())

    print("\nData Types:")
    print(df.dtypes)

except Exception as e:
    print(f"An error occurred: {e}")
