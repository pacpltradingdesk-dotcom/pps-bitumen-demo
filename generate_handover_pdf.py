# -*- coding: utf-8 -*-
"""Generate Handover PDF Document for PPS Anantam Bitumen Sales Dashboard"""
from fpdf import FPDF

class HandoverPDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 9)
        self.set_text_color(5, 150, 105)
        self.cell(0, 6, 'PPS ANANTAM  |  Bitumen Sales Dashboard v5.0.0  |  Handover Document', align='C')
        self.ln(3)
        self.set_draw_color(5, 150, 105)
        self.set_line_width(0.5)
        self.line(10, self.get_y(), 287, self.get_y())
        self.ln(5)

    def footer(self):
        self.set_y(-12)
        self.set_font('Helvetica', 'I', 7)
        self.set_text_color(128, 128, 128)
        self.cell(0, 8, f'Page {self.page_no()}/{{nb}}  |  05-Mar-2026  |  Confidential', align='C')

    def stitle(self, num, title):
        self.set_font('Helvetica', 'B', 14)
        self.set_text_color(30, 41, 59)
        self.set_fill_color(226, 232, 240)
        self.cell(0, 10, f'  {num}. {title}', fill=True, new_x='LMARGIN', new_y='NEXT')
        self.ln(3)

    def sub(self, title):
        self.set_font('Helvetica', 'B', 11)
        self.set_text_color(5, 150, 105)
        self.cell(0, 7, title, new_x='LMARGIN', new_y='NEXT')
        self.ln(1)

    def txt(self, text):
        self.set_font('Helvetica', '', 9)
        self.set_text_color(30, 41, 59)
        self.multi_cell(0, 4.5, text)
        self.ln(1)

    def code(self, text):
        self.set_font('Courier', '', 7.5)
        self.set_text_color(80, 80, 80)
        self.set_fill_color(248, 250, 252)
        for line in text.split('\n'):
            self.cell(0, 3.8, '  ' + line, fill=True, new_x='LMARGIN', new_y='NEXT')
        self.ln(2)

    def th(self, cols, widths):
        self.set_font('Helvetica', 'B', 8)
        self.set_fill_color(30, 41, 59)
        self.set_text_color(255, 255, 255)
        for i, col in enumerate(cols):
            self.cell(widths[i], 6, ' ' + col, border=1, fill=True)
        self.ln()
        self.set_text_color(30, 41, 59)

    def tr(self, cols, widths):
        self.set_font('Helvetica', '', 7.5)
        for i, col in enumerate(cols):
            if i == 0:
                self.set_font('Helvetica', 'B', 7.5)
            else:
                self.set_font('Helvetica', '', 7.5)
            self.cell(widths[i], 5, ' ' + str(col)[:65], border=1)
        self.ln()


pdf = HandoverPDF(orientation='L', format='A4')
pdf.alias_nb_pages()
pdf.set_auto_page_break(auto=True, margin=15)

# ========== COVER ==========
pdf.add_page()
pdf.ln(20)
pdf.set_font('Helvetica', 'B', 32)
pdf.set_text_color(5, 150, 105)
pdf.cell(0, 15, 'PPS ANANTAM', align='C', new_x='LMARGIN', new_y='NEXT')
pdf.set_font('Helvetica', 'B', 20)
pdf.set_text_color(30, 41, 59)
pdf.cell(0, 12, 'BITUMEN SALES DASHBOARD', align='C', new_x='LMARGIN', new_y='NEXT')
pdf.ln(5)
pdf.set_font('Helvetica', '', 16)
pdf.set_text_color(100, 100, 100)
pdf.cell(0, 10, 'Complete Project Handover Document', align='C', new_x='LMARGIN', new_y='NEXT')
pdf.ln(8)
pdf.set_draw_color(5, 150, 105)
pdf.set_line_width(1)
pdf.line(90, pdf.get_y(), 197, pdf.get_y())
pdf.ln(8)
pdf.set_font('Helvetica', '', 12)
pdf.set_text_color(60, 60, 60)
for line in [
    'Version: v5.0.0  |  Date: 05-Mar-2026',
    'Owner: Prince P Shah  |  PPS Anantam / PACPL, Vadodara, Gujarat',
    '+91 7795242424  |  princepshah@gmail.com',
    '',
    '238 Python Files  |  110,578 Lines of Code  |  46 Database Tables',
    '15 Modules  |  84 Pages  |  170+ Settings  |  9 AI Providers',
    '196 Knowledge Q&A  |  15+ API Connectors',
]:
    pdf.cell(0, 7, line, align='C', new_x='LMARGIN', new_y='NEXT')

