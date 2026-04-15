"""
PPS Anantams Logistics AI
Business Intelligence Knowledge Base
Complete reference for all 24 dashboard tabs.
Audience: New employees, department heads, partners, clients, auditors.
"""

# ─────────────────────────────────────────────────────────────────────────────
# BUSINESS OVERVIEW
# ─────────────────────────────────────────────────────────────────────────────

BUSINESS_OVERVIEW = {
    "title": "How This Business Works — Complete Overview",
    "model": (
        "PPS Anantams is a B2B bitumen trading and logistics company. "
        "We buy bitumen from PSU refineries (IOCL, BPCL, HPCL) and import terminals, "
        "then sell it to road contractors, government agencies, and infrastructure companies across India. "
        "Our revenue comes from the margin between our landed cost and the selling price."
    ),
    "revenue_flow": [
        "Source: Buy from refinery or import terminal at base price",
        "Add: GST @18% (recoverable input tax credit for buyer)",
        "Add: Freight (₹5.5/km bulk, ₹6.0/km drum)",
        "Add: Our margin (typically 8–15% on cost)",
        "= Selling price quoted to customer (FOR destination)",
    ],
    "cost_structure": [
        "Base price (60–65% of total): Refinery price or import CIF",
        "GST 18% (pass-through — not a real cost if buyer is GST-registered)",
        "Freight (20–25%): Road transport from source to site",
        "Finance cost (3–5%): Working capital interest on 30–45 day cycles",
        "Conversion cost (if drum → bulk via decanter): ₹500/MT fixed",
        "Handling, CHA, port charges (for import cargo): ₹175–200/MT",
    ],
    "crude_usd_dependency": (
        "Bitumen is a petroleum product. Its price moves directly with Brent crude oil. "
        "A ₹ 1/bbl rise in crude increases bitumen by approx ₹300–400/MT. "
        "Import bitumen is priced in USD, so a ₹1 depreciation in INR adds approx ₹380–400/MT to import cost. "
        "This makes USD/INR the second-most critical variable after crude."
    ),
    "fortnight_cycle": (
        "Indian PSU refineries revise bitumen prices on the 1st and 16th of every month — "
        "the 'fortnightly revision cycle'. These revisions are driven by crude oil movement over the prior 14 days. "
        "A typical revision ranges from ±₹200 to ±₹1,500/MT. "
        "Traders must lock purchase orders BEFORE an upward revision and DELAY purchases BEFORE a downward revision."
    ),
    "margin_structure": (
        "Gross margin target: 8–15% of cost. "
        "Net margin after finance and overheads: 4–8%. "
        "On a 1,000 MT deal at ₹42,000/MT, gross profit = ₹4,000–6,300 per MT = ₹40–63 Lakhs. "
        "Margin is extremely sensitive to crude swings — a ₹1,000/MT upward revision can wipe 2–3% margin "
        "if purchase was not locked in advance."
    ),
    "risk_areas": [
        "FX Risk: USD/INR movement directly impacts import cost",
        "Crude Volatility: ±₹ 5/bbl = ±₹1,500–2,000/MT price swing",
        "Supply Risk: Refinery shutdowns, ship delays, OPEC cuts",
        "GST Compliance: Fake supplier ITC reversal, GSTR-1/3B mismatch",
        "Credit Risk: Contractor defaults on 30–45 day payment terms",
        "Seasonal Risk: Monsoon (June–Sep) — demand collapses, inventory locked",
        "Regulatory Risk: HSN code changes, e-way bill amendments",
    ],
    "department_connections": (
        "Sales feeds pricing requests to Operations. Operations checks feasibility and source. "
        "Finance approves credit limits and reviews margins. Legal validates GST/compliance. "
        "Strategy monitors crude + market signals to time purchases. "
        "All departments are connected through this dashboard."
    ),
}

# ─────────────────────────────────────────────────────────────────────────────
# TAB KNOWLEDGE — 24 TABS
# ─────────────────────────────────────────────────────────────────────────────

