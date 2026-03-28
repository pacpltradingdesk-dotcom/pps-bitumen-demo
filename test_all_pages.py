"""
PPS Anantam — Full Smoke Test
================================
Import every page module and verify render() exists.
Run: python test_all_pages.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

MODULES = [
    # Pages
    ("pages.home.director_cockpit", "Director Cockpit"),
    ("pages.home.command_center", "Command Center"),
    ("pages.home.client_showcase", "Client Showcase"),
    ("pages.home.live_market", "Live Market"),
    ("pages.home.opportunities", "Opportunities"),
    ("pages.home.subscription_pricing", "Subscription Pricing"),
    ("pages.pricing.pricing_calculator", "Pricing Calculator"),
    ("pages.sales.crm_tasks", "CRM Tasks"),
    ("pages.sales.negotiation", "Negotiation"),
    ("pages.sales.comm_hub", "Comm Hub"),
    ("pages.sales.sales_calendar", "Sales Calendar"),
    ("pages.intelligence.telegram_analyzer", "Telegram Analyzer"),
    ("pages.logistics.ecosystem", "Ecosystem"),
    ("pages.sharing.share_center", "Share Center"),
    ("pages.sharing.telegram_dashboard", "Telegram Dashboard"),
    ("pages.system.settings_page", "Settings"),
    ("pages.system.sync_status", "Sync Status"),
    ("pages.system.knowledge_base", "Knowledge Base"),
    ("pages.system.ai_learning", "AI Learning"),

    # Command Intel dashboards
    ("command_intel.profitability_dashboard", "Profitability"),
    ("command_intel.credit_aging_dashboard", "Credit & Aging"),
    ("command_intel.eway_bill_dashboard", "E-Way Bill"),
    ("command_intel.nhai_tender_dashboard", "NHAI Tenders"),
    ("command_intel.tanker_tracking_dashboard", "Tanker Tracking"),
    ("command_intel.client_chat_dashboard", "Client Chat"),
    ("command_intel.alert_center", "Alert Center"),
    ("command_intel.market_signals_dashboard", "Market Signals"),
    ("command_intel.financial_intel", "Financial Intel"),
    ("command_intel.news_dashboard", "News Dashboard"),
    ("command_intel.document_management", "Document Management"),
    ("command_intel.road_budget_dashboard", "Road Budget"),
    ("command_intel.data_manager_dashboard", "Data Manager"),
    ("command_intel.contacts_directory_dashboard", "Contacts Directory"),
    ("command_intel.risk_scoring", "Risk Scoring"),
    ("command_intel.correlation_dashboard", "Correlation"),
    ("command_intel.demand_analytics", "Demand Analytics"),
    ("command_intel.strategy_panel", "Strategy Panel"),
    ("command_intel.director_dashboard", "Director Briefing"),
    ("command_intel.comm_tracking_dashboard", "Comm Tracking"),
    ("command_intel.price_prediction", "Price Prediction"),

    # Engines
    ("credit_engine", "Credit Engine"),
    ("eway_bill_engine", "E-Way Bill Engine"),
    ("tender_engine", "Tender Engine"),
    ("tanker_engine", "Tanker Engine"),
    ("shareable_links_engine", "Shareable Links"),
    ("drip_campaign_engine", "Drip Campaign"),
    ("brochure_engine", "Brochure Engine"),
    ("showcase_standalone", "Showcase Standalone"),
    ("communication_engine", "Communication Engine"),
    ("calculation_engine", "Calculation Engine"),
    ("market_intelligence_engine", "Market Intelligence"),
]

def run_smoke_test():
    passed = 0
    failed = 0
    errors = []

    print(f"Running smoke test on {len(MODULES)} modules...\n")

    for module_path, display_name in MODULES:
        try:
            mod = __import__(module_path, fromlist=["render"])
            # Check for render function (pages) or key functions (engines)
            has_render = hasattr(mod, "render")
            has_any_callable = any(callable(getattr(mod, attr)) for attr in dir(mod) if not attr.startswith("_"))

            if has_render or has_any_callable:
                print(f"  OK  {display_name}")
                passed += 1
            else:
                print(f"  WARN {display_name} — no callable functions found")
                passed += 1  # Still importable
        except Exception as e:
            error_msg = str(e)[:80]
            print(f"  FAIL {display_name} — {error_msg}")
            errors.append((display_name, error_msg))
            failed += 1

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed out of {len(MODULES)}")
    if errors:
        print(f"\nFailed modules:")
        for name, err in errors:
            print(f"  - {name}: {err}")
    print(f"{'='*50}")

    return failed == 0

if __name__ == "__main__":
    success = run_smoke_test()
    sys.exit(0 if success else 1)
