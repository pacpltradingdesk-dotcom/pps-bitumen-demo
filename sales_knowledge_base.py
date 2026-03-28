
# PPS Anantams Corporation Pvt. Ltd.
# Bitumen Sales Training Knowledge Base
# Complete Q&A for Sales Team, AI Chatbot, and Telecalling Training

"""
This knowledge base contains all question and answers from the official
Bitumen Sales Training Manual. It is used for:
1. Sales Person Quick Reference
2. AI Chatbot Responses
3. AI Telecalling Training Scripts
"""

# ============ KNOWLEDGE BASE STRUCTURE ============

TRAINING_SECTIONS = {
    "company":    "Company Profile & Credibility",
    "product":    "Product Fundamentals",
    "grades":     "Bitumen Grades & Applications",
    "pricing":    "Pricing & Cost Structure",
    "market":     "Market Dynamics",
    "territory":  "Territory Logic & Product Selection",
    "sales":      "Sales Process & Customer Engagement",
    "payment":    "Payment Terms & Procedures",
    "modified":   "Modified Bitumen & Emulsions",
    "logistics":  "Logistics & Supply Chain",
    "technical":  "Technical & Consumption Metrics",
    "fy26":       "FY 2025-26 Budget & Market",
    "objections": "Sales Objection Handling",
}

# ============ COMPLETE Q&A KNOWLEDGE BASE ============