TAB_KNOWLEDGE = [

    # ── 1. PRICING CALCULATOR ────────────────────────────────────────────────
    {
        "id": "pricing_calculator",
        "tab": "🧮 Pricing Calculator",
        "what": (
            "The Pricing Calculator is the core quoting engine. It takes a source (refinery or port), "
            "a destination city, and a quantity, then instantly calculates the exact landed cost — "
            "base price + GST + freight + margin — and generates a professional price slip."
        ),
        "why": (
            "Bitumen prices change every 14 days (1st & 16th cycle). Before this tool, sales staff "
            "manually called refineries, calculated freight on paper, and quoted prices that were sometimes "
            "wrong by ₹500–1,500/MT. This caused lost deals and margin leakage. "
            "This tab eliminates manual errors and cuts quote time from 2 hours to under 2 minutes."
        ),
        "impact": {
            "revenue": "Faster quotes = more deals closed. Accurate quotes = no under-pricing.",
            "cost": "Prevents under-quoting which causes margin loss. Identifies cheapest source.",
            "risk": "Eliminates manual calculation errors that led to financial losses.",
            "compliance": "GST @18% is auto-applied — prevents incorrect tax quoting.",
            "decision": "Salesperson immediately knows whether a deal is viable at the offered price.",
        },
        "users": ["Sales Team", "Sales Manager", "Pricing Head"],
        "roles": ["Sales", "Pricing", "Management"],
        "inputs": [
            "Source name (refinery/port) — selected from Source Master",
            "Destination city — from Distance Matrix (500+ cities)",
            "Quantity in MT",
            "Grade (VG30 / VG10 / VG40)",
            "Desired margin % (slider)",
            "Current base price — auto-loaded from Live Prices (Data Manager)",
        ],
        "outputs": [
            "Landed cost per MT (₹/MT)",
            "Total deal value (₹)",
            "Freight component (₹/MT)",
            "GST component (₹/MT)",
            "Margin earned (₹ and %)",
            "Downloadable PDF price slip",
            "WhatsApp-ready price message",
        ],
        "factors": [
            "1st & 16th cycle: Base price must be updated after each revision or quotes will be wrong",
            "Distance accuracy: Freight = Distance × Rate/km. Wrong distance = wrong quote",
            "Grade selection: VG30, VG10, VG40 have different base prices",
            "Bulk vs Drum: Different freight rates (₹5.5 vs ₹6.0 per km)",
            "Margin slider: Must reflect actual business costs + desired profit",
        ],
        "mistakes": [
            "Using yesterday's price on revision day (1st or 16th) — can lose ₹500–1,500/MT",
            "Wrong destination city selected — freight error can be thousands of rupees",
            "Forgetting to include GST in the quote to an unregistered buyer",
            "Setting margin too low during peak season when demand is high",
            "Not re-checking quote after a crude price spike",
        ],
        "kpis": [
            "Quotes generated per day",
            "Quote-to-order conversion rate (%)",
            "Average margin % per quote",
            "Number of price revisions missed (should be zero)",
        ],
        "risk_if_ignored": (
            "Sales staff quote wrong prices. Company sells below cost. "
            "Margin leakage of ₹500–2,000/MT across hundreds of MT = crores of loss annually."
        ),
        "linked_tabs": ["Data Manager", "Source Directory", "Feasibility", "Reports", "Sales Workspace"],
    },

    # ── 2. SALES WORKSPACE ───────────────────────────────────────────────────
    {
        "id": "sales_workspace",
        "tab": "💼 Sales Workspace",
        "what": (
            "The Sales Workspace is a deal-closing command centre for individual client engagements. "
            "It combines Client 360 profiles, real-time deal feasibility, objection-handling scripts, "
            "and WhatsApp message generators in one screen."
        ),
        "why": (
            "A salesperson talking to a major contractor needs to know: their credit limit, last 5 deals, "
            "site location, preferred grade, and what to say if they push back on price — all in one place. "
            "Without this, salespersons rely on memory or Excel sheets, causing inconsistencies and lost deals."
        ),
        "impact": {
            "revenue": "Higher close rate when salesperson has complete client context during a call",
            "cost": "Reduces time wasted on wrong clients — focus on creditworthy, high-volume buyers",
            "risk": "Credit limit check prevents selling to clients who cannot pay",
            "compliance": "Payment terms are displayed — prevents non-standard arrangements",
            "decision": "Winning talking points auto-generated based on data — removes guesswork",
        },
        "users": ["Sales Executive", "Account Manager", "Sales Manager"],
        "roles": ["Sales", "Business Development"],
        "inputs": [
            "Client selection (from CRM directory)",
            "Destination city and quantity required",
            "Current market price (auto-pulled from Pricing Calculator)",
            "Competitor price (manual entry for objection handling)",
        ],
        "outputs": [
            "Client 360 card: credit limit, outstanding, last 5 deals, payment history",
            "Deal feasibility: margin at offered price",
            "Winning talking points based on client profile",
            "Objection handling scripts (price, credit, competitor)",
            "WhatsApp message auto-generated with price, grade, delivery terms",
        ],
        "factors": [
            "Credit limit: Never quote more than approved credit limit without finance sign-off",
            "Payment history: A client with 90+ day overdue is a collection risk, not a sales opportunity",
            "Seasonal behaviour: Some clients bulk-buy before monsoon (March–May)",
            "Grade preferences: Airport/expressway clients need PMB, not VG30",
        ],
        "mistakes": [
            "Promising delivery timeline not confirmed with logistics",
            "Quoting without checking outstanding balance — extending credit to defaulters",
            "Using generic objection scripts instead of client-specific data",
            "Not logging the call outcome in CRM after using this workspace",
        ],
        "kpis": [
            "Deal conversion rate per salesperson (%)",
            "Average deal size (MT and ₹)",
            "Client outstanding as % of credit limit",
            "WhatsApp response rate after message sent",
        ],
        "risk_if_ignored": (
            "Sales team operates on gut feeling. Deals closed at wrong margins. "
            "Bad debt risk increases when credit checks are skipped."
        ),
        "linked_tabs": ["Pricing Calculator", "CRM & Tasks", "Financial Intelligence", "Reports"],
    },

    # ── 3. FEASIBILITY ───────────────────────────────────────────────────────
    {
        "id": "feasibility",
        "tab": "🏭 Feasibility",
        "what": (
            "The Feasibility tab compares ALL supply sources — PSU refineries, import terminals, "
            "and local decanters — for any destination city, and ranks them by lowest landed cost. "
            "It shows the cheapest way to supply bitumen to any location in India."
        ),
        "why": (
            "India has 16 refineries, 8 import terminals, and 10+ decanters. The cheapest source for "
            "Ahmedabad is different from the cheapest for Chennai. Without this comparison, "
            "operations teams guess the source, often costing ₹800–2,500 extra per MT."
        ),
        "impact": {
            "revenue": "Indirectly — lower cost allows competitive pricing and bigger margins",
            "cost": "Direct — identifies source savings of ₹500–3,000/MT per deal",
            "risk": "Reduces dependency on a single source — backup options visible instantly",
            "compliance": "All sources are verified PSU or licensed importers — no grey market risk",
            "decision": "Operations head can confirm feasibility in 30 seconds instead of 2 hours",
        },
        "users": ["Operations Head", "Procurement Manager", "Sales Support"],
        "roles": ["Operations", "Procurement", "Sales Support"],
        "inputs": [
            "Destination city",
            "Grade (VG30 / VG10 / VG40)",
            "Live base prices (auto-loaded from Data Manager)",
            "Distance matrix (pre-built for 500+ city-source pairs)",
        ],
        "outputs": [
            "Ranked comparison table: Refinery vs Import vs Decanter",
            "Best overall source recommendation",
            "Landed cost breakdown per option (base + GST + freight)",
            "Distance in km for each source",
            "Cost difference vs next best option (₹/MT savings)",
        ],
        "factors": [
            "Geography is king: Nearest refinery is usually cheapest, but not always (import terminals can compete for coastal cities)",
            "Decanter option: Converts drum to bulk near the city — saves long-haul freight but adds ₹500/MT conversion",
            "Import terminals (Kandla, Mundra) serve North/West India very competitively for import-grade bitumen",
            "Freight rate accuracy: ₹5.5/km bulk × 1,000 km = ₹5,500/MT freight — must match actual transporter rate",
        ],
        "mistakes": [
            "Ignoring import terminal options for cities within 500 km of a port",
            "Assuming the nearest refinery is always cheapest — freight + base price must both be checked",
            "Not updating live prices before running feasibility — stale prices give wrong rankings",
            "Overlooking the decanter option when drum supply is easier to arrange quickly",
        ],
        "kpis": [
            "Cost saving per MT vs previous source (₹/MT)",
            "Number of source switches per quarter",
            "Feasibility queries per day (indicates sales activity)",
            "Variance between estimated and actual landed cost (%)",
        ],
        "risk_if_ignored": (
            "Operations team uses habitual sources regardless of cost. "
            "Company overpays ₹500–2,000/MT × thousands of MT = ₹50 Lakhs to ₹2 Crores avoidable cost per year."
        ),
        "linked_tabs": ["Pricing Calculator", "Source Directory", "Data Manager", "Import Cost Model"],
    },

    # ── 4. CRM & TASKS ───────────────────────────────────────────────────────
    {
        "id": "crm_tasks",
        "tab": "🎯 CRM & Tasks",
        "what": (
            "CRM & Tasks is the daily sales operations manager. It auto-generates follow-up tasks, "
            "tracks lead status, shows overdue actions, and ensures no client inquiry or payment "
            "reminder is ever missed."
        ),
        "why": (
            "In B2B bitumen sales, deals take days to weeks to close. A salesperson who forgets to "
            "follow up after sending a quote loses the deal to a competitor. "
            "This tab replaces sticky notes, personal diaries, and missed WhatsApp reminders."
        ),
        "impact": {
            "revenue": "Consistent follow-ups increase deal closure by 30–40%",
            "cost": "Prevents lost deals due to inaction — each lost deal = ₹5–50 Lakhs revenue miss",
            "risk": "Payment overdue alerts prevent receivables from ageing beyond 60 days",
            "compliance": "Audit trail of client interactions for dispute resolution",
            "decision": "Manager can see which salesperson is active vs idle on any given day",
        },
        "users": ["Sales Executive", "Sales Manager", "Collections Team"],
        "roles": ["Sales", "Management", "Finance"],
        "inputs": [
            "Auto-tasks: Generated when quote is sent (2-hour follow-up trigger)",
            "Auto-tasks: Payment overdue notifications (30/60/90 day alerts)",
            "Manual tasks: Added by salesperson or manager",
            "CRM data: Client name, deal stage, priority",
        ],
        "outputs": [
            "Today's worklist with priority flags (High/Medium/Low)",
            "Overdue task list",
            "Client engagement history",
            "Task completion rate per salesperson",
        ],
        "factors": [
            "B2B sales cycle in bitumen: Enquiry → Quote → Negotiation → PO → Dispatch → Payment",
            "Payment terms: Most contractors want 30–45 days credit; standard is 100% advance or 50% advance + 50% on delivery",
            "Hot leads: Contractors with active NHAI projects need material urgently — priority follow-up",
        ],
        "mistakes": [
            "Marking a task 'done' without actually completing the action",
            "Not logging call outcomes — task history becomes useless",
            "Ignoring 90+ day overdue tasks — these become bad debt",
            "Assigning low priority to payment follow-up tasks",
        ],
        "kpis": [
            "Task completion rate % (daily)",
            "Average follow-up response time (hours)",
            "Deals in pipeline (count and ₹ value)",
            "Overdue receivable count (should trend to zero)",
        ],
        "risk_if_ignored": (
            "Leads go cold. Payments age beyond 90 days. "
            "Sales team has no accountability. Deals worth crores lost to competitors."
        ),
        "linked_tabs": ["Sales Workspace", "Financial Intelligence", "Alert System"],
    },

    # ── 5. SALES CALENDAR ────────────────────────────────────────────────────
    {
        "id": "sales_calendar",
        "tab": "📅 Sales Calendar",
        "what": (
            "The Sales Calendar is a strategic planning tool showing state-wise holidays, festivals, "
            "monsoon periods, peak/lean seasons, and NHAI budget cycles. "
            "It tells the sales team: when to push hard, when to expect no orders, and when to stock up."
        ),
        "why": (
            "Bitumen demand is highly seasonal. Road construction stops in monsoon (June–September). "
            "Q4 (Jan–March) sees peak government spending before budget close. "
            "Diwali week closes Gujarat — wrong timing of a quote costs a week's delay. "
            "This calendar eliminates timing mistakes."
        ),
        "impact": {
            "revenue": "Concentrating sales effort in peak season (Oct–March) maximises revenue",
            "cost": "Prevents inventory buildup during monsoon when there are no buyers",
            "risk": "Avoids making large purchases right before a seasonal demand collapse",
            "compliance": "Tracks state-specific holidays for e-way bill validity and dispatch planning",
            "decision": "Management can set monthly targets aligned with seasonal demand reality",
        },
        "users": ["Sales Manager", "Operations", "Management", "Procurement"],
        "roles": ["Sales", "Operations", "Strategy"],
        "inputs": [
            "State-wise holiday database (pre-built)",
            "Festival calendar (Diwali, Holi, Pongal, Eid etc.)",
            "Monsoon period (June 1 – September 30)",
            "NHAI budget cycle (FY April–March, Q4 = peak spending)",
        ],
        "outputs": [
            "Monthly demand forecast (High/Medium/Low)",
            "State-wise delivery planning calendar",
            "Holiday alerts for dispatch scheduling",
            "Seasonal buying recommendations",
        ],
        "factors": [
            "Peak season (Oct–March): NHAI releases funds, contractors execute projects, demand is 2x monsoon",
            "Lean season (June–Sep): Monsoon halts road construction. Demand drops 60–70%",
            "Pre-Diwali (Oct): Gujarat, Rajasthan, MP contractors are active",
            "March rush: Year-end government spending — highest single-month demand",
            "Election years: Pre-election road push adds 20–25% extra demand",
        ],
        "mistakes": [
            "Sending bulk dispatches the day before a state holiday (tanker stranded, e-way expires)",
            "Stocking inventory in May expecting monsoon demand — leads to 4-month cash lockup",
            "Not planning March deliveries in advance — logistics gets choked in March",
            "Ignoring regional festivals — a contractor in Karnataka will not respond during Dasara week",
        ],
        "kpis": [
            "Revenue by month vs seasonal forecast (variance %)",
            "Inventory days outstanding during monsoon (should be minimised)",
            "On-time delivery % during peak season",
            "March target achievement % (most critical month)",
        ],
        "risk_if_ignored": (
            "Sales targets set without seasonal context. Inventory purchased at wrong time. "
            "Working capital locked for 3–4 months during monsoon. Cash flow crisis."
        ),
        "linked_tabs": ["Demand Analytics", "Financial Intelligence", "Alert System", "Strategy Panel"],
    },

    # ── 6. SOURCE DIRECTORY ──────────────────────────────────────────────────
    {
        "id": "source_directory",
        "tab": "📋 Source Directory",
        "what": (
            "A complete searchable database of all 60+ bitumen sources: 16 PSU refineries, "
            "8 import terminals, and 10+ private decanters — with contact details, "
            "grades supplied, geographic coordinates, and supply capacity."
        ),
        "why": (
            "When a large order comes in from Chennai, the operations team needs to instantly know: "
            "which refineries are closest, what grades they supply, and who to call. "
            "Without a structured directory, this knowledge lives in one person's head — a single point of failure."
        ),
        "impact": {
            "revenue": "Faster supplier contact = faster order confirmation = faster deal closure",
            "cost": "Comparing multiple sources enables cost negotiation",
            "risk": "Multiple supplier contacts prevent supply disruption if one source goes offline",
            "compliance": "All listed sources are licensed PSU or verified importers — ITC-safe",
            "decision": "Operations can make sourcing decisions independently without senior staff",
        },
        "users": ["Operations Team", "Procurement", "Logistics Coordinator"],
        "roles": ["Operations", "Procurement"],
        "inputs": [
            "Refinery master data (pre-built from industry data)",
            "Port/terminal details (Kandla, Mundra, Mangalore, JNPT etc.)",
            "Decanter locations and conversion capacity",
            "Contact persons and phone numbers (manual updates)",
        ],
        "outputs": [
            "Filtered supplier list by city, grade, or category",
            "Contact details for quick outreach",
            "Source comparison for a given destination",
            "Backup supplier options if primary is unavailable",
        ],
        "factors": [
            "PSU refineries: Fixed prices (revised 1st & 16th), reliable quality, government-backed",
            "Import terminals: Price linked to international market, can be cheaper but more volatile",
            "Decanters: Local convenience, no long-haul freight, but conversion cost applies",
            "Seasonal supply: Some refineries reduce bitumen output in monsoon for other products",
        ],
        "mistakes": [
            "Calling a refinery without first checking if they have stock (allocation-based supply)",
            "Not updating contact details when refinery changes its logistics manager",
            "Assuming all refineries supply all grades — VG40 is only at select refineries",
            "Ignoring decanter option due to unfamiliarity — can save ₹1,000–2,000/MT in freight",
        ],
        "kpis": [
            "Number of active supplier relationships (should be >5)",
            "Source utilisation rate (% of sources actually used)",
            "Average lead time per source (days from order to dispatch)",
            "Supplier fallback success rate (how often backup source was used)",
        ],
        "risk_if_ignored": (
            "Company becomes dependent on 1–2 suppliers. "
            "Any supply disruption halts operations. No negotiation leverage on pricing."
        ),
        "linked_tabs": ["Feasibility", "Pricing Calculator", "Data Manager", "Supply Chain"],
    },

    # ── 7. DATA MANAGER ──────────────────────────────────────────────────────
    {
        "id": "data_manager",
        "tab": "🛠️ Data Manager",
        "what": (
            "Data Manager is the 'control room' for all live prices, freight rates, and configuration. "
            "Every time a refinery revises its price on the 1st or 16th, this is where it gets updated. "
            "All other tabs read their prices from here."
        ),
        "why": (
            "Prices change fortnightly. If a revision is not entered here, every quote "
            "generated by the Pricing Calculator will be wrong. "
            "This is the single source of truth for all financial calculations in the dashboard."
        ),
        "impact": {
            "revenue": "Accurate prices = accurate quotes = correct revenue",
            "cost": "Correct procurement prices prevent buying at wrong reference",
            "risk": "Stale prices cause systematic under/over quoting — existential risk",
            "compliance": "Price records serve as audit evidence for pricing decisions",
            "decision": "All financial models (Feasibility, Financial Intelligence) depend on this data",
        },
        "users": ["Pricing Head", "Operations Manager", "MD / Director"],
        "roles": ["Pricing", "Operations", "Management"],
        "inputs": [
            "Refinery-wise base prices (manual entry after 1st & 16th revision)",
            "Import terminal prices (manual or API-linked)",
            "Drum prices (Mumbai and Kandla locations)",
            "Freight rates per km (bulk and drum)",
            "Decanter conversion cost (₹500/MT default)",
        ],
        "outputs": [
            "Updated live_prices.json (used by all calculation modules)",
            "Price revision history log",
            "Change notification trigger (alerts sales team of revision)",
        ],
        "factors": [
            "CRITICAL: Must be updated within 1 hour of refinery circular on 1st and 16th",
            "Price revision is one-way in peak season (usually up) — any down-revision must be verified",
            "Different grades have different base prices — do not apply VG30 price to VG40",
            "Freight rates change when diesel prices change — update quarterly",
        ],
        "mistakes": [
            "Forgetting to update on 1st or 16th — all quotes for that day will be wrong",
            "Updating only one refinery and forgetting others",
            "Entering price per KL instead of per MT (unit error causes massive quote errors)",
            "Not saving after update — browser refresh reverts to old price",
        ],
        "kpis": [
            "Time between refinery revision and dashboard update (target: <1 hour)",
            "Number of revision cycles missed (target: 0)",
            "Price accuracy audit: Dashboard price vs refinery circular (%)",
        ],
        "risk_if_ignored": (
            "Every single quote from Pricing Calculator will be wrong. "
            "Company quotes old prices, wins deals at losses, or loses deals because quote seems too high. "
            "This is the highest-impact tab if neglected."
        ),
        "linked_tabs": ["Pricing Calculator", "Feasibility", "Financial Intelligence", "Change Notifications"],
    },

    # ── 8. SPECIAL PRICE (SOS) ───────────────────────────────────────────────
    {
        "id": "sos",
        "tab": "🚨 SPECIAL PRICE (SOS)",
        "what": (
            "The SOS tab is an emergency price-blast system. When bitumen prices drop significantly "
            "(>₹200/MT), it auto-generates WhatsApp alerts to all active clients "
            "so they can place orders at the lower price before it reverts."
        ),
        "why": (
            "Price drops in bitumen are temporary and tied to the 14-day revision cycle. "
            "A contractor who knows about a drop can place a large order and save ₹5–15 Lakhs. "
            "Being the first to inform clients builds trust and generates large spot orders. "
            "This tab turns a market event into a revenue opportunity."
        ),
        "impact": {
            "revenue": "Large spot orders from clients who act on price-drop alerts",
            "cost": "If company also pre-buys at the lower price, margin improves significantly",
            "risk": "If alert sent without verifying refinery circular — damages credibility",
            "compliance": "Must not quote a price below cost — ensure alert reflects real price",
            "decision": "Triggers immediate buying decisions across the client network",
        },
        "users": ["Sales Manager", "MD / Director", "Sales Team"],
        "roles": ["Sales", "Management"],
        "inputs": [
            "Trigger condition: Price drop >₹200/MT vs previous cycle",
            "Client list (all active accounts from Ecosystem Management)",
            "New price from Data Manager",
            "Validity period for the special price",
        ],
        "outputs": [
            "Auto-formatted WhatsApp message to client list",
            "SOS alert log (which clients were notified, when)",
            "Order tracking for SOS-triggered deals",
        ],
        "factors": [
            "Price drops are usually short windows of 7–14 days — urgency is real",
            "Only send alerts when price drop is confirmed via refinery circular",
            "Target clients who have active projects and immediate requirement",
            "Large clients should receive a personal call, not just WhatsApp blast",
        ],
        "mistakes": [
            "Sending SOS blast based on market rumour — not confirmed refinery price",
            "Sending to inactive clients who cannot absorb inventory in time",
            "Not having logistics ready to support the surge in orders",
            "Not pre-booking stock at the lower price before sending the alert",
        ],
        "kpis": [
            "SOS order conversion rate (alerts sent vs orders received %)",
            "Revenue from SOS-triggered orders (₹ Crore per event)",
            "Time from price drop to client notification (target: <30 minutes)",
        ],
        "risk_if_ignored": (
            "Company fails to capitalise on price-drop windows. "
            "Competitors who act faster capture the spot orders. Revenue opportunity lost every cycle."
        ),
        "linked_tabs": ["Data Manager", "Pricing Calculator", "Alert System", "CRM & Tasks"],
    },

    # ── 9. REPORTS ───────────────────────────────────────────────────────────
    {
        "id": "reports",
        "tab": "📤 Reports",
        "what": (
            "The Reports tab generates downloadable business documents: price quote PDFs, "
            "deal summaries, margin reports, and client-facing offer letters. "
            "All documents are branded with PPS Anantams identity and GSTIN."
        ),
        "why": (
            "Clients and government contractors require formal written quotations with GSTIN, "
            "terms, and proper formatting before issuing a Purchase Order. "
            "Without professional PDFs, companies like L&T or NHAI will not process the PO."
        ),
        "impact": {
            "revenue": "Professional quotes increase credibility and close rate",
            "cost": "Eliminates cost of manual document preparation",
            "risk": "Reduces errors in client-facing documents (wrong price, wrong GSTIN)",
            "compliance": "GSTIN prominently displayed — required for B2B transactions",
            "decision": "Management can review all outgoing quotes in one place",
        },
        "users": ["Sales Executive", "Sales Manager", "Operations"],
        "roles": ["Sales", "Operations"],
        "inputs": [
            "Client name and billing address",
            "Price from Pricing Calculator",
            "Grade, quantity, delivery terms",
            "Validity date and payment terms",
            "Company GSTIN (auto-filled: 24AAHCV1611L2ZD)",
        ],
        "outputs": [
            "Branded PDF price quotation",
            "Deal summary sheet",
            "Margin report for management",
            "Client-facing offer letter",
        ],
        "factors": [
            "Quote validity: Usually 48–72 hours for bitumen (prices change fast)",
            "GSTIN must be accurate — incorrect GSTIN on quote is a compliance risk",
            "Delivery terms (FOR destination vs ex-works) change who bears freight cost",
            "Payment terms stated on quote are legally binding in dispute",
        ],
        "mistakes": [
            "Quote validity not specified — client expects old price days later",
            "Wrong GSTIN on quote — causes e-invoice mismatch",
            "Sending quote to wrong email — pricing data reaches competitor",
            "Not archiving sent quotes — no evidence in dispute resolution",
        ],
        "kpis": [
            "Reports generated per week",
            "Quote-to-PO conversion rate (%)",
            "Average time from quote to PO receipt (days)",
        ],
        "risk_if_ignored": (
            "Unprofessional communication. Clients cannot process POs without formal quotes. "
            "Compliance gap if GSTIN is missing from client-facing documents."
        ),
        "linked_tabs": ["Pricing Calculator", "GST & Legal Monitor", "Sales Workspace"],
    },

    # ── 10. ECOSYSTEM MANAGEMENT ─────────────────────────────────────────────
    {
        "id": "ecosystem_management",
        "tab": "👥 Ecosystem Management",
        "what": (
            "Ecosystem Management (formerly Party Master) is the master directory of all business "
            "relationships: Suppliers (refineries/importers), Logistics (transporters), "
            "and Customers (contractors, government bodies). "
            "It is the CRM backbone of the entire dashboard."
        ),
        "why": (
            "A bitumen business deals with 3 types of parties simultaneously. "
            "Mixing up a supplier's contact with a transporter's, or not knowing a client's credit limit, "
            "causes operational chaos. This centralised directory prevents that."
        ),
        "impact": {
            "revenue": "Complete client profiles enable targeted selling",
            "cost": "Transporter directory with rates enables freight cost negotiation",
            "risk": "Credit limits visible — prevents over-extension to risky clients",
            "compliance": "GSTIN stored for all parties — ITC verification enabled",
            "decision": "Any team member can access party details independently",
        },
        "users": ["All departments"],
        "roles": ["Sales", "Operations", "Finance", "Logistics"],
        "inputs": [
            "Supplier profiles (name, location, grades, GSTIN, contact)",
            "Transporter profiles (name, permit type, route expertise, rate/km)",
            "Customer profiles (credit limit, outstanding, preferred grade, site city)",
            "Manual updates by operations or sales team",
        ],
        "outputs": [
            "Searchable party directory (by name, city, category)",
            "Client 360 card (used in Sales Workspace)",
            "Transporter shortlist for a given route",
            "Supplier contact list for procurement",
        ],
        "factors": [
            "18+ registered bulk bitumen transporters with All-India Permits are listed",
            "Customer credit limits must be reviewed quarterly — business conditions change",
            "Supplier GSTIN must be verified — fake GSTINs cause ITC reversal",
            "Transporter rates change with diesel price — update semi-annually",
        ],
        "mistakes": [
            "Not updating credit limits when a client's financial health changes",
            "Trusting a new supplier without GSTIN verification",
            "Using expired transporter permit details",
            "Not adding new clients to the directory — they stay invisible to the system",
        ],
        "kpis": [
            "Total active clients in directory",
            "% of clients with complete profiles (GSTIN, credit limit, contact)",
            "Transporter utilisation rate (%)",
            "New clients added per month",
        ],
        "risk_if_ignored": (
            "Operations and sales teams lack critical party information. "
            "Credit extended to risky clients. ITC claimed from non-compliant suppliers. "
            "Logistics coordination fails without transporter contacts."
        ),
        "linked_tabs": ["Sales Workspace", "CRM & Tasks", "GST & Legal Monitor", "Risk Scoring"],
    },

    # ── 11. AI ASSISTANT ─────────────────────────────────────────────────────
    {
        "id": "ai_assistant",
        "tab": "🤖 AI Assistant",
        "what": (
            "The AI Assistant is a natural-language chatbot trained on the complete Bitumen Sales "
            "Knowledge Base. Any employee can ask it questions — product specs, pricing logic, "
            "GST rules, objection scripts — and get instant answers."
        ),
        "why": (
            "Training a new sales person takes 2–3 months. With the AI Assistant, a new joiner "
            "can ask 'What is VG30 used for?' or 'How do I handle a price objection?' "
            "and get an expert answer instantly. Senior staff are freed from repetitive Q&A."
        ),
        "impact": {
            "revenue": "Faster onboarding = salesperson productive sooner",
            "cost": "Reduces training time and senior staff interruptions",
            "risk": "Consistent answers — no incorrect product or compliance information given to clients",
            "compliance": "GST, e-way bill, and legal queries answered from verified knowledge base",
            "decision": "Field staff can resolve client objections independently, improving close rate",
        },
        "users": ["New Employees", "Sales Executives", "Field Staff"],
        "roles": ["All roles"],
        "inputs": [
            "Natural language question from user",
            "Keyword match against 50+ Q&A topics in Knowledge Base",
        ],
        "outputs": [
            "Best-match answer with confidence score",
            "Section reference (product, pricing, logistics, etc.)",
            "Suggested related questions",
        ],
        "factors": [
            "Answer quality depends on knowledge base depth — update KB when industry changes",
            "Confidence score below 60% means the question is outside KB scope",
            "Not a replacement for legal or financial professional advice",
        ],
        "mistakes": [
            "Treating AI answer as final word on legal/compliance matters — consult CA/lawyer",
            "Not updating KB when regulations change — AI gives outdated answers",
            "Using for client-facing quotes without verification from Pricing Calculator",
        ],
        "kpis": [
            "Questions answered per day",
            "Average confidence score (%)",
            "New employee query volume (indicator of onboarding activity)",
        ],
        "risk_if_ignored": (
            "New employees struggle to find information. Senior staff overloaded with basic queries. "
            "Inconsistent answers given to clients."
        ),
        "linked_tabs": ["Knowledge Base", "Settings"],
    },

    # ── 12. KNOWLEDGE BASE ────────────────────────────────────────────────────
    {
        "id": "knowledge_base",
        "tab": "📚 Knowledge Base",
        "what": (
            "The Knowledge Base is the structured library of all institutional knowledge: "
            "product fundamentals, grade applications, pricing logic, sales scripts, logistics rules, "
            "payment terms, and now — complete business intelligence for all dashboard tabs."
        ),
        "why": (
            "In a commodity trading business, knowledge is the competitive advantage. "
            "A salesperson who understands why VG30 costs more than imported bitumen, "
            "or why March is peak season, will outsell someone who does not. "
            "This KB ensures that knowledge is not locked in one person's experience."
        ),
        "impact": {
            "revenue": "Informed salespeople close more deals at better margins",
            "cost": "Reduces dependency on external consultants for basic training",
            "risk": "Consistent, accurate product and compliance information shared across team",
            "compliance": "Regulatory updates documented and accessible to all",
            "decision": "Decision-making quality improves when context is available",
        },
        "users": ["All staff", "New joiners", "Partners", "Investors", "Auditors"],
        "roles": ["All roles"],
        "inputs": [
            "Curated Q&A content (sales training manual)",
            "Business intelligence articles (this document)",
            "Regulatory updates (GST, BIS standards, IRC codes)",
            "Manual additions by management or HR",
        ],
        "outputs": [
            "Searchable Q&A library",
            "Section-wise training modules",
            "Business overview and tab guides",
            "Onboarding roadmap for new employees",
        ],
        "factors": [
            "Knowledge base value degrades if not updated — assign an owner for updates",
            "Separate sections for product, sales, operations, compliance, strategy",
            "Must be accessible to all staff — no gating by seniority",
        ],
        "mistakes": [
            "Treating KB as a one-time document — requires quarterly updates",
            "Not adding learnings from lost deals or compliance incidents",
            "Not connecting KB to AI Assistant — manual search defeats the purpose",
        ],
        "kpis": [
            "Total articles / Q&A entries (target: >100)",
            "Last updated date (should be within 30 days)",
            "Monthly search queries (indicates usage)",
        ],
        "risk_if_ignored": (
            "Institutional knowledge stays with senior staff. "
            "High attrition risk — if a senior person leaves, knowledge leaves with them."
        ),
        "linked_tabs": ["AI Assistant", "GST & Legal Monitor", "Price Prediction"],
    },

    # ── 13. SETTINGS ─────────────────────────────────────────────────────────
    {
        "id": "settings",
        "tab": "⚙️ Settings",
        "what": (
            "Settings manages system-level configuration: API keys for live data feeds, "
            "WhatsApp integration credentials, alert thresholds, user access controls, "
            "and global dashboard preferences."
        ),
        "why": (
            "The dashboard fetches live crude prices, USD/INR rates, and market data from APIs. "
            "Without valid credentials in Settings, all real-time features show mock data. "
            "This is the technical foundation that keeps the intelligence modules alive."
        ),
        "impact": {
            "revenue": "Live data = accurate market intelligence = better trade timing",
            "cost": "API cost is minimal vs the value of real-time decision-making",
            "risk": "Misconfigured settings can break data feeds silently — all forecasts wrong",
            "compliance": "Access controls ensure only authorised staff change prices or configurations",
            "decision": "Correct alert thresholds ensure management is notified of real events",
        },
        "users": ["IT Administrator", "CTO", "MD"],
        "roles": ["Technology", "Management"],
        "inputs": [
            "API keys (crude price feed, forex rate, commodity exchange)",
            "WhatsApp Business API credentials",
            "Alert thresholds (crude price level, margin floor, payment overdue days)",
            "User role assignments",
        ],
        "outputs": [
            "Active/inactive status of each API connection",
            "Alert configuration confirmation",
            "Access control log",
        ],
        "factors": [
            "API keys must be renewed periodically — expiry silently breaks live data",
            "Alert threshold for crude: Recommended ₹75/bbl (warning) and ₹80/bbl (critical)",
            "WhatsApp API requires Meta Business verification",
        ],
        "mistakes": [
            "Sharing API keys with unauthorised staff",
            "Setting margin alert threshold too low — alert fatigue from too many warnings",
            "Not testing settings after changes — broken configuration discovered during a crisis",
        ],
        "kpis": [
            "API uptime % (target: >99%)",
            "Number of false alerts (should trend to zero with correct thresholds)",
            "Last settings audit date",
        ],
        "risk_if_ignored": (
            "Live data stops working. All intelligence modules show stale or mock data. "
            "Management makes decisions on incorrect market information."
        ),
        "linked_tabs": ["API Dashboard", "Alert System", "Data Manager"],
    },

    # ── 14. API DASHBOARD ────────────────────────────────────────────────────
    {
        "id": "api_dashboard",
        "tab": "🌐 API Dashboard",
        "what": (
            "The API Dashboard shows the live status of all external data connections: "
            "crude oil price feed, USD/INR forex rate, weather APIs, and commodity exchanges. "
            "It is the health monitor for the dashboard's real-time intelligence."
        ),
        "why": (
            "When an API fails silently, the dashboard continues showing stale data while "
            "appearing to work normally. A crude price that is 3 days old can cause a ₹1,500/MT "
            "pricing error. This tab makes data source health visible and actionable."
        ),
        "impact": {
            "revenue": "Ensures price intelligence is always based on live data",
            "cost": "Early detection of API failure prevents costly pricing mistakes",
            "risk": "API failure = stale data = wrong decisions. This tab catches it first",
            "compliance": "Audit trail of when data was last refreshed",
            "decision": "Strategy and pricing decisions should only be made when all APIs are green",
        },
        "users": ["IT", "Operations Manager", "Strategy Team"],
        "roles": ["Technology", "Operations", "Strategy"],
        "inputs": [
            "API connection health checks (auto-ping every 60 seconds)",
            "Last successful data refresh timestamp",
            "Error codes from failed API calls",
        ],
        "outputs": [
            "Green/Yellow/Red status per API",
            "Last refresh time per data source",
            "Error log with actionable fix instructions",
            "Data freshness score",
        ],
        "factors": [
            "Crude price API: Most critical — must be green before any price decision",
            "USD/INR rate: Must be live before import cost calculations",
            "Fallback mode: Dashboard uses last known good data if API fails",
        ],
        "mistakes": [
            "Ignoring yellow status — partial data failure is still a failure",
            "Making import decisions when USD/INR API is red",
            "Not escalating API failure to IT within 30 minutes",
        ],
        "kpis": [
            "API uptime % by source (target: >99%)",
            "Mean time to detect (MTTD) API failure (target: <5 minutes)",
            "Mean time to resolve (MTTR) (target: <2 hours)",
        ],
        "risk_if_ignored": (
            "Stale data drives wrong pricing, wrong import timing, and wrong strategy. "
            "In a market where ₹500/MT difference decides deal outcomes, stale data is dangerous."
        ),
        "linked_tabs": ["Settings", "Data Manager", "Alert System", "Price Prediction"],
    },

    # ── 15. PRICE PREDICTION ─────────────────────────────────────────────────
    {
        "id": "price_prediction",
        "tab": "🔮 Price Prediction",
        "what": (
            "Price Prediction uses a Multi-Linear Regression + Deep Learning (MLR-DL) model "
            "to forecast the next bitumen price revision (1st or 16th cycle) based on "
            "Brent crude movement, USD/INR rate, furnace oil parity, and ocean freight trends."
        ),
        "why": (
            "If you know the price will rise by ₹800/MT in 14 days, you can buy maximum stock NOW "
            "and sell at a higher price later — capturing ₹800/MT × thousands of MT profit. "
            "Conversely, if prices are predicted to fall, delay purchases and avoid inventory loss. "
            "This model is the single highest-ROI feature in the dashboard."
        ),
        "impact": {
            "revenue": "Timing inventory purchases before price rises can add ₹40–80 Lakhs per cycle",
            "cost": "Avoiding purchases before price drops prevents ₹800–1,500/MT inventory loss",
            "risk": "Reduces exposure to price volatility through informed advance buying",
            "compliance": "Model outputs are for internal decision-making, not client commitments",
            "decision": "MD and procurement head use this to decide import quantity and timing",
        },
        "users": ["MD / Director", "CFO", "Procurement Head", "Strategy Team"],
        "roles": ["Management", "Finance", "Strategy"],
        "inputs": [
            "Brent crude price (14-day average from API)",
            "USD/INR exchange rate (current and 14-day trend)",
            "Furnace oil (FO) spread vs crude",
            "Ocean freight rate (Iraq/Gulf to Indian ports)",
            "Previous revision prices (from Historical Revisions tab)",
        ],
        "outputs": [
            "Next revision date (1st or 16th of next month)",
            "Predicted price (₹/MT) with confidence band (Low–High range)",
            "Waterfall driver analysis (how much each factor contributes)",
            "24-month forward revision calendar",
            "Plain-English model rationale",
        ],
        "factors": [
            "Brent crude: 1 USD/bbl change = approx ₹300–400/MT impact on bitumen",
            "USD/INR: 1 rupee depreciation = approx ₹380–400/MT on import cost",
            "Lag effect: Crude prices today affect bitumen price in the NEXT cycle (7–14 day lag)",
            "Refinery discretion: PSUs sometimes absorb market changes — model cannot predict this",
            "Monsoon factor: Refineries occasionally reduce bitumen output, limiting supply",
        ],
        "mistakes": [
            "Treating predicted price as certain — it is a probability range, not a guarantee",
            "Buying maximum stock based on prediction without hedging downside risk",
            "Ignoring the confidence band — a wide band means high uncertainty",
            "Using prediction to make client commitments on future price",
        ],
        "kpis": [
            "Prediction accuracy: Actual vs predicted (target: within ±₹400/MT)",
            "Directional accuracy: Correct up/down call (target: >85%)",
            "Revenue captured from correct prediction-led purchases (₹ Lakhs)",
        ],
        "risk_if_ignored": (
            "Company buys inventory at random times. Catches price rises after they happen. "
            "Competitors with price intelligence consistently buy cheaper and sell higher."
        ),
        "linked_tabs": ["Import Cost Model", "Financial Intelligence", "Data Manager", "Past Predictions", "Alert System"],
    },

    # ── 16. IMPORT COST MODEL ────────────────────────────────────────────────
    {
        "id": "import_cost_model",
        "tab": "📦 Import Cost Model",
        "what": (
            "The Import Cost Model provides a granular, line-by-line cost breakdown for importing "
            "bitumen from Gulf countries (Iraq, Saudi Arabia, UAE) to Indian ports — covering "
            "FOB price, ocean freight, insurance, customs duty (2.5%), CHA charges, port handling, "
            "GST, and final landed cost per MT."
        ),
        "why": (
            "Import bitumen is 10–20% cheaper at the refinery gate but carries many additional costs. "
            "Without a detailed model, importers underestimate total landed cost by ₹2,000–5,000/MT "
            "and end up selling at a loss. This model ensures every cost component is accounted for."
        ),
        "impact": {
            "revenue": "Accurate import cost enables competitive but profitable pricing",
            "cost": "Identifies cost-reduction opportunities in freight, CHA, or port handling",
            "risk": "Prevents the common error of underestimating import duty and GST",
            "compliance": "Customs duty, BCD, and IGST calculations are built into the model",
            "decision": "Import vs domestic sourcing decision made with full cost visibility",
        },
        "users": ["MD", "CFO", "Procurement Head", "Import Coordinator"],
        "roles": ["Management", "Finance", "Procurement"],
        "inputs": [
            "FOB price (USD/MT) from supplier quote",
            "Ocean freight (USD/MT) — varies by vessel size and port",
            "Insurance % of CIF value (typically 0.5%)",
            "USD/INR exchange rate (live from API)",
            "Vessel quantity (MT) — affects per-MT fixed cost allocation",
            "Port berthing charges (₹ fixed total)",
            "CHA charges (₹/MT), Handling (₹/MT)",
            "Customs duty % (currently 2.5%) and GST 18%",
        ],
        "outputs": [
            "CIF value per MT",
            "Total import duty per MT",
            "Port charges per MT",
            "Total landed cost per MT in INR",
            "Break-even selling price",
            "Margin at various selling prices (sensitivity analysis)",
            "Comparison vs domestic refinery cost",
        ],
        "factors": [
            "Switch Bill of Lading (BL): ₹150–200/MT — often overlooked, always required",
            "Vessel size matters: 5,000 MT vs 10,000 MT vessel — port charges per MT halve",
            "Demurrage risk: Each extra day at port costs ₹ 15,000–25,000 (shared across cargo)",
            "IGST on import is recoverable as ITC — not a real cost for GST-registered buyers",
            "Exchange rate lock: Companies that hedge USD/INR exposure at time of order protect margin",
        ],
        "mistakes": [
            "Forgetting Switch BL cost (₹166–200/MT) — eats directly into margin",
            "Using spot forex rate for costing but vessel takes 21 days — rate may move adversely",
            "Not accounting for detention/demurrage if discharge takes longer than laycan",
            "Confusing CIF and FOB basis — freight and insurance responsibility shifts",
            "Assuming all ports have same handling cost — Kandla and JNPT rates differ significantly",
        ],
        "kpis": [
            "Import vs domestic cost differential (₹/MT) per cycle",
            "Actual vs modelled landed cost variance (%)",
            "Demurrage incidents per shipment (target: 0)",
            "CHA cost per MT vs industry benchmark",
        ],
        "risk_if_ignored": (
            "Import deals signed without understanding full cost. "
            "Company discovers post-shipment that the deal is loss-making. "
            "A 5,000 MT shipment at ₹1,000/MT loss = ₹50 Lakh direct loss."
        ),
        "linked_tabs": ["Price Prediction", "Feasibility", "Financial Intelligence", "Supply Chain"],
    },

    # ── 17. SUPPLY CHAIN ─────────────────────────────────────────────────────
    {
        "id": "supply_chain",
        "tab": "🚢 Supply Chain",
        "what": (
            "The Supply Chain tab tracks active import shipments: vessel names, ETA, port, "
            "quantity, and delivery status. It also models domestic supply chains — "
            "tanker dispatch from refineries, transit time, and stock availability."
        ),
        "why": (
            "Clients ask 'When will material arrive?' Operations needs to know 'Which tanker "
            "is delivering where today?' A delay in one vessel can cascade into missed contractor "
            "deadlines and penalty clauses. Real-time visibility prevents surprises."
        ),
        "impact": {
            "revenue": "On-time delivery protects repeat business and reduces penalty risk",
            "cost": "Proactive delay detection allows rerouting before demurrage accrues",
            "risk": "Vessel delay visibility allows advance notice to clients — protects relationships",
            "compliance": "E-way bill validity aligned with actual transit times",
            "decision": "Procurement can time next order based on current stock transit status",
        },
        "users": ["Operations Manager", "Logistics Coordinator", "MD"],
        "roles": ["Operations", "Logistics", "Management"],
        "inputs": [
            "Vessel name, quantity, loading port, destination port",
            "Bill of Lading date and ETA",
            "Domestic tanker dispatch records",
            "Port congestion status (manual or API)",
        ],
        "outputs": [
            "Active shipment tracker with status (In Transit / At Port / Discharged)",
            "ETA countdown per vessel",
            "Delay alerts with client impact assessment",
            "Domestic tanker dispatch status",
        ],
        "factors": [
            "Transit time: Gulf to India = 14–21 days depending on port",
            "Monsoon disruption: June–Sep — domestic trucking delays 20–30%",
            "Port congestion: Kandla and Mundra see seasonal backlogs in Oct–Nov",
            "E-way bill: Valid for 1 day per 200 km — must match actual transit time",
        ],
        "mistakes": [
            "Promising delivery dates without checking vessel ETA first",
            "Not monitoring vessel AIS tracking — delay discovered only at port",
            "E-way bill generated too early — expires before delivery",
            "No backup plan when vessel delays by 3–5 days",
        ],
        "kpis": [
            "On-time delivery % (target: >90%)",
            "Average vessel delay in days",
            "Demurrage cost per quarter (target: zero)",
            "Domestic tanker turnaround time (days)",
        ],
        "risk_if_ignored": (
            "Contractor sites run out of material mid-project. Penalty clauses triggered. "
            "Company reputation damaged. Repeat business lost."
        ),
        "linked_tabs": ["Import Cost Model", "Alert System", "Sales Calendar", "Financial Intelligence"],
    },

    # ── 18. DEMAND ANALYTICS ─────────────────────────────────────────────────
    {
        "id": "demand_analytics",
        "tab": "👷 Demand Analytics",
        "what": (
            "Demand Analytics analyses government infrastructure spending patterns, NHAI project awards, "
            "election cycle effects, state budget allocations, and monsoon impact to predict "
            "which regions will have high bitumen demand and when."
        ),
        "why": (
            "Bitumen demand in India is 90% driven by government road projects. "
            "Knowing that Rajasthan has ₹8,000 Crore of road projects starting in Q3 "
            "allows the sales team to target Rajasthan contractors 3 months in advance."
        ),
        "impact": {
            "revenue": "Proactive targeting of high-demand regions before competitors",
            "cost": "Stock prepositioned in right locations reduces urgent freight cost",
            "risk": "Prevents over-stocking in regions where demand is actually declining",
            "compliance": "Project pipeline data helps validate contractor legitimacy",
            "decision": "Sales territory planning aligned with actual infrastructure activity",
        },
        "users": ["Sales Director", "Strategy Head", "Regional Managers"],
        "roles": ["Sales", "Strategy", "Management"],
        "inputs": [
            "NHAI project award announcements (public data)",
            "State budget road allocation (annual)",
            "Election cycle calendar",
            "Monsoon forecast (June–Sep impact)",
            "Historical demand patterns by state and month",
        ],
        "outputs": [
            "State-wise demand heatmap",
            "Seasonal demand multiplier by region",
            "Top 5 high-demand states for the current quarter",
            "Election cycle demand uplift estimate",
        ],
        "factors": [
            "Government spending is front-loaded in Q4 (Jan–March) before FY close",
            "Election year: Pre-election road push adds 20–25% demand nationally",
            "Post-monsoon (Oct–Nov): Delayed projects restart — demand surge",
            "Northeast India has unique demand pattern — isolated from mainland logistics",
        ],
        "mistakes": [
            "Targeting states based on historical data without checking current project awards",
            "Ignoring monsoon impact on Northeast and coastal states",
            "Assuming national demand pattern applies uniformly to all regions",
            "Not adjusting inventory pre-positioning based on demand forecast",
        ],
        "kpis": [
            "Forecast vs actual regional sales volume (variance %)",
            "Market share by state",
            "New contractor acquisitions in high-demand regions",
            "Time to first contact after project award announcement",
        ],
        "risk_if_ignored": (
            "Sales effort concentrated in saturated regions while high-growth regions are missed. "
            "Competitors capture emerging demand. Revenue growth stagnates."
        ),
        "linked_tabs": ["Sales Calendar", "Strategy Panel", "CRM & Tasks", "Alert System"],
    },

    # ── 19. FINANCIAL INTELLIGENCE ───────────────────────────────────────────
    {
        "id": "financial_intel",
        "tab": "💰 Financial Intelligence",
        "what": (
            "Financial Intelligence provides the CFO-level view: shipment-wise P&L, "
            "receivable aging, working capital stress analysis, monthly margin trends, "
            "break-even volume, and 'what-if' scenario modelling for crude/freight/FX changes."
        ),
        "why": (
            "A sales team can celebrate booking 10,000 MT while the CFO sees that "
            "receivables have aged to 90+ days and working capital is exhausted. "
            "This tab ensures financial health is monitored alongside sales performance."
        ),
        "impact": {
            "revenue": "Identifies which shipments/clients are actually profitable vs just high-volume",
            "cost": "Working capital cost visibility — interest on 45-day receivable cycles",
            "risk": "Receivable aging alerts prevent cash flow crisis",
            "compliance": "GST credit tracking ensures ITC is claimed on time",
            "decision": "Break-even analysis informs minimum order quantity and margin floor",
        },
        "users": ["CFO", "MD", "Finance Manager", "Board"],
        "roles": ["Finance", "Management"],
        "inputs": [
            "Shipment-wise revenue and cost (from deal records)",
            "Receivable aging data (client-wise outstanding)",
            "Working capital position",
            "GST credit receivable",
            "Scenario parameters: crude %, freight ₹/MT, USD change %",
        ],
        "outputs": [
            "Monthly P&L summary (Revenue / COGS / Gross Profit / Net Margin)",
            "Vessel-wise profitability table",
            "Receivable aging buckets (0–30 / 31–60 / 61–90 / 90+ days)",
            "Working capital requirement forecast",
            "Scenario simulation: margin impact of crude/FX/freight changes",
            "Break-even MT per month",
        ],
        "factors": [
            "Crude +1% → margin -0.4% (model sensitivity)",
            "Freight +₹1/MT → margin -0.15%",
            "USD +1% → margin -0.3% (on import cargo)",
            "12% average margin — at ₹40,000/MT base, that is ₹4,800/MT gross profit",
            "Working capital cycle: Pay supplier D+0, collect from client D+30 to D+45 — need 45-day float",
        ],
        "mistakes": [
            "Focusing only on revenue — a high-revenue deal with 3% margin is worse than a small deal with 15%",
            "Ignoring 90+ day receivables — these often become uncollectible",
            "Not factoring GST credit in cashflow — large ITC receivable can fund working capital",
            "Running scenario analysis with unrealistic crude change assumptions",
        ],
        "kpis": [
            "Gross margin % (target: 10–15%)",
            "Net margin % (target: 4–8%)",
            "Receivables >60 days as % of total (target: <15%)",
            "Working capital cycle days (target: <45)",
            "Monthly EBITDA (₹ Lakhs)",
        ],
        "risk_if_ignored": (
            "Company shows revenue growth but is actually cash-flow negative. "
            "Bad debts accumulate silently. Working capital crisis hits suddenly. "
            "Profitable-looking business becomes insolvent."
        ),
        "linked_tabs": ["Price Prediction", "Risk Scoring", "Reports", "CRM & Tasks", "Import Cost Model"],
    },

    # ── 20. GST & LEGAL MONITOR ──────────────────────────────────────────────
    {
        "id": "gst_legal",
        "tab": "🛡️ GST & Legal Monitor",
        "what": (
            "GST & Legal Monitor tracks compliance obligations: GSTR-1 and GSTR-3B filing deadlines, "
            "e-way bill rules, Input Tax Credit (ITC) reconciliation, supplier GST status, "
            "and regulatory updates affecting the bitumen trade."
        ),
        "why": (
            "GST non-compliance in bitumen trading can trigger ITC reversal of crores (if supplier's "
            "GSTIN is fake or cancelled), penalties up to 100% of tax, and DGGI investigations. "
            "The HSN code for bitumen (27132000) must be correctly applied in every invoice."
        ),
        "impact": {
            "revenue": "ITC reversal can wipe out months of profit in a single assessment",
            "cost": "Timely filing avoids late fees (₹50/day) and interest (18%/year)",
            "risk": "Fake GSTIN supplier = ITC reversal = direct cash loss",
            "compliance": "GSTR-1/3B reconciliation is mandatory for GST audit readiness",
            "decision": "Procurement team must check supplier GSTIN before every purchase",
        },
        "users": ["CA / Finance Team", "Legal Head", "MD", "Procurement"],
        "roles": ["Finance", "Legal", "Compliance"],
        "inputs": [
            "GSTR-1 filing deadline (11th of following month)",
            "GSTR-3B deadline (20th of following month)",
            "Supplier GSTIN list (from Ecosystem Management)",
            "E-way bill distance and validity rules",
            "HSN code: 27132000 (Petroleum bitumen)",
        ],
        "outputs": [
            "Compliance calendar with upcoming deadlines",
            "Supplier GSTIN risk flags",
            "ITC reconciliation status",
            "E-way bill compliance checklist",
            "Regulatory update alerts",
        ],
        "factors": [
            "HSN 27132000: Petroleum bitumen — GST rate 18%. Wrong HSN = notice from GSTN",
            "GSTR-2B matching: ITC can only be claimed if supplier has filed GSTR-1",
            "E-way bill: Required for movement >50 km or value >₹50,000. Valid 1 day per 200 km",
            "Section 74: GST department can raise demand with 100% penalty for fake ITC",
            "DGGI investigations: Trigger when cumulative ITC from a supplier seems disproportionate",
        ],
        "mistakes": [
            "Buying from a supplier whose GSTIN is suspended — ITC will be reversed",
            "Generating e-way bill for wrong distance — vehicle intercepted, goods detained",
            "Filing GSTR-3B without reconciling with GSTR-2B — mismatch creates liability",
            "Using wrong HSN code on invoice — attracts wrong tax rate and scrutiny",
            "Not checking regulatory updates — new e-invoice threshold changes affect workflow",
        ],
        "kpis": [
            "GSTR-1 / GSTR-3B filing compliance rate (target: 100% on time)",
            "ITC reconciliation rate: GSTR-2B matched % (target: >95%)",
            "E-way bill violation count (target: 0)",
            "Suppliers with active GSTIN % (target: 100%)",
        ],
        "risk_if_ignored": (
            "DGGI investigation. ITC reversal of crores. Penalty = 100% of tax amount. "
            "Director-level personal liability. Business operations halted during investigation."
        ),
        "linked_tabs": ["Risk Scoring", "Alert System", "Ecosystem Management", "Reports"],
    },

    # ── 21. RISK SCORING ─────────────────────────────────────────────────────
    {
        "id": "risk_scoring",
        "tab": "⚡ Risk Scoring",
        "what": (
            "Risk Scoring provides a composite, AI-generated risk score (0–100) across six dimensions: "
            "Market Risk, Supply Risk, Financial Risk, Compliance Risk, Legal Exposure, and Margin Safety. "
            "It then calculates an overall Business Health Score."
        ),
        "why": (
            "Senior management cannot monitor 24 modules simultaneously. "
            "The Risk Score condenses all risk signals into one number. "
            "If Health Score drops below 60, something in the business needs immediate attention."
        ),
        "impact": {
            "revenue": "Early risk detection prevents revenue-threatening events",
            "cost": "Proactive risk management is cheaper than crisis management",
            "risk": "Single number dashboard of all business risks — enables prioritisation",
            "compliance": "Compliance risk sub-score flags GST/legal issues early",
            "decision": "Board and management review Health Score as the first KPI of the week",
        },
        "users": ["MD", "CFO", "Board", "Department Heads"],
        "roles": ["Management", "Finance", "Legal"],
        "inputs": [
            "Market data (crude volatility, seasonal position)",
            "Supply chain status (vessel delays, refinery allocation)",
            "Financial data (receivable aging, working capital)",
            "Compliance data (GST filing status, supplier GSTIN checks)",
            "Legal data (investigation flags, notices)",
            "Margin data (current vs floor margin)",
        ],
        "outputs": [
            "Overall Health Score (0–100)",
            "6 dimension risk scores with visual gauges",
            "Risk trend chart (week-on-week movement)",
            "Action recommendations for high-risk areas",
        ],
        "factors": [
            "Weight distribution: Market 20%, Financial 20%, Margin Safety 20%, Supply 15%, Compliance 15%, Legal 10%",
            "Score <40: Critical — immediate intervention needed",
            "Score 40–70: Watch — monitor daily",
            "Score >70: Healthy — normal operations",
            "Peak season reduces market risk but increases operational risk",
        ],
        "mistakes": [
            "Treating the score as an automatic system — it requires human review of flagged areas",
            "Ignoring a single dimension spike even if overall score is good",
            "Not correlating risk score drop with real business events",
        ],
        "kpis": [
            "Weekly Health Score (target: >70)",
            "Days with Health Score below 60 (target: <5 per quarter)",
            "Risk score improvement after corrective action",
        ],
        "risk_if_ignored": (
            "Multiple small risks accumulate unnoticed into a major crisis. "
            "No early warning system. Company discovers problems only when they become emergencies."
        ),
        "linked_tabs": ["GST & Legal Monitor", "Financial Intelligence", "Alert System", "Strategy Panel"],
    },

    # ── 22. ALERT SYSTEM ─────────────────────────────────────────────────────
    {
        "id": "alert_system",
        "tab": "🔔 Alert System",
        "what": (
            "The Alert System is the real-time notification centre. "
            "It monitors crude prices, vessel ETAs, margin levels, payment overdue, "
            "GST mismatches, and supplier risk flags — then generates prioritised alerts "
            "with specific action instructions."
        ),
        "why": (
            "In a commodity trading business, a ₹5/bbl crude spike in the morning can mean "
            "₹1,500/MT cost increase by afternoon. An alert that reaches the MD in 5 minutes "
            "instead of 5 hours can save crores of rupees in purchase timing."
        ),
        "impact": {
            "revenue": "Timely alerts on price drops enable SOS blasts and large spot orders",
            "cost": "Crude spike alerts trigger advance buying before cost increase",
            "risk": "Supplier investigation alert prevents ITC loss from a blacklisted supplier",
            "compliance": "GST mismatch alerts prevent filing errors",
            "decision": "Every critical alert comes with a specific recommended action",
        },
        "users": ["MD", "Sales Manager", "Finance", "Operations"],
        "roles": ["All senior roles"],
        "inputs": [
            "Crude price threshold breaches (API)",
            "Vessel ETA changes (Supply Chain feed)",
            "Margin below floor level (Financial Intelligence)",
            "Payment overdue triggers (CRM)",
            "Supplier GSTIN flag (GST Monitor)",
            "Manual alerts created by management",
        ],
        "outputs": [
            "Prioritised alert list (Critical / Warning / Info)",
            "Alert details with recommended action",
            "Acknowledgement log (who saw it and when)",
            "Alert history for audit",
        ],
        "factors": [
            "Critical alerts must be acknowledged within 2 hours",
            "Crude crossing ₹80/bbl threshold: Expected ₹500–700/MT increase in next 7 days",
            "Margin below 8% on any route: Flag for immediate re-quoting",
            "Supplier under DGGI investigation: Suspend purchases immediately",
        ],
        "mistakes": [
            "Alert fatigue: Too many low-priority alerts cause real critical alerts to be missed",
            "Not acknowledging alerts — creates audit gap",
            "Not following recommended action — alert becomes noise",
            "Only MD has access to alerts — must be visible to relevant department heads",
        ],
        "kpis": [
            "Critical alert acknowledgement time (target: <2 hours)",
            "Alert-to-action rate (% of alerts that resulted in action)",
            "False positive rate (% of alerts that were not real issues)",
            "Revenue saved/loss prevented from acted alerts (₹ Lakhs per quarter)",
        ],
        "risk_if_ignored": (
            "Management operates blind. Crude spikes, vessel delays, and GST issues discovered "
            "after the damage is done. Reactive business instead of proactive."
        ),
        "linked_tabs": ["API Dashboard", "Risk Scoring", "SPECIAL PRICE (SOS)", "GST & Legal Monitor"],
    },

    # ── 23. STRATEGY PANEL ───────────────────────────────────────────────────
    {
        "id": "strategy_panel",
        "tab": "📊 Strategy Panel",
        "what": (
            "The Strategy Panel is the AI-driven executive decision support system. "
            "It analyses current market conditions and gives structured recommendations on "
            "the three biggest recurring decisions in bitumen trading: "
            "Import Now or Wait? / Hedge Crude Exposure? / Increase Inventory?"
        ),
        "why": (
            "These three decisions, made correctly across 24 revision cycles per year, "
            "determine 80% of the company's profitability. "
            "Without structured analysis, they are made on gut feel. "
            "This panel makes them data-driven with confidence scores and reasoning."
        ),
        "impact": {
            "revenue": "Correct import timing can add ₹80–150 Lakhs per cycle",
            "cost": "Avoiding inventory buildup during downtrend prevents ₹50–100 Lakhs loss",
            "risk": "Hedging recommendations protect against FX and crude volatility",
            "compliance": "Strategy decisions documented for board / investor review",
            "decision": "Replaces 3-hour management meetings with a structured, data-backed view",
        },
        "users": ["MD", "CFO", "Board", "Strategy Director"],
        "roles": ["Management", "Strategy", "Finance"],
        "inputs": [
            "Current market position (peak/off season, monsoon flag)",
            "FOB price and trend",
            "USD/INR rate and trend",
            "Ocean freight rate",
            "Current inventory level (MT)",
            "Working capital availability",
        ],
        "outputs": [
            "3 key decision recommendations with confidence scores",
            "Reasoning bullets for each recommendation",
            "Risk caveat for each decision",
            "Colour-coded urgency (Green = Act / Yellow = Monitor / Red = Hold)",
        ],
        "factors": [
            "Import decision: Peak season (Oct–Mar) = import now. Monsoon = wait",
            "Hedge decision: Crude volatility >15% = partial hedge recommended",
            "Inventory decision: Storage cost ₹50/MT/month vs price appreciation risk",
            "Confidence score: Based on current data quality and market stability",
        ],
        "mistakes": [
            "Over-riding AI recommendation without documenting reasons",
            "Acting on 'IMPORT NOW' without checking LC/working capital availability",
            "Ignoring the risk caveat section of each recommendation",
            "Using strategy panel as sole input — must be combined with MD's market judgment",
        ],
        "kpis": [
            "Recommendation adherence rate (%)",
            "P&L impact of import timing decisions (₹ Lakhs per quarter)",
            "Inventory days saved by correct 'wait' decisions",
            "Hedge coverage as % of import exposure",
        ],
        "risk_if_ignored": (
            "Strategic decisions made on intuition alone. "
            "Systematic losses from wrong import timing. No accountability for strategy calls."
        ),
        "linked_tabs": ["Price Prediction", "Import Cost Model", "Financial Intelligence", "Risk Scoring", "Demand Analytics"],
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# RISK MATRIX SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

RISK_MATRIX = [
    {"risk": "Crude Oil Price Spike", "probability": "High", "impact": "Critical", "mitigation": "Price Prediction + advance buying; Strategy Panel hedge recommendation", "tabs": "Price Prediction, Alert System, Strategy Panel"},
    {"risk": "USD/INR Depreciation", "probability": "Medium", "impact": "High", "mitigation": "Import cost model forex sensitivity; consider forward contracts", "tabs": "Import Cost Model, Financial Intelligence"},
    {"risk": "Fortnightly Revision Missed", "probability": "Low", "impact": "Critical", "mitigation": "Data Manager update SOP on 1st and 16th; Change Notifications alert", "tabs": "Data Manager, Alert System"},
    {"risk": "Fake GSTIN Supplier (ITC Reversal)", "probability": "Medium", "impact": "Critical", "mitigation": "GSTIN verification in Ecosystem Management; GST Monitor alerts", "tabs": "GST & Legal Monitor, Risk Scoring"},
    {"risk": "Client Payment Default (Bad Debt)", "probability": "Medium", "impact": "High", "mitigation": "Credit limit check in Sales Workspace; 90+ day alert in CRM & Financial Intelligence", "tabs": "Financial Intelligence, CRM & Tasks"},
    {"risk": "Vessel Delay / Demurrage", "probability": "Medium", "impact": "High", "mitigation": "Supply Chain tracking; Alert System ETA change notification", "tabs": "Supply Chain, Alert System"},
    {"risk": "Monsoon Inventory Lockup", "probability": "High (seasonal)", "impact": "High", "mitigation": "Sales Calendar seasonal planning; reduce inventory from May", "tabs": "Sales Calendar, Demand Analytics"},
    {"risk": "Margin Erosion Below Floor", "probability": "Medium", "impact": "High", "mitigation": "Alert System margin floor breach; re-quote all outstanding offers", "tabs": "Alert System, Financial Intelligence"},
    {"risk": "E-Way Bill Compliance Failure", "probability": "Low", "impact": "Medium", "mitigation": "GST Monitor e-way bill checklist; operations SOP compliance", "tabs": "GST & Legal Monitor"},
    {"risk": "API Data Feed Failure", "probability": "Low", "impact": "Medium", "mitigation": "API Dashboard monitoring; fallback to last known good data", "tabs": "API Dashboard, Settings"},
    {"risk": "Sales Team Knowledge Gap", "probability": "High", "impact": "Medium", "mitigation": "AI Assistant + Knowledge Base; structured onboarding roadmap", "tabs": "Knowledge Base, AI Assistant"},
    {"risk": "DGGI / GST Investigation", "probability": "Low", "impact": "Critical", "mitigation": "ITC reconciliation; supplier GSTIN audit; clean invoice records", "tabs": "GST & Legal Monitor, Risk Scoring, Alert System"},
]

# ─────────────────────────────────────────────────────────────────────────────
# TOP 50 FAQ
# ─────────────────────────────────────────────────────────────────────────────

FAQ_50 = [
    # BUSINESS MODEL
    {"q": "What business does PPS Anantams do?", "a": "We are a B2B bitumen trading and logistics company. We procure bitumen from PSU refineries and import terminals, then supply it to road contractors and infrastructure companies across India."},
    {"q": "How does the company make money?", "a": "By buying bitumen at source price (+ GST + freight) and selling it at a margin of 8–15% to end contractors. The margin per MT multiplied by total MT sold = gross profit."},
    {"q": "Why does bitumen price change so often?", "a": "Bitumen is a crude oil derivative. PSU refineries revise prices on the 1st and 16th of every month based on crude oil movement. A ₹ 5/bbl crude change can move bitumen by ₹1,500–2,000/MT."},
    {"q": "What is the 1st and 16th cycle?", "a": "Indian PSU refineries (IOCL, BPCL, HPCL etc.) revise bitumen prices twice a month — on the 1st and 16th. These are called 'fortnightly revisions'. All procurement and pricing decisions revolve around these dates."},
    {"q": "What is the difference between domestic and import bitumen?", "a": "Domestic bitumen comes from Indian refineries (IOCL, BPCL etc.) at INR-denominated prices. Import bitumen comes from Gulf countries at USD-denominated FOB price, with additional ocean freight, customs duty (2.5%), and port charges. Import is often cheaper at source but carries FX and demurrage risk."},
    {"q": "What is VG30 and who uses it?", "a": "VG30 (Viscosity Grade 30) is the standard bitumen grade used for city roads, highways, and general road construction in India. It is the highest-volume product in our portfolio."},
    {"q": "What is GST on bitumen?", "a": "18% GST applies on bitumen (HSN code 27132000). For registered buyers, this is Input Tax Credit (ITC) — they recover it. For unregistered buyers, it is an additional cost."},
    {"q": "What is a landed cost?", "a": "Landed cost = Base price + GST + Freight from source to destination. It is the total cost per MT to get the material to the buyer's site. This is the basis for all pricing decisions."},
    # PRICING & MARGINS
    {"q": "What is a good margin in bitumen trading?", "a": "Gross margin of 10–15% is healthy. Net margin after finance costs and overheads is 4–8%. Margins below 8% gross warrant immediate re-evaluation of the supply source or selling price."},
    {"q": "How do I calculate the selling price for a customer?", "a": "Use the Pricing Calculator tab. Enter source, destination, and desired margin %. It calculates: (Base Price × 1.18 GST) + Freight + Margin = Selling Price."},
    {"q": "What is the freight rate for bulk bitumen?", "a": "Standard rate: ₹5.5 per km for bulk tankers. ₹6.0 per km for drum bitumen. These are configurable in Data Manager."},
    {"q": "How much does decanting cost?", "a": "Decanting (converting drum bitumen to bulk) costs ₹500/MT fixed at the decanter facility, plus local transport of ~30 km from decanter to site."},
    {"q": "When should I use an import terminal vs a refinery?", "a": "Use the Feasibility tab. For cities within 300–500 km of Kandla/Mundra (Gujarat, Rajasthan), import terminals often beat refinery landed cost. For inland cities, nearby refineries are usually cheaper."},
    {"q": "What happens to my margin if crude rises ₹1,000/MT?", "a": "If you have not yet bought stock, your cost rises by ₹1,000/MT and margin falls by approximately 2–3% (on a 12% margin base). Use Financial Intelligence scenario simulator to get the exact impact."},
    # OPERATIONS
    {"q": "How long does an import shipment take?", "a": "Gulf to Indian ports: 14–21 days transit. Add 2–5 days for port clearance, customs, and CHA. Total from order to available stock: 21–28 days."},
    {"q": "What is an e-way bill?", "a": "A government-issued electronic document required for movement of goods worth >₹50,000 or distance >50 km. For bitumen tankers, it is mandatory for every dispatch. Valid for 1 day per 200 km."},
    {"q": "What is Switch BL?", "a": "Switch Bill of Lading — a document that replaces the original BL with a new one showing the Indian importer as consignee instead of the overseas buyer. Costs ₹150–200/MT and is mandatory for most Gulf imports."},
    {"q": "Who are the main bitumen transporters?", "a": "Specialised bulk bitumen tanker operators with All-India Permits. See Source Directory → Transporters section for the 18+ registered transporters in our network."},
    {"q": "What is demurrage?", "a": "A penalty charged by the shipping company when a vessel stays at port longer than the agreed free time (usually 3–5 days). Cost: ₹ 15,000–25,000/day. Divided across cargo MT, this can be ₹300–500/MT extra cost."},
    {"q": "What is the peak season for bitumen?", "a": "October to March. Government budget release, post-monsoon project restart, and NHAI execution peak in these months. Demand is 2x the monsoon average."},
    {"q": "Why does demand drop in monsoon?", "a": "Road construction requires dry conditions. Bitumen cannot be laid in rain. All outdoor road projects halt from June to September across most of India."},
    # COMPLIANCE
    {"q": "What is GSTR-1 and when is it due?", "a": "GSTR-1 is the monthly return of outward supplies (sales invoices). Due on the 11th of the following month. Filing late attracts ₹50/day penalty."},
    {"q": "What is GSTR-3B and when is it due?", "a": "GSTR-3B is the monthly summary return of tax liability and ITC claim. Due on the 20th of the following month. Non-filing attracts 18% interest on outstanding tax."},
    {"q": "What is ITC reversal?", "a": "If a supplier's GSTIN is fake, cancelled, or they have not filed GSTR-1, the GST department reverses your Input Tax Credit. You must pay back the tax plus 18% interest. Always verify supplier GSTIN before purchase."},
    {"q": "What is HSN code for bitumen?", "a": "27132000 — Petroleum Bitumen. Must be correctly mentioned on every invoice, e-way bill, and GST return. Wrong HSN attracts notices and incorrect tax rates."},
    {"q": "What is Section 74 GST?", "a": "Section 74 is invoked for cases of fraud, wilful misstatement, or suppression. Demand = tax + 100% penalty. Directors can face personal liability. Avoid by ensuring all supplier GSTINs are valid and ITC reconciliation is clean."},
    # RISK
    {"q": "What is the biggest risk in bitumen trading?", "a": "Crude oil price volatility. A sudden ₹ 10/bbl spike can increase cost by ₹3,000–4,000/MT overnight. If you hold inventory bought at old price, margin is protected. If you are buying fresh, margin collapses."},
    {"q": "What is FX risk?", "a": "For import bitumen, cost is in USD. If you fix the selling price in INR today but the rupee depreciates by ₹2 before you import, your import cost rises by ₹800–1,000/MT with no increase in selling price."},
    {"q": "What is supply risk?", "a": "Refineries can reduce bitumen allocation, ships can be delayed, and ports can be congested. Supply risk is higher in peak season when demand is maximum. Always have 2–3 backup sources identified in Source Directory."},
    {"q": "What is credit risk?", "a": "The risk that a client does not pay. In bitumen, contractors sometimes face project payment delays and pass the cash crunch to suppliers. Receivables beyond 90 days often become bad debt. Monitor aging in Financial Intelligence."},
    # STRATEGY
    {"q": "When should we import vs buy from domestic refineries?", "a": "Use the Strategy Panel and Feasibility tab. Import is cheaper when: crude is low, rupee is strong, and freight is competitive. Domestic is better when: import logistics are complex and domestic source is close to delivery point."},
    {"q": "What is the ideal inventory holding period?", "a": "In peak season: 15–20 days of forward demand. In monsoon: minimum possible — avoid cash lockup. Storage at Kandla terminal costs ₹50/MT/month."},
    {"q": "How do we decide when to pre-buy stock?", "a": "Use Price Prediction. If next cycle is forecast to rise >₹500/MT with >70% confidence, pre-buy maximum capacity. The gain on pre-bought stock exceeds storage cost significantly."},
    {"q": "How do we compete with larger traders?", "a": "Speed of quote (Pricing Calculator delivers in 90 seconds vs 2 hours manually), quality of client relationships (Sales Workspace + CRM), and source optimisation (Feasibility tab). Larger traders are slower; we win on agility."},
    # CLIENTS
    {"q": "What kind of clients do we serve?", "a": "Road contractors (L&T, Dilip Buildcon, HG Infra), government project contractors, NHAI sub-contractors, municipal corporations, and PMC agencies."},
    {"q": "What payment terms do contractors expect?", "a": "Most large contractors want 30–45 day credit. Our standard is 100% advance. Compromise: 50% advance + 50% against delivery, with a post-dated cheque as security."},
    {"q": "Why do clients ask for 'FOR destination' pricing?", "a": "'FOR destination' (Freight On Road to destination) means we bear freight cost and include it in the price. This is standard in India for bitumen quotes. It reduces client logistics headache and is preferred by large contractors."},
    {"q": "How do we handle a client who says 'your price is high'?", "a": "Use Sales Workspace → Objection Handling section. Key responses: Show transparency of cost components; offer source optimisation (closer source = lower price); highlight quality and reliability advantage over cheaper unknown traders."},
    # PRODUCTS
    {"q": "What grades of bitumen do we supply?", "a": "VG10 (cold regions), VG30 (standard), VG40 (highways, high-stress), PMB (airports, expressways), CRMB (crumb rubber — highways), Bitumen Emulsions (thin layers, cold mix)."},
    {"q": "What is the minimum order quantity?", "a": "For bulk: 1 tanker = 15–20 MT minimum. For drum: 1 truck = 5–10 MT. Full vessel import: 3,000–10,000 MT. For small quantities, decanter option is recommended."},
    {"q": "What is the shelf life of bitumen?", "a": "Bitumen has no fixed expiry, but prolonged storage at high temperatures causes oxidation and hardening. Stored material must be maintained at 130–160°C and used within 6 months for best quality."},
    # DASHBOARD
    {"q": "Which tab should I use first as a new employee?", "a": "Start with Knowledge Base (product training) → AI Assistant (Q&A) → Sales Calendar (seasonal context) → Pricing Calculator (core skill). Full roadmap in Training section."},
    {"q": "How often should I update prices in Data Manager?", "a": "On every 1st and 16th of the month, within 1 hour of receiving the refinery price revision circular. No exceptions."},
    {"q": "What does the Health Score in Risk Scoring mean?", "a": "It is a composite 0–100 score of all business risks. >70 = healthy. 40–70 = watch zone. <40 = critical intervention needed. Review it every Monday morning."},
    {"q": "What is the difference between Pricing Calculator and Feasibility?", "a": "Pricing Calculator quotes a specific source-destination-margin combination. Feasibility COMPARES all sources and finds the cheapest one. Use Feasibility first to pick the best source, then Pricing Calculator to generate the quote."},
    {"q": "What is SOS blast and when should it be sent?", "a": "SOS (SPECIAL PRICE) is an emergency price-drop notification to clients. Send ONLY when: (a) Refinery has confirmed the price drop in writing, and (b) You have arranged stock at the lower price. Never send based on rumour."},
    {"q": "What is the Alert System threshold for crude?", "a": "Warning: ₹75/bbl. Critical: ₹80/bbl. These are configurable in Settings. When critical threshold is breached, expect ₹500–700/MT bitumen price increase in the next revision cycle."},
    {"q": "How do I use the Strategy Panel?", "a": "Review it every Monday before the week's procurement decisions. Three questions: (1) Import now or wait? (2) Hedge crude? (3) Stock up? Each has a confidence score and plain-English reasoning. Discuss with MD before acting."},
    {"q": "What happens if I ignore the GST Monitor for a month?", "a": "GSTR-1 filing is missed — ₹50/day penalty. GSTR-3B missed — 18% interest on unpaid tax. Supplier GSTIN not checked — ITC claimed from cancelled supplier — reversal demand of crores. Never ignore it."},
]

# ─────────────────────────────────────────────────────────────────────────────
# TRAINING ROADMAP FOR NEW EMPLOYEES
# ─────────────────────────────────────────────────────────────────────────────

TRAINING_ROADMAP = [
    {
        "week": "Week 1: Foundation",
        "objective": "Understand the business, product, and market",
        "tasks": [
            "Read Business Overview article in Knowledge Base",
            "Complete Knowledge Base: Company, Product, Grades, Market sections (Q&A)",
            "Use AI Assistant — ask 10 questions about bitumen grades and pricing",
            "Study Sales Calendar — understand peak vs monsoon season",
            "Shadow a senior on Pricing Calculator for 5 live quotes",
        ],
        "assessment": "Can explain: What is bitumen? What is VG30? Why does price change on 1st/16th?",
    },
    {
        "week": "Week 2: Pricing & Feasibility",
        "objective": "Master cost calculation and source selection",
        "tasks": [
            "Generate 10 independent quotes on Pricing Calculator",
            "Run Feasibility for 5 different cities — identify cheapest source each time",
            "Study Import Cost Model — understand all line items",
            "Review Source Directory — know at least 10 refineries and 5 import terminals",
            "Check Data Manager — understand 1st & 16th update process",
        ],
        "assessment": "Can calculate landed cost independently for any city. Can identify best source.",
    },
    {
        "week": "Week 3: Sales & Client Management",
        "objective": "Handle client interactions and deal closure",
        "tasks": [
            "Work through Sales Workspace for 3 mock clients",
            "Practice objection handling scripts",
            "Generate a PDF quote from Reports tab",
            "Set up 3 tasks in CRM & Tasks",
            "Create a WhatsApp price blast message using SOS tab (for practice)",
        ],
        "assessment": "Can handle a full client call independently: quote, objection handling, follow-up.",
    },
    {
        "week": "Week 4: Intelligence & Compliance",
        "objective": "Understand market intelligence and compliance obligations",
        "tasks": [
            "Review Price Prediction — understand inputs and 24-month calendar",
            "Study GST & Legal Monitor — know GSTR-1, GSTR-3B deadlines and HSN code",
            "Read Risk Scoring — understand all 6 risk dimensions",
            "Review Alert System — understand critical vs warning thresholds",
            "Study Financial Intelligence — understand receivable aging and margin analysis",
        ],
        "assessment": "Can explain: What is ITC reversal? What triggers a crude alert? What is Health Score?",
    },
    {
        "week": "Week 5: Strategy & Integration",
        "objective": "See the whole picture and contribute strategically",
        "tasks": [
            "Review Strategy Panel with manager — discuss current recommendations",
            "Attend a Demand Analytics review — identify 2 target regions for next quarter",
            "Do a Supply Chain status check — track all active shipments",
            "Review Ecosystem Management — add a new client profile",
            "Present a 5-minute summary of market conditions using dashboard data",
        ],
        "assessment": "Can brief MD on current market conditions, risks, and opportunities using dashboard.",
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# RENDER FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def render():
    """Render the complete Business Intelligence Knowledge Base in Streamlit."""
    import streamlit as st

    st.markdown("""
    <div style="background:linear-gradient(135deg,#1e3a5f,#0f2340);
    padding:24px;border-radius:14px;margin-bottom:24px;">
    <div style="font-size:1.6rem;font-weight:900;color:#f8fafc;">
    🏛️ Business Intelligence Knowledge Base
    </div>
    <div style="color:#94a3b8;margin-top:6px;">
    Complete reference for all 24 dashboard tabs — for employees, partners, investors, and auditors.
    </div>
    </div>
    """, unsafe_allow_html=True)

    main_tabs = st.tabs([
        "🏢 Business Overview",
        "📑 Tab-by-Tab Guide",
        "⚠️ Risk Matrix",
        "❓ Top 50 FAQs",
        "🎓 Training Roadmap",
    ])

    # ── TAB 1: BUSINESS OVERVIEW ─────────────────────────────────────────────
    with main_tabs[0]:
        ov = BUSINESS_OVERVIEW
        st.markdown(f"## {ov['title']}")

        st.info(ov['model'])

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 💰 Revenue Flow")
            for step in ov['revenue_flow']:
                st.markdown(f"- {step}")

            st.markdown("### 🔄 Fortnightly Revision Cycle")
            st.warning(ov['fortnight_cycle'])

            st.markdown("### 📐 Margin Structure")
            st.success(ov['margin_structure'])

        with col2:
            st.markdown("### 🏗️ Cost Structure")
            for item in ov['cost_structure']:
                st.markdown(f"- {item}")

            st.markdown("### 🛢️ Crude & USD Dependency")
            st.error(ov['crude_usd_dependency'])

        st.markdown("### ⚠️ Key Risk Areas")
        risk_cols = st.columns(2)
        for i, risk in enumerate(ov['risk_areas']):
            risk_cols[i % 2].warning(f"🔴 {risk}")

        st.markdown("### 🔗 How Departments Connect")
        st.info(ov['department_connections'])

    # ── TAB 2: TAB-BY-TAB GUIDE ──────────────────────────────────────────────
    with main_tabs[1]:
        search = st.text_input("🔍 Search tabs by keyword", placeholder="e.g. GST, pricing, import...")

        tabs_to_show = TAB_KNOWLEDGE
        if search:
            s = search.lower()
            tabs_to_show = [
                t for t in TAB_KNOWLEDGE
                if s in t['tab'].lower()
                or s in t['what'].lower()
                or s in t['why'].lower()
                or any(s in str(v).lower() for v in t['impact'].values())
                or any(s in x.lower() for x in t.get('mistakes', []))
                or any(s in x.lower() for x in t.get('kpis', []))
            ]
            if not tabs_to_show:
                st.warning("No tabs match your search. Try a different keyword.")

        for tab in tabs_to_show:
            with st.expander(f"{tab['tab']}  ·  Users: {', '.join(tab['users'][:2])}"):

                st.markdown(f"#### 1️⃣ What is this tab?")
                st.write(tab['what'])

                st.markdown(f"#### 2️⃣ Why does it exist?")
                st.write(tab['why'])

                st.markdown("#### 3️⃣ Business Impact")
                ic1, ic2, ic3 = st.columns(3)
                ic1.success(f"**Revenue**\n{tab['impact']['revenue']}")
                ic2.warning(f"**Cost**\n{tab['impact']['cost']}")
                ic3.error(f"**Risk**\n{tab['impact']['risk']}")
                ic4, ic5 = st.columns(2)
                ic4.info(f"**Compliance**\n{tab['impact']['compliance']}")
                ic5.info(f"**Decisions**\n{tab['impact']['decision']}")

                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown("#### 4️⃣ Who Uses This?")
                    st.write(f"**Departments:** {', '.join(tab['users'])}")
                    st.write(f"**Roles:** {', '.join(tab['roles'])}")

                    st.markdown("#### 5️⃣ Key Inputs")
                    for inp in tab['inputs']:
                        st.markdown(f"- {inp}")

                    st.markdown("#### 6️⃣ Key Outputs")
                    for out in tab['outputs']:
                        st.markdown(f"- {out}")

                with col_b:
                    st.markdown("#### 7️⃣ Important Factors")
                    for f in tab['factors']:
                        st.markdown(f"- {f}")

                    st.markdown("#### 8️⃣ Common Mistakes")
                    for m in tab['mistakes']:
                        st.markdown(f"⚠️ {m}")

                    st.markdown("#### 9️⃣ KPIs to Monitor")
                    for k in tab['kpis']:
                        st.markdown(f"📊 {k}")

                st.error(f"**🔟 Risk If Ignored:** {tab['risk_if_ignored']}")

                if tab.get('linked_tabs'):
                    st.markdown(f"**🔗 Connected Tabs:** `{'` · `'.join(tab['linked_tabs'])}`")

    # ── TAB 3: RISK MATRIX ───────────────────────────────────────────────────
    with main_tabs[2]:
        import pandas as pd
        st.markdown("### ⚠️ Business Risk Matrix")
        st.caption("Probability × Impact assessment for all key business risks.")

        severity_order = {"Critical": 0, "High": 1, "Medium": 2}
        prob_order = {"High": 0, "Medium": 1, "Low": 2}

        df = pd.DataFrame(RISK_MATRIX)
        df = df.sort_values(
            by=["impact", "probability"],
            key=lambda col: col.map(severity_order if col.name == "impact" else prob_order)
        )

        def colour_impact(val):
            if val == "Critical": return "background-color:#fee2e2;color:#991b1b;font-weight:bold"
            if val == "High": return "background-color:#fef3c7;color:#92400e;font-weight:bold"
            return "background-color:#dcfce7;color:#166534"

        def colour_prob(val):
            if val == "High": return "color:#dc2626;font-weight:bold"
            if val == "Medium": return "color:#d97706;font-weight:bold"
            return "color:#16a34a"

        styled = df.style.applymap(colour_impact, subset=["impact"]).applymap(colour_prob, subset=["probability"])
        st.dataframe(styled, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("### 🔴 Critical Risk: Action Protocols")
        critical = [r for r in RISK_MATRIX if r['impact'] == 'Critical']
        for r in critical:
            with st.expander(f"🔴 {r['risk']}"):
                st.write(f"**Probability:** {r['probability']}")
                st.write(f"**Mitigation:** {r['mitigation']}")
                st.write(f"**Relevant Tabs:** {r['tabs']}")

    # ── TAB 4: TOP 50 FAQs ───────────────────────────────────────────────────
    with main_tabs[3]:
        st.markdown("### ❓ Top 50 Business Questions")
        faq_search = st.text_input("🔍 Search FAQs", placeholder="e.g. margin, GST, freight...")

        categories = {
            "Business Model": FAQ_50[:8],
            "Pricing & Margins": FAQ_50[8:14],
            "Operations & Logistics": FAQ_50[14:21],
            "GST & Compliance": FAQ_50[21:27],
            "Risk & Strategy": FAQ_50[27:34],
            "Clients & Sales": FAQ_50[34:40],
            "Products": FAQ_50[40:43],
            "Dashboard Usage": FAQ_50[43:],
        }

        if faq_search:
            s = faq_search.lower()
            matched = [f for f in FAQ_50 if s in f['q'].lower() or s in f['a'].lower()]
            if matched:
                for item in matched:
                    with st.expander(f"❓ {item['q']}"):
                        st.write(item['a'])
            else:
                st.warning("No FAQs matched. Try another keyword.")
        else:
            for cat_name, items in categories.items():
                st.markdown(f"#### 📌 {cat_name}")
                for item in items:
                    with st.expander(f"❓ {item['q']}"):
                        st.write(item['a'])
                st.markdown("---")

    # ── TAB 5: TRAINING ROADMAP ──────────────────────────────────────────────
    with main_tabs[4]:
        st.markdown("### 🎓 New Employee Training Roadmap")
        st.info("Complete this 5-week programme to become a fully productive team member.")

        for week_data in TRAINING_ROADMAP:
            with st.expander(f"📅 {week_data['week']}  —  {week_data['objective']}"):
                st.markdown(f"**Objective:** {week_data['objective']}")
                st.markdown("**Tasks:**")
                for task in week_data['tasks']:
                    st.markdown(f"- {task}")
                st.success(f"**Week-End Assessment:** {week_data['assessment']}")
