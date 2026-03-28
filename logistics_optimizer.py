import pandas as pd
import numpy as np

class LogisticsOptimizer:
    def __init__(self, file_path):
        self.file_path = file_path
        self.df = None
        self.contacts_df = None

    def load_data(self):
        """
        Loads the 1GB Excel file.
        For large files, we use 'chunksize' or convert to Parquet first.
        """
        print(f"Loading data from {self.file_path}...")
        try:
            # OPTIMIZATION: Reading large Excel files is slow.
            # We recommend converting this to .parquet for production use.
            self.df = pd.read_excel(self.file_path) 
            print("Data loaded successfully.")
        except Exception as e:
            print(f"Error loading file: {e}")

    def clean_data(self):
        """
        Standardizes column names and types.
        """
        if self.df is not None:
            # Example: Standardizing column names based on your description
            # You may need to adjust these mapping keys based on the actual Excel headers
            self.df.rename(columns={
                'Refinery Location': 'source_location',
                'Loading Point': 'loading_point',
                'Import Port': 'port',
                'Base Price': 'base_price',
                'Discount': 'discount',
                'Transportation Cost': 'transport_cost',
                'Customer Location': 'destination'
            }, inplace=True)
            
            # Ensure numeric types
            cols_to_numeric = ['base_price', 'discount', 'transport_cost']
            for col in cols_to_numeric:
                if col in self.df.columns:
                    self.df[col] = pd.to_numeric(self.df[col], errors='coerce').fillna(0)

    def calculate_landed_cost(self, tax_rate=0.18):
        """
        Calculates the final landed cost for the customer.
        Formula: (Base Price + Tax) - Discount + Transportation
        """
        if self.df is not None:
            # 1. Apply Tax to Base Price (assuming Tax is on Base)
            self.df['price_with_tax'] = self.df['base_price'] * (1 + tax_rate)
            
            # 2. Subtract Discount
            self.df['price_after_discount'] = self.df['price_with_tax'] - self.df['discount']
            
            # 3. Add Transportation
            # Note: Logic for 'Drum' vs 'Bulk' truck load can be added here if columns exist
            self.df['landed_cost'] = self.df['price_after_discount'] + self.df['transport_cost']
            
            return self.df

    def find_lowest_price_pan_india(self, customer_location):
        """
        Finds the cheapest source (Refinery/Port) for a specific customer.
        """
        if self.df is None:
            return None
            
        # Filter for the specific customer or destination
        # Assuming there's a 'destination' column
        customer_options = self.df[self.df['destination'] == customer_location].copy()
        
        if customer_options.empty:
            return f"No routes found for customer at {customer_location}"
            
        # Sort by Landed Cost
        customer_options.sort_values(by='landed_cost', ascending=True, inplace=True)
        
        # Get the best option
        best_option = customer_options.iloc[0]
        
        return {
            "Best Source": best_option.get('source_location') or best_option.get('port'),
            "Landed Cost": best_option['landed_cost'],
            "Base Price": best_option['base_price'],
            "Transport": best_option['transport_cost'],
            "Savings vs Next Best": 0 # Placeholder logic
        }

    def generate_dashboard_view(self):
        """
        Simulates the output for the Salesperson.
        """
        print("\n--- Sales Dashboard Generation ---")
        # In a real app, this would return data for Streamlit/Dash
        # Group by Destination and find min landed_cost
        summary = self.df.groupby('destination')['landed_cost'].min().reset_index()
        return summary

# --- Usage Example ---
if __name__ == "__main__":
    # Update this path to your actual file
    file_path = r"C:\Users\HP\Desktop\Sales VG30 Dashboard all india prising.xlsx"
    
    optimizer = LogisticsOptimizer(file_path)
    
    # Check if we can run (requires Python + Pandas)
    import sys
    print(f"Running with Python {sys.version}")
    
    # 1. Load
    optimizer.load_data()
    
    # 2. Process
    optimizer.clean_data()
    optimizer.calculate_landed_cost()
    
    # 3. Example Query
    # city = "Mumbai"
    # result = optimizer.find_lowest_price_pan_india(city)
    # print(f"Best price for {city}: {result}")
