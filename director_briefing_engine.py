"""
PPS Anantam — Director Daily Intelligence Center v1.0
======================================================
Generates comprehensive daily briefing for the company director.
Aggregates data from all engines into a structured briefing dict.

Sections:
  - Yesterday Summary (deals, enquiries, communications, market, payments)
  - Today's Actions (calls, negotiations, quotes, followups)
  - 15-Day Outlook (demand score, price direction, stock strategy)
  - Sparkline Data (7-day trends)
  - Opportunities & Alerts
"""

import json
import datetime
from pathlib import Path
from typing import Dict, List

import pytz

IST = pytz.timezone("Asia/Kolkata")
BASE = Path(__file__).parent


def _load_json(path, default=None):
    if default is None:
        default = []
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError):
        pass
    return default


def _fmt_inr(amount) -> str:
    """Format INR with Indian comma system."""
    if amount is None:
        return "N/A"
    try:
        amount = float(amount)
        if amount < 0:
            return f"-{_fmt_inr(-amount)}"
        integer_part = str(int(amount))
        if len(integer_part) <= 3:
            return f"\u20b9{integer_part}"
        last3 = integer_part[-3:]
        remaining = integer_part[:-3]
        groups = []
        while remaining:
            groups.insert(0, remaining[-2:])
            remaining = remaining[:-2]
        return f"\u20b9{','.join(groups)},{last3}"
    except (ValueError, TypeError):
        return str(amount)