# ========== 1. OVERVIEW ==========
pdf.add_page()
pdf.stitle('1', 'PROJECT OVERVIEW')
pdf.txt('A comprehensive bitumen trading management platform for PPS Anantam (PACPL), Vadodara, Gujarat. Handles international import pricing (CFR), domestic sales (3-tier offers), CRM (132+ contacts), real-time market intelligence, AI analytics (9-provider chain), director briefings, document management (SO/PO/PAY), maritime logistics, and compliance (GST/Customs/DPDP).')
pdf.ln(2)
w = [70, 50]
pdf.th(['Metric', 'Value'], w)
for m, v in [
    ('Total Python Files', '238'), ('Total Lines of Code', '110,578'),
    ('Database Tables', '46'), ('Database Records', '14,000+'),
    ('Navigation Modules', '15'), ('Sidebar Pages', '84'),
    ('Settings Keys', '170+'), ('AI Providers', '9'),
    ('API Connectors', '15+'), ('Knowledge Base Q&A', '196'),
]:
    pdf.tr([m, v], w)

# ========== 2. TECH STACK ==========
pdf.add_page()
pdf.stitle('2', 'TECHNOLOGY STACK')
pdf.sub('Core Framework')
w = [50, 50, 30]
pdf.th(['Component', 'Technology', 'Version'], w)
for row in [
    ('Web Framework', 'Streamlit', '1.53.1'), ('Language', 'Python', '3.12'),
    ('Database', 'SQLite', 'WAL mode'), ('Charts', 'Plotly', '5.18+'),
    ('PDF', 'fpdf2 + ReportLab', '2.8.7/4.0.8'), ('Data', 'Pandas + NumPy', '2.1+/1.26+'),
]:
    pdf.tr(list(row), w)
pdf.ln(3)
pdf.sub('AI & ML Stack')
w = [55, 75]
pdf.th(['Component', 'Technology'], w)
for row in [
    ('Sentiment', 'FinBERT > DistilBERT > VADER > Keyword'),
    ('Forecasting', 'Prophet + SARIMAX + ARIMA ensemble'),
    ('Boosting', 'XGBoost + LightGBM'),
    ('Embeddings', 'sentence-transformers (MiniLM-L6-v2)'),
    ('Vector Search', 'FAISS (faiss-cpu)'),
    ('Text Search', 'TF-IDF + RRF fusion'),
]:
    pdf.tr(list(row), w)
pdf.ln(3)
pdf.sub('Dependencies (requirements.txt)')
pdf.code(
    'streamlit  pandas  numpy  reportlab  fpdf2  sqlmodel  yfinance  openpyxl  xlrd\n'
    'plotly  requests  pytrends  prophet  scikit-learn  statsmodels  scipy\n'
    'xgboost  lightgbm  transformers  torch  vaderSentiment  faiss-cpu\n'
    'sentence-transformers  cryptography  psutil'
)

# ========== 3. ARCHITECTURE ==========
pdf.add_page()
pdf.stitle('3', 'ARCHITECTURE OVERVIEW')
pdf.code(
    'PRESENTATION:  dashboard.py(5193) + command_intel/(55 pages) + chart_engine + news_ticker\n'
    'BUSINESS:      calculation_engine + crm_engine + recommendation_engine + negotiation_engine\n'
    'INTELLIGENCE:  ai_fallback(9 providers) + chatbot + finbert + ml_forecast + rag_engine\n'
    'DATA:          database.py(46 tables) + api_hub(15+ APIs) + settings(170+) + vault\n'
    'INFRA:         sre_engine + log_engine + role_engine + resilience_manager + model_monitor'
)
pdf.ln(2)
pdf.sub('Data Flow')
pdf.code(
    'External APIs -> api_hub_engine -> lkg_cache -> database -> SQLite\n'
    'User Input -> dashboard.py -> calculation_engine -> Pricing\n'
    '                           -> crm_engine -> Contacts/Deals\n'
    '                           -> chatbot -> AI Response\n'
    '                           -> chart_engine -> Visualization\n'
    '                           -> pdf_export -> PDF Document'
)

