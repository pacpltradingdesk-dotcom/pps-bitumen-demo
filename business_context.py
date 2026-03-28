"""
Business Context Engine — PACPL Bitumen Industry Knowledge Base
================================================================
Central repository of PPS Anantam Capital Pvt Ltd's business knowledge.
Injected into ALL AI prompts to ensure domain-accurate responses.

PPS Anantam Capital Pvt Ltd — Business Intelligence v1.0
"""

from __future__ import annotations


# ==============================================================================
# COMPANY PROFILE
# ==============================================================================

COMPANY = {
    "legal_name": "PPS Anantam Capital Pvt Ltd",
    "trade_name": "PACPL / PPS Anantam",
    "location": "Vadodara, Gujarat, India",
    "established": "2002",
    "experience_years": 24,
    "industry": "Bitumen Trading & Supply",
    "gst_state": "Gujarat (24)",
    "pan_prefix": "AACP",
    "business_type": "Trader / Importer / Supplier",
    "key_markets": [
        "Gujarat", "Rajasthan", "Madhya Pradesh", "Maharashtra",
        "Karnataka", "Tamil Nadu", "Andhra Pradesh", "Telangana",
        "Uttar Pradesh", "Bihar", "West Bengal", "Odisha",
    ],
}

# ==============================================================================
# PRODUCT CATALOG
# ==============================================================================

PRODUCTS = {
    "paving_grades": {
        "VG-10": {
            "full_name": "Viscosity Grade 10",
            "use": "Spraying, surface dressing, paving in cold regions",
            "penetration": "80-100",
            "packaging": "Bulk / Drum (170-180 kg)",
        },
        "VG-30": {
            "full_name": "Viscosity Grade 30",
            "use": "Most common road paving grade, highways, expressways",
            "penetration": "50-70",
            "packaging": "Bulk / Drum",
            "note": "Highest demand grade (~60% of all sales)",
        },
        "VG-40": {
            "full_name": "Viscosity Grade 40",
            "use": "Heavy traffic roads, intersections, airport runways",
            "penetration": "40-60",
            "packaging": "Bulk / Drum",
        },
    },
    "modified_grades": {
        "CRMB-55": {
            "full_name": "Crumb Rubber Modified Bitumen 55",
            "use": "High-stress pavements, bridges, flyovers",
        },
        "CRMB-60": {
            "full_name": "Crumb Rubber Modified Bitumen 60",
            "use": "Expressways, airport runways, heavy-duty roads",
        },
        "PMB": {
            "full_name": "Polymer Modified Bitumen",
            "use": "Premium roads, waterproofing, roofing",
        },
    },
    "emulsions": {
        "SS-1": {"full_name": "Slow Setting Emulsion", "use": "Tack coat, prime coat"},
        "RS-1": {"full_name": "Rapid Setting Emulsion", "use": "Surface dressing, chip seal"},
        "MS": {"full_name": "Medium Setting Emulsion", "use": "Premix, cold mix patching"},
    },
    "industrial": {
        "Oxidized Bitumen": {"grades": ["85/25", "90/15", "115/15"], "use": "Waterproofing, roofing, pipe coating"},
        "Cutback Bitumen": {"grades": ["RC", "MC", "SC"], "use": "Prime coat, dust laying"},
    },
}

# ==============================================================================
# PRICING RULES
# ==============================================================================

PRICING = {
    "international": {
        "basis": "CFR (Cost & Freight) Indian port",
        "customs_duty_pct": 2.5,
        "landing_charges_pct": 1.0,
        "gst_pct": 18.0,
        "formula": "Landed Cost = CIF + (CIF * landing%) + Customs Duty on (CIF + landing) + GST on assessable value",
        "note": "Assessable value = CIF + landing charges. Customs duty on assessable value. GST on (assessable + duty).",
    },
    "domestic": {
        "basis": "Ex-refinery / Ex-depot price",
        "freight_bulk_per_km": 5.5,
        "freight_drum_per_km": 6.0,
        "gst_pct": 18.0,
        "formula": "Delivered Price = Base Price + Freight + GST on (Base + Freight)",
        "note": "GST applied on base_price + freight combined, not separately.",
    },
    "margins": {
        "minimum_margin_per_mt": 500,
        "aggressive_offer_add": 500,
        "balanced_offer_add": 800,
        "premium_offer_add": 1200,
        "note": "3-tier offer: aggressive (+500), balanced (+800), premium (+1200) above landed cost",
    },
    "terms": {
        "quote_validity": "24 hours",
        "default_payment": "100% Advance",
        "credit_for_vip": "50% advance, 50% against delivery (Platinum/Gold VIP only)",
        "currency": "INR (Rs)",
        "unit": "Per Metric Ton (MT)",
    },
}

# ==============================================================================
# SUPPLY CHAIN
# ==============================================================================

SUPPLY_CHAIN = {
    "domestic_sources": {
        "refineries": ["IOCL", "HPCL", "BPCL", "MRPL", "CPCL", "NRL"],
        "pricing": "PSU refineries publish fortnightly price circulars",
        "lead_time": "3-7 days from order placement",
    },
    "import_sources": {
        "countries": ["Iran", "Bahrain", "Singapore", "South Korea", "Thailand"],
        "basis": "CFR Indian port",
        "lead_time": "15-30 days from LC opening to discharge",
        "lot_size": "3,000-5,000 MT per vessel",
    },
    "logistics": {
        "bulk_tanker": {"capacity": "20-24 MT", "rate": "Rs 5.5/km", "note": "Heated tankers for viscous grades"},
        "drum": {"weight": "170-180 kg each", "rate": "Rs 6/km", "note": "Easier to store, longer shelf life"},
        "major_ports": ["Mundra", "Kandla", "JNPT (Nhava Sheva)", "Haldia", "Vizag", "Chennai"],
        "storage": "Heated tanks at port terminals, typical capacity 5,000-10,000 MT",
    },
}

# ==============================================================================
# BUYER PERSONAS & CATEGORIES
# ==============================================================================

BUYER_PERSONAS = {
    "road_contractor": {
        "description": "Government road contractors (NHAI, PWD, state highways)",
        "typical_order": "500-2000 MT per project",
        "decision_factor": "Price, delivery reliability, credit terms",
        "season": "Oct-Mar peak (road construction season)",
    },
    "private_builder": {
        "description": "Residential/commercial construction companies",
        "typical_order": "50-200 MT per project",
        "decision_factor": "Quality certification, timely delivery",
    },
    "waterproofing_company": {
        "description": "Waterproofing and roofing material manufacturers",
        "typical_order": "20-100 MT/month regular",
        "decision_factor": "Consistent quality, competitive pricing",
        "products": "Oxidized bitumen, PMB",
    },
    "dealer": {
        "description": "Regional bitumen product dealers and distributors",
        "typical_order": "100-500 MT/month",
        "decision_factor": "Margin, territory exclusivity, payment terms",
    },
    "decanter": {
        "description": "Decanter units that repack bulk into drums",
        "typical_order": "200-1000 MT/month",
        "decision_factor": "Bulk pricing, consistent supply",
    },
    "commission_agent": {
        "description": "Brokers connecting buyers and sellers",
        "typical_commission": "Rs 50-200/MT",
        "decision_factor": "Relationship, market information",
    },
}

