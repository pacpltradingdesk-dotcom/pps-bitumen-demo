import pandas as pd
import numpy as np
import streamlit as st
import os

class CostOptimizer:
    def __init__(self, data_path=None):
        self.data_path = data_path or os.path.join(os.path.dirname(os.path.abspath(__file__)), "logistics_data.parquet")
        self.df = None

    def load_data(self):
        """Loads the optimized Parquet data."""
        try:
            self.df = pd.read_parquet(self.data_path)
            
            # Ensure necessary columns for Data Manager
            if 'is_active' not in self.df.columns:
                self.df['is_active'] = 1 # Default all active (1=True, 0=False)
            
            # Ensure numeric types for calculation columns
            cols_to_numeric = ['base_bulk', 'base_drum', 'disc_bulk', 'disc_drum', 'transport_bulk', 'transport_drum', 'distance_km', 'rate_per_km']
            for col in cols_to_numeric:
                if col in self.df.columns:
                    self.df[col] = pd.to_numeric(self.df[col], errors='coerce').fillna(0)
            
            return True
        except Exception as e:
            st.error(f"Error loading data: {e}. Did you run 'convert_data.py'?")
            return False

    def save_data(self):
        """Saves current dataframe to Parquet."""
        if self.df is not None:
            self.df.to_parquet(self.data_path, index=False)
            return True
        return False

    def get_cities(self):
        """Returns sorted list of unique Cities/Destinations."""
        if self.df is None: return []
        target_col = 'destination' if 'destination' in self.df.columns else 'customer_location'
        if target_col not in self.df.columns: return []
        return sorted(self.df[target_col].dropna().unique().tolist())

    def get_all_sources(self):
        """Returns unique list of all Loading Points / Refineries."""
        if self.df is None: return []
        if 'source_location' in self.df.columns:
            return sorted(self.df['source_location'].dropna().unique().tolist())
        return []
        
    def get_clients_by_city(self, city):
        """Returns list of Clients located in a specific City."""
        if self.df is None: return []
        if 'customer_name' in self.df.columns:
             return sorted(self.df[self.df['destination'] == city]['customer_name'].unique().tolist())
        return [f"Generic Customer in {city}"]

    def update_source_price(self, source, base_bulk, disc_bulk, is_active, base_drum=None, disc_drum=None):
        """Updates Price and Availability for a Source (Refinery) globally."""
        if self.df is None: return False
        
        mask = self.df['source_location'] == source
        if mask.any():
            self.df.loc[mask, 'base_bulk'] = float(base_bulk)
            self.df.loc[mask, 'disc_bulk'] = float(disc_bulk)
            self.df.loc[mask, 'is_active'] = 1 if is_active else 0
            
            if base_drum is not None:
                self.df.loc[mask, 'base_drum'] = float(base_drum)
            if disc_drum is not None:
                self.df.loc[mask, 'disc_drum'] = float(disc_drum)
                
            self.save_data()
            return True
        return False

    def update_route_logistics(self, source, destination, distance, bulk_rate_per_km, drum_transport_cost):
        """Updates Logistics for a specific Source-Destination route."""
        if self.df is None: return False

        # Match Source + Destination
        mask = (self.df['source_location'] == source) & (self.df['destination'] == destination)
        
        if mask.any():
            dist_val = float(distance)
            rate_val = float(bulk_rate_per_km)
            
            # Update Distance
            self.df.loc[mask, 'distance_km'] = dist_val
            
            # Update Rate Per KM column
            if 'rate_per_km' in self.df.columns:
                 self.df.loc[mask, 'rate_per_km'] = rate_val
            
            # Recalculate Total Bulk Freight (Dist * Rate)
            # User Requirement: "Ton per km price for bulk... and drum one way charges"
            new_bulk_cost = dist_val * rate_val
            self.df.loc[mask, 'transport_bulk'] = new_bulk_cost

            # Update Drum Logistics (Fixed "One Way" Charge)
            self.df.loc[mask, 'transport_drum'] = float(drum_transport_cost)
            
            self.save_data()
            return True
        return False

    def calculate_best_price(self, customer_location, load_type="Bulk", price_overrides=None, product_grade="VG30"):
        """
        Main logic: Finds cheapest source for a given customer.
        """
        if self.df is None: return None

        # 1. Filter for Customer AND Active Sources
        dest_col = 'customer_location' if 'customer_location' in self.df.columns else 'destination'
        
        # ACTIVE CHECK: Ensure is_active == 1 (or True)
        df_cust = self.df[(self.df[dest_col] == customer_location) & (self.df['is_active'] == 1)].copy()

        if df_cust.empty:
            return None

        # 2. Map Columns (Dynamic mapping based on Load Type)
        if load_type == 'Bulk':
            base_col = 'base_bulk' 
            disc_col = 'disc_bulk'
            transport_col = 'transport_bulk'
        else:
            base_col = 'base_drum'
            disc_col = 'disc_drum'
            transport_col = 'transport_drum'
            
        # VG10 LOGIC (Legacy / Diff Map)
        if product_grade == "VG10":
            if f"{base_col}_vg10" in df_cust.columns:
                base_col = f"{base_col}_vg10"
            else:
                # Map of City -> Price Diff (VG10 - VG30)
                diff_map = {
                    "Barauni": -800, "Bathinda": -1300, "Chennai": -500, "Kochi": -2120, "Guwahati": -780,
                    "Haldia": -1000, "Hyderabad": -3280, "Indore": 1997, "Jabalpur": -780, "Mathura": -1300,
                    "Mumbai": -1810, "Panipat": -1300, "Visakhapatnam": -100, "Mysore": -800
                }
                for city, diff in diff_map.items():
                    mask = df_cust['port'] == city
                    if mask.any():
                        # Create temp column for calculation if needed, or adjust later
                        # For simplicity, we assume base_bulk is updated in-memory for this calc
                        # But rewriting existing column affects other rows if not careful? 
                        # We are working on a .copy(), so it is safe.
                        if base_col in df_cust.columns:
                             df_cust.loc[mask, base_col] = df_cust.loc[mask, base_col] + diff
        
        # Fallback if specific cols don't exist
        if base_col not in df_cust.columns: base_col = 'base_price'
        if disc_col not in df_cust.columns: disc_col = 'discount' 
        if transport_col not in df_cust.columns: transport_col = 'transport_cost'

        # 3. Calculate Landed Cost
        tax_rate = 0.18 # Default GST
        
        df_cust['base_price_calc'] = pd.to_numeric(df_cust[base_col], errors='coerce').fillna(0)
        df_cust['discount_calc'] = pd.to_numeric(df_cust[disc_col], errors='coerce').fillna(0)
        df_cust['transport_calc'] = pd.to_numeric(df_cust[transport_col], errors='coerce').fillna(0)
        
        # --- REAL TIME UPDATES (Apply Manual Overrides if any passed) ---
        if price_overrides:
            for source, new_price in price_overrides.items():
                mask = df_cust['source_location'] == source
                if mask.any():
                    df_cust.loc[mask, 'base_price_calc'] = float(new_price)
        
        # MATH: (Base * 1.18) - Discount + Transport
        # Note: Previous feedback implied (Base - Disc) * Tax? 
        # But standard invoice usually is Base -> Disc -> Tax.
        # User image suggested: Base + Tax - Discount?
        # Let's stick to: Final = (Base * 1.18) - Discount + Transport (matching previous successful logic)
        
        # Refined Math based on "Discount For Bulk" usually being Pre-Tax or Post-Tax?
        # If Discount is "1500 PMT", it's usually deducted from Base.
        # Let's do: (Base - Disc) * 1.18 + Transport
        # This is safer for "Discount".
        # However, checking Step 9 logic: 
        # "net_start = best_row['base_price'] + tax_val - best_row['discount']"
        # where tax_val = base * 0.18.
        # So it was: (Base * 1.18) - Discount. 
        # We will keep this consistent.
        
        df_cust['final_price'] = (df_cust['base_price_calc'] * (1 + tax_rate)) - df_cust['discount_calc'] + df_cust['transport_calc']

        # 4. Sort and Pick Best
        df_sorted = df_cust.sort_values(by='final_price', ascending=True)
        
        if df_sorted.empty: return None

        best_option = df_sorted.iloc[0]
        next_best = df_sorted.iloc[1] if len(df_sorted) > 1 else None
        savings = (next_best['final_price'] - best_option['final_price']) if next_best is not None else 0
        
        return {
            "source": best_option.get('source_location', 'Unknown Source'),
            "port": best_option.get('port', 'N/A'),
            "base_price": best_option['base_price_calc'], 
            "freight": best_option['transport_calc'],
            "distance": best_option.get('distance_km', 0),
            "discount": best_option['discount_calc'],
            "final_landed_cost": best_option['final_price'],
            "savings_vs_next": savings,
            "next_best_source": next_best.get('source_location') if next_best is not None else "None",
            "all_options": df_sorted[['source_location', 'base_price_calc', 'transport_calc', 'final_price']].rename(columns={'base_price_calc':'base_price', 'transport_calc':'transport_cost'})
        }