# ========== 4. NAVIGATION ==========
pdf.stitle('4', 'NAVIGATION (15 Modules, 84 Pages)')
w = [8, 35, 60, 90]
pdf.th(['#', 'Module', 'Key Pages', 'Description'], w)
for row in [
    ('1', 'Home', 'Executive Dashboard', 'KPI cards, market overview, alerts'),
    ('2', 'Director Briefing', 'Daily Brief', 'Auto-generated executive summary'),
    ('3', 'Procurement', 'Import Calc, Price History, Advisor', 'International import cost modeling'),
    ('4', 'Sales', 'Pricing, Quotation, CRM, Directory', 'Sales operations & customer management'),
    ('5', 'Documents', 'Document Mgmt (SO/PO/PAY)', 'Business document generation'),
    ('6', 'Logistics', 'Maritime Intel, Port Tracker', 'Shipping & logistics management'),
    ('7', 'Intelligence', 'News, Signals, Correlation, Infra', 'Market research & analytics'),
    ('8', 'Compliance', 'GST Monitor, Audit, DPDP', 'Regulatory compliance'),
    ('9', 'Reports', 'Daily Log, Analytics, PDF', 'Business reporting'),
    ('10', 'System Control', 'Settings, Health, SRE, Alerts', 'System administration'),
    ('11', 'Developer', 'Dev Ops, API Hub, Bug Tracker', 'Developer tools'),
    ('12', 'AI & Knowledge', 'AI Setup, Chatbot, KB', 'AI management'),
]:
    pdf.tr(list(row), w)

# ========== 5. AI STACK ==========
pdf.add_page()
pdf.stitle('5', 'AI & INTELLIGENCE STACK')
pdf.sub('9-Provider Fallback Chain')
w = [8, 30, 40, 42, 15, 15]
pdf.th(['#', 'Provider', 'Model', 'Type', 'Cost', 'PII'], w)
for row in [
    ('1', 'Ollama', 'Llama3', 'Local Offline', 'FREE', 'Yes'),
    ('2', 'HuggingFace', 'Zephyr-7B', 'Cloud API', 'FREE', 'Yes'),
    ('3', 'GPT4All', 'Phi-3 Mini', 'Fully Offline', 'FREE', 'Yes'),
    ('4', 'Groq', 'Llama-3.3-70B', 'Cloud (Speed)', 'FREE', 'Yes'),
    ('5', 'Gemini', '2.0 Flash', 'Cloud (Analysis)', 'FREE', 'Yes'),
    ('6', 'Mistral', 'Small', 'Cloud (EU-safe)', 'FREE', 'Yes'),
    ('7', 'DeepSeek', 'Chat', 'Cloud (Research)', 'FREE', 'RESTR'),
    ('8', 'OpenAI', 'GPT-4o-mini', 'Paid Optional', 'PAID', 'Yes'),
    ('9', 'Claude', 'Haiku', 'Paid Fallback', 'PAID', 'Yes'),
]:
    pdf.tr(list(row), w)
pdf.ln(3)
pdf.sub('Task-Based Routing (10 Types)')
w = [40, 30, 55]
pdf.th(['Task', 'Primary', 'Fallback'], w)
for row in [
    ('whatsapp_reply', 'Groq', 'Ollama -> Gemini'),
    ('email_draft', 'Gemini', 'Ollama -> Mistral'),
    ('market_analysis', 'Gemini', 'DeepSeek -> Ollama'),
    ('customer_chat', 'Groq', 'Ollama -> Gemini'),
    ('director_brief', 'Gemini', 'Ollama -> Groq'),
    ('call_script', 'Ollama', 'Groq -> Gemini'),
    ('price_inquiry', 'Groq', 'Ollama -> Gemini'),
    ('hindi_regional', 'Gemini', 'Ollama -> Groq'),
    ('private_data', 'Ollama', 'GPT4All (offline only)'),
    ('research_only', 'DeepSeek', 'Gemini -> Mistral'),
]:
    pdf.tr(list(row), w)