CONTACT_CATEGORIES = [
    "Bitumen Importer", "Bitumen Exporter", "Bitumen Trader",
    "Bitumen Product Dealer", "Decanter Unit",
    "Commission Agent / Broker", "Truck Transporter", "Tanker Transporter",
    "Road Contractor", "Waterproofing Company", "Refinery",
]

# ==============================================================================
# SEASONAL PATTERNS
# ==============================================================================

SEASONAL = {
    "peak_season": {
        "months": "October - March",
        "reason": "Road construction season, govt fiscal year spending",
        "demand_level": "HIGH",
        "strategy": "Focus on large orders, maintain stock",
    },
    "moderate_season": {
        "months": "April - May, September",
        "reason": "Pre/post monsoon, project planning",
        "demand_level": "MODERATE",
        "strategy": "Build relationships, negotiate annual contracts",
    },
    "slow_season": {
        "months": "June - August",
        "reason": "Monsoon halts road construction across India",
        "demand_level": "LOW",
        "strategy": "Focus on industrial/waterproofing, build import inventory",
    },
    "fiscal_year_end": {
        "months": "February - March",
        "reason": "Government budget utilization rush",
        "demand_level": "VERY HIGH",
        "strategy": "Maximize sales, premium pricing acceptable",
    },
}

# ==============================================================================
# NEGOTIATION RULES
# ==============================================================================

NEGOTIATION = {
    "rules": [
        "NEVER go below minimum margin of Rs 500/MT",
        "Quote validity is 24 hours — bitumen prices change daily",
        "Default payment: 100% advance before dispatch",
        "Credit terms ONLY for Platinum/Gold VIP customers with proven track record",
        "Always quote GST-inclusive delivered price for transparency",
        "For imports: quote CFR + all duties + GST (fully landed price)",
        "Freight is NON-NEGOTIABLE below Rs 5.5/km bulk, Rs 6/km drum",
        "Larger orders (500+ MT) can get aggressive offer (+500 margin)",
        "Regular customers (monthly orders) qualify for balanced offer (+800)",
        "Premium offer (+1200) for small/one-time/urgent orders",
    ],
    "competitor_response": [
        "If competitor quotes lower, verify: are they including GST? Freight? Actual grade?",
        "Never match competitor price below our minimum margin",
        "Offer value-adds: faster delivery, quality guarantee, technical support",
        "For PSU tenders: match L1 only if margin is above Rs 500/MT",
    ],
    "escalation": [
        "Orders above 1000 MT: Director approval required",
        "Credit terms: Director approval required",
        "Price below balanced offer: Manager approval required",
        "Import orders: Director handles directly",
    ],
}


# ==============================================================================
# OWNER IDENTITY
# ==============================================================================

OWNER_IDENTITY = {
    "name": "PRINCE P SHAH",
    "short": "PPS",
    "trade_name": "PACPL",
    "legal_name": "PPS Anantams Corporation Private Limited",
    "mobile": "+91 7795242424",
    "email": "princepshah@gmail.com",
    "role": "Commission Agent + Logistics Arranger",
    "specialty": "Imported Bitumen (Drum + Bulk)",
    "experience_years": 24,
    "contact_database_size": 24000,
    "credit_policy": "STRICTLY NO CREDIT - ADVANCE PAYMENT ONLY",
    "stronghold_regions": ["West India", "Southwest India"],
    "expansion_regions": ["North India", "East India", "South India"],
    "expansion_target": "Small cities + Small towns across India",
}

# ==============================================================================
# CUSTOMER SEGMENTS (8 comprehensive segments)
# ==============================================================================

# DEPRECATED: BUYER_PERSONAS above is kept for backward compatibility.
# Use CUSTOMER_SEGMENTS for all new code.

