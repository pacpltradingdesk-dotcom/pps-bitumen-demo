
import random
import datetime

# --- 1. AREA MARKET INSIGHTS ---
# Database of market conditions by City/State
MARKET_INSIGHTS_DB = {
    "Warangal": {
        "demand": "High",
        "activity": "🔥 NHAI Expansion (NH-163)",
        "issues": "Traffic restrictions 10AM-4PM",
        "price_range": "42,500 - 43,200",
        "pitch": "Sir, Warangal side lifting is very high due to NHAI work. Trucks are short, better to book slot today."
    },
    "Hyderabad": {
        "demand": "Medium",
        "activity": "Outer Ring Road Maintenance",
        "issues": "No heavy entry before 11 PM",
        "price_range": "41,800 - 42,400",
        "pitch": "Hyderabad demand is steady. We have vehicles returning from Vijayawada that can give you a good rate."
    },
    "Bhopal": {
        "demand": "Low",
        "activity": "State PWD Patchwork",
        "issues": "Toll Naka delays common",
        "price_range": "44,000 - 44,800",
        "pitch": "Market is slow in MP right now, we can push for a discount if you take full tanker."
    },
    "Guwahati": {
        "demand": "High",
        "activity": "Border Road Org (BRO) Projects",
        "issues": "Landslide Risk / 4-Day Transit",
        "price_range": "48,000 - 49,500",
        "pitch": "North East routes are tricky with rains starting soon. Stock up now to avoid stock-out."
    },
    "Pune": {
        "demand": "High",
        "activity": "Metro & Flyover Works",
        "issues": "Strict police checking for papers",
        "price_range": "40,500 - 41,200",
        "pitch": "Pune checks are strict. Our tankers have 100% clean papers, so zero detention risk."
    }
}

# --- 2. COMPETITOR BENCHMARKS (Silent Comparison) ---
# What "They" usually do vs "Us"
COMPETITOR_INTEL = {
    "South": {
        "competitor_price": "Usually ₹200 lower",
        "their_weakness": "Uses open-market unverified tankers (Theft Risk).",
        "our_strength": "GPS-Tracked Dedicated Fleet.",
        "script": "Others might save you ₹200, but do they give GPS tracking? We ensure 100% quantity reaches your site."
    },
    "West": {
        "competitor_price": "Comparable",
        "their_weakness": "Delays of 24-48 hours common.",
        "our_strength": "Guaranteed 12-hour Dispatch.",
        "script": "Rates are matched. But I can give you a loading slip within 2 hours. Can they confirm that?"
    },
    "North": {
        "competitor_price": "Aggressive / Low",
        "their_weakness": "Old stock / Heating issues.",
        "our_strength": "Fresh Refinery Load.",
        "script": "Sir, low rates in North often mean re-heated material. Ours is fresh from Panipat/Mathura refinery."
    }
}

# --- 3. DELIVERY & RISK LOGIC ---
def get_delivery_confidence(source, destination, distance):
    """Calculates confidence scores based on route logic."""
    
    # Base Scores
    dispatch_prob = 95
    delay_risk = 5
    reliability = 4.8
    
    # Logic Adjustments
    if distance > 1000:
        dispatch_prob -= 10 # Long haul has variability
        delay_risk += 20
        reliability = 4.2
        
    if "Guwahati" in destination or "Silchar" in destination:
        dispatch_prob -= 15
        delay_risk += 40
        reliability = 3.8 # Tough terrain
        
    if "Mumbai" in source and distance < 300:
        dispatch_prob = 99
        delay_risk = 1
        reliability = 5.0 # Local strength
        
    return {
        "dispatch_prob": dispatch_prob,
        "delay_risk": delay_risk,
        "reliability_score": reliability,
        "success_rate": f"{random.randint(92, 99)}%" # Mock historical data
    }

# --- 4. FOLLOW-UP INTELLIGENCE ---
def get_followup_strategy(quote_price, margin, days_passed=1):
    if days_passed == 1:
        return {
            "action": "Urgency Follow-up",
            "script": "Sir, refinery prices might increase tomorrow. Can we lock this order today?"
        }
    elif days_passed == 3:
        return {
            "action": "Value Reinforcement",
            "script": "Just checking in. I checked with dispatch, we have a slot available for immediate loading if you confirm."
        }
    else:
        return {
            "action": "Re-Quote / Market Update",
            "script": "Market has moved. Let me send you a refreshed offer for this week."
        }

# --- 5. DATA INGESTION ---
def get_area_insight(city):
    """Get insight for a city, or return generic default."""
    return MARKET_INSIGHTS_DB.get(city, {
        "demand": "Steady",
        "activity": "General Maintenance",
        "issues": "Standard Transit Time",
        "price_range": "Market Rate",
        "pitch": "Demand is stable. Good time to buy."
    })

def get_competitor_intel(region="South"):
    return COMPETITOR_INTEL.get(region, COMPETITOR_INTEL["South"])