KNOWLEDGE_BASE = [

    # ═══════════════════════════════════════════════════════════
    # SECTION 1: COMPANY PROFILE & CREDIBILITY  (Pages 1-3, 24-30)
    # ═══════════════════════════════════════════════════════════

    # -- Pages 1-3: Training Introduction & Objectives --
    {
        "section": "company",
        "question": "Who is the company providing this bitumen sales training?",
        "answer": "This training is provided by PPS Anantams Corporation Pvt. Ltd.",
        "keywords": ["company", "pps", "anantams", "who", "training provider"]
    },
    {
        "section": "company",
        "question": "What is the nature of this document?",
        "answer": "It is a comprehensive internal training manual for sales, operations, and procurement teams.",
        "keywords": ["document", "manual", "training", "what is this"]
    },
    {
        "section": "company",
        "question": "What is the primary industry focus of the company?",
        "answer": "The company focuses on bitumen supply and infrastructure development support.",
        "keywords": ["industry", "focus", "bitumen supply", "infrastructure"]
    },
    {
        "section": "company",
        "question": "What are the main objectives of this training program?",
        "answer": "The objectives are to provide product knowledge on bitumen grades, offer a clear market understanding of supply dynamics, achieve sales excellence in customer engagement, and ensure operational clarity regarding payments and logistics.",
        "keywords": ["objective", "goal", "learn", "training program"]
    },
    {
        "section": "company",
        "question": "What will the sales team learn regarding market understanding?",
        "answer": "They will learn to grasp supply dynamics, refinery operations, and the demand-supply scenario in India.",
        "keywords": ["sales team", "market understanding", "supply dynamics", "learn"]
    },
    {
        "section": "company",
        "question": "How is operational clarity defined in this training?",
        "answer": "It involves learning payment terms, logistics, compliance, and company policies to ensure smooth project execution.",
        "keywords": ["operational clarity", "payment", "logistics", "compliance"]
    },

    # -- Pages 24-30: Company Profile, Credibility & Vision --
    {
        "section": "company",
        "question": "What is the focus of the Company Profile section?",
        "answer": "It provides the company profile, credibility, and mission of PPS Anantams Corporation Pvt. Ltd.",
        "keywords": ["company profile", "credibility", "mission", "section 4"]
    },
    {
        "section": "company",
        "question": "What is the company's motto or tagline?",
        "answer": "'Building Roads on Reliability - A trusted partner in India's bitumen supply chain.'",
        "keywords": ["motto", "tagline", "slogan", "reliability"]
    },
    {
        "section": "company",
        "question": "What is the significance of the company profile for a salesperson?",
        "answer": "This section provides the credentials needed to build trust and establish the company as a professional and stable partner.",
        "keywords": ["salesperson", "credentials", "trust", "professional"]
    },
    {
        "section": "company",
        "question": "What makes PPS Anantams a reliable partner in the bitumen industry?",
        "answer": "Our promoters have 6 to 24 years of combined experience in bitumen trading, logistics, and supply chain management. We coordinate supplies through major pan-India terminals.",
        "keywords": ["reliable", "experience", "partner", "why us", "advantage"]
    },
    {
        "section": "company",
        "question": "From which headquarters does PPS Anantams coordinate its operations?",
        "answer": "The company coordinates its nationwide operations from its headquarters in Gujarat.",
        "keywords": ["headquarters", "gujarat", "office", "location"]
    },
    {
        "section": "company",
        "question": "Who are the primary types of customers served by PPS Anantams?",
        "answer": "The company serves infrastructure developers, government contractors, EPC companies, and road construction executors.",
        "keywords": ["customers", "clients", "who do you serve", "contractors"]
    },
    {
        "section": "company",
        "question": "What is the legal status and registered office location of the company?",
        "answer": "PPS Anantams Corporation Pvt. Ltd. is a Private Limited Company with its registered office in Vadodara, Gujarat.",
        "keywords": ["legal status", "registered office", "vadodara", "private limited"]
    },
    {
        "section": "company",
        "question": "Is the company ISO compliant?",
        "answer": "Yes, the company is listed as ISO compliant.",
        "keywords": ["iso", "compliant", "certification", "standard"]
    },
    {
        "section": "company",
        "question": "What email and phone details should be used for sales inquiries?",
        "answer": "The contact number is +91 94482 81224 and the email is sales.ppsanantams@gmail.com.",
        "keywords": ["contact", "phone", "email", "sales inquiry"]
    },
    {
        "section": "company",
        "question": "What are the key figures that highlight your company's market presence?",
        "answer": "We have 24+ years of combined industry experience, operate across 5+ major port terminals, and conduct 100% of our transactions through banking channels.",
        "keywords": ["key figures", "market presence", "24 years", "port terminals"]
    },
    {
        "section": "company",
        "question": "Which specific port terminals does PPS Anantams operate through?",
        "answer": "The company has a strategic presence across Mundra, Mumbai, Karwar, Haldia, and Kolkata.",
        "keywords": ["port terminals", "mundra", "mumbai", "karwar", "haldia", "kolkata"]
    },
    {
        "section": "company",
        "question": "How does having 100% banking-only transactions benefit the company?",
        "answer": "It ensures complete transparency and financial discipline, which enables the company to manage complex supply chains and seasonal demand fluctuations reliably.",
        "keywords": ["banking transactions", "transparency", "financial discipline", "benefit"]
    },
    {
        "section": "company",
        "question": "What is the company's ultimate goal or vision?",
        "answer": "To become India's most reliable and innovative bitumen partner, setting new benchmarks in logistics, service, and customer trust.",
        "keywords": ["vision", "goal", "ultimate", "benchmark"]
    },
    {
        "section": "company",
        "question": "What is the mission regarding product quality and partnerships?",
        "answer": "The mission is to deliver high-quality solutions with consistent specifications and build long-term partnerships through transparency and performance.",
        "keywords": ["mission", "quality", "partnerships", "transparency"]
    },
    {
        "section": "company",
        "question": "How does PPS Anantams intend to support India's infrastructure?",
        "answer": "By providing dependable, scalable supply systems and maintaining the highest standards of compliance and financial discipline.",
        "keywords": ["infrastructure support", "scalable", "compliance", "supply systems"]
    },
    {
        "section": "company",
        "question": "Why should a contractor choose to work with PPS Anantams specifically?",
        "answer": "Customers choose us for our extensive industry experience, reliable all-India logistics network, financial discipline, and performance-driven execution.",
        "keywords": ["why choose", "contractor", "advantage", "why us"]
    },
    {
        "section": "company",
        "question": "What does an end-to-end capability mean for your clients?",
        "answer": "It means we handle everything from sourcing and documentation to storage coordination and final delivery management with full transparency.",
        "keywords": ["end to end", "capability", "sourcing", "delivery"]
    },
    {
        "section": "company",
        "question": "What is the client-centric approach mentioned in the manual?",
        "answer": "It is an approach focused on enabling the success of the customer's project through transparent processes and responsive coordination.",
        "keywords": ["client centric", "approach", "customer focus", "responsive"]
    },
    {
        "section": "company",
        "question": "How does your company's financial structure benefit your customers?",
        "answer": "We are 100% compliant with GST and Income Tax and are funded entirely by our own capital. This debt-free model ensures supply stability and competitive, stable pricing.",
        "keywords": ["financial", "stable", "debt free", "gst compliant", "own capital"]
    },
    {
        "section": "company",
        "question": "Does PPS Anantams rely on bank limits or letters of credit for its operations?",
        "answer": "No, the company has zero dependence on bank limits, overdrafts, or letters of credit, operating entirely on its own capital.",
        "keywords": ["bank limits", "letter of credit", "overdraft", "debt free"]
    },
    {
        "section": "company",
        "question": "Why do large contractors prefer working with financially compliant suppliers?",
        "answer": "It prevents future complications in their own audits and project documentation, providing them with the assurance of a clean statutory record.",
        "keywords": ["large contractors", "compliant supplier", "audit", "statutory"]
    },

    # ═══════════════════════════════════════════════════════════
    # SECTION 2: PRODUCT FUNDAMENTALS  (Pages 3-6)
    # ═══════════════════════════════════════════════════════════

    {
        "section": "product",
        "question": "What is the primary focus of the Industry and Product Fundamentals section?",
        "answer": "It focuses on the foundation of bitumen as a petroleum product and its role in India's infrastructure.",
        "keywords": ["section 1", "industry", "product fundamentals", "foundation"]
    },
    {
        "section": "product",
        "question": "Why is it important to understand bitumen as a petroleum product?",
        "answer": "Understanding its origin as a petroleum product is fundamental to explaining its availability and pricing to customers.",
        "keywords": ["petroleum product", "origin", "availability", "pricing"]
    },
    {
        "section": "product",
        "question": "What role does bitumen play in India's development?",
        "answer": "Bitumen plays a critical role in infrastructure development as the foundational binder for road construction across the country.",
        "keywords": ["india", "development", "infrastructure", "road construction", "role"]
    },
    {
        "section": "product",
        "question": "What is bitumen and how is it used?",
        "answer": "Bitumen is a black, sticky, and highly viscous petroleum product obtained exclusively from refining crude oil. It acts as the primary binding agent in asphalt concrete, providing essential waterproofing, flexibility, and durability.",
        "keywords": ["what is bitumen", "bitumen", "definition", "explain", "asphalt"]
    },
    {
        "section": "product",
        "question": "How is bitumen produced during the refining process?",
        "answer": "It represents the heaviest fraction remaining after all lighter petroleum products have been extracted during refining.",
        "keywords": ["produced", "refining", "heaviest fraction", "process"]
    },
    {
        "section": "product",
        "question": "What specific properties make bitumen irreplaceable in road infrastructure?",
        "answer": "Its unique adhesive and cohesive properties make it essential for creating functional and modern road surfaces.",
        "keywords": ["properties", "adhesive", "cohesive", "irreplaceable"]
    },
    {
        "section": "product",
        "question": "Why should I care about the quality of the bitumen you supply?",
        "answer": "Quality is critical because poor quality leads to premature road failure and negatively affects tender approvals. High-quality bitumen ensures waterproof protection, strong adhesive bonding, and long-lasting durability.",
        "keywords": ["quality", "important", "why", "poor quality", "road failure"]
    },
    {
        "section": "product",
        "question": "How does bitumen behave under different temperatures?",
        "answer": "It exhibits thermoplastic behavior, meaning it softens when heated for workability during construction and hardens when cooled for performance.",
        "keywords": ["temperature", "thermoplastic", "softens", "hardens", "behavior"]
    },
    {
        "section": "product",
        "question": "What are the business consequences of supplying poor quality bitumen?",
        "answer": "It impacts engineer satisfaction, project success, the contractor's market reputation, and ultimately determines repeat business opportunities.",
        "keywords": ["consequences", "poor quality", "reputation", "repeat business"]
    },
    {
        "section": "product",
        "question": "Is it possible for private parties to manufacture bitumen locally?",
        "answer": "No, bitumen cannot be manufactured by individuals or private parties outside refineries. It is exclusively a petroleum refinery product.",
        "keywords": ["manufacture", "private", "make", "produce", "locally"]
    },
    {
        "section": "product",
        "question": "What is the relationship between petrol/diesel and bitumen?",
        "answer": "Bitumen is the final residue left after lighter products like petrol, diesel, kerosene, and LPG have been extracted from crude oil.",
        "keywords": ["petrol", "diesel", "relationship", "residue", "crude oil"]
    },
    {
        "section": "product",
        "question": "Why is refinery dependency a critical point for the sales team?",
        "answer": "Because bitumen is exclusively a refinery product, its availability and pricing are directly linked to refinery operations and global crude oil processing.",
        "keywords": ["refinery dependency", "availability", "pricing linked", "crude oil"]
    },
    {
        "section": "product",
        "question": "How is Bitumen manufactured in an Oil Company?",
        "answer": "It is produced through the fractional distillation of crude oil. In the vacuum distillation column, lighter fractions (petrol, diesel, kerosene) are boiled off. The heaviest residue at the bottom is processed (via air blowing or blending) to create specific viscosity grades like VG30/VG40.",
        "keywords": ["manufacturing", "oil company", "distillation", "process", "made"]
    },

    # ═══════════════════════════════════════════════════════════
    # SECTION 3: BITUMEN GRADES & APPLICATIONS  (Pages 10-13)
    # ═══════════════════════════════════════════════════════════

    {
        "section": "grades",
        "question": "What does the training section on bitumen types cover?",
        "answer": "It covers the different types of bitumen used in road construction, including various grades, their applications, and consumption patterns.",
        "keywords": ["bitumen types", "grades", "applications", "section 2"]
    },
    {
        "section": "grades",
        "question": "Why is it important for sales conversations to understand bitumen grades?",
        "answer": "Understanding grades allows for more effective conversations and helps the salesperson match products to specific project requirements.",
        "keywords": ["sales conversations", "understand grades", "match products"]
    },
    {
        "section": "grades",
        "question": "Who determines which bitumen grade is used for a project?",
        "answer": "Engineers specify grades based on project requirements, climate zones, and expected traffic patterns.",
        "keywords": ["who determines", "engineer", "grade selection", "project"]
    },
    {
        "section": "grades",
        "question": "What does the VG in VG-grade bitumen stand for?",
        "answer": "VG stands for 'Viscosity Grade.' It is a measure of the bitumen's resistance to flow at specified temperatures. The Indian Roads Congress (IRC) and the Bureau of Indian Standards (BIS) standardize these grades for different climatic conditions and traffic loads.",
        "keywords": ["vg", "viscosity", "grade", "meaning", "irc", "bis"]
    },
    {
        "section": "grades",
        "question": "Who standardizes bitumen grades in India?",
        "answer": "The Indian Roads Congress (IRC) and the Bureau of Indian Standards (BIS) standardize these grades for different climatic conditions and traffic loads.",
        "keywords": ["standardize", "irc", "bis", "india", "grades"]
    },
    {
        "section": "grades",
        "question": "What technical factors determine a grade's suitability for a specific application?",
        "answer": "Suitability is determined by specific penetration values, softening points, and viscosity measurements.",
        "keywords": ["technical factors", "penetration", "softening point", "viscosity"]
    },
    {
        "section": "grades",
        "question": "Which grade should I use for a standard city road versus a heavy-duty highway?",
        "answer": "VG30 is the most common grade for general road construction and city roads. For heavy-duty applications and high-stress corridors, VG40 is recommended due to its higher temperature resistance.",
        "keywords": ["vg30", "vg40", "city", "highway", "difference", "which grade"]
    },
    {
        "section": "grades",
        "question": "In which regions is VG10 bitumen typically used?",
        "answer": "VG10 is used in cold and hilly regions, such as the Himalayan states, where a softer bitumen is required.",
        "keywords": ["vg10", "cold", "hilly", "himalayan", "region"]
    },
    {
        "section": "grades",
        "question": "What is the demand profile for VG30 in the Indian market?",
        "answer": "VG30 has the highest market demand as it is the standard for most highway and district road construction.",
        "keywords": ["vg30", "demand", "market", "highest", "standard"]
    },
    {
        "section": "grades",
        "question": "At what stage of the road construction process is bitumen actually applied?",
        "answer": "Bitumen is used in the DBM (Dense Bituminous Macadam) layer, which is the load-bearing layer, and the BC (Bituminous Concrete) layer, which is the top wearing surface.",
        "keywords": ["road construction", "stage", "dbm", "bc", "layer", "applied"]
    },
    {
        "section": "grades",
        "question": "Is bitumen used in the foundation layers like the sub-grade or sub-base?",
        "answer": "No, the foundation layers consist of compacted soil and granular materials; no bitumen is used at that level.",
        "keywords": ["foundation", "sub-grade", "sub-base", "no bitumen"]
    },
    {
        "section": "grades",
        "question": "How does understanding the road layer structure help the sales team?",
        "answer": "It helps explain why specific grades are required and assists in calculating the quantity of bitumen needed based on layer thickness.",
        "keywords": ["road layer", "structure", "sales team", "calculate quantity"]
    },
    {
        "section": "grades",
        "question": "Which Bitumen grade corresponds to which weather?",
        "answer": "1. VG10: Cold/Hilly regions (Prevents cold cracking).\n2. VG30: Moderate/Standard climates (Most India).\n3. VG40: Hot climates & Heavy Traffic (Resists melting/rutting).",
        "keywords": ["weather", "climate", "temperature", "selection", "vg10", "vg30", "vg40"]
    },

    # ═══════════════════════════════════════════════════════════
    # SECTION 4: PRICING & COST STRUCTURE  (Pages 17-18 + Advanced)
    # ═══════════════════════════════════════════════════════════

    {
        "section": "pricing",
        "question": "Why is there such a wide range in bitumen prices in the market?",
        "answer": "Market prices vary between Rs 32 and Rs 60 per kg because they reflect multiple cost components accumulated from the refinery gate to the contractor's site.",
        "keywords": ["price", "vary", "range", "wide", "why"]
    },
    {
        "section": "pricing",
        "question": "Is bitumen pricing arbitrary based on the trader?",
        "answer": "No, the variation is a result of a specific breakdown of costs including material, taxes, logistics, and handling.",
        "keywords": ["arbitrary", "trader", "pricing", "breakdown"]
    },
    {
        "section": "pricing",
        "question": "What is the purpose of explaining the pricing structure to a customer?",
        "answer": "Explaining the breakdown allows the sales team to justify the price professionally and transparently, building trust with the buyer.",
        "keywords": ["explain pricing", "justify", "transparency", "trust"]
    },
    {
        "section": "pricing",
        "question": "Can you break down what factors contribute to the final price of bitumen?",
        "answer": "The price includes base material cost, GST, transportation freight, handling and storage, working capital interest, transit loss, and a reasonable trader margin.",
        "keywords": ["price breakdown", "factors", "gst", "freight", "margin", "cost"]
    },
    {
        "section": "pricing",
        "question": "How does distance affect the final cost of bitumen?",
        "answer": "Freight costs from the port or refinery to the delivery location vary significantly based on distance and impact the final landed cost.",
        "keywords": ["distance", "freight", "final cost", "landed cost"]
    },
    {
        "section": "pricing",
        "question": "What is Transit Loss in the context of bitumen pricing?",
        "answer": "Transit loss accounts for the material loss that occurs during handling and temperature variations during the transport process.",
        "keywords": ["transit loss", "material loss", "handling", "temperature"]
    },
    {
        "section": "pricing",
        "question": "How are actual market prices for bitumen determined?",
        "answer": "Actual prices are determined by taking the refinery base price, subtracting a variable 'Refinery Discount,' and adding transportation and conversion costs.",
        "keywords": ["market price", "determined", "refinery discount", "formula"]
    },
    {
        "section": "pricing",
        "question": "What is included in the quoted price per kg?",
        "answer": "The price includes ONLY the basic bitumen material cost at the terminal or loading point. Exclusions (at actuals): GST, Freight, Loading/Unloading, Tolls, Detention.",
        "keywords": ["quote", "include", "exclude", "terms", "per kg"]
    },
    {
        "section": "pricing",
        "question": "How is import parity price calculated for bitumen?",
        "answer": "Import parity = FOB price (Iraq/UAE, USD/MT) x USD/INR exchange rate + Ocean freight (₹ 30-45/MT) x USD/INR + Insurance (0.5% of CIF value) + Customs duty (2.5% of CIF) + Port charges Rs 75-150/MT + GST 18% of (CIF + Customs + Port). At Brent ~₹ 75/bbl, FOB Iraq bitumen is approximately ₹ 380-400/MT. Typical landed cost at Kandla: Rs 47,000-49,500/MT before dealer margin.",
        "keywords": ["import parity", "landed cost", "how calculated", "fob", "cif", "customs duty", "formula"]
    },
    {
        "section": "pricing",
        "question": "How does Brent crude price affect Indian bitumen price?",
        "answer": "Every ₹ 1 increase in Brent crude price increases Indian bitumen price by approximately Rs 100-120/MT. This is because: (1) Bitumen feedstock cost is directly linked to crude; (2) PSU refineries revise prices to maintain margins; (3) Import parity recalculates with new FOB price.",
        "keywords": ["brent effect", "crude price impact", "how crude affects", "brent to bitumen"]
    },
    {
        "section": "pricing",
        "question": "How does USD/INR exchange rate affect bitumen prices?",
        "answer": "Every Rs 1 depreciation in USD/INR increases imported bitumen landed cost by approximately Rs 75-90/MT. PSU prices are less directly affected but follow import parity trend.",
        "keywords": ["usd inr", "exchange rate", "rupee depreciation", "forex effect", "dollar rate"]
    },
    {
        "section": "pricing",
        "question": "What is decanting and when is it cheaper than buying bulk bitumen?",
        "answer": "Decanting is the process of converting drum bitumen into bulk liquid form using a decanter machine (steam-heated tank). It is cheaper than bulk when: (1) Destination is far from a bulk terminal (>600 km); (2) Order quantity is small (<200 MT); (3) Site has no bulk storage facility. Typical decanting cost: Rs 450-600/MT conversion + drum price premium of Rs 2,000-3,500/MT over bulk.",
        "keywords": ["decanting", "decanter", "drum to bulk", "when cheaper", "drum conversion"]
    },
    {
        "section": "pricing",
        "question": "What is the 1st and 16th pricing cycle for bitumen?",
        "answer": "PSU refineries (IOCL, BPCL, HPCL) revise bitumen prices on the 1st and 16th of every month, creating 24 pricing events per year. Notification is issued 2-3 days before effective date. Key implication: If price is expected to rise on 1st, push customers to book before month-end.",
        "keywords": ["1st 16th", "pricing cycle", "revision cycle", "monthly revision", "when prices change"]
    },

    # ═══════════════════════════════════════════════════════════
    # SECTION 5: MARKET DYNAMICS  (Pages 7-9, 31-34)
    # ═══════════════════════════════════════════════════════════

    # -- Pages 7-9: Refineries, Imports, Supply Gaps --
    {
        "section": "market",
        "question": "Which are the major refineries in India that form the backbone of the domestic supply?",
        "answer": "The major refineries include Indian Oil Corporation (Panipat, Mathura, Barauni, Haldia), Bharat Petroleum (Mumbai, Kochi), Hindustan Petroleum (Mumbai, Visakhapatnam), Reliance Industries (Jamnagar), MRPL (Mangalore), CPCL (Chennai), and Numaligarh Refinery (Assam).",
        "keywords": ["refineries", "iocl", "bpcl", "hpcl", "reliance", "produce", "india"]
    },
    {
        "section": "market",
        "question": "Which refinery complex is known as the largest in India?",
        "answer": "Reliance Industries in Jamnagar, Gujarat, is the largest refinery complex in the domestic landscape.",
        "keywords": ["largest refinery", "reliance", "jamnagar", "gujarat"]
    },
    {
        "section": "market",
        "question": "Under what standards do Indian refineries operate?",
        "answer": "These refineries operate under strict Bureau of Indian Standards (BIS) specifications and government oversight.",
        "keywords": ["standards", "bis", "government", "specifications"]
    },
    {
        "section": "market",
        "question": "Why does your company focus on imports if India has its own refineries?",
        "answer": "India faces a structural bitumen shortage of approximately 50%. While domestic refineries produce about 5 million metric tons, the annual requirement is 10 million metric tons, making international imports essential.",
        "keywords": ["import", "why", "shortage", "demand", "supply", "50 percent"]
    },
    {
        "section": "market",
        "question": "Why can't Indian refineries simply produce more bitumen to meet demand?",
        "answer": "Refineries prioritize higher-value products like petrol and diesel; bitumen is a residual output dependent on total crude oil processing capacity and product mix optimization.",
        "keywords": ["produce more", "capacity", "prioritize", "residual", "petrol diesel"]
    },
    {
        "section": "market",
        "question": "What is the current annual bitumen requirement in India?",
        "answer": "The country's annual requirement stands at approximately 10 million metric tons.",
        "keywords": ["annual requirement", "10 million", "demand", "india"]
    },
    {
        "section": "market",
        "question": "Are there specific reasons why we shouldn't just rely on domestic refinery output?",
        "answer": "Domestic output is constrained by crude processing volumes and cannot be independently scaled. Imports are also necessary to handle seasonal demand peaks and regional supply imbalances efficiently.",
        "keywords": ["domestic output", "constrained", "seasonal", "supply imbalance"]
    },
    {
        "section": "market",
        "question": "When is the peak season for bitumen demand in India?",
        "answer": "Road construction activity concentrates between October and March, creating demand surges that domestic supply cannot accommodate alone.",
        "keywords": ["peak season", "october", "march", "demand surge", "construction"]
    },
    {
        "section": "market",
        "question": "How do imports help with regional supply gaps?",
        "answer": "Refineries are concentrated in specific states; importing through multiple ports helps distribute supply more efficiently to regions with gaps.",
        "keywords": ["regional", "supply gaps", "ports", "distribute", "imports help"]
    },

    # -- Pages 31-34: Refinery Economics, Pricing, Centre Zones --
    {
        "section": "market",
        "question": "What does the section on Market Dynamics and Refinery Economics cover?",
        "answer": "It covers price determination, geographic factors, and how refinery economics shape the bitumen market.",
        "keywords": ["market dynamics", "refinery economics", "section 5", "price determination"]
    },
    {
        "section": "market",
        "question": "Is geography a major factor in bitumen sales?",
        "answer": "Yes, geography determines product viability and is a fundamental part of the refinery economics.",
        "keywords": ["geography", "factor", "viability", "location"]
    },
    {
        "section": "market",
        "question": "What is the primary goal of understanding market dynamics for the sales team?",
        "answer": "To understand why prices fluctuate and how to position products effectively based on where the refinery is located.",
        "keywords": ["goal", "understand", "price fluctuate", "position products"]
    },
    {
        "section": "market",
        "question": "What factors influence the discount a refinery might offer?",
        "answer": "Refinery discounts depend on production capacity, regional competition, logistics advantages, and specific sales strategies.",
        "keywords": ["refinery discount", "factors", "competition", "logistics"]
    },
    {
        "section": "market",
        "question": "What is Conversion Cost in the pricing structure?",
        "answer": "It refers to the charges for decanting bitumen from drums to bulk form, which is often applicable for remote markets.",
        "keywords": ["conversion cost", "decanting", "drums to bulk", "remote"]
    },
    {
        "section": "market",
        "question": "How does refinery density differ between North and South India?",
        "answer": "South India has a high refinery density (average distance 420-800 km), while North India has a low density (average distance 350-1,000 km) with fewer facilities.",
        "keywords": ["north south", "refinery density", "distance", "difference"]
    },
    {
        "section": "market",
        "question": "What is the result of high refinery competition in South India?",
        "answer": "It leads to higher refinery discounts, making bulk bitumen very cost-competitive and limiting the viability of drum bitumen.",
        "keywords": ["south india", "competition", "discount", "bulk competitive"]
    },
    {
        "section": "market",
        "question": "How does the lower competition in North India affect the market?",
        "answer": "Bulk transportation becomes costly over long distances, which makes drum bitumen economically viable and allows decanter operations to flourish.",
        "keywords": ["north india", "lower competition", "drum viable", "decanter"]
    },
    {
        "section": "market",
        "question": "What are Centre Zones and why are they important for business?",
        "answer": "Centre Zones are areas midway between refineries (like Indore or Nagpur) where bulk freight is expensive from all directions, creating natural demand for drum bitumen.",
        "keywords": ["centre zones", "midway", "indore", "nagpur", "drum demand"]
    },
    {
        "section": "market",
        "question": "Which cities are identified as high-potential Centre Zone markets?",
        "answer": "Cities like Nagpur, Indore, Bhopal, Raipur, Jabalpur, Udaipur, and Kota are major Centre Zones.",
        "keywords": ["centre zone cities", "nagpur", "indore", "bhopal", "raipur", "kota"]
    },
    {
        "section": "market",
        "question": "Who are the primary customers in Centre Zones?",
        "answer": "Decanters -- facilities that buy drum bitumen, convert it to bulk, and supply it locally -- are the primary customers in these areas.",
        "keywords": ["centre zone customers", "decanters", "convert", "local supply"]
    },

    # ═══════════════════════════════════════════════════════════
    # SECTION 6: TERRITORY LOGIC & PRODUCT SELECTION  (Pages 35-44)
    # ═══════════════════════════════════════════════════════════

    {
        "section": "territory",
        "question": "What is the focus of the Product Specialization and Territory Logic section?",
        "answer": "It helps the sales team recommend the right product for the right region, driven by logistics economics and customer location.",
        "keywords": ["product specialization", "territory logic", "section 6", "recommend"]
    },
    {
        "section": "territory",
        "question": "Is product selection based on salesperson preference?",
        "answer": "No, it is purely driven by logistics economics and the customer's specific location.",
        "keywords": ["product selection", "preference", "logistics", "location driven"]
    },
    {
        "section": "territory",
        "question": "What is the risk of pushing the wrong product in a territory?",
        "answer": "It leads to unprofitable transactions and customer dissatisfaction because the pricing will not be competitive for that specific location.",
        "keywords": ["wrong product", "risk", "unprofitable", "not competitive"]
    },
    {
        "section": "territory",
        "question": "What are your core products and which one is the primary specialization?",
        "answer": "Our primary specialization is Imported Drum Bitumen (180 kg). Bulk Bitumen is handled selectively as a secondary product for South India requirements.",
        "keywords": ["core products", "specialization", "drum", "bulk", "180 kg"]
    },
    {
        "section": "territory",
        "question": "From which ports do you primarily import drum bitumen?",
        "answer": "We import through Kandla, Mundra, and Mumbai ports.",
        "keywords": ["ports", "import", "kandla", "mundra", "mumbai"]
    },
    {
        "section": "territory",
        "question": "How do you determine whether to sell bulk or drum bitumen to a customer?",
        "answer": "The decision is based on territory logic: where bulk economics are favorable (South), we sell bulk; where drum economics are better (North/Central), we sell drum.",
        "keywords": ["drum", "bulk", "when", "territory", "logic", "determine"]
    },
    {
        "section": "territory",
        "question": "Where do your drum bitumen imports come from and which ports do you use?",
        "answer": "Drum bitumen is sourced internationally from Middle East and Gulf countries, imported through Kandla, Mundra, and Mumbai.",
        "keywords": ["imports source", "middle east", "gulf", "drum source"]
    },
    {
        "section": "territory",
        "question": "What is the role of Kandla Port in your business?",
        "answer": "Kandla is our primary import terminal with the largest drum handling capacity, serving North and Central India extensively.",
        "keywords": ["kandla port", "role", "primary terminal", "drum handling"]
    },
    {
        "section": "territory",
        "question": "Do these imports undergo quality checks?",
        "answer": "Yes, all imports meet Bureau of Indian Standards (BIS) specifications and undergo quality checks at the port facilities.",
        "keywords": ["quality checks", "bis", "import quality", "port checks"]
    },
    {
        "section": "territory",
        "question": "What are the standard specifications of the drums you supply?",
        "answer": "We supply mild steel drums with 180 kg net weight. They are stackable for efficiency and available in both VG30 and VG40 grades.",
        "keywords": ["drum specs", "180 kg", "mild steel", "stackable", "specifications"]
    },
    {
        "section": "territory",
        "question": "How do your imported drums compare to Indian refinery drums?",
        "answer": "Indian refinery drums are typically 154 kg net and more expensive. Our 180 kg imported drums offer better value and more consistent quality.",
        "keywords": ["imported vs domestic", "154 kg", "180 kg", "comparison", "value"]
    },
    {
        "section": "territory",
        "question": "What is the advantage of imported drums?",
        "answer": "They have better quality consistency than domestic refinery drums while remaining fully specification-compliant.",
        "keywords": ["advantage", "imported drums", "consistency", "compliant"]
    },
    {
        "section": "territory",
        "question": "Why is the Kandla-Mundra hub considered the most dominant for drum bitumen?",
        "answer": "It offers the lowest freight rates, established logistics networks, and consistent import volumes, making it the most efficient hub for North and Central India.",
        "keywords": ["kandla", "mundra", "hub", "dominant", "lowest freight"]
    },
    {
        "section": "territory",
        "question": "What is the typical economic radius for drum supply from Kandla-Mundra?",
        "answer": "The radius is remarkably far, often reaching 1,500 to 2,000 kilometers economically due to favorable freight structures.",
        "keywords": ["economic radius", "1500 km", "2000 km", "reach", "freight"]
    },
    {
        "section": "territory",
        "question": "Which states are fully covered by the Kandla-Mundra hub?",
        "answer": "Coverage includes Gujarat, Rajasthan, MP, Chhattisgarh, UP, Delhi NCR, Haryana, Punjab, and several extended reach states like Bihar and Jharkhand.",
        "keywords": ["states covered", "gujarat", "rajasthan", "mp", "up", "delhi"]
    },
    {
        "section": "territory",
        "question": "When should I choose drum supply from Mumbai instead of Kandla?",
        "answer": "Only when the customer is within an approximately 200-km radius of Mumbai (e.g., Pune, Thane) where short distance freight compensates for higher port costs.",
        "keywords": ["mumbai", "when", "200 km", "pune", "thane"]
    },
    {
        "section": "territory",
        "question": "What are the main drawbacks of the Mumbai port for bitumen?",
        "answer": "Significantly higher port costs and congestion charges compared to Kandla and Mundra.",
        "keywords": ["mumbai drawbacks", "higher costs", "congestion", "port costs"]
    },
    {
        "section": "territory",
        "question": "What should I do if a customer is more than 200 km from Mumbai?",
        "answer": "You should always check if Kandla-Mundra freight is more competitive and recommend the option that ensures better pricing for the customer.",
        "keywords": ["200 km", "mumbai", "check kandla", "competitive", "recommend"]
    },
    {
        "section": "territory",
        "question": "Can you supply drum bitumen to South India?",
        "answer": "We focus exclusively on bulk bitumen in South India. Selling drum bitumen there would make the price uncompetitive against local bulk suppliers.",
        "keywords": ["south india drum", "uncompetitive", "bulk only south"]
    },
    {
        "section": "territory",
        "question": "Why does bulk bitumen work better in the South?",
        "answer": "High refinery density and efficient, well-developed bulk tanker logistics make bulk bitumen significantly cheaper than drum bitumen in that region.",
        "keywords": ["bulk south", "refinery density", "tanker logistics", "cheaper"]
    },
    {
        "section": "territory",
        "question": "What is the sales strategy for South India?",
        "answer": "Position ourselves as bulk coordinators with access to Karwar and Mangalore sources, and transparently explain why bulk serves the customer better.",
        "keywords": ["south india strategy", "bulk coordinator", "karwar", "mangalore"]
    },
    {
        "section": "territory",
        "question": "How does the Drum-to-Bulk conversion model work for remote contractors?",
        "answer": "Drums are transported to a decanter facility, heated to a liquid state (150-165C), and then sold locally as bulk to contractors who lack long-distance tanker access.",
        "keywords": ["drum to bulk", "conversion", "decanter", "heated", "150 165"]
    },
    {
        "section": "territory",
        "question": "What is the temperature range for liquefying bitumen in a decanter?",
        "answer": "The bitumen is typically heated to between 150C and 165C to bring it to a liquid state.",
        "keywords": ["temperature", "liquefying", "decanter", "150", "165"]
    },
    {
        "section": "territory",
        "question": "How many drums does a typical truck carry for transport to decanters?",
        "answer": "Trucks usually carry between 120 and 140 drums per vehicle for economical long-distance transport.",
        "keywords": ["drums per truck", "120", "140", "transport", "truck capacity"]
    },
    {
        "section": "territory",
        "question": "What are the five critical questions a salesperson must ask before quoting?",
        "answer": "You must ask for the customer's location, distance from the port, required quantity, storage availability, and final usage pattern.",
        "keywords": ["five questions", "before quoting", "location", "quantity", "storage"]
    },
    {
        "section": "territory",
        "question": "Why is knowing the Final Usage Pattern important?",
        "answer": "It helps identify if the customer needs bitumen for a hot mix plant, road patchwork, or for resale as a trader.",
        "keywords": ["final usage", "hot mix", "patchwork", "trader", "resale"]
    },
    {
        "section": "territory",
        "question": "How does quantity affect the pricing structure?",
        "answer": "Quantity determines the logistics cost impact and whether a bulk or drum supply model is most viable and competitive.",
        "keywords": ["quantity", "pricing", "logistics cost", "viable"]
    },
    {
        "section": "territory",
        "question": "What is the recommendation for a large contractor with a tank in North India?",
        "answer": "Recommend bulk if a refinery is nearby; otherwise, recommend drum if the location is remote.",
        "keywords": ["north india", "large contractor", "tank", "recommendation"]
    },
    {
        "section": "territory",
        "question": "Which product is always recommended for a hot mix plant in South India?",
        "answer": "Bulk only is the recommended product for hot mix plants in South India.",
        "keywords": ["hot mix plant", "south india", "bulk only", "recommended"]
    },
    {
        "section": "territory",
        "question": "What should you recommend to a trader or decanter in a Centre Zone?",
        "answer": "You should recommend drum bitumen sourced from the Kandla-Mundra hub.",
        "keywords": ["trader", "decanter", "centre zone", "recommend drum"]
    },
    {
        "section": "territory",
        "question": "Which PSU refinery serves Gujarat and Rajasthan?",
        "answer": "Primary: IOCL Koyali (Vadodara, Gujarat) -- closest to our HQ. Secondary: IOCL Mathura (UP) for North Rajasthan. BPCL Mumbai for South Gujarat. For import: Kandla and Mundra ports serve all of Gujarat and Rajasthan.",
        "keywords": ["gujarat refinery", "rajasthan refinery", "iocl koyali", "territory", "state refinery"]
    },
    {
        "section": "territory",
        "question": "Which ports handle bitumen imports for South India?",
        "answer": "South India import ports: (1) Ennore (Chennai) for TN/AP; (2) Vizag for AP/Odisha; (3) Mangalore for Karnataka/Kerala. West coast: Kandla, Mundra, JNPT. East coast: Paradip, Haldia.",
        "keywords": ["south india ports", "import port", "ennore", "vizag", "mangalore"]
    },
    {
        "section": "territory",
        "question": "When to recommend drum bitumen vs bulk bitumen to a customer?",
        "answer": "Recommend DRUMS when: (1) Order < 100 MT; (2) No bulk storage; (3) Remote location (>700 km from port/refinery); (4) Multiple small deliveries needed. Recommend BULK when: (1) Order > 200 MT; (2) Has storage tank; (3) Near major city or port. Drum premium: Rs 2,000-3,500/MT.",
        "keywords": ["drum vs bulk", "when drum", "drum supply", "bulk supply", "recommend"]
    },
    {
        "section": "territory",
        "question": "How does distance affect the PSU vs import feasibility decision?",
        "answer": "Rule of thumb: (1) Within 400 km of a PSU refinery -> PSU is cheaper; (2) 400-700 km -> depends on specific prices; (3) > 700 km from any PSU + within 300 km of a port -> import is usually cheaper. Gujarat is unique: near both IOCL Koyali AND Kandla/Mundra ports.",
        "keywords": ["distance feasibility", "psu vs import", "when import cheaper", "break even"]
    },

    # ═══════════════════════════════════════════════════════════
    # SECTION 7: SALES PROCESS & CUSTOMER ENGAGEMENT  (Pages 45-52)
    # ═══════════════════════════════════════════════════════════

    {
        "section": "sales",
        "question": "What does the Sales Process and Customer Engagement section cover?",
        "answer": "It details building credibility and professional communication, providing a systematic approach that converts inquiries into orders through credible and logical sales techniques.",
        "keywords": ["sales process", "customer engagement", "section 7", "credibility"]
    },
    {
        "section": "sales",
        "question": "Is bitumen sold through standard consumer marketing?",
        "answer": "No, it is a critical infrastructure input where buyers evaluate suppliers based on price, reliability, and professional execution.",
        "keywords": ["consumer marketing", "infrastructure input", "evaluate", "buyers"]
    },
    {
        "section": "sales",
        "question": "What is the expected mindset of a salesperson at PPS Anantams?",
        "answer": "You must position yourself as an industry peer, using correct terminology (MT, VG grades, decanter) and focusing on business logic rather than persuasive tactics.",
        "keywords": ["mindset", "industry peer", "terminology", "business logic"]
    },
    {
        "section": "sales",
        "question": "Why should you avoid using excessive sir or formal scripts?",
        "answer": "They can sound junior and signal inexperience, which decreases credibility with professional bitumen buyers.",
        "keywords": ["sir", "formal", "junior", "credibility", "avoid"]
    },
    {
        "section": "sales",
        "question": "What three criteria do bitumen buyers use to evaluate a supplier?",
        "answer": "Buyers only care about price competitiveness, supply reliability, and professional execution.",
        "keywords": ["criteria", "evaluate", "price", "reliability", "execution"]
    },
    {
        "section": "sales",
        "question": "Why is Pre-Call Intimation mandatory?",
        "answer": "Business owners receive dozens of calls daily; an advance message via WhatsApp or SMS provides context, shows respect for their time, and differentiates you from random callers.",
        "keywords": ["pre-call", "intimation", "whatsapp", "advance message", "mandatory"]
    },
    {
        "section": "sales",
        "question": "What should the intimation message include?",
        "answer": "It should include your name, company, specialization (imported drum/bulk), and a request for a comfortable time to have a short discussion the next day.",
        "keywords": ["intimation message", "include", "name", "company", "specialization"]
    },
    {
        "section": "sales",
        "question": "What if the customer doesn't respond to the message?",
        "answer": "You should still proceed with the call the next day, using the message as a reference to establish continuity.",
        "keywords": ["no response", "proceed", "call", "continuity"]
    },
    {
        "section": "sales",
        "question": "What is the correct way to open a sales call with a new customer?",
        "answer": "The opening should be peer-to-peer: 'Hello, this is [Your Name] calling from PPS Anantams Corporation. As discussed yesterday, I'm calling regarding bitumen supply.'",
        "keywords": ["opening", "call", "script", "start", "correct way"]
    },
    {
        "section": "sales",
        "question": "What is wrong about the traditional sales opening?",
        "answer": "The traditional opening sounds desperate ('can you give us one chance?'), uses excessive 'sir,' and makes unsubstantiated claims.",
        "keywords": ["wrong opening", "desperate", "traditional", "mistake"]
    },
    {
        "section": "sales",
        "question": "How does the correct opening position the salesperson?",
        "answer": "It positions you as an industry professional who understands the customer already deals in bitumen, inviting a conversation rather than a 'pitch.'",
        "keywords": ["position", "professional", "conversation", "not pitch"]
    },
    {
        "section": "sales",
        "question": "What credibility points should you deliver within the first 30 seconds?",
        "answer": "Mention the 24 years of industry experience, the import sources (Kandla/Mumbai), and the fact that you are a regular supplier with zero complaints.",
        "keywords": ["credibility", "30 seconds", "experience", "zero complaints"]
    },
    {
        "section": "sales",
        "question": "How should you use trade references to build trust?",
        "answer": "Use them subtly and conditionally. Mention that established traders in their state already buy from us, and offer to share specific references only if they show interest.",
        "keywords": ["trade references", "trust", "subtly", "references"]
    },
    {
        "section": "sales",
        "question": "What are the Reference Quality rules?",
        "answer": "Only share references from stable, established customers who have given permission, and never from those with pending execution issues.",
        "keywords": ["reference quality", "rules", "permission", "stable customers"]
    },
    {
        "section": "sales",
        "question": "Why is it a mistake to quote prices blindly?",
        "answer": "Quoting without context creates distrust and makes you look like an amateur. You must first understand the location and competitive context.",
        "keywords": ["quote blindly", "mistake", "distrust", "amateur"]
    },
    {
        "section": "sales",
        "question": "What three quick questions reveal the right pricing level for a customer?",
        "answer": "Ask about their monthly requirement in MT, their storage facility (tank/decanter), and their final usage (hot mix/resale/patchwork).",
        "keywords": ["quick questions", "pricing level", "requirement", "storage"]
    },
    {
        "section": "sales",
        "question": "What logic should you use when discussing price?",
        "answer": "Explain that prices across India are similar and the real difference comes from refinery discounts and logistics costs specific to their territory.",
        "keywords": ["price logic", "similar prices", "logistics costs", "territory"]
    },
    {
        "section": "sales",
        "question": "How can you distinguish a bulk buyer from a drum buyer?",
        "answer": "Bulk buyers usually need 200+ MT, have tanks, and are near refineries. Drum buyers need 20-100 MT, lack infrastructure, and are in remote zones.",
        "keywords": ["bulk buyer", "drum buyer", "distinguish", "profile"]
    },
    {
        "section": "sales",
        "question": "Which region is a strong indicator of a bulk buyer?",
        "answer": "South India is a strong indicator for bulk buyer requirements.",
        "keywords": ["south india", "bulk buyer", "indicator", "region"]
    },
    {
        "section": "sales",
        "question": "What should you do if we are not competitive for a specific bulk buyer's location?",
        "answer": "Transparently explain that bulk from a specific local source works better for them; this honesty builds long-term trust even if you lose that specific sale.",
        "keywords": ["not competitive", "transparent", "honesty", "long-term trust"]
    },
    {
        "section": "sales",
        "question": "What is the Soft Close approach in sales?",
        "answer": "'Let me share today's workable price with you based on our discussion. If it matches your expectation, we can plan supply accordingly.'",
        "keywords": ["soft close", "approach", "workable price", "plan supply"]
    },
    {
        "section": "sales",
        "question": "Why should a salesperson never beg for orders?",
        "answer": "Begging or sounding desperate signals instability. Buyers respect suppliers who are confident, dignified, and honest about their capabilities.",
        "keywords": ["beg", "desperate", "dignity", "confident", "never beg"]
    },
    {
        "section": "sales",
        "question": "What is the Critical Sales Discipline mentioned in the manual?",
        "answer": "Maintaining professional dignity, never making unrealistic promises, and accepting that some deals may be for the future while staying connected.",
        "keywords": ["sales discipline", "dignity", "realistic", "connected"]
    },
    {
        "section": "sales",
        "question": "How to handle Price High objection?",
        "answer": "Explain that refined base prices are similar; difference is logistics. Offer to calculate exact landed cost to show value.",
        "keywords": ["price high", "expensive", "objection", "landed cost"]
    },

    # ═══════════════════════════════════════════════════════════
    # SECTION 8: PAYMENT TERMS & PROCEDURES  (Pages 53-55)
    # ═══════════════════════════════════════════════════════════

    {
        "section": "payment",
        "question": "What does the Payment Terms and Transaction Procedures section cover?",
        "answer": "It outlines the payment terms and transaction procedures for both bulk and drum bitumen, with clear policies to protect both the company and customer interests.",
        "keywords": ["payment terms", "section 8", "transaction", "procedures"]
    },
    {
        "section": "payment",
        "question": "Are these payment policies flexible for new customers?",
        "answer": "These are clear policies designed to protect both the company and customer interests, reflecting industry-standard practices.",
        "keywords": ["flexible", "new customers", "policy", "industry standard"]
    },
    {
        "section": "payment",
        "question": "Why are transaction procedures emphasized in the training?",
        "answer": "To ensure that the sales team provides consistent information to customers, preventing future disputes or financial risks.",
        "keywords": ["why emphasized", "consistent", "disputes", "financial risks"]
    },
    {
        "section": "payment",
        "question": "Why is 100% advance payment mandatory for bulk bitumen?",
        "answer": "Once a tanker leaves the terminal, the risk of diversion or non-payment is unmanageable. This is the industry-standard for bulk commodities.",
        "keywords": ["bulk", "payment", "advance", "100 percent", "mandatory", "tanker"]
    },
    {
        "section": "payment",
        "question": "How does the payment process for drum bitumen differ?",
        "answer": "Drums allow for payment after loading because they can be held at the loading point until payment is confirmed via the weightment slip.",
        "keywords": ["drum", "payment", "after loading", "weightment slip"]
    },
    {
        "section": "payment",
        "question": "When might advance payment be required for drums?",
        "answer": "For remote locations or uncontrolled truck routes where the risk of the material reaching the customer before payment is higher.",
        "keywords": ["advance drums", "remote", "truck routes", "risk"]
    },
    {
        "section": "payment",
        "question": "What exactly is included in the quoted price per kg?",
        "answer": "The price includes ONLY the basic bitumen material cost at the terminal or loading point.",
        "keywords": ["quoted price", "included", "basic cost", "terminal"]
    },
    {
        "section": "payment",
        "question": "What are the Exclusions that a customer must pay for at actuals?",
        "answer": "Exclusions include GST, transportation freight, loading/unloading charges, tolls, entry taxes, and any detention or demurrage charges.",
        "keywords": ["exclusions", "gst", "freight", "tolls", "detention", "actuals"]
    },
    {
        "section": "payment",
        "question": "What is the Transparency Principle mentioned in the manual?",
        "answer": "We never bundle costs or hide charges. Every component is itemized clearly to prevent misunderstandings and build long-term trust.",
        "keywords": ["transparency principle", "never hide", "itemized", "trust"]
    },

    # ═══════════════════════════════════════════════════════════
    # SECTION 9: MODIFIED BITUMEN & EMULSIONS  (Pages 19-23)
    # ═══════════════════════════════════════════════════════════

    {
        "section": "modified",
        "question": "What does the section on other bitumen products cover?",
        "answer": "It covers other bitumen products beyond standard VG-grades, such as emulsions and modified bitumen for specialized applications.",
        "keywords": ["other products", "section 3", "emulsions", "modified"]
    },
    {
        "section": "modified",
        "question": "Why are specialized bitumen products used in road construction?",
        "answer": "They serve specific surface treatment needs and are designed for applications like extreme weather or high-traffic endurance.",
        "keywords": ["specialized", "surface treatment", "extreme weather", "high traffic"]
    },
    {
        "section": "modified",
        "question": "Are modified bitumen products as common as VG-grade bitumen?",
        "answer": "They are specialized, meaning they are used for specific technical requirements rather than the bulk of general road foundation work.",
        "keywords": ["common", "specialized", "technical requirements", "vg-grade"]
    },
    {
        "section": "modified",
        "question": "What is Bituminous Emulsion and when is it used?",
        "answer": "Bituminous emulsion is a liquid mixture of bitumen and water stabilized with an emulsifying agent. It is applied at ambient temperatures for prime coats, tack coats, and patchwork.",
        "keywords": ["emulsion", "liquid", "cold", "patchwork", "prime coat", "tack coat"]
    },
    {
        "section": "modified",
        "question": "What happens to the emulsion after it is applied to a surface?",
        "answer": "The emulsion 'breaks down' -- the water evaporates, and the bitumen coats the aggregate particles.",
        "keywords": ["emulsion breaks", "water evaporates", "aggregate", "applied"]
    },
    {
        "section": "modified",
        "question": "What is the advantage of using emulsions over hot bitumen?",
        "answer": "Emulsions eliminate the need for heating during application, making the process safer and reducing costs for certain road treatments.",
        "keywords": ["advantage emulsion", "no heating", "safer", "reduce cost"]
    },
    {
        "section": "modified",
        "question": "What is the difference between CRMB and PMB modified bitumen?",
        "answer": "CRMB (Crumb Rubber Modified Bitumen) uses recycled rubber to enhance elasticity for highways, while PMB (Polymer Modified Bitumen) uses polymers to provide premium stability for airport runways and expressways.",
        "keywords": ["crmb", "pmb", "difference", "modified", "rubber", "polymer"]
    },
    {
        "section": "modified",
        "question": "What is Natural Rubber Modified Bitumen (NRMB) used for?",
        "answer": "NRMB is often mandated in specific states like Kerala to support the local rubber industry while providing enhanced elasticity and temperature resistance.",
        "keywords": ["nrmb", "natural rubber", "kerala", "mandated"]
    },
    {
        "section": "modified",
        "question": "Which modified bitumen is considered the premium grade for the most demanding applications?",
        "answer": "Polymer Modified Bitumen (PMB) is the premium grade used for airport runways and bridge decks due to its superior resistance to deformation.",
        "keywords": ["premium grade", "pmb", "airport", "bridge deck", "deformation"]
    },
    {
        "section": "modified",
        "question": "What is Plastic Bitumen and is it currently widely used?",
        "answer": "Plastic Bitumen incorporates processed waste plastic (5-10%). Its commercial adoption is currently limited and it is primarily used in government-mandated zones.",
        "keywords": ["plastic bitumen", "waste plastic", "limited", "government mandated"]
    },
    {
        "section": "modified",
        "question": "What are the challenges facing the adoption of plastic bitumen?",
        "answer": "Challenges include inconsistent waste quality, processing complexities, and a lack of long-term performance data.",
        "keywords": ["plastic challenges", "inconsistent", "processing", "performance data"]
    },
    {
        "section": "modified",
        "question": "What is the current status of Agro-Based Bitumen?",
        "answer": "It is currently in the research and pilot project phase and is not yet commercially viable for large-scale infrastructure projects.",
        "keywords": ["agro based", "research", "pilot", "not viable"]
    },
    {
        "section": "modified",
        "question": "How do you handle orders for modified bitumen and emulsions?",
        "answer": "We leverage partnerships with reputed Indian manufacturers to fulfill these requirements, ensuring customers receive factory-fresh material with proper certifications.",
        "keywords": ["supply", "modified", "available", "partnerships", "manufacturers"]
    },
    {
        "section": "modified",
        "question": "Why can't you quote a price for modified bitumen instantly?",
        "answer": "Costs vary significantly based on manufacturer location, quantity, freight distance, and current raw material costs.",
        "keywords": ["modified price", "vary", "manufacturer", "cannot quote instantly"]
    },
    {
        "section": "modified",
        "question": "What is the recommended professional approach when a customer asks for modified products?",
        "answer": "Clearly state that we specialize in VG-grade and coordinate with partners for modified products, asking the customer for complete project details first to ensure accuracy.",
        "keywords": ["professional approach", "modified request", "specialize vg", "project details"]
    },

    # ═══════════════════════════════════════════════════════════
    # SECTION 10: LOGISTICS & SUPPLY CHAIN
    # ═══════════════════════════════════════════════════════════

    {
        "section": "logistics",
        "question": "What is Transit Loss?",
        "answer": "Standard material loss during handling/transport, factored into pricing.",
        "keywords": ["transit", "loss", "handling", "transport"]
    },

    # ═══════════════════════════════════════════════════════════
    # SECTION 11: TECHNICAL & CONSUMPTION METRICS  (Pages 14-16)
    # ═══════════════════════════════════════════════════════════

    # -- Pages 14-16: Bitumen Content, Estimation --
    {
        "section": "technical",
        "question": "What is the standard percentage of bitumen required in a typical asphalt mix?",
        "answer": "Bitumen content typically ranges from 2% to 7% by weight of the total mix, as per MoRTH specifications and IRC guidelines.",
        "keywords": ["percentage", "asphalt mix", "morth", "irc", "2 to 7"]
    },
    {
        "section": "technical",
        "question": "Does DBM require more bitumen than Bituminous Concrete (BC)?",
        "answer": "No, DBM typically requires 4.5-5.5% bitumen, whereas BC usually requires a higher percentage of 5-6.5% for void filling and durability.",
        "keywords": ["dbm", "bc", "more bitumen", "percentage", "comparison"]
    },
    {
        "section": "technical",
        "question": "What factors can influence the exact percentage of bitumen in a road mix?",
        "answer": "Factors include the type of layer, aggregate gradation, traffic intensity, axle loads, climate zones, and the project engineer's mix design.",
        "keywords": ["factors", "percentage", "aggregate", "traffic", "mix design"]
    },
    {
        "section": "technical",
        "question": "What are the minimum and maximum bitumen content limits for road applications?",
        "answer": "The minimum is 2% for specific applications, and the maximum is 7% for specialized applications.",
        "keywords": ["minimum", "maximum", "limits", "2 percent", "7 percent"]
    },
    {
        "section": "technical",
        "question": "What is the average bitumen percentage used specifically for DBM?",
        "answer": "The average bitumen content for a Dense Bituminous Macadam (DBM) layer is 4.5%.",
        "keywords": ["average", "dbm", "4.5 percent", "dense bituminous"]
    },
    {
        "section": "technical",
        "question": "What is the standard average for Bituminous Concrete (BC) surface layers?",
        "answer": "The standard average bitumen content for BC surface layers is 6%.",
        "keywords": ["average", "bc", "6 percent", "surface layer"]
    },
    {
        "section": "technical",
        "question": "How can I quickly estimate the amount of bitumen needed per square meter?",
        "answer": "A quick reference range is 3 to 7 kg per square meter, with the lower range for DBM and the higher range for BC layers.",
        "keywords": ["estimate", "per square meter", "3 to 7 kg", "quick reference"]
    },
    {
        "section": "technical",
        "question": "If I have a road project that is 1 kilometer long and 7 meters wide, what is the minimum bitumen required?",
        "answer": "Based on the minimum estimate of 3 kg per m2, a 7,000 m2 area (1km x 7m) would require a minimum of 21,000 kg of bitumen.",
        "keywords": ["1 km", "7 meters", "21000 kg", "minimum", "calculate"]
    },
    {
        "section": "technical",
        "question": "Should the sales team commit to exact quantities based on quick calculations?",
        "answer": "No, these are for initial estimation only. Actual consumption must always be based on the project engineer's approved mix design and specifications.",
        "keywords": ["commit", "exact quantities", "estimation only", "mix design"]
    },

    # -- Existing Technical Deep Dive --
    {
        "section": "technical",
        "question": "How much Bitumen is used per Square Meter (SQM)?",
        "answer": "1. Tack Coat: 0.2 - 0.3 kg/sqm.\n2. Prime Coat: 0.6 - 1.0 kg/sqm.\n3. Road Layer (50mm DBM): Approx 5.5 - 6.0 kg/sqm (at 4.5% content).",
        "keywords": ["consumption", "sqm", "coverage", "quantity", "usage"]
    },
    {
        "section": "technical",
        "question": "How is Bitumen actually applied on roads?",
        "answer": "It is heated to 150-160C to liquefy. It is then mixed with hot aggregates (stone/sand) in a Hot Mix Plant. This 'Hot Mix' is transported via dumpers, laid by a Paver finisher, and compacted by rollers before cooling.",
        "keywords": ["application", "how used", "mixing", "process", "road"]
    },
    {
        "section": "technical",
        "question": "What is PMB (Polymer Modified Bitumen) and when is it used?",
        "answer": "PMB is VG-40 base bitumen modified with SBS (Styrene Butadiene Styrene) or EVA polymer at 3-4% dosage. Required by IRC SP:53 for: highways with >10 mSA traffic loading, bus depots, toll plazas, bridge deck waterproofing. Price premium: Rs 8,000-12,000/MT over VG-30.",
        "keywords": ["pmb", "polymer modified", "sbs", "eva", "modified bitumen", "when use pmb"]
    },
    {
        "section": "technical",
        "question": "How much bitumen is needed per kilometre of road?",
        "answer": "Approximate consumption per km: (1) 4-lane highway (7m wide, 50mm DBM + 25mm BC): 140-160 MT/km; (2) 2-lane road (3.5m wide, 40mm): 55-70 MT/km; (3) Urban road (surface dressing, 10mm): 8-12 MT/km; (4) Pothole repair: 0.5-2 MT/km.",
        "keywords": ["bitumen per km", "consumption per km", "how much bitumen", "mt per km"]
    },
    {
        "section": "technical",
        "question": "What is the difference between VG-30 and VG-40?",
        "answer": "VG-30: Kinematic viscosity 2400-3600 cSt at 60C. Used for normal traffic roads, city roads (~70% of market). VG-40: Kinematic viscosity 3200-4800 cSt at 60C. Stiffer, higher softening point. Used for heavy traffic highways, bus terminals. VG-40 premium: Rs 1,500-2,500/MT over VG-30.",
        "keywords": ["vg30 vs vg40", "difference vg30 vg40", "which grade", "viscosity grade"]
    },
    {
        "section": "technical",
        "question": "What is CRMB (Crumb Rubber Modified Bitumen)?",
        "answer": "CRMB is bitumen modified with crumb rubber from waste tyres at 15-20% dosage. Mandated by IRC SP:107 for surface course on National Highways since 2018. Grades: CRMB-50, CRMB-55, CRMB-60. Price: Rs 5,000-8,000/MT premium over VG-30.",
        "keywords": ["crmb", "crumb rubber", "rubber modified", "waste tyre", "irc 107"]
    },
    {
        "section": "technical",
        "question": "How do you read a bitumen test report (COA)?",
        "answer": "Key parameters: (1) Penetration at 25C; (2) Softening Point -- VG-30 minimum 47C; (3) Viscosity at 60C -- VG-30: 2400-3600 Poise; (4) Ductility at 27C -- minimum 75 cm; (5) Flash Point -- minimum 220C; (6) Specific Gravity -- 1.01-1.05. If softening point < 47C or ductility < 75 cm, the batch fails IS 73:2013 spec.",
        "keywords": ["test report", "coa", "certificate of analysis", "penetration", "softening point", "is 73"]
    },

    # ═══════════════════════════════════════════════════════════
    # SECTION 12: FY 2025-26 BUDGET & MARKET
    # ═══════════════════════════════════════════════════════════

    {
        "section": "fy26",
        "question": "What is India's road infrastructure budget for FY 2025-26?",
        "answer": "MORTH has allocated Rs 11.11 lakh crore for road infrastructure in FY 2025-26 -- the highest ever. PM GatiShakti targets 50 km/day highway construction. This directly drives bitumen demand with an estimated 8.5-10.5 million MT requirement nationally.",
        "keywords": ["budget", "fy26", "fy2026", "morth", "infrastructure", "11.11", "lakh crore"]
    },
    {
        "section": "fy26",
        "question": "What is the expected bitumen demand for FY 2025-26?",
        "answer": "India's bitumen demand for FY 2025-26 is estimated at 8.5-10.5 million MT. Domestic production covers approximately 5 MT, leaving 4-5 MT to be imported. Peak demand months: October-March. Gujarat, Maharashtra, UP, and Rajasthan are the top-consuming states.",
        "keywords": ["demand", "fy26", "2026", "million mt", "import gap", "consumption"]
    },
    {
        "section": "fy26",
        "question": "What is PM GatiShakti and how does it affect bitumen demand?",
        "answer": "PM GatiShakti is a national master plan for multi-modal connectivity targeting 50 km/day highway construction. Higher highway construction pace directly increases bitumen offtake -- every 1 km of 4-lane highway requires 140-160 MT of bitumen.",
        "keywords": ["gatishakti", "gati shakti", "50 km", "highway", "nhai"]
    },
    {
        "section": "fy26",
        "question": "Which states consume the most bitumen in India?",
        "answer": "Top bitumen-consuming states: (1) Uttar Pradesh -- largest road network; (2) Maharashtra -- Mumbai-Nagpur highway; (3) Rajasthan -- large highway projects; (4) Gujarat -- port connectivity, industrial corridors; (5) Madhya Pradesh -- Bharatmala Phase 1.",
        "keywords": ["which state", "top state", "highest demand", "gujarat", "maharashtra", "up"]
    },
    {
        "section": "fy26",
        "question": "What is the NHAI budget for FY 2025-26?",
        "answer": "NHAI has been allocated approximately Rs 1.68 lakh crore for highway construction in FY 2025-26. NHAI is targeting construction of 12,000+ km of national highways. This is the single largest driver of bulk bitumen demand.",
        "keywords": ["nhai", "national highway", "budget", "highway construction", "fy26"]
    },

    # ═══════════════════════════════════════════════════════════
    # SECTION 13: SALES OBJECTION HANDLING
    # ═══════════════════════════════════════════════════════════

    {
        "section": "objections",
        "question": "Customer says: Your price is too high compared to local supplier.",
        "answer": "Response: 'Sir, I understand the comparison. But let me show you the full cost picture. Local suppliers often quote low but hide: (1) GST ITC mismatch risk; (2) Quality risk -- substandard VG grade causes road failure; (3) No e-invoice -- your audit risk increases. Our price includes IS 73-certified material, e-invoice, full ITC chain, and on-time delivery. The net cost to you is actually lower.'",
        "keywords": ["price too high", "expensive", "local supplier cheaper", "competitor cheaper", "objection"]
    },
    {
        "section": "objections",
        "question": "Customer says: I will buy directly from IOCL.",
        "answer": "Response: 'IOCL direct supply is excellent for large captive consumers. For project-based contractors, IOCL requires: (1) Pre-registration (45-90 days); (2) Full advance or bank guarantee; (3) Fixed delivery windows; (4) Minimum lifting quantity. We offer same-day confirmation, flexible quantity from 10 MT, and custom delivery scheduling.'",
        "keywords": ["iocl direct", "buy direct", "refinery direct", "iocl", "bpcl direct", "objection"]
    },
    {
        "section": "objections",
        "question": "Customer says: Import bitumen quality is risky.",
        "answer": "Response: 'This is a valid concern. Our import supply is quality-protected at three levels: (1) Origin lab test -- COA from refinery before loading; (2) Port QC -- independent inspection at Kandla/Mundra by accredited lab; (3) Pre-delivery test -- we can arrange BIS-accredited lab report at your site. All material meets IS 73:2013 specification.'",
        "keywords": ["import quality", "risky", "bad quality", "is 73", "certificate", "objection"]
    },
    {
        "section": "objections",
        "question": "Customer says: I will wait for bitumen prices to fall.",
        "answer": "Response: 'Bitumen prices are linked to Brent crude and USD/INR -- two factors moving against a price drop. Our forecast model shows prices stable-to-upward for the next 3-4 months. Additionally, for every 10 days of delay, a typical highway project loses 0.8-1.2 km of laying opportunity. Shall I show you the forecast data?'",
        "keywords": ["wait", "price will fall", "prices drop", "hold off", "delay purchase", "objection"]
    },
    {
        "section": "objections",
        "question": "Customer says: Other dealers give 60-day credit.",
        "answer": "Response: 'Our standard terms are 30 days for established accounts. For 45+ day credit, we require: (1) 6-month purchase history; (2) Credit limit approval (3-5 days); (3) PDC or bank guarantee. Dealers offering 60-day credit typically build 2-3% higher margin. Net-net, you may pay more. Shall we calculate the effective cost comparison?'",
        "keywords": ["60 day credit", "payment terms", "credit period", "other dealers", "objection"]
    },
    {
        "section": "objections",
        "question": "Customer says: Why 100% advance payment?",
        "answer": "Response: 'For first-time orders, 100% advance protects both parties. For repeat customers with good history, we move to 50% advance + 50% on delivery, then to credit terms. Think of it as building a banking relationship -- creditworthiness is established through transaction history. We want to grow with you.'",
        "keywords": ["advance payment", "100% advance", "why advance", "upfront payment", "objection"]
    },
]