CUSTOMER_SEGMENTS = {
    "importer": {
        "label": "Bitumen Importer",
        "description": "Companies importing bulk bitumen via sea vessels from Middle East",
        "typical_volume": "5,000-50,000 MT per shipment",
        "key_terms": ["FOB", "CFR", "CIF", "LC", "BL", "Ship chartering"],
        "key_ports": ["Mundra", "Kandla", "JNPT", "Haldia", "Vizag"],
        "source_countries": ["UAE", "Kuwait", "Saudi Arabia", "Iran", "Bahrain"],
        "decision_factors": ["FOB price trends", "Ship availability", "Port slot", "Currency hedge", "Regulatory changes"],
        "pain_points": ["Demurrage risk", "Quality variation", "LC complexity", "Customs delays"],
        "communication_style": "formal_english",
        "tone": "Peer-to-peer, expert-to-expert. Never talk basics.",
        "frequency": "weekly",
        "best_call_time": "10:00-12:00",
        "what_they_want": [
            "FOB price intelligence",
            "Vessel/ship sourcing help",
            "Port slot information",
            "Customs/regulatory updates",
            "Market demand data from our 24,000 contacts",
        ],
        "chatbot_script": {
            "greeting": "Thank you for your interest in PACPL import services. We handle FOB/CFR/CIF basis cargoes at all major Indian ports with 24 years of experience.",
            "qualification": "May I know the grade, quantity, origin country, and target discharge port?",
            "pitch": "We offer competitive CFR rates with transparent landed cost breakdown including customs (2.5%), landing charges (1%), and GST (18%). Our 24,000-contact network gives us real-time demand intelligence.",
            "fob_price_query": "FOB price from Hamriyah/Jebel Ali currently around ${price}/MT for VG-30. Singapore MOPS + premium basis. Shall I connect you with our Middle East supplier contacts for exact quote?",
            "vessel_query": "Let me check current vessel availability. We have contacts with regular bulk carriers on UAE-India route. What is your preferred discharge port - Kandla or Mumbai?",
            "objection_credit": "Import transactions are strictly 100% advance against BL. We can facilitate LC arrangement through our banking partners.",
            "close": "I can prepare a detailed CFR cost sheet within 1 hour. Shall I proceed?",
        },
    },
    "exporter": {
        "label": "Bitumen Exporter",
        "description": "Indian companies re-exporting bitumen to neighboring countries",
        "typical_volume": "500-5,000 MT per shipment",
        "key_terms": ["FOB", "Export documentation", "Certificate of Origin", "Shipping Bill"],
        "destination_countries": ["Nepal", "Bangladesh", "Sri Lanka", "Myanmar", "East Africa"],
        "decision_factors": ["Export price opportunity", "Documentation support", "Supply reliability", "Loading port"],
        "pain_points": ["Export compliance complexity", "Border delays", "Payment collection risk"],
        "communication_style": "formal_english",
        "tone": "Business partnership approach",
        "frequency": "bi-weekly",
        "what_they_want": [
            "Consistent supply guarantee",
            "Competitive pricing for export parity",
            "Proper documentation support",
            "Flexible packaging (drum/bulk as needed)",
        ],
        "chatbot_script": {
            "greeting": "PACPL supports bitumen exports with complete documentation and competitive FOB pricing from Indian ports.",
            "qualification": "Which country are you exporting to? What grade and quantity? Preferred loading port?",
            "pitch": "We handle all export documentation including Certificate of Origin, shipping bill, and can arrange loading at Kandla/Mundra. For Nepal: Kolkata/Raxaul route preferred.",
            "objection_credit": "Export orders require advance payment or confirmed irrevocable LC.",
            "close": "Let me prepare an FOB cost sheet with all documentation charges included.",
        },
    },
    "trader": {
        "label": "Bitumen Trader",
        "description": "Buy and sell bitumen for profit margin. No own storage. Active in local markets.",
        "typical_volume": "50-500 MT per transaction",
        "key_terms": ["Daily rate", "Spot price", "Conference rate", "Quick turnaround"],
        "decision_factors": ["Price (ALWAYS lead with price)", "Immediate availability", "Quick loading", "Competitive rate vs others"],
        "pain_points": ["Rate volatility", "Quick decision windows", "Market timing", "Trust on quality/quantity"],
        "communication_style": "casual_hindi_english",
        "tone": "Quick, clear, no-nonsense. Lead with PRICE first.",
        "frequency": "daily",
        "best_call_time": "09:00-11:00",
        "what_they_want": [
            "Daily price updates (morning)",
            "Immediate availability confirmation",
            "Quick loading from Kandla/Mumbai",
            "Competitive rate vs other suppliers",
            "Trust - no cheating on quality/quantity",
        ],
        "chatbot_script": {
            "greeting": "Namaste ji! PPS yahan se. Aaj ka rate chahiye?",
            "qualification": "Konsa grade? VG30? Kitna quantity? Kahan delivery?",
            "pitch": "Aaj VG-30 ka rate:\nEx-Kandla: Rs {ex_price}/MT\nDelivered {city}: Rs {del_price}/MT\nStock available: {stock} MT\nPayment: Advance only\nDelivery: {days} days\nOrder karna hai? Reply 1",
            "objection_price": "Bhaiji, hamara rate already market mein best hai. 50 MT se upar order pe special rate discuss kar sakte hain. PPS sir se directly baat karein?",
            "objection_credit": "Trader transaction mein advance payment hi hota hai. Quick deal, quick dispatch. Credit ke chakkar mein rate mein margin add karna padta jo aapko mahanga padta.",
            "close": "Rate lock kar doon? WhatsApp pe formal quote bhej deta hoon.",
        },
    },
    "decanter": {
        "label": "Decanter Unit",
        "description": "Units within 200-240 KM of Kandla port converting drum bitumen to bulk. Critical supply chain link.",
        "typical_volume": "200-1,000 MT per month (regular)",
        "key_terms": ["Bulk to drum", "Decanting charges", "Heated storage", "Drum filling", "Repack"],
        "key_locations": ["Gandhidham", "Bhachau", "Morbi", "Rajkot", "Ahmedabad"],
        "decision_factors": ["Bulk discount", "Consistent supply", "Delivery reliability", "Advance ship arrival info"],
        "pain_points": ["Supply consistency", "Quality variation between lots", "Storage cost", "Truck arrangement at Kandla"],
        "communication_style": "casual_gujarati_hindi",
        "tone": "Regular business partner. Daily contact. They give YOU intelligence.",
        "frequency": "daily",
        "value_as_intelligence": [
            "How much stock at their facility today?",
            "How many trucks loaded/unloaded today?",
            "Who else is buying from this decanter?",
            "Any supply shortage coming?",
            "Price expectation for next week?",
        ],
        "what_they_want": [
            "Regular drum supply at best price",
            "Advance information on ship arrivals",
            "Truck arrangement at Kandla",
            "Market demand updates from Pan India",
        ],
        "chatbot_script": {
            "greeting": "Namaskar! PACPL se Kandla port se regular bulk supply available hai.",
            "qualification": "Monthly consumption kitna hai? VG30 ya VG10? Heated tanker chahiye?",
            "pitch": "200km radius mein competitive bulk rate with regular supply guarantee. Ship arrival ki advance info milegi.",
            "stock_query": "Aaj Kandla pe approximately {stock} drums available hain. Aapko kitna chahiye? Loading schedule confirm karein toh slot book kar dete hain.",
            "objection_credit": "Monthly contract mein 50% advance, 50% against delivery consider kar sakte hain after 3 successful orders.",
            "close": "Monthly supply agreement banayen? Trial lot se start karte hain.",
        },
    },
    "product_manufacturer": {
        "label": "Bitumen Product Manufacturer",
        "description": "Companies manufacturing PMB, CRMB, Emulsion, Cutback, Modified Bitumen from base bitumen",
        "typical_volume": "10-200 MT per week (daily consumption basis)",
        "key_terms": ["Base bitumen", "Penetration value", "Ductility", "Softening point", "IS 73:2013"],
        "products_they_make": ["PMB", "CRMB-55", "CRMB-60", "Emulsion (SS-1, RS-1, MS)", "Oxidized Bitumen", "Cutback"],
        "decision_factors": ["Consistent quality", "Reliable daily supply", "Technical spec compliance", "Test certificates"],
        "pain_points": ["Quality consistency across lots", "Supply interruption stops production", "Grade specification match"],
        "communication_style": "technical_english",
        "tone": "Technical expert, quality focused. Never compromise on quality claims.",
        "frequency": "daily",
        "what_they_want": [
            "Consistent quality every shipment",
            "Test certificates and COA (Certificate of Analysis)",
            "Regular daily/weekly supply schedule",
            "Technical support on grade selection",
            "Advance notice if grade not available",
        ],
        "chatbot_script": {
            "greeting": "PACPL supplies base bitumen to leading PMB/CRMB manufacturers across India with consistent quality guarantee.",
            "qualification": "What is your daily consumption? Which base grade do you use? VG-30 or VG-10?",
            "pitch": "Hamara VG-30 - IS 73:2013 specification:\nPenetration at 25C: 50-70 (0.1mm)\nSoftening Point: Min 47C\nDuctility: Min 75 cm\nFlash Point: Min 220C\nTest certificate available with every lot.",
            "objection_credit": "For regular manufacturers with 3+ month track record, we offer weekly billing after initial advance period.",
            "close": "Shall I arrange a trial lot with full lab analysis for your QC team?",
        },
    },
    "road_contractor": {
        "label": "Road Contractor",
        "description": "NHAI, state PWD, PMGSY, municipal contractors. Biggest volume buyers.",
        "typical_volume": "500-50,000 MT per project",
        "key_terms": ["NHAI", "PWD", "PMGSY", "BOT", "HAM", "EPC", "Tender", "RA bill", "Work Order", "MoRTH spec"],
        "project_types": ["National Highway", "State Highway", "District Road", "Urban Road", "Airport Runway"],
        "decision_factors": ["Price vs tender rate", "Delivery to project site", "Quality certificates", "GST compliant invoicing"],
        "pain_points": ["RA bill payment delays", "Seasonal construction window (Oct-Mar)", "Quality compliance for NHAI"],
        "communication_style": "formal_hindi_english",
        "tone": "Reliable partner, not just supplier. Lead with site delivery capability.",
        "frequency": "monthly + on price change",
        "seasonal": "Heavy buying Oct-Mar, almost nil Jul-Sep (monsoon)",
        "what_they_want": [
            "Site delivery - not ex-works",
            "Competitive landed cost at project site",
            "GST compliant invoicing",
            "Test certificates (mandatory for NHAI)",
            "Reliable delivery timeline - project delays = penalties",
        ],
        "chatbot_script": {
            "greeting": "PACPL provides bitumen supply to NHAI/PWD/State Highway projects across India with site delivery.",
            "qualification": "Which project? HAM/BOT/EPC? Estimated bitumen requirement? Project site location?",
            "pitch": "Bilkul! {state} delivery ke liye:\nNearest supply point: {source}\nGrade available: VG-30, VG-40\nApprox landed cost {city}: Rs {price}/MT\nSite address bataiye - exact rate + delivery time confirm karte hain.\nGST invoice + test certificate provided.",
            "objection_credit": "For government projects: 100% advance. We understand RA bill cycles but cannot extend credit. We can discuss milestone-based advance schedule for long-term projects.",
            "objection_price": "Hamara rate tender rate se kam hai. Plus quality guarantee + on-time delivery + complete documentation. L&T, Dilip Buildcon jaise clients trust karte hain.",
            "close": "Share your work order number and project location. I will prepare a project-specific quotation within 2 hours.",
        },
    },
    "truck_transporter": {
        "label": "Truck Transporter",
        "description": "Most valuable INTELLIGENCE SOURCE. Present at loading points. Know everything happening in market.",
        "typical_interaction": "Intelligence sharing + freight negotiation",
        "key_terms": ["Freight rate", "Loading point", "Transit time", "Toll", "Return load"],
        "key_routes": ["Kandla-Gujarat cities", "Kandla-Rajasthan", "Mumbai-Maharashtra", "Haldia-Bihar/WB"],
        "decision_factors": ["Regular consistent loading work", "Fair freight rate", "No waiting at loading point", "Quick payment"],
        "intelligence_value": [
            "How many trucks loading at Kandla today?",
            "Any congestion at port gate?",
            "Which destination is getting most loads?",
            "Any road blocks or route issues?",
            "Freight rate expectation next week?",
            "Who else is buying/selling right now?",
        ],
        "communication_style": "casual_hindi",
        "tone": "Respectful, treat as business partner. Ask for information - they love sharing.",
        "frequency": "daily",
        "what_they_want": [
            "Regular consistent loading work",
            "No waiting time at loading point",
            "Fair freight rate",
            "Advance payment or quick payment",
            "Return load arrangement if possible",
        ],
        "chatbot_script": {
            "greeting": "PPS ji yahan se. Transport ke liye ya market info ke liye?",
            "qualification": "Kahan se kahan load hai? Kitne truck available hain aaj?",
            "freight_query": "Kandla-{city} current freight:\nBitumen tanker (25 MT): Rs {tanker_rate}/MT\nDrum truck (15 MT): Rs {truck_rate}/trip\nTransit time: {days} days\nAapke paas truck available hai abhi?",
            "info_exchange": "Aaj Kandla pe loading kaisi hai? Kitne trucks queue mein hain? Koi naya buyer aaya hai?",
            "pitch": "Regular loading guarantee with same-day payment for freight.",
            "close": "Next load ke liye ready rehna. Ek order confirm hone wala hai.",
        },
    },
    "tanker_transporter": {
        "label": "Tanker Transporter",
        "description": "Specialized heated/insulated tanker operators for bulk liquid bitumen",
        "typical_interaction": "Tanker booking + rate negotiation",
        "key_terms": ["Heated tanker", "Insulated tanker", "Bulker", "20-24 MT capacity", "Temperature maintenance"],
        "requirements": ["Heating coils functional", "Insulation intact", "Calibration certificate", "Driver trained for viscous cargo"],
        "decision_factors": ["Tanker availability", "Rate per km", "Temperature maintenance capability", "Advance booking"],
        "intelligence_value": [
            "Tanker availability in market",
            "Competitor dispatch information",
            "Rate trends for tanker freight",
        ],
        "communication_style": "casual_hindi",
        "tone": "Long-term partnership. Give advance booking, regular work.",
        "frequency": "weekly + as needed",
        "what_they_want": [
            "Advance booking (not last minute)",
            "Loading/unloading point details in advance",
            "Temperature requirement specification",
            "Quick turnaround at loading/unloading",
            "Fair rate + quick payment",
        ],
        "chatbot_script": {
            "greeting": "PPS ji se. Tanker booking ke liye call kar rahe hain.",
            "qualification": "Kitne MT load hai? Kahan se kahan? Heated chahiye ya normal insulated?",
            "pitch": "Regular loading guarantee, same-day freight settlement. Advance booking milegi.",
            "close": "Tanker bhejo, loading ready hai. ETA batao.",
        },
    },
}

