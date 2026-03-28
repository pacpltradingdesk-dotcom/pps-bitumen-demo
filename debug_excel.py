import pandas as pd

file_path = r"C:\Users\HP\Desktop\crm data.xlsx"
df = pd.read_excel(file_path, header=None)  # Read without assuming headers

print(f"Total rows: {len(df)}")
print(f"\nFirst 10 rows:")
print(df.head(10))
print(f"\nColumn count: {len(df.columns)}")