# ============ CHATBOT FUNCTIONS ============

import re
from difflib import SequenceMatcher

def normalize_text(text):
    """Normalize text for matching."""
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    return text

def calculate_similarity(text1, text2):
    """Calculate similarity between two texts."""
    return SequenceMatcher(None, normalize_text(text1), normalize_text(text2)).ratio()

def find_best_match(user_query, min_similarity=0.3):
    """Find the best matching Q&A for a user query."""
    user_query_normalized = normalize_text(user_query)
    best_match = None
    best_score = 0

    for qa in KNOWLEDGE_BASE:
        # Check question similarity
        q_similarity = calculate_similarity(user_query, qa['question'])

        # Check keyword matches
        keyword_score = 0
        for keyword in qa.get('keywords', []):
            if keyword.lower() in user_query_normalized:
                keyword_score += 0.2

        # Combined score
        total_score = q_similarity + keyword_score

        if total_score > best_score:
            best_score = total_score
            best_match = qa

    if best_score >= min_similarity:
        return best_match, best_score
    return None, 0

def get_chatbot_response(user_query):
    """Get chatbot response for a user query."""
    match, score = find_best_match(user_query)

    if match:
        return {
            "found": True,
            "answer": match['answer'],
            "question": match['question'],
            "section": TRAINING_SECTIONS.get(match['section'], match['section']),
            "confidence": min(score * 100, 100)
        }
    else:
        return {
            "found": False,
            "answer": "I'm sorry, I couldn't find a specific answer to that question. Please contact our sales team at +91 94482 81224 or email sales.ppsanantams@gmail.com for assistance.",
            "question": user_query,
            "section": "general",
            "confidence": 0
        }