# ==============================================================================
# PRICE FACTORS (10 monitored factors)
# ==============================================================================

PRICE_FACTORS = {
    "crude_oil": {
        "name": "Crude Oil (Brent/Dubai)",
        "impact": "PRIMARY - ₹ 1/bbl change = approx Rs 300-400/MT bitumen impact",
        "monitor": "Daily via EIA/yfinance. Dubai Crude most relevant for India.",
        "threshold_pct": 3.0,
        "alert_threshold": "More than 2% movement in 24 hours",
        "direction": "direct",
    },
    "usd_inr": {
        "name": "USD/INR Exchange Rate",
        "impact": "Rs 1 INR change = approx Rs 380-400/MT import landed cost impact",
        "monitor": "Daily via RBI/ExchangeRate-API",
        "threshold_pct": 1.0,
        "alert_threshold": "More than 0.5% movement",
        "direction": "direct",
    },
    "ship_arrivals": {
        "name": "Ship/Vessel Arrivals at Kandla",
        "impact": "More ships = more supply = price drops. Track VesselFinder/MarineTraffic.",
        "monitor": "Maritime intelligence engine",
        "threshold_pct": None,
        "alert_threshold": "New vessel ETA within 7 days",
        "direction": "inverse",
    },
    "port_congestion": {
        "name": "Port Congestion at Kandla",
        "impact": "Congestion = delay = supply shortage = price UP",
        "monitor": "Kandla Port Trust / maritime_intel_engine",
        "threshold_pct": None,
        "alert_threshold": "Berth waiting more than 3 days",
        "direction": "direct",
    },
    "truck_availability": {
        "name": "Truck/Tanker Availability at Loading Points",
        "impact": "More trucks = faster offtake = stable price. Less trucks = slow offtake = delay.",
        "monitor": "Transporter intelligence network (daily calls). ONLY WE HAVE THIS.",
        "threshold_pct": None,
        "alert_threshold": "Shortage reported by 2+ transporters",
        "direction": "inverse",
    },
    "conference_pricing": {
        "name": "Conference/Cartel Pricing",
        "impact": "Major importers agree minimum price. All prices rise together - no competition.",
        "monitor": "Market intelligence + trader contacts",
        "threshold_pct": 2.0,
        "alert_threshold": "News of conference = advise buyers to stock up NOW",
        "direction": "direct",
    },
    "seasonal_demand": {
        "name": "Seasonal Demand Pattern",
        "impact": "Oct-Mar peak road construction = tight supply. Jun-Aug monsoon = no road work. Feb-Mar fiscal rush.",
        "monitor": "Calendar + infra demand engine + sales_calendar.py",
        "threshold_pct": None,
        "alert_threshold": "Season transition month",
        "direction": "direct",
    },
    "middle_east_supply": {
        "name": "Middle East Supply Situation",
        "impact": "Iran/Bahrain/Singapore production cuts affect import supply",
        "monitor": "Reuters, Bloomberg energy news, OPEC announcements",
        "threshold_pct": None,
        "alert_threshold": "Production cut announcement or refinery shutdown",
        "direction": "inverse",
    },
    "govt_policy": {
        "name": "Government Policy Changes",
        "impact": "NHAI budget allocation, customs duty changes, GST revision",
        "monitor": "PIB (Press Information Bureau), NHAI website, news_engine",
        "threshold_pct": None,
        "alert_threshold": "Policy change announcement affecting bitumen",
        "direction": "variable",
    },
    "psu_prices": {
        "name": "PSU Refinery Published Prices (IOCL/HPCL/BPCL)",
        "impact": "Direct benchmark. PSU raises price = our imports competitive. PSU drops = we must match.",
        "monitor": "IOCL/HPCL/BPCL price circulars (1st and 16th of month)",
        "threshold_pct": 1.5,
        "alert_threshold": "PSU circular published with rate change",
        "direction": "direct",
    },
}

