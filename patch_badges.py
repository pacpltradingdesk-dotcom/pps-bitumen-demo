import os

dashboard_path = r"c:\Users\HP\Desktop\project_bitumen sales\bitumen sales dashboard\dashboard.py"
api_dash_path = r"c:\Users\HP\Desktop\project_bitumen sales\bitumen sales dashboard\api_dashboard.py"
intel_dir = r"c:\Users\HP\Desktop\project_bitumen sales\bitumen sales dashboard\command_intel"

with open(dashboard_path, "r", encoding="utf-8") as f:
    d_content = f.read()

if "from ui_badges import display_badge" not in d_content:
    d_content = d_content.replace("import streamlit as st\n", "import streamlit as st\nfrom ui_badges import display_badge\n")

tabs = {
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

for tab, badge in tabs.items():
    search1 = f'if selected_page == "{tab}":\n'
    search2 = f'elif selected_page == "{tab}":\n'
    insert = f'    display_badge("{badge}")\n'
    
    if search1 in d_content and insert not in d_content:
        d_content = d_content.replace(search1, search1 + insert)
    if search2 in d_content and insert not in d_content:
        d_content = d_content.replace(search2, search2 + insert)

with open(dashboard_path, "w", encoding="utf-8") as f:
    f.write(d_content)
print("Dashboard.py patched")

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

for fname, b_type in intel_files.items():
    p = os.path.join(intel_dir, fname)
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            c = f.read()
        import_stmt = "import sys\nimport os\nif os.path.dirname(os.path.dirname(__file__)) not in sys.path:\n    sys.path.append(os.path.dirname(os.path.dirname(__file__)))\nfrom ui_badges import display_badge\n"
        
        if "from ui_badges import display_badge" not in c:
            c = c.replace("import streamlit as st\n", f"import streamlit as st\n{import_stmt}")
            
        render_def = "def render():\n"
        if render_def in c and f'display_badge("{b_type}")' not in c:
            c = c.replace(render_def, render_def + f'    display_badge("{b_type}")\n')
            
        with open(p, "w", encoding="utf-8") as f:
            f.write(c)

print("Intel files patched")

if os.path.exists(api_dash_path):
    with open(api_dash_path, "r", encoding="utf-8") as f:
        c = f.read()
    if "from ui_badges import display_badge" not in c:
        c = c.replace("import streamlit as st\n", "import streamlit as st\nfrom ui_badges import display_badge\n")
    if "def render():\n" in c and 'display_badge("real-time")' not in c:
        c = c.replace("def render():\n", 'def render():\n    display_badge("real-time")\n')
    with open(api_dash_path, "w", encoding="utf-8") as f:
        f.write(c)
print("api_dashboard patched")