def get_section_questions(section_key):
    """Get all questions for a specific section."""
    return [qa for qa in KNOWLEDGE_BASE if qa['section'] == section_key]

def get_quick_reference(topic):
    """Get quick reference for common topics."""
    quick_refs = {
        "grades": "VG10: Cold regions | VG30: Standard roads (most common) | VG40: Heavy highways",
        "ports": "Kandla (primary), Mundra, Mumbai (200km radius only), Karwar (South)",
        "payment": "Bulk: 100% advance | Drum: After loading (with confirmation)",
        "contact": "+91 94482 81224 | sales.ppsanantams@gmail.com | Vadodara, Gujarat",
        "drums": "180 kg imported drums (vs 154 kg domestic) | VG30 & VG40 available",
        "territory": "North/Central: Drum | South: Bulk | Centre Zones: Drum to decanters"
    }
    return quick_refs.get(topic, None)

# ============ AI ASSISTANT FUNCTIONS ============

def polish_email(rough_text, tone="Professional"):
    """
    Simulates AI Email Polishing.
    In production, this would call OpenAI API.
    """
    templates = {
        "Professional": f"Dear Sir/Madam,\n\n{rough_text}\n\nWe look forward to your positive response.\n\nBest Regards,\nPPS Anantams Sales Team",
        "Urgent": f"URGENT ATTENTION REQUIRED\n\nDear Partner,\n\n{rough_text}\n\nPlease treat this as a priority.\n\nRegards,\nPPS Anantams",
        "Friendly": f"Hi Team,\n\nHope you're doing well!\n\n{rough_text}\n\nThanks & Regards,\n[Your Name]"
    }
    # Simple wrapper for now
    return templates.get(tone, rough_text)