pdf.ln(3)
pdf.sub('Intelligence Engines')
pdf.txt(
    'PII Filter: Strips phone/email/PAN/GSTIN/Aadhaar for restricted providers. '
    'Sentiment: FinBERT > DistilBERT > VADER > Keyword (4-tier). '
    'Forecasting: Prophet+SARIMAX+ARIMA ensemble with confidence intervals. '
    'RAG: FAISS+TF-IDF hybrid with RRF fusion, synonym expansion, cross-encoder rerank. '
    'Knowledge Base: 196 Q&A across 13 sections from 55-page training document.'
)

# ========== 6. DATABASE ==========
pdf.add_page()
pdf.stitle('6', 'DATABASE SCHEMA (46 Tables)')
pdf.txt('SQLite with WAL mode | Connection pooling (Queue maxsize=5) | 80+ CRUD functions | 7 schema migrations | Parameterized queries')
pdf.ln(1)
w = [50, 20, 85]
pdf.th(['Table', 'Records', 'Purpose'], w)
for row in [
    ('suppliers', '63', 'Supplier master (refineries, traders)'),
    ('customers', '3', 'Customer master'),
    ('contacts', '132', 'All contacts (customers, prospects, suppliers)'),
    ('crm_tasks', '8', 'CRM task tracking'),
    ('deals', '0', 'Sales deal pipeline'),
    ('price_history', '8', 'Historical price records'),
    ('fx_history', '76', 'Forex rate history'),
    ('infra_demand_scores', '13,260', 'State-wise infrastructure demand data'),
    ('infra_news', '444', 'Infrastructure news articles'),
    ('infra_budgets', '15', 'State infrastructure budgets'),
    ('director_briefings', '176', 'Generated briefing records'),
    ('alerts', '12', 'System alerts'),
    ('users', '1', 'User accounts (RBAC)'),
    ('terms_master', '16', 'Payment/delivery terms'),
    ('email_queue', '2', 'Pending emails'),
    ('whatsapp_queue', '2', 'Pending WhatsApp messages'),
    ('company_master', '1', 'Company info (PPS Anantam)'),
    ('bank_master', '1', 'Bank account details'),
    ('transporters', '1', 'Transporter details'),
    ('_schema_version', '7', 'Migration tracking'),
    ('_doc_counters', '3', 'Document numbering (SO/PO/PAY)'),
    ('sales_orders', '0', 'SO documents'),
    ('purchase_orders', '0', 'PO documents'),
    ('payment_orders', '0', 'Payment documents'),
]:
    pdf.tr(list(row), w)

# ========== 7. API CONNECTORS ==========
pdf.add_page()
pdf.stitle('7', 'API CONNECTORS (15+ Sources)')
w = [42, 38, 60, 15]
pdf.th(['Connector', 'Source', 'Data', 'TTL'], w)
for row in [
    ('eia_crude', 'US EIA', 'WTI/Brent crude prices', 'Var'),
    ('fawazahmed0_fx', 'fawazahmed0', 'Live forex rates', 'Short'),
    ('frankfurter_fx', 'Frankfurter', 'EUR/USD/INR rates', 'Short'),
    ('fred_macro', 'US Federal Reserve', 'Macro indicators', 'Long'),
    ('rbi_fx_historical', 'RBI India', 'Historical INR rates', 'Long'),
    ('newsapi', 'NewsAPI.org', 'Global news articles', '10m'),
    ('gnews_rss', 'Google News', 'Free news feed', '10m'),
    ('openweather', 'OpenWeatherMap', 'Weather (ports)', '15m'),
    ('open_meteo_hub', 'Open-Meteo', 'Free weather', '15m'),
    ('maritime_intel', 'Multiple', 'Vessel & port data', '15m'),
    ('world_bank_india', 'World Bank', 'India economic data', 'Long'),
    ('un_comtrade', 'UN Comtrade', 'Trade statistics', 'Long'),
    ('comtrade_hs271320', 'UN Comtrade', 'Bitumen HS271320', 'Long'),
    ('data_gov_in', 'data.gov.in', 'India highway data', 'Long'),
    ('ppac_proxy', 'PPAC India', 'Petroleum prices', 'Var'),
]:
    pdf.tr(list(row), w)