# ==============================================================================
# GEOGRAPHIC INTELLIGENCE (5 regions)
# ==============================================================================

GEOGRAPHIC_INTELLIGENCE = {
    "west_india": {
        "label": "West India (OUR STRONGHOLD)",
        "states": ["Gujarat", "Rajasthan", "Goa"],
        "strength": "stronghold",
        "key_ports": ["Kandla", "Mundra"],
        "supply_chain": "Drum bitumen -> Decanter -> Bulk. Well-established truck network.",
        "psu_policy": {"Gujarat": "Open", "Rajasthan": "Mixed", "Goa": "Open"},
        "key_cities": ["Ahmedabad", "Vadodara", "Rajkot", "Surat", "Jaipur", "Jodhpur", "Udaipur"],
        "small_towns_target": ["Saurashtra", "Kutch", "Interior Rajasthan", "Marwar"],
        "notes": "Home territory. Maximum decanter presence around Kandla. Rajasthan is large volume market.",
    },
    "southwest_india": {
        "label": "Southwest India (OUR STRONGHOLD)",
        "states": ["Maharashtra", "Karnataka"],
        "strength": "stronghold",
        "key_ports": ["JNPT (Nhava Sheva)", "Mangalore"],
        "supply_chain": "Mumbai port imports + some coastal shipping",
        "psu_policy": {"Maharashtra": "Mixed", "Karnataka": "Open"},
        "key_cities": ["Mumbai", "Pune", "Nagpur", "Bangalore", "Hubli"],
        "small_towns_target": ["Vidarbha", "Marathwada", "North Karnataka"],
        "notes": "Large highway network. Maharashtra has highest road km in India. Grow small cities.",
    },
    "north_india": {
        "label": "North India (EXPANSION TARGET)",
        "states": ["Uttar Pradesh", "Madhya Pradesh", "Delhi NCR", "Haryana", "Punjab", "Himachal Pradesh", "J&K"],
        "strength": "expansion",
        "key_ports": [],
        "supply_chain": "Long haul trucks Kandla -> North India. High transport cost = higher landed cost.",
        "psu_policy": {"UP": "PSU-dominant", "MP": "Mixed", "Haryana": "Open", "Punjab": "Mixed"},
        "key_cities": ["Lucknow", "Bhopal", "Indore", "Delhi", "Chandigarh", "Jaipur"],
        "notes": "UP is largest state by road km. Decanters near Kandla serve up to 500 KM efficiently. Target small towns - big players cover big cities.",
    },
    "east_india": {
        "label": "East India (EXPANSION TARGET)",
        "states": ["West Bengal", "Bihar", "Odisha", "Jharkhand", "Assam"],
        "strength": "expansion",
        "key_ports": ["Haldia", "Paradip"],
        "supply_chain": "Need East India supply partner. Haldia/Paradip for port imports.",
        "psu_policy": {"West Bengal": "PSU-dominant", "Bihar": "Mixed", "Odisha": "Open"},
        "key_cities": ["Kolkata", "Patna", "Bhubaneswar", "Ranchi", "Guwahati"],
        "notes": "Bihar road density is lowest = growth opportunity. Need partner with East India import capability.",
    },
    "south_india": {
        "label": "South India (EXPANSION TARGET)",
        "states": ["Tamil Nadu", "Andhra Pradesh", "Telangana", "Kerala"],
        "strength": "expansion",
        "key_ports": ["Chennai", "Vizag", "Ennore"],
        "supply_chain": "CPCL refinery in Chennai. Strong local private importers.",
        "psu_policy": {"Tamil Nadu": "Mixed", "AP": "Open", "Telangana": "Open", "Kerala": "PSU-dominant"},
        "key_cities": ["Chennai", "Hyderabad", "Visakhapatnam", "Vijayawada", "Kochi"],
        "notes": "AP has aggressive highway expansion. Target small contractors - big ones already served by locals.",
    },
}

# State policy quick lookup for AI
STATE_PSU_POLICY = {
    "Gujarat": "Open", "Rajasthan": "Mixed", "Maharashtra": "Mixed",
    "Karnataka": "Open", "Goa": "Open",
    "Uttar Pradesh": "PSU-dominant", "Madhya Pradesh": "Mixed",
    "Haryana": "Open", "Punjab": "Mixed",
    "West Bengal": "PSU-dominant", "Bihar": "Mixed", "Odisha": "Open",
    "Tamil Nadu": "Mixed", "Andhra Pradesh": "Open",
    "Telangana": "Open", "Kerala": "PSU-dominant",
}

# ==============================================================================
# PAYMENT POLICY (STRICT NO CREDIT)
# ==============================================================================

