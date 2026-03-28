import os
import re

dashboard_path = r"c:\Users\HP\Desktop\project_bitumen sales\bitumen sales dashboard\dashboard.py"
intel_dir = r"c:\Users\HP\Desktop\project_bitumen sales\bitumen sales dashboard\command_intel"

with open(dashboard_path, "r", encoding="utf-8") as f:
    dashboard_content = f.read()

if "from ui_badges import display_badge" not in dashboard_content:
    dashboard_content = dashboard_content.replace(
        "import streamlit as st\n",
        "import streamlit as st\nfrom ui_badges import display_badge\n"
    )

dashboard_tabs = {
    "🧮 Pricing Calculator": "calculated",
    "💼 Sales Workspace": "historical",
    "🏭 Feasibility": "calculated",
    "🎯 CRM & Tasks": "historical",
    "📅 Sales Calendar": "historical",
    "📋 Source Directory": "historical",
    "🛠️ Data Manager": "historical",
    "🚨 SPECIAL PRICE (SOS)": "calculated",
    "📤 Reports": "historical",
    "👥 Ecosystem Management": "historical",
    "🤖 AI Assistant": "calculated",
    "📚 Knowledge Base": "historical",
    "⚙️ Settings": "historical",
    "🌐 API Dashboard": "real-time"
}

for tab_name, badge_type in dashboard_tabs.items():
    # we want to insert display_badge immediately after the selected_page check
    # so we'll use regex to find where selected_page is checked
    pattern = re.compile(rf'(if selected_page == "{re.escape(tab_name)}":\n)')
    if f'display_badge("{badge_type}")' not in dashboard_content:
        dashboard_content = pattern.sub(rf'\1    display_badge("{badge_type}")\n', dashboard_content)

with open(dashboard_path, "w", encoding="utf-8") as f:
    f.write(dashboard_content)

print("Dashboard updated.")

intel_files = {
    "price_prediction.py": "calculated",
    "import_cost_model.py": "calculated",
    "supply_chain.py": "historical",
    "demand_analytics.py": "historical",
    "financial_intel.py": "calculated",
    "gst_legal_monitor.py": "historical",
    "risk_scoring.py": "calculated",
    "alert_system.py": "real-time",
    "strategy_panel.py": "calculated"
}

for fname, badge_type in intel_files.items():
    fpath = os.path.join(intel_dir, fname)
    if os.path.exists(fpath):
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
        
        if "from ui_badges import display_badge" not in content:
            import_str = "import sys\nimport os\nsys.path.append(os.path.dirname(os.path.dirname(__file__)))\nfrom ui_badges import display_badge\n"
            content = content.replace("import streamlit as st\n", f"{import_str}\nimport streamlit as st\n")
            
        if f'display_badge("{badge_type}")' not in content:
            content = re.sub(r'(def render\(\):\n)', rf'\1    display_badge("{badge_type}")\n', content)
            
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(content)

print("Intelligence modules updated.")