pdf.ln(3)
pdf.txt('Cache: Last-Known-Good (LKG) in lkg_cache/*.json. Smart TTL per source. Dead letter queue for failures. Fallback to stale cache with warning.')

# ========== 8. SETTINGS ==========
pdf.stitle('8', 'KEY SETTINGS (170+ Total)')
w = [65, 30]
pdf.th(['Setting Key', 'Default'], w)
for row in [
    ('margin_min_per_mt', '500'), ('gst_rate_pct', '18'),
    ('customs_duty_pct', '2.5'), ('landing_charges_pct', '1.0'),
    ('bulk_rate_per_km', '5.5'), ('drum_rate_per_km', '6.0'),
    ('quote_validity_hours', '24'), ('payment_default_terms', '100% Advance'),
    ('email_enabled', 'False'), ('whatsapp_enabled', 'False'),
    ('whatsapp_rate_limit_per_day', '1000'), ('sms_enabled', 'False'),
    ('ai_enabled', 'True'), ('ai_deepseek_pii_filter', 'True'),
    ('ticker_speed', '600'), ('crm_hot_threshold_days', '7'),
    ('crm_warm_threshold_days', '30'), ('crm_cold_threshold_days', '90'),
    ('maritime_enabled', 'True'), ('rbac_enabled', 'False'),
]:
    pdf.tr(list(row), w)

# ========== 9. BUSINESS RULES ==========
pdf.add_page()
pdf.stitle('9', 'BUSINESS RULES & FORMULAS')
pdf.sub('International Import (CFR to Landed Cost)')
pdf.code(
    'CIF = FOB + Ocean Freight + Insurance\n'
    'Landing Charges = CIF x 1%\n'
    'Assessable Value = CIF + Landing Charges\n'
    'Customs Duty = Assessable Value x 2.5%\n'
    'Landed Cost (INR) = (Assessable + Customs) x FX Rate + Port + CHA + Handling'
)
pdf.sub('Domestic Sales (3-Tier Offers)')
pdf.code(
    'Aggressive = Base + Rs 500/MT  + Freight + GST (18% of Base+Freight)\n'
    'Balanced   = Base + Rs 800/MT  + Freight + GST (18% of Base+Freight)\n'
    'Premium    = Base + Rs 1200/MT + Freight + GST (18% of Base+Freight)\n'
    'Minimum margin enforced: Rs 500/MT\n'
    'Freight: bulk Rs 5.5/km, drum Rs 6.0/km'
)
pdf.sub('CRM Contact Temperature')
pdf.code(
    '<= 7 days:  HOT  (urgent follow-up)\n'
    '<= 30 days: WARM (regular follow-up)\n'
    '<= 90 days: COLD (re-engagement needed)\n'
    'else:       DORMANT (reactivation campaign)'
)
pdf.sub('Products & Ports')
pdf.txt('Grades: VG10, VG30, VG40, Emulsion, CRMB-55, CRMB-60, PMB')
pdf.txt('Ports: Kandla, Mundra, Mangalore, JNPT, Karwar, Haldia, Ennore, Paradip')

# ========== 10. SECURITY ==========
pdf.stitle('10', 'SECURITY & ACCESS CONTROL')
w = [30, 100]
pdf.th(['Role', 'Access Level'], w)
for row in [
    ('director', 'Full access - all modules, settings, data'),
    ('sales', 'Sales, CRM, Documents, Intelligence - no system control'),
    ('operations', 'Procurement, Logistics, Documents - no AI settings'),
    ('viewer', 'Read-only - dashboards and reports only'),
]:
    pdf.tr(list(row), w)
pdf.ln(2)
pdf.txt(
    'Session timeout: 30 min | Login rate limit: 5/5min | '
    'Vault: Fernet+PBKDF2 encryption for API keys | DPDP compliance mode | '
    'PII filter for AI | Parameterized SQL queries | No user input in HTML'
)