def generate_custom_reply(customer_name, topic, key_points):
    """
    Generates a contextual reply based on topic.
    """
    if topic == "Price Negotiation":
        return f"Dear {customer_name},\n\nThank you for your offer. However, our current price of {key_points} is the best possible workable rate given the current international crude prices. We ensure premium quality and timely delivery which cheaper alternatives may not guarantee."
    elif topic == "Supply Delay":
        return f"Dear {customer_name},\n\nWe apologize for the delay in the vehicle reaching your site. This is due to {key_points}. We are constantly tracking the vehicle and it should reach by [Time]."
    return f"Dear {customer_name},\n\nRegarding {topic}: {key_points}\n\nLet us know how to proceed."

# ============ TELECALLING SCRIPTS ============

TELECALLING_SCRIPTS = {
    "intro": """
Hello, this is [Your Name] calling from PPS Anantams Corporation, Vadodara.
We are importers and suppliers of VG-grade bitumen.
I wanted to briefly introduce our company - is this a good time for 2 minutes?
""",

    "credibility": """
Sir, we have 24+ years of combined experience in bitumen trading.
We import through Kandla and Mumbai ports and have regular supplies to major contractors in your state.
We are a debt-free, 100% banking transaction company with zero complaints.
""",

    "qualification": """
Before I share pricing, may I know:
1. What is your approximate monthly requirement in MT?
2. Do you have a storage tank or work with a decanter?
3. Are you using this for your own projects or trading?
""",

    "closing": """
Based on our discussion, I can share today's workable price for your location.
If it matches your expectation, we can plan a trial supply.
Shall I send you the rate card on WhatsApp?
""",

    "objection_price": """
I understand price is important.
Actually, base prices are similar across India - the difference comes from logistics costs.
Let me calculate the exact landed cost for your location -
sometimes Kandla route works better than Mumbai even for your area.
""",

    "objection_credit": """
We operate on advance payment basis which allows us to offer competitive rates.
Many large contractors prefer this as it ensures clean documentation and stable supply.
For the first order, if you're comfortable, we can start with a smaller quantity as trial.
""",

    "follow_up": """
Hello Sir, this is [Name] from PPS Anantams following up on our bitumen discussion.
I wanted to check if you've had a chance to review the rates I shared.
Is there any upcoming requirement we can support?
"""
}

def get_telecalling_script(scenario):
    """Get telecalling script for a scenario."""
    return TELECALLING_SCRIPTS.get(scenario, TELECALLING_SCRIPTS['intro'])

# ============ EXPORT FOR DASHBOARD ============

def get_all_sections():
    """Get all training sections."""
    return TRAINING_SECTIONS

def get_knowledge_count():
    """Get count of Q&A pairs."""
    return len(KNOWLEDGE_BASE)
