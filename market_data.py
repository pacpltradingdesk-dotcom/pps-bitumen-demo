import datetime
import random
import yfinance as yf
from api_manager import fetch_api_data

def format_change(chg_7d):
    color = "green" if chg_7d >= 0 else "red"
    return f"{chg_7d:+.2f}%", color

def get_live_market_data():
    """
    Fetches LIVE market data using the robust API Manager data layer.
    Includes caching, fallbacks, and multi-provider reliability.
    """
    data = {}
    
    # 1. Brent Crude
    brent_data = fetch_api_data("brent")
    if brent_data and 'current' in brent_data:
        curr = float(brent_data['current'])
        hist = float(brent_data.get('history_7d', curr))
        chg = ((curr - hist) / hist) * 100 if hist else 0.0
        chg_str, color = format_change(chg)
        data['brent'] = {"value": f"${curr:.2f}", "value_7d": f"${hist:.2f}", "change": chg_str, "color": color}
    else:
        data['brent'] = {"value": "N/A", "value_7d": "N/A", "change": "0.00%", "color": "grey"}

    # 2. WTI Crude
    wti_data = fetch_api_data("wti")
    if wti_data and 'current' in wti_data:
        curr = float(wti_data['current'])
        hist = float(wti_data.get('history_7d', curr))
        chg = ((curr - hist) / hist) * 100 if hist else 0.0
        chg_str, color = format_change(chg)
        data['wti'] = {"value": f"${curr:.2f}", "value_7d": f"${hist:.2f}", "change": chg_str, "color": color}
    else:
        data['wti'] = {"value": "N/A", "value_7d": "N/A", "change": "0.00%", "color": "grey"}

    # 3. USD/INR
    usdinr_data = fetch_api_data("usdinr")
    if usdinr_data and 'current' in usdinr_data:
        curr = float(usdinr_data['current'])
        hist = float(usdinr_data.get('history_7d', curr))
        chg = ((curr - hist) / hist) * 100 if hist else 0.0
        chg_str, color = format_change(chg)
        data['usdinr'] = {"value": f"{curr:.2f}", "value_7d": f"{hist:.2f}", "change": chg_str, "color": color}
    else:
        data['usdinr'] = {"value": "N/A", "value_7d": "N/A", "change": "0.00%", "color": "grey"}

    # 4. DXY
    dxy_data = fetch_api_data("dxy")
    if dxy_data and 'current' in dxy_data:
        curr = float(dxy_data['current'])
        hist = float(dxy_data.get('history_7d', curr))
        chg = ((curr - hist) / hist) * 100 if hist else 0.0
        chg_str, color = format_change(chg)
        data['dxy'] = {"value": f"{curr:.2f}", "value_7d": f"{hist:.2f}", "change": chg_str, "color": color}
    else:
        data['dxy'] = {"value": "N/A", "value_7d": "N/A", "change": "0.00%", "color": "grey"}
        
    # 5. Timestamp
    time_data = fetch_api_data("current_time")
    if time_data and 'current' in time_data:
        data['timestamp'] = f"{time_data['current']} IST"
    else:
        data['timestamp'] = datetime.datetime.now().strftime("%H:%M IST")

    return data

def get_simulated_data():
    """Fallback if internet is completely down. Baselines updated Q1 2026."""
    brent  = 75.50 + random.uniform(-0.5, 0.5)
    wti    = 71.50 + random.uniform(-0.5, 0.5)
    usdinr = 86.80 + random.uniform(-0.15, 0.15)
    dxy    = 104.2

    brent_7d  = brent  / 1.008
    wti_7d    = wti    / 0.994
    usdinr_7d = usdinr / 1.003

    chg_b = f"{((brent  - brent_7d)  / brent_7d  * 100):+.2f}%"
    chg_w = f"{((wti    - wti_7d)    / wti_7d    * 100):+.2f}%"
    chg_fx = f"{((usdinr - usdinr_7d) / usdinr_7d * 100):+.2f}%"

    return {
        "brent":  {"value": f"${brent:.2f}",   "value_7d": f"${brent_7d:.2f}",   "change": chg_b,  "color": "green" if brent  > brent_7d  else "red"},
        "wti":    {"value": f"${wti:.2f}",     "value_7d": f"${wti_7d:.2f}",     "change": chg_w,  "color": "green" if wti    > wti_7d    else "red"},
        "usdinr": {"value": f"{usdinr:.2f}",   "value_7d": f"{usdinr_7d:.2f}",   "change": chg_fx, "color": "green" if usdinr > usdinr_7d else "red"},
        "dxy":    {"value": f"{dxy:.2f}",      "value_7d": "104.20",             "change": "0.0%", "color": "grey"},
        "timestamp": datetime.datetime.now().strftime("%H:%M IST (Offline)"),
    }