# ========== 11. TOP FILES ==========
pdf.add_page()
pdf.stitle('11', 'FILE REFERENCE (Top 30 by Lines of Code)')
w = [65, 15, 75]
pdf.th(['File', 'LOC', 'Purpose'], w)
for row in [
    ('dashboard.py', '5193', 'Main Streamlit app, routing, UI'),
    ('database.py', '3611', 'SQLite CRUD, pooling, migrations'),
    ('contractor_osint.py', '2294', 'Contractor OSINT intelligence'),
    ('api_hub_engine.py', '2186', '15+ API connectors with LKG cache'),
    ('business_knowledge_base.py', '1852', 'Extended business knowledge'),
    ('sre_engine.py', '1644', 'Self-healing, health monitoring'),
    ('sales_knowledge_base.py', '1451', '196 Q&A pairs, fuzzy search'),
    ('document_management.py', '1411', 'SO/PO/Payment document management'),
    ('calculation_engine.py', '1343', 'Pricing formulas (import+domestic)'),
    ('discussion_guidance_engine.py', '1333', 'Sales discussion guidance'),
    ('chart_engine.py', '1273', '15+ Plotly chart types'),
    ('infra_demand_engine.py', '1253', 'India infrastructure demand scoring'),
    ('recommendation_engine.py', '1214', 'Purchase recommendations'),
    ('business_context.py', '1210', 'Business context for AI'),
    ('ai_fallback_engine.py', '1200', '9-provider AI chain + PII filter'),
    ('trading_chatbot_engine.py', '1155', 'AI chatbot with context'),
    ('market_pulse_engine.py', '1138', 'Real-time market pulse'),
    ('maritime_intelligence_engine.py', '1108', 'Maritime & vessel tracking'),
    ('business_advisor_engine.py', '1059', 'Strategic business advisories'),
    ('news_engine.py', '1037', 'News fetching & processing'),
    ('market_intelligence_engine.py', '1025', 'Market analysis & signals'),
    ('competitor_intelligence.py', '981', 'Competitor tracking'),
    ('sync_engine.py', '949', 'Data synchronization'),
    ('ml_forecast_engine.py', '937', 'Prophet+SARIMAX+ARIMA ensemble'),
    ('sre_dashboard.py', '918', 'SRE monitoring dashboard'),
    ('communication_engine.py', '876', 'Communication templates'),
    ('whatsapp_engine.py', '822', 'WhatsApp Business API'),
    ('crm_automation_dashboard.py', '817', 'CRM main dashboard'),
    ('email_engine.py', '788', 'Email sending (SendGrid)'),
    ('pdf_export_engine.py', '778', 'PDF report generation'),
]:
    pdf.tr(list(row), w)

# ========== 12. KNOWN ISSUES ==========
pdf.add_page()
pdf.stitle('12', 'KNOWN ISSUES & OPEN ITEMS')
pdf.sub('Fixed Issues (05-Mar-2026)')
w = [15, 60, 80]
pdf.th(['Sev', 'Issue', 'Fix Applied'], w)
for row in [
    ('CRIT', 'finbert_engine.py _HAS_VADER forward reference', 'Moved VADER detection block before usage'),
    ('HIGH', 'CRM dashboard contacts showing 0 (key mismatch)', 'Corrected key mapping in crm_automation_dashboard'),
    ('MED', 'Missing ticker_speed in DEFAULT_SETTINGS', 'Added ticker_speed: 600 to defaults'),
]:
    pdf.tr(list(row), w)
pdf.ln(3)
pdf.sub('Open Items')
w = [15, 60, 80]
pdf.th(['Sev', 'Issue', 'Notes'], w)
for row in [
    ('MED', 'News ticker 2 rows vs 6 in spec', 'Could split: Crude/Forex/Logistics/NHAI/MoRTH/PMGSY'),
    ('MED', 'save_settings() no write error handling', 'Add try/except around JSON write'),
    ('MED', 'SQL table names via f-strings', 'Internal constants only - low risk'),
    ('LOW', 'pickle.load() in rag_engine', 'Local cache files only'),
    ('LOW', 'No hard delete in database', 'Design decision - soft delete'),
    ('LOW', 'unsafe_allow_html in multiple places', 'Internal data only'),
]:
    pdf.tr(list(row), w)

