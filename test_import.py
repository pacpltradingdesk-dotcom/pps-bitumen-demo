import sys
sys.path.insert(0, r"C:\Users\HP\Desktop\project_bitumen sales\bitumen sales dashboard")

from party_master import import_sales_from_excel

# Test import
file_path = r"C:\Users\HP\Desktop\crm data.xlsx"
count, message = import_sales_from_excel(file_path, "Big Trader")

print(f"Result: {count} records processed")
print(f"Message: {message}")