PAYMENT_POLICY = {
    "default": "100% Advance before dispatch",
    "strict": True,
    "rationale": "Bitumen is a volatile commodity. Price changes daily. Credit exposure is unacceptable for commission agents.",
    "ai_must_never": [
        "Offer credit",
        "Say 'we can discuss payment terms'",
        "Give impression of flexibility on payment",
        "Apologize for no-credit policy",
    ],
    "ai_must_always": [
        "State clearly: Payment advance only",
        "Explain why without being rude",
        "Offer solutions within advance payment framework",
    ],
    "scripts": {
        "standard": "Hum advance payment basis pe hi kaam karte hain. Yeh hamari strict policy hai - is wajah se hum aapko sabse competitive price de paate hain.",
        "credit_request_30d": "Hum advance payment basis pe hi kaam karte hain. Credit ke chakkar mein price mein margin add karna padta jo aapko mahanga padta. Advance payment pe aapko best market rate milega.",
        "competitor_gives_credit": "Unka price dekhen - credit ka cost unke rate mein add hota hai. Hamara advance rate unke credit rate se bhi kam hoga. Comparison karein - aap khud samjhenge.",
        "big_company_trust": "Aapki company ke baare mein hum jaante hain aur respect karte hain. Lekin advance payment hamari business model hai - sab ke liye same. Bade order pe price mein hum flexible hain.",
        "government_project": "Government project ke liye: 100% advance. We understand RA bill cycles but cannot extend credit. Milestone-based advance schedule discuss kar sakte hain.",
        "vip_exception": "Credit facility (50% advance, 50% against delivery) available ONLY for Platinum/Gold VIP customers with minimum 12 months successful advance history. Director approval required.",
    },
    "bank_details_for_templates": {
        "bank_name": "ICICI BANK",
        "account_no": "184105001402",
        "ifsc": "ICIC0001841",
        "branch": "Vadodara",
        "account_name": "PPS Anantams Corporation Private Limited",
    },
}

# ==============================================================================
# MESSAGE CLASSIFICATION (10 types for AI)
# ==============================================================================

MESSAGE_CLASSIFICATION = {
    "price_inquiry": {
        "label": "Price Inquiry",
        "patterns": ["price", "rate", "cost", "bhav", "kitna", "kya rate", "daam"],
        "priority": "high",
        "auto_reply": True,
        "action": "Give current price for their location. Calculate landed cost. Ask: Grade? Quantity? Delivery point?",
        "scope": "pricing",
    },
    "availability_check": {
        "label": "Availability / Stock Check",
        "patterns": ["available", "stock", "ready", "dispatch", "kab milega", "in stock"],
        "priority": "high",
        "auto_reply": True,
        "action": "Check live stock database. Confirm grade, quantity, loading point. Give delivery date.",
        "scope": "logistics",
    },
    "order_placement": {
        "label": "Order Placement",
        "patterns": ["order", "confirm", "book", "lock", "proceed", "buy", "purchase"],
        "priority": "critical",
        "auto_reply": False,
        "action": "Confirm price + quantity + grade. Give bank details for advance payment. Confirm on receipt.",
        "scope": "buyer_inquiry",
    },
    "complaint": {
        "label": "Complaint / Issue",
        "patterns": ["complaint", "problem", "issue", "quality", "damage", "wrong", "not satisfied"],
        "priority": "critical",
        "auto_reply": False,
        "action": "IMMEDIATELY flag to PPS (human escalation). Do NOT resolve quality complaints by AI.",
        "escalation_script": "PPS sir ko abhi inform kar diya hai. Wo personally aapse 30 minutes mein baat karenge.",
        "scope": "general",
    },
    "market_info": {
        "label": "Market Information Request",
        "patterns": ["market", "trend", "crude", "forecast", "outlook", "brent", "opec"],
        "priority": "medium",
        "auto_reply": True,
        "action": "Share today's market intelligence. Price trend, supply situation. Make them feel exclusive.",
        "scope": "general",
    },
    "transport_inquiry": {
        "label": "Transport / Logistics Query",
        "patterns": ["transport", "truck", "tanker", "freight", "vehicle", "loading", "shipping"],
        "priority": "medium",
        "auto_reply": True,
        "action": "Give freight rate for their route. Suggest transporter. Confirm transit time.",
        "scope": "logistics",
    },
    "technical_query": {
        "label": "Technical / Specification Query",
        "patterns": ["specification", "spec", "test", "viscosity", "penetration", "BIS", "grade"],
        "priority": "medium",
        "auto_reply": True,
        "action": "Grade specification. Test certificates. Application guidance.",
        "scope": "buyer_inquiry",
    },
    "new_contact": {
        "label": "New Contact (First Time)",
        "patterns": ["introduce", "new", "first time", "referral", "recommended", "who are you"],
        "priority": "high",
        "auto_reply": True,
        "action": "Full welcome + business introduction. Collect: Name, Company, City, Grade needed. Add to CRM. Alert PPS for personal follow-up.",
        "scope": "general",
    },
    "festival_greeting": {
        "label": "Festival / General Greeting",
        "patterns": ["diwali", "holi", "eid", "happy", "festival", "wish", "greeting", "good morning"],
        "priority": "low",
        "auto_reply": True,
        "action": "Warm response. Slip in one business update if appropriate.",
        "scope": "general",
    },
    "regional_hindi": {
        "label": "Hindi / Regional Language",
        "patterns": ["ji", "sahab", "bhai", "seth", "chahiye", "batao", "bolo"],
        "priority": "medium",
        "auto_reply": True,
        "action": "Detect language. Reply in SAME language. Use Bhashini API for regional.",
        "scope": "general",
    },
}

# ==============================================================================
# DAILY AUTOMATION SCHEDULE
# ==============================================================================

DAILY_AUTOMATION_SCHEDULE = {
    "0500": {
        "task": "price_gathering",
        "description": "Fetch Dubai crude overnight change, USD/INR morning rate, MarineTraffic Kandla vessels",
    },
    "0630": {
        "task": "pps_daily_brief",
        "description": "Generate and send PPS Daily Intelligence Brief via WhatsApp",
        "format": "Market data + Stock status + Top 10 to call + Yesterday summary",
    },
    "0700": {
        "task": "festival_check",
        "description": "Check if festival today/tomorrow. If yes, broadcast to all 24,000 contacts.",
    },
    "0900": {
        "task": "daily_broadcast",
        "description": "AI selects 2,400 from priority queue. Morning price update via WhatsApp + Email.",
    },
    "1000_to_1800": {
        "task": "live_response",
        "description": "All incoming messages answered within 60 seconds. AI handles Tier 1 (price/availability/standard). PPS handles Tier 2 (negotiations, complaints).",
    },
    "1800": {
        "task": "price_alerts",
        "description": "If crude moved >2%, send price alert. Alert buyers: Buy now before price rises. Alert sellers: Adjust ask price.",
    },
    "2100": {
        "task": "daily_report",
        "description": "Full activity summary to PPS. Tomorrow contact list preview. Urgent follow-ups flagged.",
    },
}