# ========== 13. DEPLOYMENT ==========
pdf.ln(5)
pdf.stitle('13', 'DEPLOYMENT & OPERATIONS')
pdf.code(
    '# Development:   streamlit run dashboard.py\n'
    '# Production:    streamlit run dashboard.py --server.port 8501 --server.headless true\n'
    '# DB Backup:     cp bitumen_dashboard.db backup_YYYYMMDD.db\n'
    '# Monitor:       System Control > SRE | Developer > API Hub | AI & Knowledge > AI Setup'
)
pdf.sub('Verification Commands')
pdf.code(
    'python -c "from database import get_all_suppliers; print(len(get_all_suppliers()))"\n'
    'python -c "from ai_fallback_engine import get_provider_status; print(len(get_provider_status()))"\n'
    'python -c "from sales_knowledge_base import get_knowledge_count; print(get_knowledge_count())"\n'
    'python -m py_compile dashboard.py && echo OK'
)
pdf.sub('Environment Variables (Optional)')
pdf.code(
    'GROQ_API_KEY=gsk_...          # Free\n'
    'GEMINI_API_KEY=AI...          # Free\n'
    'MISTRAL_API_KEY=...           # Free\n'
    'DEEPSEEK_API_KEY=sk-...       # Free (research only)\n'
    'OPENAI_API_KEY=sk-...         # Paid\n'
    'ANTHROPIC_API_KEY=sk-ant-...  # Paid'
)

# ========== 14. HISTORY ==========
pdf.add_page()
pdf.stitle('14', 'DEVELOPMENT HISTORY (Phases 1-8)')
for title, desc in [
    ('Phase 1: Foundation',
     'Basic Streamlit dashboard. WTI/Brent price display. Excel data import. Seed data (63 suppliers, 3 customers).'),
    ('Phase 2: Database Migration',
     'JSON to SQLite. Calculation engine (CFR + domestic). Settings engine. Connection pooling, WAL mode.'),
    ('Phase 3: New Homepage',
     'Executive dashboard with KPI cards. 8-category navigation. Director Briefing, CRM, Market Intel, Reports pages.'),
    ('Phase 4: Intelligence',
     'Opportunity, communication, negotiation engines. CRM v2.0 with deal pipeline.'),
    ('Phase 5: System Improvement (04-Mar-2026)',
     'DB transactions, vault encryption, RBAC (4 roles), CRM SQLite migration, customs/GST formula fixes, '
     'FinBERT+VADER sentiment, SARIMAX ensemble forecast, RAG hybrid search, model monitor, page registry, '
     'chart exports, KPI sparklines, centralized logging, BDI/Gold connectors.'),
    ('Phase 6: Multi-AI Provider Stack (05-Mar-2026)',
     '9-provider fallback chain (Ollama to Claude). Task-based routing (10 types). PII filter for restricted '
     'providers. Health tracking with auto-disable/recover. Provider setup wizard.'),
    ('Phase 7: Knowledge Base Expansion (05-Mar-2026)',
     'Expanded from 58 to 196 Q&A pairs across 13 sections. Sourced from 55-page sales training document.'),
    ('Phase 8: Full QA Audit (05-Mar-2026)',
     '238 files audited. 28/28 smoke tests passed. 3 critical/high bugs found and fixed. 6 open items documented.'),
]:
    pdf.sub(title)
    pdf.txt(desc)

# ========== FINAL ==========
pdf.ln(8)
pdf.set_draw_color(5, 150, 105)
pdf.set_line_width(0.5)
pdf.line(10, pdf.get_y(), 287, pdf.get_y())
pdf.ln(5)
pdf.set_font('Helvetica', 'B', 12)
pdf.set_text_color(30, 41, 59)
pdf.cell(0, 8, 'Owner: Prince P Shah  |  +91 7795242424  |  PPS Anantam / PACPL, Vadodara, Gujarat', align='C')
pdf.ln(8)
pdf.set_font('Helvetica', 'I', 9)
pdf.set_text_color(128, 128, 128)
pdf.cell(0, 6, '238 Python files  |  110,578 LOC  |  46 tables  |  15 modules  |  84 pages', align='C')

# Save
output_path = 'pdf_exports/HANDOVER_DOCUMENT_05-Mar-2026.pdf'
pdf.output(output_path)
print(f'PDF saved: {output_path}')
print(f'Total pages: {pdf.page_no()}')