class DirectorBriefingEngine:
    """Generates the complete daily director briefing."""

    def __init__(self):
        from settings_engine import load_settings
        self.settings = load_settings()

    def generate_briefing(self, target_date=None) -> dict:
        """Master method — produces the complete daily briefing."""
        now = datetime.datetime.now(IST)
        if target_date is None:
            target_date = now.strftime("%Y-%m-%d")

        hour = now.hour
        if hour < 12:
            greeting = "Good Morning"
        elif hour < 17:
            greeting = "Good Afternoon"
        else:
            greeting = "Good Evening"

        briefing = {
            "greeting": greeting,
            "timestamp": now.strftime("%Y-%m-%d %H:%M IST"),
            "generated_at": now.strftime("%Y-%m-%d %H:%M IST"),
            "briefing_date": target_date,
            "yesterday_summary": self.get_yesterday_summary(target_date),
            "today_actions": self.get_today_actions(),
            "fifteen_day_outlook": self._get_outlook(),
            "sparklines": self.get_sparkline_data(),
            "opportunities": self._get_recent_opportunities(),
            "alerts": self._get_active_alerts(),
            "market_signals": self._get_market_signals(),
        }
        return briefing

    def _get_market_signals(self) -> dict:
        """Get master market intelligence signal for briefing."""
        try:
            from market_intelligence_engine import get_master_signal
            return get_master_signal()
        except Exception:
            return {
                "market_direction": "N/A",
                "confidence": 0,
                "demand_outlook": "N/A",
                "risk_level": "N/A",
                "recommended_action": "Market intelligence engine unavailable",
            }

    def get_yesterday_summary(self, reference_date: str = None) -> dict:
        """Aggregate yesterday's deal, communication, market, and payment data."""
        summary = {
            "deals_closed": {"count": 0, "total_value": 0, "avg_margin": 0},
            "enquiries_received": {"count": 0, "top_customers": []},
            "communications": {"whatsapp": 0, "email": 0, "calls": 0, "total": 0},
            "market_movement": {
                "brent_pct": 0, "brent_price": 0,
                "fx_pct": 0, "fx_rate": 0,
            },
            "payments_received": {"amount": 0, "from_customers": []},
            "outstanding_collections": {"total": 0, "overdue_count": 0},
        }

        # Deals summary
        try:
            from database import get_all_deals
            deals = get_all_deals()
            yesterday = (datetime.datetime.now(IST) - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
            recent_deals = [d for d in deals
                            if (d.get("created_at") or "")[:10] == yesterday
                            or (d.get("po_date") or "")[:10] == yesterday]
            summary["deals_closed"]["count"] = len(recent_deals)
            total_val = sum(d.get("total_value_inr", 0) or 0 for d in recent_deals)
            summary["deals_closed"]["total_value"] = total_val
            margins = [d.get("margin_pct", 0) or 0 for d in recent_deals if d.get("margin_pct")]
            summary["deals_closed"]["avg_margin"] = round(sum(margins) / max(len(margins), 1), 1)
        except Exception:
            pass

        # Communications count
        try:
            comm_log = _load_json(BASE / "communication_log.json", [])
            yesterday_str = (datetime.datetime.now(IST) - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
            for c in comm_log:
                sent_at = c.get("sent_at", "")
                if yesterday_str in sent_at:
                    ch = c.get("channel", "").lower()
                    if "whatsapp" in ch:
                        summary["communications"]["whatsapp"] += 1
                    elif "email" in ch:
                        summary["communications"]["email"] += 1
                    elif "call" in ch:
                        summary["communications"]["calls"] += 1
                    summary["communications"]["total"] += 1
        except Exception:
            pass

        # Market movement
        try:
            crude = _load_json(BASE / "tbl_crude_prices.json", [])
            brent = [r for r in crude if r.get("benchmark") == "Brent" and r.get("price")]
            if len(brent) >= 2:
                latest = brent[-1]["price"]
                prev = brent[-2]["price"]
                summary["market_movement"]["brent_price"] = latest
                if prev > 0:
                    summary["market_movement"]["brent_pct"] = round(
                        (latest - prev) / prev * 100, 2)

            fx = _load_json(BASE / "tbl_fx_rates.json", [])
            usd_inr = [r for r in fx if "USD" in str(r.get("from_currency", "")) and r.get("rate")]
            if len(usd_inr) >= 2:
                latest_fx = usd_inr[-1]["rate"]
                prev_fx = usd_inr[-2]["rate"]
                summary["market_movement"]["fx_rate"] = latest_fx
                if prev_fx > 0:
                    summary["market_movement"]["fx_pct"] = round(
                        (latest_fx - prev_fx) / prev_fx * 100, 2)
        except Exception:
            pass

        # Outstanding collections
        try:
            from database import get_dashboard_stats
            stats = get_dashboard_stats()
            summary["outstanding_collections"]["total"] = stats.get("total_outstanding_inr", 0)
        except Exception:
            pass

        return summary

    def get_today_actions(self) -> dict:
        """Priority-ranked action list for today."""
        actions = {
            "buyers_to_call": [],
            "suppliers_to_negotiate": [],
            "pending_quotes": [],
            "followups_due": [],
            "payments_expected": [],
            "dispatches_scheduled": [],
        }

        # CRM targets
        try:
            from crm_engine import IntelligentCRM
            crm = IntelligentCRM()
            targets = crm.get_todays_targets()
            actions["buyers_to_call"] = targets.get("buyers_to_call", [])[:5]
            actions["suppliers_to_negotiate"] = targets.get("suppliers_to_negotiate", [])[:3]
            actions["followups_due"] = targets.get("followups_due", [])[:5]
        except Exception:
            pass

        # Pending quotes from deals pipeline
        try:
            from database import get_deals_by_stage
            enquiries = get_deals_by_stage("enquiry")
            actions["pending_quotes"] = [
                {"customer": d.get("destination", ""),
                 "grade": d.get("grade", ""),
                 "qty": d.get("quantity_mt", 0),
                 "deal_id": d.get("id")}
                for d in enquiries[:5]
            ]
        except Exception:
            pass

        return actions

    def get_sparkline_data(self, days: int = 7) -> dict:
        """7-day sparkline data for Brent, VG30, and FX."""
        sparklines = {
            "brent": [],
            "fx": [],
        }

        try:
            crude = _load_json(BASE / "tbl_crude_prices.json", [])
            brent = [r.get("price") for r in crude
                     if r.get("benchmark") == "Brent" and r.get("price")]
            sparklines["brent"] = brent[-days:] if len(brent) >= days else brent
        except Exception:
            pass

        try:
            fx = _load_json(BASE / "tbl_fx_rates.json", [])
            rates = [r.get("rate") for r in fx
                     if "USD" in str(r.get("from_currency", "")) and r.get("rate")]
            sparklines["fx"] = rates[-days:] if len(rates) >= days else rates
        except Exception:
            pass

        return sparklines

    def _get_outlook(self) -> dict:
        """Get 15-day forward strategy outlook."""
        try:
            from forward_strategy_engine import ForwardStrategyEngine
            engine = ForwardStrategyEngine()
            return engine.generate_full_outlook()
        except Exception:
            return {
                "demand_score": {"total_score": 50, "label": "MODERATE", "color": "#c9a84c"},
                "price_direction": {"direction": "STABLE", "confidence_pct": 50, "arrow": "\u25c6"},
                "stock_strategy": {"strategy": "HOLD", "action": "Data insufficient for recommendation",
                                   "rationale": ["Strategy engine unavailable"]},
                "generated_at": datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M IST"),
            }

    def _get_recent_opportunities(self) -> list:
        """Get recent discovered opportunities."""
        try:
            from database import get_all_opportunities
            opps = get_all_opportunities(status="new")
            return opps[:5]
        except Exception:
            return []

    def _get_active_alerts(self) -> list:
        """Get active unresolved alerts."""
        try:
            from database import get_alerts
            return get_alerts(status="new", limit=10)
        except Exception:
            return []

    def save_briefing_to_db(self, briefing: dict) -> int:
        """Store briefing in director_briefings table."""
        try:
            from database import insert_director_briefing
            return insert_director_briefing({
                "briefing_date": briefing.get("briefing_date",
                    datetime.datetime.now(IST).strftime("%Y-%m-%d")),
                "generated_at": briefing.get("timestamp", ""),
                "briefing_data": json.dumps(briefing, default=str),
            })
        except Exception:
            return -1

    def format_whatsapp_summary(self, briefing: dict) -> str:
        """Format briefing as PPS Daily Brief WhatsApp message."""
        yesterday = briefing.get("yesterday_summary", {})
        actions = briefing.get("today_actions", {})
        outlook = briefing.get("fifteen_day_outlook", {})

        market = yesterday.get("market_movement", {})
        strategy = outlook.get("stock_strategy", {})
        demand = outlook.get("demand_score", {})
        price_dir = outlook.get("price_direction", {})
        deals = yesterday.get("deals_closed", {})
        comms = yesterday.get("communications", {})
        outstanding = yesterday.get("outstanding_collections", {})

        greeting = briefing.get("greeting", "Good Morning")

        lines = [
            f"*{greeting}, PPS Sir*",
            f"*PACPL Daily Brief \u2014 {briefing.get('timestamp', '')}*",
            "",
            "\U0001F4CA *MARKET STATUS*",
            f"  Brent: ${market.get('brent_price', 'N/A')}/bbl ({market.get('brent_pct', 0):+.1f}%)",
            f"  USD/INR: {market.get('fx_rate', 'N/A')} ({market.get('fx_pct', 0):+.1f}%)",
            "",
            "\U0001F4C8 *15-DAY OUTLOOK*",
            f"  Price: {price_dir.get('arrow', '')} {price_dir.get('direction', 'N/A')} "
            f"({price_dir.get('confidence_pct', 0)}% conf)",
            f"  Demand: {demand.get('total_score', 0)}/100 ({demand.get('label', '')})",
            f"  Strategy: *{strategy.get('strategy', 'N/A')}*",
            f"  {strategy.get('action', '')}",
            "",
            "\U0001F4B0 *YESTERDAY SUMMARY*",
            f"  Deals: {deals.get('count', 0)} "
            f"(Value: {_fmt_inr(deals.get('total_value', 0))})",
            f"  Comms: {comms.get('total', 0)} "
            f"(WA:{comms.get('whatsapp', 0)} | Email:{comms.get('email', 0)} | "
            f"Calls:{comms.get('calls', 0)})",
            f"  Outstanding: {_fmt_inr(outstanding.get('total', 0))}",
            "",
        ]

        # Top 10 to call
        buyers = actions.get("buyers_to_call", [])
        if buyers:
            lines.append("\U0001F4DE *TOP CALLS TODAY*")
            for i, b in enumerate(buyers[:10], 1):
                name = b.get("name", "Unknown")
                city = b.get("city", "")
                reason = b.get("reason", "")
                city_str = f" ({city})" if city else ""
                reason_str = f" \u2014 {reason}" if reason else ""
                lines.append(f"  {i}. {name}{city_str}{reason_str}")
            lines.append("")

        # Followups
        followups = actions.get("followups_due", [])
        if followups:
            lines.append("\U0001F504 *FOLLOWUPS DUE*")
            for fu in followups[:5]:
                name = fu.get("customer_name", fu.get("name", "Unknown"))
                lines.append(f"  \u2022 {name}")
            lines.append("")

        lines.extend([
            "\u2014 *PACPL Agentic AI*",
            "PPS Anantam Corporation Pvt Ltd",
            "\U0001F4F1 +91 7795242424",
        ])
        return "\n".join(lines)