# ==============================================================================
# CONTEXT BUILDER
# ==============================================================================


def get_business_context(scope: str = "general", segment: str = "") -> str:
    """
    Build business context string for AI prompt injection.

    Scopes:
        general       — Company + products + seasonal + identity
        pricing       — Full pricing + margins + terms + price factors
        logistics     — Supply chain + freight + ports + geographic
        buyer_inquiry — Products + pricing + segments + seasonal
        seller_offer  — Supply chain + pricing + import details
        negotiation   — Negotiation rules + payment policy + competitor handling
        geographic    — Regional intelligence
        payment_policy — NO CREDIT scripts
        price_factors — 10 monitored factors
        daily_schedule — Automation schedule
        full          — Everything (for trading chatbot)

    segment: Optional segment key (e.g., "trader", "road_contractor") for
             segment-specific chatbot script injection.
    """
    parts = []

    # Always include company header + owner identity
    parts.append(
        f"COMPANY: {COMPANY['trade_name']} ({COMPANY['legal_name']}), "
        f"{COMPANY['location']}. {COMPANY['experience_years']} years in "
        f"{COMPANY['industry']}."
    )
    parts.append(_owner_identity_summary())

    if scope == "general":
        parts.append(_products_summary())
        parts.append(_seasonal_summary())
        parts.append(_pricing_brief())

    elif scope == "pricing":
        parts.append(_pricing_full())
        parts.append(_price_factors_summary())
        parts.append(_seasonal_summary())

    elif scope == "logistics":
        parts.append(_logistics_full())
        parts.append(_geographic_summary())
        parts.append(_pricing_brief())

    elif scope == "buyer_inquiry":
        parts.append(_products_summary())
        parts.append(_pricing_full())
        parts.append(_segments_summary())
        parts.append(_seasonal_summary())

    elif scope == "seller_offer":
        parts.append(_logistics_full())
        parts.append(_pricing_full())
        parts.append(_products_summary())

    elif scope == "negotiation":
        parts.append(_negotiation_full())
        parts.append(_payment_policy_summary())
        parts.append(_pricing_full())
        parts.append(_seasonal_summary())

    elif scope == "geographic":
        parts.append(_geographic_summary())
        parts.append(_seasonal_summary())

    elif scope == "payment_policy":
        parts.append(_payment_policy_summary())

    elif scope == "price_factors":
        parts.append(_price_factors_summary())

    elif scope == "daily_schedule":
        parts.append(_daily_schedule_summary())

    elif scope == "full":
        parts.append(_products_summary())
        parts.append(_pricing_full())
        parts.append(_price_factors_summary())
        parts.append(_logistics_full())
        parts.append(_geographic_summary())
        parts.append(_segments_summary())
        parts.append(_payment_policy_summary())
        parts.append(_negotiation_full())
        parts.append(_seasonal_summary())
        parts.append(_daily_schedule_summary())

    else:
        # Unknown scope — return general
        parts.append(_products_summary())
        parts.append(_seasonal_summary())

    # Inject segment-specific chatbot script if provided
    if segment:
        seg_text = _segment_script(segment)
        if seg_text:
            parts.append(seg_text)

    return "\n\n".join(parts)


def _products_summary() -> str:
    lines = ["PRODUCTS:"]
    lines.append("Paving Grades: VG-10 (spraying/cold regions), VG-30 (highways, 60% of sales), VG-40 (heavy traffic/airports)")
    lines.append("Modified: CRMB-55/60 (bridges/flyovers), PMB (premium roads/waterproofing)")
    lines.append("Emulsions: SS-1 (tack coat), RS-1 (surface dressing), MS (cold mix)")
    lines.append("Industrial: Oxidized Bitumen (waterproofing/roofing), Cutback (prime coat)")
    return "\n".join(lines)


def _pricing_brief() -> str:
    return (
        "PRICING: Min margin Rs 500/MT. 3-tier offers: Aggressive(+500), "
        "Balanced(+800), Premium(+1200). GST 18%. Quote valid 24 hours. "
        "Payment: 100% Advance (credit for VIP only)."
    )


def _pricing_full() -> str:
    lines = ["PRICING RULES:"]
    p = PRICING
    lines.append(f"International: {p['international']['formula']}")
    lines.append(f"  Customs Duty: {p['international']['customs_duty_pct']}%, "
                 f"Landing: {p['international']['landing_charges_pct']}%, "
                 f"GST: {p['international']['gst_pct']}%")
    lines.append(f"Domestic: {p['domestic']['formula']}")
    lines.append(f"  Freight: Bulk Rs {p['domestic']['freight_bulk_per_km']}/km, "
                 f"Drum Rs {p['domestic']['freight_drum_per_km']}/km, "
                 f"GST: {p['domestic']['gst_pct']}%")
    lines.append(f"Margins: Min Rs {p['margins']['minimum_margin_per_mt']}/MT. "
                 f"Aggressive(+{p['margins']['aggressive_offer_add']}), "
                 f"Balanced(+{p['margins']['balanced_offer_add']}), "
                 f"Premium(+{p['margins']['premium_offer_add']})")
    lines.append(f"Terms: {p['terms']['quote_validity']} validity, "
                 f"{p['terms']['default_payment']}, unit = {p['terms']['unit']}")
    return "\n".join(lines)


def _seasonal_summary() -> str:
    s = SEASONAL
    return (
        f"SEASONS: Peak({s['peak_season']['months']}) = {s['peak_season']['reason']}. "
        f"Slow({s['slow_season']['months']}) = {s['slow_season']['reason']}. "
        f"Fiscal rush({s['fiscal_year_end']['months']}) = {s['fiscal_year_end']['reason']}."
    )


def _logistics_full() -> str:
    sc = SUPPLY_CHAIN
    lines = ["SUPPLY CHAIN:"]
    lines.append(f"Domestic Refineries: {', '.join(sc['domestic_sources']['refineries'])}")
    lines.append(f"  Lead time: {sc['domestic_sources']['lead_time']}")
    lines.append(f"Import Sources: {', '.join(sc['import_sources']['countries'])}")
    lines.append(f"  Basis: {sc['import_sources']['basis']}, Lead time: {sc['import_sources']['lead_time']}")
    lines.append(f"  Lot size: {sc['import_sources']['lot_size']}")
    lines.append(f"Logistics: Bulk tanker {sc['logistics']['bulk_tanker']['capacity']} "
                 f"@ Rs {sc['logistics']['bulk_tanker']['rate']}")
    lines.append(f"  Drum: {sc['logistics']['drum']['weight']} @ Rs {sc['logistics']['drum']['rate']}")
    lines.append(f"Major Ports: {', '.join(sc['logistics']['major_ports'])}")
    return "\n".join(lines)


def _buyer_personas_summary() -> str:
    lines = ["BUYER TYPES:"]
    for key, persona in BUYER_PERSONAS.items():
        desc = persona["description"]
        order = persona.get("typical_order", "varies")
        lines.append(f"  {key}: {desc} (typical: {order})")
    return "\n".join(lines)


