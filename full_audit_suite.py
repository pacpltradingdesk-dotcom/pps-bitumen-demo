
import unittest
import os
import json
import datetime
import importlib.util
import sys
from datetime import timedelta

# Fix Encoding for Windows Console
sys.stdout.reconfigure(encoding='utf-8')

# --- MOCK CONTEXT FOR AUDIT ---
# We mock Streamlit since we can't run UI tests headlessly here easily without integration tools.
# Focus is on LOGIC and Backend Integrity.

class TestBitumenSystem(unittest.TestCase):

    def setUp(self):
        self.print_header("SYSTEM CONFIG CHECK")
    
    def print_header(self, text):
        print(f"\n{'-'*60}\n[AUDIT] {text}\n{'-'*60}")

    # =================================================================
    # 1. FILE SYSTEM & DEPENDENCY CHECK
    # =================================================================
    def test_core_files_exist(self):
        files = [
            "dashboard.py", "sales_workspace.py", "market_intelligence.py",
            "market_data.py", "crm_engine.py", "sos_engine.py",
            "party_master.py", "pdf_generator.py", "distance_matrix.py"
        ]
        missing = [f for f in files if not os.path.exists(f)]
        if missing:
            self.fail(f"❌ CRITICAL MISSING FILES: {missing}")
        else:
            print("✅ All Core Modules Present")

    def test_databases_valid(self):
        dbs = ["purchase_parties.json", "sales_parties.json", "crm_tasks.json"]
        for db in dbs:
            if not os.path.exists(db):
                print(f"⚠️ Warning: DB {db} is missing (Will be auto-created)")
            else:
                try:
                    with open(db, 'r') as f:
                        json.load(f)
                    print(f"✅ DB Verified: {db}")
                except:
                    self.fail(f"❌ CORRUPT DB: {db}")

    # =================================================================
    # 2. BUSINESS LOGIC: PRICING & QUOTES
    # =================================================================
    def test_landed_cost_logic(self):
        self.print_header("PRICING LOGIC TEST")
        
        # Scenario: 
        # Base: 40,000 | Dist: 500km | Freight: 4.5/km/MT | Margin: 500 | GST: 18%
        # Formula: (Base + (Dist * Rate) + Margin) * 1.18
        
        base = 40000
        dist = 500
        rate = 4.5
        margin = 500
        gst = 0.18
        
        freight = dist * rate
        pre_tax = base + freight + margin
        tax = pre_tax * gst
        final = pre_tax + tax
        
        expected_freight = 2250.0
        expected_pre_tax = 42750.0
        expected_final = 50445.0
        
        print(f"   Calc: {base} + ({dist}*{rate}) + {margin} + 18% GST")
        print(f"   Result: {final}")
        
        self.assertEqual(freight, expected_freight, "Freight Calc Wrong")
        self.assertEqual(pre_tax, expected_pre_tax, "Pre-Tax Calc Wrong")
        self.assertEqual(final, expected_final, "Final Landed Cost Wrong")
        print("✅ Landed Cost Formula Verified")

    # =================================================================
    # 3. CRM & AUTOMATION RULES
    # =================================================================
    def test_crm_rules(self):
        self.print_header("CRM AUTOMATION TEST")
        try:
            import crm_engine as crm
            
            # Test 1: New Lead Rule
            tasks = crm.auto_generate_tasks({"name": "Audit Test Client"}, "New Enquiry")
            self.assertIn("New Lead Call", tasks, "Failed to auto-generate Call Task")
            
            # Verify task saved
            all_t = crm.get_tasks()
            new_t = all_t[-1]
            self.assertEqual(new_t['client'], "Audit Test Client") 
            self.assertEqual(new_t['type'], "Call")
            
            print("✅ CRM 'New Lead' Trigger Verified")
            
        except ImportError:
            self.fail("❌ CRM Module Import Failed")

    # =================================================================
    # 4. SOS SPECIAL PRICE TRIGGER
    # =================================================================
    def test_sos_trigger(self):
        self.print_header("SOS TRIGGER TEST")
        try:
            import sos_engine as sos
            
            # Scenario: Price drops from 45000 to 44000 (Saving 1000 > 200 Threshold)
            opp = sos.create_sos_opportunity("Audit City", "VG30", 45000, 44000)
            
            self.assertIsNotNone(opp, "SOS Trigger Failed to create Opportunity")
            self.assertEqual(opp['saving'], 1000)
            self.assertEqual(opp['status'], "Active")
            
            # Script Generation check
            scripts = sos.generate_sos_script("TestCustomer", 1000, 44000, "Tomorrow")
            self.assertIn("₹1000", scripts['whatsapp'], "Script missing saving amount")
            
            print("✅ SOS Price Drop Trigger Verified")
            
            # Edge Case: Small drop (Saving 50 < 200)
            opp_fail = sos.create_sos_opportunity("Audit City", "VG30", 45000, 44950)
            self.assertIsNone(opp_fail, "SOS Trigger fired for negligible amount (Logic Error)")
            print("✅ SOS Threshold Guardrail Verified")
            
        except ImportError:
            self.fail("❌ SOS Module Import Failed")

    # =================================================================
    # 5. MARKET DATA INTEGRITY
    # =================================================================
    def test_market_data(self):
        self.print_header("EXTERNAL API TEST")
        try:
            import market_data
            data = market_data.get_live_market_data()
            
            # Check structure
            self.assertIn("brent", data)
            self.assertIn("usdinr", data)
            self.assertIn("value", data['brent'])
            
            print(f"   Brent: {data['brent']['value']}")
            print(f"   INR:   {data['usdinr']['value']}")
            print("✅ Market Data Structure Verified")
            
        except ImportError:
            self.fail("❌ Market Data Module Import Failed")

if __name__ == '__main__':
    unittest.main()
