"""
PPS Anantam — Purchase Advisor Engine v1.0
==========================================
Computes a weighted urgency index from 6 real-time sub-signals
and maps it to an actionable recommendation.

Sub-signals:
  1. price_trend     — crude/bitumen price direction
  2. demand_season   — seasonal construction demand
  3. inventory_level — current stock position
  4. crude_momentum  — crude oil momentum (RSI-like)
  5. fx_pressure     — USD/INR pressure on import cost
  6. supply_risk     — supply chain disruption risk
"""

import datetime
import json
from pathlib import Path

BASE = Path(__file__).parent
PERSIST_FILE = BASE / "tbl_purchase_advisor.json"


class PurchaseAdvisorEngine:
    """Compute procurement urgency from live market signals."""

    def __init__(self):
        self._weights = {
            "price_trend": 0.25,
            "demand_season": 0.20,
            "inventory_level": 0.15,
            "crude_momentum": 0.20,
            "fx_pressure": 0.10,
            "supply_risk": 0.10,
        }
        # Override weights from settings if available
        try:
            from settings_engine import get as sg
            w = sg("purchase_advisor_urgency_weights")
            if isinstance(w, dict) and len(w) == 6:
                self._weights = w
        except Exception:
            pass

    # ── Sub-signal computations ──────────────────────────────────────────────

    def _price_trend_signal(self, signals, crude_data):
        """0 = prices falling fast (wait), 100 = rising fast (buy now)."""
        if signals:
            crude_sig = signals.get("crude_market", {})
            d = crude_sig.get("direction", "SIDEWAYS")
            if d == "UP":
                return 85
            elif d == "DOWN":
                return 25
            return 50
        if crude_data and len(crude_data) >= 7:
            prices = [float(r.get("price", 0)) for r in crude_data if r.get("price")]
            if len(prices) >= 7:
                recent = sum(prices[-3:]) / 3
                older = sum(prices[-7:-3]) / max(len(prices[-7:-3]), 1)
                if older > 0:
                    change_pct = ((recent - older) / older) * 100
                    return max(0, min(100, 50 + change_pct * 10))
        return 50

    def _demand_season_signal(self):
        """0 = deep off-season, 100 = peak construction season."""
        month = datetime.date.today().month
        season_map = {
            1: 90, 2: 95, 3: 100, 4: 85, 5: 70,
            6: 30, 7: 15, 8: 15, 9: 30,
            10: 80, 11: 90, 12: 95,
        }
        return season_map.get(month, 50)

    def _inventory_signal(self):
        """0 = well stocked, 100 = critically low. Heuristic from deals."""
        try:
            from database import _get_conn
            conn = _get_conn()
            row = conn.execute(
                "SELECT COUNT(*) FROM deals WHERE status='pending'"
            ).fetchone()
            conn.close()
            pending = row[0] if row else 0
            # More pending orders = lower inventory → higher urgency
            return max(0, min(100, 40 + pending * 10))
        except Exception:
            return 50

    def _crude_momentum_signal(self, signals, crude_data):
        """RSI-like momentum. 0 = oversold (wait), 100 = overbought (buy now before more rise)."""
        if signals:
            crude_sig = signals.get("crude_market", {})
            vol = crude_sig.get("volatility", "MEDIUM")
            d = crude_sig.get("direction", "SIDEWAYS")
            base = 50
            if d == "UP":
                base = 70
            elif d == "DOWN":
                base = 30
            if vol == "HIGH":
                base += 15
            return max(0, min(100, base))
        if crude_data and len(crude_data) >= 14:
            prices = [float(r.get("price", 0)) for r in crude_data if r.get("price")]
            if len(prices) >= 14:
                gains = sum(max(0, prices[i] - prices[i-1]) for i in range(1, len(prices)))
                losses = sum(max(0, prices[i-1] - prices[i]) for i in range(1, len(prices)))
                if losses == 0:
                    return 90
                rs = gains / losses
                rsi = 100 - (100 / (1 + rs))
                return max(0, min(100, int(rsi)))
        return 50

    def _fx_pressure_signal(self, signals):
        """0 = INR strong (low cost), 100 = INR weak (high cost → buy before worse)."""
        if signals:
            cs = signals.get("currency", {})
            p = cs.get("pressure", "MEDIUM")
            return {"HIGH": 80, "MEDIUM": 50, "LOW": 20}.get(p, 50)
        return 50

    def _supply_risk_signal(self, signals):
        """0 = ample supply, 100 = critical shortage."""
        if signals:
            port_sig = signals.get("ports", {})
            news_sig = signals.get("news", {})
            pr = {"HIGH": 80, "MEDIUM": 45, "LOW": 15}.get(
                port_sig.get("port_risk", "LOW"), 30)
            nr = {"HIGH": 70, "MEDIUM": 40, "LOW": 10}.get(
                news_sig.get("supply_risk", "LOW"), 20)
            return max(0, min(100, (pr + nr) // 2))
        return 30

    # ── Main computation ─────────────────────────────────────────────────────

    def compute_urgency_index(self):
        """Compute the weighted urgency index (0-100) and recommendation."""
        # Load market signals
        signals = {}
        try:
            from market_intelligence_engine import MarketIntelligenceEngine
            eng = MarketIntelligenceEngine()
            signals = eng.compute_all_signals()
            if signals.get("master", {}).get("status") != "OK":
                signals = {}
        except Exception:
            pass

        # Load crude data
        crude_data = []
        try:
            from api_hub_engine import NormalizedTables
            crude_data = NormalizedTables.crude_prices(30)
        except Exception:
            pass

        # Compute all 6 sub-signals
        sub = {
            "price_trend": self._price_trend_signal(signals, crude_data),
            "demand_season": self._demand_season_signal(),
            "inventory_level": self._inventory_signal(),
            "crude_momentum": self._crude_momentum_signal(signals, crude_data),
            "fx_pressure": self._fx_pressure_signal(signals),
            "supply_risk": self._supply_risk_signal(signals),
        }

        # Weighted composite
        urgency = sum(self._weights[k] * sub[k] for k in self._weights)
        urgency = max(0, min(100, round(urgency)))

        # Recommendation
        if urgency >= 80:
            rec = "BUY NOW"
            rec_detail = "All signals point to immediate procurement. Lock prices today."
            rec_color = "#ef4444"
        elif urgency >= 60:
            rec = "PRE-BUY"
            rec_detail = "Favorable window — start procurement within 7 days."
            rec_color = "#f59e0b"
        elif urgency >= 40:
            rec = "HOLD"
            rec_detail = "Market is neutral — monitor daily and await better entry."
            rec_color = "#3b82f6"
        else:
            wait_days = max(7, int((40 - urgency) * 0.5) + 7)
            rec = f"WAIT {wait_days} DAYS"
            rec_detail = f"Market conditions unfavorable — reassess in {wait_days} days."
            rec_color = "#22c55e"

        # Stock recommendation
        month = datetime.date.today().month
        is_peak = month in [10, 11, 12, 1, 2, 3]
        if urgency >= 70 and is_peak:
            stock_rec = "Stock 20+ days of inventory — peak season + rising costs"
        elif urgency >= 70:
            stock_rec = "Stock 15 days — urgency high despite off-season"
        elif is_peak:
            stock_rec = "Stock 10-15 days — peak season but costs manageable"
        else:
            stock_rec = "Maintain 7-day stock — off-season with stable costs"

        result = {
            "urgency_index": urgency,
            "recommendation": rec,
            "recommendation_detail": rec_detail,
            "recommendation_color": rec_color,
            "sub_signals": sub,
            "weights": dict(self._weights),
            "stock_recommendation": stock_rec,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M IST"),
            "has_live_data": bool(signals or crude_data),
        }

        # Persist
        self._persist(result)
        return result

    def _persist(self, result):
        """Save latest result + append to history."""
        try:
            history = []
            if PERSIST_FILE.exists():
                with open(PERSIST_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    history = data.get("history", [])
            history.append({
                "timestamp": result["timestamp"],
                "urgency_index": result["urgency_index"],
                "recommendation": result["recommendation"],
            })
            # Keep last 90 entries
            history = history[-90:]
            with open(PERSIST_FILE, "w", encoding="utf-8") as f:
                json.dump({"latest": result, "history": history}, f,
                          indent=2, ensure_ascii=False)
        except Exception:
            pass

    def get_history(self):
        """Load historical urgency data."""
        try:
            if PERSIST_FILE.exists():
                with open(PERSIST_FILE, "r", encoding="utf-8") as f:
                    return json.load(f).get("history", [])
        except Exception:
            pass
        return []