def _negotiation_full() -> str:
    lines = ["NEGOTIATION RULES:"]
    for rule in NEGOTIATION["rules"]:
        lines.append(f"  - {rule}")
    lines.append("\nCOMPETITOR RESPONSE:")
    for rule in NEGOTIATION["competitor_response"]:
        lines.append(f"  - {rule}")
    lines.append("\nESCALATION:")
    for rule in NEGOTIATION["escalation"]:
        lines.append(f"  - {rule}")
    return "\n".join(lines)


def _owner_identity_summary() -> str:
    o = OWNER_IDENTITY
    return (
        f"OWNER: {o['name']} ({o['short']}), "
        f"Trade: {o['trade_name']}, {o['experience_years']}yr exp, "
        f"Role: {o['role']}, Contacts: {o['contact_database_size']:,}. "
        f"CREDIT POLICY: {o['credit_policy']}"
    )


def _price_factors_summary() -> str:
    lines = ["PRICE FACTORS (10 Monitored):"]
    for key, factor in PRICE_FACTORS.items():
        lines.append(f"  {factor['name']}: {factor['impact']}")
        if factor.get("threshold_pct"):
            lines.append(f"    Alert threshold: {factor['threshold_pct']}% change")
    return "\n".join(lines)


def _geographic_summary(region: str = "") -> str:
    lines = ["GEOGRAPHIC INTELLIGENCE:"]
    for key, geo in GEOGRAPHIC_INTELLIGENCE.items():
        if region and key != region:
            continue
        states = ", ".join(geo["states"])
        lines.append(f"  {geo['label']}: {states}")
        if geo.get("key_ports"):
            lines.append(f"    Ports: {', '.join(geo['key_ports'])}")
        lines.append(f"    Notes: {geo['notes']}")
    return "\n".join(lines)


def _payment_policy_summary() -> str:
    pp = PAYMENT_POLICY
    lines = [f"PAYMENT POLICY: {pp['default']} (STRICT: {pp['strict']})"]
    lines.append(f"  Rationale: {pp['rationale']}")
    for key, script in pp["scripts"].items():
        lines.append(f"  Script[{key}]: {script}")
    bank = pp["bank_details_for_templates"]
    lines.append(f"  Bank: {bank['bank_name']}, A/C: {bank['account_no']}, IFSC: {bank['ifsc']}")
    return "\n".join(lines)


def _segments_summary() -> str:
    lines = ["CUSTOMER SEGMENTS (8):"]
    for key, seg in CUSTOMER_SEGMENTS.items():
        vol = seg.get("typical_volume", "varies")
        lines.append(f"  {seg['label']}: {seg['description']} (typical: {vol})")
    return "\n".join(lines)


def _segment_script(segment: str) -> str:
    seg = CUSTOMER_SEGMENTS.get(segment)
    if not seg:
        return ""
    lines = [f"SEGMENT CONTEXT: {seg['label']}"]
    lines.append(f"  Description: {seg['description']}")
    lines.append(f"  Volume: {seg.get('typical_volume', 'varies')}")
    lines.append(f"  Style: {seg.get('communication_style', 'formal_english')}")
    lines.append(f"  Tone: {seg.get('tone', '')}")
    script = seg.get("chatbot_script", {})
    if script:
        lines.append("  CHATBOT SCRIPT:")
        for k, v in script.items():
            lines.append(f"    {k}: {v}")
    wants = seg.get("what_they_want", [])
    if wants:
        lines.append("  WHAT THEY WANT:")
        for w in wants:
            lines.append(f"    - {w}")
    return "\n".join(lines)


def _daily_schedule_summary() -> str:
    lines = ["DAILY AUTOMATION SCHEDULE:"]
    for time_key, info in DAILY_AUTOMATION_SCHEDULE.items():
        lines.append(f"  {time_key}: {info['task']} - {info['description']}")
    return "\n".join(lines)


# ==============================================================================
# CONVENIENCE FUNCTIONS
# ==============================================================================


def get_all_products() -> dict:
    """Return full product catalog."""
    return PRODUCTS


def get_pricing_rules() -> dict:
    """Return full pricing rules dict."""
    return PRICING


def get_negotiation_rules() -> dict:
    """Return negotiation rules dict."""
    return NEGOTIATION


def get_supply_chain_info() -> dict:
    """Return supply chain information."""
    return SUPPLY_CHAIN


def get_company_info() -> dict:
    """Return company profile."""
    return COMPANY


def get_segment_info(segment: str) -> dict:
    """Return info dict for a specific customer segment."""
    return CUSTOMER_SEGMENTS.get(segment, {})


def get_segment_chatbot_script(segment: str) -> dict:
    """Return chatbot script for a specific segment."""
    seg = CUSTOMER_SEGMENTS.get(segment, {})
    return seg.get("chatbot_script", {})


def get_all_segments() -> dict:
    """Return all 8 customer segments."""
    return CUSTOMER_SEGMENTS


def get_price_factors() -> dict:
    """Return all 10 price factors."""
    return PRICE_FACTORS


def get_geographic_intelligence(region: str = "") -> dict:
    """Return geographic intelligence, optionally filtered by region."""
    if region:
        return GEOGRAPHIC_INTELLIGENCE.get(region, {})
    return GEOGRAPHIC_INTELLIGENCE


def get_payment_policy() -> dict:
    """Return payment policy with scripts."""
    return PAYMENT_POLICY


def get_message_classification_types() -> dict:
    """Return all 10 message classification types."""
    return MESSAGE_CLASSIFICATION


def get_daily_schedule() -> dict:
    """Return daily automation schedule."""
    return DAILY_AUTOMATION_SCHEDULE


def get_owner_identity() -> dict:
    """Return owner identity info."""
    return OWNER_IDENTITY


def get_state_psu_policy(state: str) -> str:
    """Return PSU policy for a state (Open/Mixed/PSU-dominant)."""
    return STATE_PSU_POLICY.get(state, "Unknown")


def get_segment_for_category(category: str) -> str:
    """Map contact category string to segment key."""
    _CAT_MAP = {
        "Bitumen Importer": "importer",
        "Importer": "importer",
        "Bitumen Exporter": "exporter",
        "Exporter": "exporter",
        "Bitumen Trader": "trader",
        "Trader": "trader",
        "Bitumen Product Dealer": "product_manufacturer",
        "Product Manufacturer": "product_manufacturer",
        "Decanter Unit": "decanter",
        "Decanter": "decanter",
        "Road Contractor": "road_contractor",
        "Contractor": "road_contractor",
        "Commission Agent / Broker": "trader",
        "Commission Agent": "trader",
        "Truck Transporter": "truck_transporter",
        "Tanker Transporter": "tanker_transporter",
        "Refinery": "importer",
        "Waterproofing Company": "product_manufacturer",
    }
    return _CAT_MAP.get(category, "trader")
