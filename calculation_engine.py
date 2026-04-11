"""
PPS Anantam — Calculation Engine v1.0
======================================
Central engine for all pricing, landed cost, margin, and offer calculations.
Used by: Sales Workspace, Feasibility, Import Cost Model, Opportunity Engine.

Key Formulas:
  International Landed = FOB(INR) + Freight(INR) + Insurance + CIF + Port + CHA + Handling + Customs + GST
  Domestic Landed = (Base x 1.18 GST) + (Distance x Rate/km)
  Decanter Landed = (Drum x 1.18) + Drum_Transport + Rs.500 conversion + Local_Transport
  Offer Tiers: Aggressive (min margin), Balanced (1.6x), Premium (2.4x)

Author : PPS Anantam Engineering
Version: 1.0
"""

from __future__ import annotations

import datetime
import json
import math
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# External project imports (with safe fallbacks)
# ---------------------------------------------------------------------------

try:
    from settings_engine import load_settings
except ImportError:
    def load_settings() -> dict:
        """Fallback if settings_engine is not available."""
        return {
            "margin_min_per_mt": 500,
            "margin_balanced_multiplier": 1.6,
            "margin_premium_multiplier": 2.4,
            "gst_rate_pct": 18,
            "customs_duty_pct": 2.5,
            "bulk_rate_per_km": 5.5,
            "drum_rate_per_km": 6.0,
            "decanter_conversion_cost": 500,
            "default_fob_usd": 380,
            "default_freight_usd": 35,
            "default_insurance_pct": 0.5,
            "default_switch_bl_usd": 2,
            "default_port_charges_inr": 10000,
            "default_cha_per_mt": 75,
            "default_handling_per_mt": 100,
            "default_vessel_qty_mt": 5000,
        }

try:
    from distance_matrix import get_distance, DESTINATION_COORDS, SOURCE_COORDS
except ImportError:
    DESTINATION_COORDS = {}
    SOURCE_COORDS = {}

    def get_distance(source: str, destination: str) -> float:
        """Fallback: return a conservative 350 km default."""
        return 350.0

try:
    from source_master import (
        INDIAN_REFINERIES,
        IMPORT_TERMINALS,
        PRIVATE_DECANTERS,
        ALL_SOURCES,
        get_source_category,
        SOURCE_CATEGORIES,
    )
except ImportError:
    # Minimal inline definitions when source_master is unavailable
    INDIAN_REFINERIES = [
        {"name": "IOCL Koyali", "city": "Vadodara", "state": "Gujarat", "category": "INDIAN_REFINERY"},
        {"name": "IOCL Mathura", "city": "Mathura", "state": "Uttar Pradesh", "category": "INDIAN_REFINERY"},
        {"name": "BPCL Mumbai", "city": "Mumbai", "state": "Maharashtra", "category": "INDIAN_REFINERY"},
        {"name": "HPCL Visakhapatnam", "city": "Visakhapatnam", "state": "Andhra Pradesh", "category": "INDIAN_REFINERY"},
        {"name": "CPCL Chennai", "city": "Chennai", "state": "Tamil Nadu", "category": "INDIAN_REFINERY"},
        {"name": "MRPL Mangalore", "city": "Mangalore", "state": "Karnataka", "category": "INDIAN_REFINERY"},
    ]
    IMPORT_TERMINALS = [
        {"name": "Kandla Port Import", "city": "Kandla", "state": "Gujarat", "category": "IMPORT_TERMINAL"},
        {"name": "Mundra Port Import", "city": "Mundra", "state": "Gujarat", "category": "IMPORT_TERMINAL"},
        {"name": "JNPT Import Terminal", "city": "Nhava Sheva", "state": "Maharashtra", "category": "IMPORT_TERMINAL"},
        {"name": "Mangalore Port Import", "city": "Mangalore", "state": "Karnataka", "category": "IMPORT_TERMINAL"},
    ]
    PRIVATE_DECANTERS = [
        {"name": "Ahmedabad Decanter", "city": "Ahmedabad", "state": "Gujarat", "category": "PRIVATE_DECANTER"},
        {"name": "Vadodara Decanter", "city": "Vadodara", "state": "Gujarat", "category": "PRIVATE_DECANTER"},
        {"name": "Pune Decanter", "city": "Pune", "state": "Maharashtra", "category": "PRIVATE_DECANTER"},
        {"name": "Hyderabad Decanter", "city": "Hyderabad", "state": "Telangana", "category": "PRIVATE_DECANTER"},
    ]
    ALL_SOURCES = INDIAN_REFINERIES + IMPORT_TERMINALS + PRIVATE_DECANTERS
    SOURCE_CATEGORIES = {
        "INDIAN_REFINERY": "Indian Refinery (PSU)",
        "IMPORT_TERMINAL": "Import Terminal",
        "PRIVATE_DECANTER": "Private Decanter",
    }

    def get_source_category(name: str) -> str:
        for s in ALL_SOURCES:
            if s["name"] == name:
                return s["category"]
        return "UNKNOWN"

try:
    from india_localization import format_inr, format_inr_short, format_datetime_ist
except ImportError:
    def format_inr(amount, include_symbol: bool = True) -> str:
        """Indian comma system formatter (fallback)."""
        try:
            amount = float(amount)
            is_negative = amount < 0
            amount = abs(amount)
            s = f"{amount:.2f}"
            integer_part, decimal_part = s.split(".")
            last_three = integer_part[-3:]
            other = integer_part[:-3]
            if other:
                last_three = "," + last_three
                grouped = []
                while other:
                    grouped.append(other[-2:])
                    other = other[:-2]
                grouped.reverse()
                other = ",".join(grouped)
                formatted = other + last_three + "." + decimal_part
            else:
                formatted = last_three + "." + decimal_part
            res = f"Rs. {formatted}" if include_symbol else formatted
            return f"-{res}" if is_negative else res
        except (ValueError, TypeError):
            return str(amount)

    def format_inr_short(amount, include_symbol: bool = True) -> str:
        try:
            amount = float(amount)
            if abs(amount) >= 1_00_00_000:
                res = f"{amount / 1_00_00_000:.2f} Cr"
            elif abs(amount) >= 1_00_000:
                res = f"{amount / 1_00_000:.2f} Lakh"
            else:
                return format_inr(amount, include_symbol)
            return f"Rs. {res}" if include_symbol else res
        except (ValueError, TypeError):
            return str(amount)

    def format_datetime_ist(dt=None) -> str:
        if dt is None:
            dt = datetime.datetime.now()
        return dt.strftime("%Y-%m-%d %H:%M IST")


# ---------------------------------------------------------------------------
# Live-prices loader (same logic as feasibility_engine)
# ---------------------------------------------------------------------------

PRICE_CONFIG_FILE = Path(__file__).parent / "live_prices.json"

_DEFAULT_LIVE_PRICES: Dict[str, float] = {
    # PSU Refineries (VG30 Bulk ex-refinery Rs./MT)
    "IOCL Koyali": 42_000, "IOCL Mathura": 42_500, "IOCL Haldia": 41_800,
    "IOCL Barauni": 41_500, "IOCL Panipat": 42_200, "IOCL Digboi": 41_000,
    "IOCL Guwahati": 41_200, "IOCL Bongaigaon": 41_100,
    "BPCL Mumbai": 43_000, "BPCL Kochi": 42_800,
    "HPCL Mumbai": 42_900, "HPCL Visakhapatnam": 41_600,
    "CPCL Chennai": 42_100, "MRPL Mangalore": 41_900,
    "NRL Numaligarh": 41_300, "ONGC Tatipaka": 41_500,
    "HMEL Bhatinda": 42_000, "BORL Bina": 41_700,
    "RIL Jamnagar": 42_400, "Nayara Vadinar": 42_200,
    # Import terminals (landed at port, Rs./MT)
    "Mangalore Port Import": 38_500, "Karwar Port Import": 38_800,
    "Digi Port Import": 39_000, "Taloja Terminal": 39_500,
    "VVF Mumbai Terminal": 39_200, "Kandla Port Import": 38_000,
    "Mundra Port Import": 37_800, "JNPT Import Terminal": 39_800,
    "Haldia Port Import": 39_000, "Ennore Port Import": 39_200,
    # Drum prices
    "DRUM_MUMBAI_VG30": 37_000, "DRUM_KANDLA_VG30": 35_500,
    "DRUM_MUMBAI_VG10": 38_000, "DRUM_KANDLA_VG10": 36_500,
    # Operational constants
    "DECANTER_CONVERSION_COST": 500,
    "BULK_RATE_PER_KM": 5.5,
    "DRUM_RATE_PER_KM": 6.0,
}


def _load_live_prices() -> Dict[str, float]:
    """Merge saved live_prices.json over the default price map."""
    prices = dict(_DEFAULT_LIVE_PRICES)
    if PRICE_CONFIG_FILE.exists():
        try:
            with open(PRICE_CONFIG_FILE, "r", encoding="utf-8") as fh:
                saved = json.load(fh)
            if isinstance(saved, dict):
                prices.update(saved)
        except (json.JSONDecodeError, IOError):
            pass
    return prices


# ---------------------------------------------------------------------------
# Drum-source routing helpers (Kandla vs Mumbai)
# ---------------------------------------------------------------------------

KANDLA_COORDS = (23.03, 70.22)
MUMBAI_COORDS = (19.08, 72.88)

_KANDLA_DRUM_STATES = {
    "Gujarat", "Rajasthan", "Madhya Pradesh", "Uttar Pradesh", "Delhi",
    "Haryana", "Punjab", "Himachal Pradesh", "Jammu & Kashmir",
    "Uttarakhand", "Bihar", "Jharkhand", "Chhattisgarh", "West Bengal",
    "Odisha", "Chandigarh",
}


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance * 1.3 road-factor, in km."""
    R = 6371
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c * 1.3, 0)


def _drum_source_for(destination: str) -> str:
    """Decide whether Kandla or Mumbai serves drums for *destination*."""
    # Attempt state-based lookup first (via distance_matrix or inline map)
    try:
        from distance_matrix import CITY_STATE_MAP
        state = CITY_STATE_MAP.get(destination, "")
    except ImportError:
        state = ""

    if state in _KANDLA_DRUM_STATES:
        return "Kandla"

    # Fallback: pick whichever port is closer
    if destination in DESTINATION_COORDS:
        lat, lon = DESTINATION_COORDS[destination]
        d_k = _haversine(KANDLA_COORDS[0], KANDLA_COORDS[1], lat, lon)
        d_m = _haversine(MUMBAI_COORDS[0], MUMBAI_COORDS[1], lat, lon)
        return "Kandla" if d_k <= d_m else "Mumbai"

    return "Kandla"  # safe default for northern operations


# ===================================================================
#  MAIN CLASS
# ===================================================================

class BitumenCalculationEngine:
    """
    Central calculation engine for the PPS Anantam Bitumen Sales Dashboard.

    Responsibilities
    ----------------
    * International import landed-cost modelling (Iraq / Middle-East to India).
    * Domestic refinery-to-site landed-cost calculation.
    * Decanter (drum-to-bulk conversion) cost modelling.
    * Three-tier offer-price generation (Aggressive / Balanced / Premium).
    * Multi-source ranking for any destination.
    * Deal economics and profitability analysis.
    * Deal risk scoring (credit, delivery, volatility, margin).
    * Sensitivity / what-if analysis on key cost drivers.

    All monetary values are in INR (per MT) unless stated otherwise.
    """

    # ------------------------------------------------------------------
    # 1. Initialisation
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        """
        Load business rules from ``settings_engine`` and live prices from
        ``live_prices.json``.  Every configurable threshold, rate, and
        multiplier is available as an instance attribute for easy override
        in tests or ad-hoc scenarios.
        """
        self._settings: Dict[str, Any] = load_settings()
        self._prices: Dict[str, float] = _load_live_prices()

        # ------ margins & pricing ------
        self.min_margin: float = float(self._settings.get("margin_min_per_mt", 500))
        self.balanced_mult: float = float(self._settings.get("margin_balanced_multiplier", 1.6))
        self.premium_mult: float = float(self._settings.get("margin_premium_multiplier", 2.4))

        # ------ tax rates ------
        self.gst_rate: float = float(self._settings.get("gst_rate_pct", 18)) / 100.0
        self.customs_duty_pct: float = float(self._settings.get("customs_duty_pct", 2.5))
        self.landing_charges_pct: float = float(self._settings.get("landing_charges_pct", 1.0)) / 100.0

        # ------ transport ------
        self.bulk_rate_per_km: float = float(
            self._prices.get("BULK_RATE_PER_KM",
                             self._settings.get("bulk_rate_per_km", 5.5))
        )
        self.drum_rate_per_km: float = float(
            self._prices.get("DRUM_RATE_PER_KM",
                             self._settings.get("drum_rate_per_km", 6.0))
        )
        self.decanter_conversion_cost: float = float(
            self._prices.get("DECANTER_CONVERSION_COST",
                             self._settings.get("decanter_conversion_cost", 500))
        )

        # ------ import cost defaults ------
        self.default_fob_usd: float = float(self._settings.get("default_fob_usd", 380))
        self.default_freight_usd: float = float(self._settings.get("default_freight_usd", 35))
        self.default_insurance_pct: float = float(self._settings.get("default_insurance_pct", 0.5))
        self.default_switch_bl_usd: float = float(self._settings.get("default_switch_bl_usd", 2))
        self.default_port_charges_inr: float = float(self._settings.get("default_port_charges_inr", 10_000))
        self.default_cha_per_mt: float = float(self._settings.get("default_cha_per_mt", 75))
        self.default_handling_per_mt: float = float(self._settings.get("default_handling_per_mt", 100))
        self.default_vessel_qty_mt: float = float(self._settings.get("default_vessel_qty_mt", 5_000))

        # ------ timestamps ------
        self._created_at: str = format_datetime_ist()

    # ------------------------------------------------------------------
    #  Internal helpers
    # ------------------------------------------------------------------

    def _get_base_price(self, source_name: str) -> float:
        """Return ex-refinery / ex-terminal base price for *source_name*."""
        return float(self._prices.get(source_name, 42_000))

    def _safe_distance(self, source: str, destination: str) -> float:
        """
        Return road-distance (km) between *source* and *destination*,
        falling back to 350 km when the pair is missing from the matrix.
        """
        try:
            d = get_distance(source, destination)
            return d if d and d > 0 else 350.0
        except Exception:
            return 350.0

    @staticmethod
    def _round2(value: float) -> float:
        return round(value, 2)

    @staticmethod
    def _build_breakdown(items: List[Tuple[str, float]]) -> List[Dict[str, Any]]:
        """
        Build a display-ready breakdown list.

        Each entry: ``{"label": ..., "amount": ..., "formatted": ...}``
        """
        breakdown: List[Dict[str, Any]] = []
        for label, amt in items:
            breakdown.append({
                "label": label,
                "amount": round(amt, 2),
                "formatted": format_inr(round(amt, 2)),
            })
        return breakdown

    def _now_ist(self) -> str:
        """Current IST timestamp string."""
        return format_datetime_ist()

    # ------------------------------------------------------------------
    # 2.  International Landed Cost
    # ------------------------------------------------------------------

    def calculate_international_landed_cost(self, params: dict) -> dict:
        """
        Full Iraq-to-India import landed cost per MT.

        Parameters (all in ``params`` dict)
        ------------------------------------
        fob_usd           : FOB price in USD/MT
        freight_usd       : Ocean freight in USD/MT
        insurance_pct     : Insurance as % of (FOB+Freight), default 0.5
        usdinr            : USD/INR exchange rate
        vessel_qty_mt     : Vessel cargo quantity in MT, default 5000
        port_charges_inr  : Total port/berthing charges in INR, default 10000
        cha_per_mt        : CHA (clearing/handling agent) in INR/MT, default 75
        handling_per_mt   : Port handling charges in INR/MT, default 100
        customs_duty_pct  : Customs duty as % of CIF, default 2.5
        inland_freight_per_mt : Additional inland freight in INR/MT, default 0
        switch_bl_usd     : Switch Bill of Lading cost in USD/MT, default 2

        Returns
        -------
        dict with every line item, total landed cost, and ``breakdown`` list
        suitable for UI rendering.
        """
        # --- extract with defaults ---
        fob_usd: float = float(params.get("fob_usd", self.default_fob_usd))
        freight_usd: float = float(params.get("freight_usd", self.default_freight_usd))
        insurance_pct: float = float(params.get("insurance_pct", self.default_insurance_pct))
        usdinr: float = float(params.get("usdinr", 83.25))
        vessel_qty_mt: float = float(params.get("vessel_qty_mt", self.default_vessel_qty_mt))
        port_charges_inr: float = float(params.get("port_charges_inr", self.default_port_charges_inr))
        cha_per_mt: float = float(params.get("cha_per_mt", self.default_cha_per_mt))
        handling_per_mt: float = float(params.get("handling_per_mt", self.default_handling_per_mt))
        customs_duty_pct: float = float(params.get("customs_duty_pct", self.customs_duty_pct))
        inland_freight_per_mt: float = float(params.get("inland_freight_per_mt", 0))
        switch_bl_usd: float = float(params.get("switch_bl_usd", self.default_switch_bl_usd))

        # --- calculation ---
        fob_inr = fob_usd * usdinr
        freight_inr = freight_usd * usdinr
        insurance_inr = (fob_inr + freight_inr) * insurance_pct / 100.0
        cif_inr = fob_inr + freight_inr + insurance_inr

        switch_bl_inr = switch_bl_usd * usdinr
        port_per_mt = port_charges_inr / vessel_qty_mt if vessel_qty_mt > 0 else 0
        landing_charges_inr = cif_inr * self.landing_charges_pct
        assessable_value_inr = cif_inr + landing_charges_inr
        customs_inr = assessable_value_inr * customs_duty_pct / 100.0

        subtotal = (
            cif_inr
            + landing_charges_inr
            + switch_bl_inr
            + port_per_mt
            + cha_per_mt
            + handling_per_mt
            + customs_inr
        )
        gst_inr = subtotal * self.gst_rate
        landed_at_port = subtotal + gst_inr
        total_landed = landed_at_port + inland_freight_per_mt

        # Shipment-level aggregates
        total_shipment_value = total_landed * vessel_qty_mt
        total_gst_credit = gst_inr * vessel_qty_mt

        # --- breakdown for display ---
        breakdown_items = [
            ("FOB Price (INR)", fob_inr),
            ("Ocean Freight (INR)", freight_inr),
            ("Insurance", insurance_inr),
            ("CIF Value", cif_inr),
            (f"Landing Charges ({self.landing_charges_pct * 100:.0f}%)", landing_charges_inr),
            ("Assessable Value", assessable_value_inr),
            ("Switch B/L", switch_bl_inr),
            ("Port Charges / MT", port_per_mt),
            ("CHA Charges / MT", cha_per_mt),
            ("Handling / MT", handling_per_mt),
            (f"Customs Duty @ {customs_duty_pct}%", customs_inr),
            ("Subtotal (pre-GST)", subtotal),
            (f"GST @ {self.gst_rate * 100:.0f}%", gst_inr),
            ("Landed at Port", landed_at_port),
            ("Inland Freight / MT", inland_freight_per_mt),
            ("TOTAL LANDED COST", total_landed),
        ]

        return {
            # Individual line items
            "fob_usd": self._round2(fob_usd),
            "freight_usd": self._round2(freight_usd),
            "insurance_pct": insurance_pct,
            "usdinr": self._round2(usdinr),
            "vessel_qty_mt": vessel_qty_mt,
            "fob_inr": self._round2(fob_inr),
            "freight_inr": self._round2(freight_inr),
            "insurance_inr": self._round2(insurance_inr),
            "cif_inr": self._round2(cif_inr),
            "landing_charges_pct": self.landing_charges_pct * 100,
            "landing_charges_inr": self._round2(landing_charges_inr),
            "assessable_value_inr": self._round2(assessable_value_inr),
            "switch_bl_usd": switch_bl_usd,
            "switch_bl_inr": self._round2(switch_bl_inr),
            "port_charges_inr": port_charges_inr,
            "port_per_mt": self._round2(port_per_mt),
            "cha_per_mt": cha_per_mt,
            "handling_per_mt": handling_per_mt,
            "customs_duty_pct": customs_duty_pct,
            "customs_inr": self._round2(customs_inr),
            "subtotal": self._round2(subtotal),
            "gst_rate": self.gst_rate,
            "gst_inr": self._round2(gst_inr),
            "landed_at_port": self._round2(landed_at_port),
            "inland_freight_per_mt": self._round2(inland_freight_per_mt),
            "total_landed": self._round2(total_landed),
            # Formatted for display
            "total_landed_formatted": format_inr(round(total_landed, 2)),
            # Shipment-level
            "total_shipment_value": self._round2(total_shipment_value),
            "total_shipment_value_formatted": format_inr_short(round(total_shipment_value, 2)),
            "total_gst_credit": self._round2(total_gst_credit),
            "total_gst_credit_formatted": format_inr_short(round(total_gst_credit, 2)),
            # Breakdown for UI
            "breakdown": self._build_breakdown(breakdown_items),
            "timestamp": self._now_ist(),
        }

    # ------------------------------------------------------------------
    # 3.  Domestic Landed Cost (Refinery / Import Terminal to Site)
    # ------------------------------------------------------------------

    def calculate_domestic_landed_cost(
        self,
        base_price: float,
        source: str,
        destination: str,
        load_type: str = "Bulk",
        grade: str = "VG30",
    ) -> dict:
        """
        Calculate landed cost from an Indian refinery or import terminal
        to the customer's delivery site.

        Parameters
        ----------
        base_price   : Ex-refinery / ex-terminal price (INR/MT, before GST).
        source       : Source name as listed in ``source_master``.
        destination  : Customer city name as listed in ``distance_matrix``.
        load_type    : ``'Bulk'`` or ``'Drum'``.
        grade        : Bitumen grade, e.g. ``'VG30'``, ``'VG10'``.

        Returns
        -------
        dict with base_price, gst, freight, distance_km, rate_per_km,
        landed_cost, and display breakdown.
        """
        distance_km = self._safe_distance(source, destination)
        rate_per_km = self.bulk_rate_per_km if load_type == "Bulk" else self.drum_rate_per_km

        freight = distance_km * rate_per_km
        gst = base_price * self.gst_rate
        landed_cost = base_price + gst + freight

        breakdown_items = [
            ("Base Price (ex-refinery)", base_price),
            (f"GST @ {self.gst_rate * 100:.0f}%", gst),
            (f"Freight ({distance_km:.0f} km x {format_inr(rate_per_km, include_symbol=False)}/km)", freight),
            ("TOTAL LANDED COST", landed_cost),
        ]

        return {
            "source": source,
            "destination": destination,
            "grade": grade,
            "load_type": load_type,
            "base_price": self._round2(base_price),
            "gst": self._round2(gst),
            "freight": self._round2(freight),
            "distance_km": distance_km,
            "rate_per_km": rate_per_km,
            "landed_cost": self._round2(landed_cost),
            "landed_cost_formatted": format_inr(round(landed_cost, 2)),
            "breakdown": self._build_breakdown(breakdown_items),
            "timestamp": self._now_ist(),
        }

    # ------------------------------------------------------------------
    # 4.  Decanter (Drum-to-Bulk Conversion) Cost
    # ------------------------------------------------------------------

    def calculate_decanter_cost(
        self,
        destination: str,
        grade: str = "VG30",
    ) -> dict:
        """
        Calculate the cost of drum bitumen decanted into bulk near the
        customer site.

        Logic
        -----
        1. Determine whether drums come from Kandla or Mumbai.
        2. Drum base price + 18% GST.
        3. Add drum transport from source port to decanter (near city).
        4. Add Rs.500 conversion cost at the decanter.
        5. Add 30 km local transport from decanter to customer site.

        Returns
        -------
        dict with full cost breakdown.
        """
        drum_source = _drum_source_for(destination)

        if drum_source == "Kandla":
            drum_base = float(self._prices.get(f"DRUM_KANDLA_{grade}", 35_500))
            src_coords = KANDLA_COORDS
            src_label = "Kandla"
        else:
            drum_base = float(self._prices.get(f"DRUM_MUMBAI_{grade}", 37_000))
            src_coords = MUMBAI_COORDS
            src_label = "Mumbai"

        # Distance: drum source port to destination city
        if destination in DESTINATION_COORDS:
            dest_lat, dest_lon = DESTINATION_COORDS[destination]
            drum_transport_km = _haversine(src_coords[0], src_coords[1], dest_lat, dest_lon)
        else:
            drum_transport_km = 500.0  # conservative fallback

        drum_with_gst = drum_base * (1 + self.gst_rate)
        drum_transport = drum_transport_km * self.drum_rate_per_km
        conversion_cost = self.decanter_conversion_cost
        local_km = 30.0
        local_transport = local_km * self.bulk_rate_per_km

        landed_cost = drum_with_gst + drum_transport + conversion_cost + local_transport

        breakdown_items = [
            (f"Drum Base ({src_label}, {grade})", drum_base),
            (f"GST @ {self.gst_rate * 100:.0f}%", drum_with_gst - drum_base),
            (f"Drum Transport ({drum_transport_km:.0f} km)", drum_transport),
            ("Decanter Conversion", conversion_cost),
            (f"Local Transport ({local_km:.0f} km)", local_transport),
            ("TOTAL LANDED (Decanter)", landed_cost),
        ]

        return {
            "source": f"Local Decanter ({destination})",
            "destination": destination,
            "grade": grade,
            "source_type": "PRIVATE_DECANTER",
            "drum_source": src_label,
            "drum_base_price": self._round2(drum_base),
            "drum_with_gst": self._round2(drum_with_gst),
            "drum_transport_km": drum_transport_km,
            "drum_transport": self._round2(drum_transport),
            "conversion_cost": self._round2(conversion_cost),
            "local_km": local_km,
            "local_transport": self._round2(local_transport),
            "landed_cost": self._round2(landed_cost),
            "landed_cost_formatted": format_inr(round(landed_cost, 2)),
            "breakdown": self._build_breakdown(breakdown_items),
            "timestamp": self._now_ist(),
        }

    # ------------------------------------------------------------------
    # 5.  Offer Price Generation (Three-Tier)
    # ------------------------------------------------------------------

    def generate_offer_prices(
        self,
        landed_cost: float,
        customer_last_price: Optional[float] = None,
    ) -> dict:
        """
        Generate three-tier offer prices based on landed cost and the
        configured margin structure.

        Tiers
        -----
        * **Aggressive** : landed_cost + min_margin  (thinnest acceptable margin)
        * **Balanced**   : landed_cost + min_margin x 1.6  (standard quote)
        * **Premium**    : landed_cost + min_margin x 2.4  (value-sell / premium)

        If *customer_last_price* is provided, the engine also computes a
        ``client_benefit_pct`` showing how much cheaper the aggressive
        quote is compared to what the client last paid.

        Returns
        -------
        dict with tier details and optional client benefit percentage.
        """
        margin_agg = self.min_margin
        margin_bal = self.min_margin * self.balanced_mult
        margin_pre = self.min_margin * self.premium_mult

        price_agg = landed_cost + margin_agg
        price_bal = landed_cost + margin_bal
        price_pre = landed_cost + margin_pre

        # Margin as percentage of selling price
        pct_agg = (margin_agg / price_agg * 100) if price_agg > 0 else 0
        pct_bal = (margin_bal / price_bal * 100) if price_bal > 0 else 0
        pct_pre = (margin_pre / price_pre * 100) if price_pre > 0 else 0

        client_benefit_pct: Optional[float] = None
        if customer_last_price and customer_last_price > 0:
            client_benefit_pct = round(
                (customer_last_price - price_agg) / customer_last_price * 100, 2
            )

        return {
            "landed_cost": self._round2(landed_cost),
            "aggressive": {
                "price": self._round2(price_agg),
                "price_formatted": format_inr(round(price_agg, 2)),
                "margin": self._round2(margin_agg),
                "margin_pct": round(pct_agg, 2),
                "label": "Aggressive (Min Margin)",
            },
            "balanced": {
                "price": self._round2(price_bal),
                "price_formatted": format_inr(round(price_bal, 2)),
                "margin": self._round2(margin_bal),
                "margin_pct": round(pct_bal, 2),
                "label": "Balanced (Standard)",
            },
            "premium": {
                "price": self._round2(price_pre),
                "price_formatted": format_inr(round(price_pre, 2)),
                "margin": self._round2(margin_pre),
                "margin_pct": round(pct_pre, 2),
                "label": "Premium (Value Sell)",
            },
            "client_benefit_pct": client_benefit_pct,
            "customer_last_price": customer_last_price,
            "timestamp": self._now_ist(),
        }

    # ------------------------------------------------------------------
    # 6.  Find Best Sources for a Destination
    # ------------------------------------------------------------------

    def find_best_sources(
        self,
        destination: str,
        grade: str = "VG30",
        load_type: str = "Bulk",
        top_n: int = 5,
    ) -> list:
        """
        Iterate every source (refineries + import terminals + decanters),
        calculate landed cost for each, and return the cheapest *top_n*
        options sorted by total landed cost (ascending).

        Each result item contains:
        ``{rank, source, source_type, base_price, distance_km, freight,
        landed_cost, savings_vs_next}``

        Parameters
        ----------
        destination : Customer city.
        grade       : Bitumen grade.
        load_type   : ``'Bulk'`` or ``'Drum'``.
        top_n       : Maximum results to return.

        Returns
        -------
        list[dict] sorted cheapest-first.
        """
        options: List[Dict[str, Any]] = []

        # --- Refineries ---
        for ref in INDIAN_REFINERIES:
            name = ref["name"]
            base_price = self._get_base_price(name)
            result = self.calculate_domestic_landed_cost(
                base_price=base_price,
                source=name,
                destination=destination,
                load_type=load_type,
                grade=grade,
            )
            options.append({
                "source": name,
                "source_type": "INDIAN_REFINERY",
                "source_label": SOURCE_CATEGORIES.get("INDIAN_REFINERY", "Indian Refinery"),
                "base_price": result["base_price"],
                "distance_km": result["distance_km"],
                "freight": result["freight"],
                "gst": result["gst"],
                "landed_cost": result["landed_cost"],
            })

        # --- Import Terminals ---
        for term in IMPORT_TERMINALS:
            name = term["name"]
            base_price = self._get_base_price(name)
            result = self.calculate_domestic_landed_cost(
                base_price=base_price,
                source=name,
                destination=destination,
                load_type=load_type,
                grade=grade,
            )
            options.append({
                "source": name,
                "source_type": "IMPORT_TERMINAL",
                "source_label": SOURCE_CATEGORIES.get("IMPORT_TERMINAL", "Import Terminal"),
                "base_price": result["base_price"],
                "distance_km": result["distance_km"],
                "freight": result["freight"],
                "gst": result["gst"],
                "landed_cost": result["landed_cost"],
            })

        # --- Private Decanters (one per destination — source auto-selected) ---
        if PRIVATE_DECANTERS:
            dec_result = self.calculate_decanter_cost(destination, grade)
            options.append({
                "source": dec_result["source"],
                "source_type": "PRIVATE_DECANTER",
                "source_label": SOURCE_CATEGORIES.get("PRIVATE_DECANTER", "Private Decanter"),
                "base_price": dec_result["drum_base_price"],
                "distance_km": dec_result["drum_transport_km"] + dec_result["local_km"],
                "freight": dec_result["drum_transport"] + dec_result["local_transport"],
                "gst": round(dec_result["drum_with_gst"] - dec_result["drum_base_price"], 2),
                "landed_cost": dec_result["landed_cost"],
            })

        # --- Sort by landed cost ---
        options.sort(key=lambda x: x["landed_cost"])

        # --- Assign ranks and savings vs next ---
        ranked: List[Dict[str, Any]] = []
        for idx, opt in enumerate(options[:top_n]):
            savings_vs_next = 0.0
            if idx + 1 < len(options):
                savings_vs_next = round(options[idx + 1]["landed_cost"] - opt["landed_cost"], 2)
            ranked.append({
                "rank": idx + 1,
                "source": opt["source"],
                "source_type": opt["source_type"],
                "source_label": opt["source_label"],
                "base_price": opt["base_price"],
                "base_price_formatted": format_inr(opt["base_price"]),
                "distance_km": opt["distance_km"],
                "freight": opt["freight"],
                "freight_formatted": format_inr(opt["freight"]),
                "gst": opt["gst"],
                "landed_cost": opt["landed_cost"],
                "landed_cost_formatted": format_inr(opt["landed_cost"]),
                "savings_vs_next": savings_vs_next,
                "savings_vs_next_formatted": format_inr(savings_vs_next),
            })

        return ranked

    # ------------------------------------------------------------------
    # 7.  Deal Economics
    # ------------------------------------------------------------------

    def calculate_deal_economics(self, deal_params: dict) -> dict:
        """
        Full profitability and economics analysis for a proposed deal.

        Parameters (in ``deal_params``)
        --------------------------------
        buy_price           : Purchase / base price INR/MT
        sell_price          : Proposed selling price INR/MT
        quantity_mt         : Deal quantity in metric tonnes
        source              : Source name
        destination         : Customer city
        load_type           : 'Bulk' or 'Drum' (default 'Bulk')
        grade               : Bitumen grade (default 'VG30')
        customer_last_price : Previous price the customer paid (optional)

        Returns
        -------
        dict with landed_cost, margin_per_mt, margin_pct, total_revenue,
        total_cost, total_profit, gst_amount, offer_tiers,
        client_benefit_pct, risk_level.
        """
        buy_price: float = float(deal_params.get("buy_price", 0))
        sell_price: float = float(deal_params.get("sell_price", 0))
        quantity_mt: float = float(deal_params.get("quantity_mt", 0))
        source: str = deal_params.get("source", "")
        destination: str = deal_params.get("destination", "")
        load_type: str = deal_params.get("load_type", "Bulk")
        grade: str = deal_params.get("grade", "VG30")
        customer_last_price: Optional[float] = deal_params.get("customer_last_price")
        if customer_last_price is not None:
            customer_last_price = float(customer_last_price)

        # Calculate landed cost from source to destination
        landed = self.calculate_domestic_landed_cost(
            base_price=buy_price,
            source=source,
            destination=destination,
            load_type=load_type,
            grade=grade,
        )
        landed_cost = landed["landed_cost"]

        # Margins
        margin_per_mt = sell_price - landed_cost
        margin_pct = (margin_per_mt / sell_price * 100) if sell_price > 0 else 0

        # Totals
        total_revenue = sell_price * quantity_mt
        total_cost = landed_cost * quantity_mt
        total_profit = margin_per_mt * quantity_mt

        # GST on sale
        gst_amount = sell_price * self.gst_rate * quantity_mt

        # Offer tiers
        offers = self.generate_offer_prices(landed_cost, customer_last_price)

        # Client benefit
        client_benefit_pct = offers.get("client_benefit_pct")

        # Risk level based on margin
        if margin_per_mt < 0:
            risk_level = "LOSS"
        elif margin_per_mt < self.min_margin * 0.5:
            risk_level = "HIGH"
        elif margin_per_mt < self.min_margin:
            risk_level = "MEDIUM"
        elif margin_per_mt < self.min_margin * self.balanced_mult:
            risk_level = "LOW"
        else:
            risk_level = "VERY LOW"

        return {
            "source": source,
            "destination": destination,
            "grade": grade,
            "load_type": load_type,
            "buy_price": self._round2(buy_price),
            "sell_price": self._round2(sell_price),
            "quantity_mt": quantity_mt,
            "landed_cost": self._round2(landed_cost),
            "landed_cost_formatted": format_inr(round(landed_cost, 2)),
            "margin_per_mt": self._round2(margin_per_mt),
            "margin_per_mt_formatted": format_inr(round(margin_per_mt, 2)),
            "margin_pct": round(margin_pct, 2),
            "total_revenue": self._round2(total_revenue),
            "total_revenue_formatted": format_inr_short(round(total_revenue, 2)),
            "total_cost": self._round2(total_cost),
            "total_cost_formatted": format_inr_short(round(total_cost, 2)),
            "total_profit": self._round2(total_profit),
            "total_profit_formatted": format_inr_short(round(total_profit, 2)),
            "gst_amount": self._round2(gst_amount),
            "gst_amount_formatted": format_inr_short(round(gst_amount, 2)),
            "offer_tiers": offers,
            "client_benefit_pct": client_benefit_pct,
            "risk_level": risk_level,
            "distance_km": landed["distance_km"],
            "freight": landed["freight"],
            "timestamp": self._now_ist(),
        }

    # ------------------------------------------------------------------
    # 8.  Deal Risk Scoring
    # ------------------------------------------------------------------

    def calculate_deal_risk_score(self, params: dict) -> dict:
        """
        Multi-factor risk score for a proposed deal.

        Factors and Weights
        -------------------
        * **Credit Risk (30%)** : outstanding_inr, payment_reliability (0-100)
        * **Delivery Risk (25%)** : distance_km, is_monsoon (bool)
        * **Volatility Risk (25%)** : crude_7d_change_pct
        * **Margin Risk (20%)** : margin_per_mt vs min_margin

        Parameters (in ``params``)
        ---------------------------
        outstanding_inr       : Customer outstanding balance in INR (default 0)
        payment_reliability   : 0-100 score of payment history (default 70)
        distance_km           : Delivery distance in km (default 350)
        is_monsoon            : True if delivery during Jun-Sep (default False)
        crude_7d_change_pct   : 7-day crude price change percentage (default 0)
        margin_per_mt         : Achieved margin in INR/MT (default 500)

        Returns
        -------
        dict with overall_score (0-100, lower is riskier), grade (A+ to D),
        factor breakdown, and recommendation string.
        """
        outstanding = float(params.get("outstanding_inr", 0))
        reliability = float(params.get("payment_reliability", 70))
        distance_km = float(params.get("distance_km", 350))
        is_monsoon = bool(params.get("is_monsoon", False))
        crude_change = float(params.get("crude_7d_change_pct", 0))
        margin_per_mt = float(params.get("margin_per_mt", self.min_margin))

        # ---- Credit Risk (30%) — higher score = safer ----
        # Outstanding > 50L is risky; >1Cr very risky
        if outstanding <= 0:
            credit_outstanding_score = 100.0
        elif outstanding <= 5_00_000:
            credit_outstanding_score = 85.0
        elif outstanding <= 25_00_000:
            credit_outstanding_score = 60.0
        elif outstanding <= 50_00_000:
            credit_outstanding_score = 35.0
        elif outstanding <= 1_00_00_000:
            credit_outstanding_score = 15.0
        else:
            credit_outstanding_score = 5.0

        # Payment reliability directly maps to score
        credit_reliability_score = min(max(reliability, 0), 100)

        credit_score = (credit_outstanding_score * 0.5) + (credit_reliability_score * 0.5)

        # ---- Delivery Risk (25%) ----
        if distance_km <= 200:
            dist_score = 95.0
        elif distance_km <= 500:
            dist_score = 80.0
        elif distance_km <= 1000:
            dist_score = 60.0
        elif distance_km <= 1500:
            dist_score = 40.0
        else:
            dist_score = 20.0

        monsoon_penalty = 20.0 if is_monsoon else 0.0
        delivery_score = max(dist_score - monsoon_penalty, 5.0)

        # ---- Volatility Risk (25%) ----
        abs_change = abs(crude_change)
        if abs_change <= 1.0:
            volatility_score = 95.0
        elif abs_change <= 3.0:
            volatility_score = 75.0
        elif abs_change <= 5.0:
            volatility_score = 50.0
        elif abs_change <= 8.0:
            volatility_score = 30.0
        else:
            volatility_score = 10.0

        # ---- Margin Risk (20%) ----
        margin_ratio = margin_per_mt / self.min_margin if self.min_margin > 0 else 0
        if margin_ratio >= 2.0:
            margin_score = 100.0
        elif margin_ratio >= 1.5:
            margin_score = 85.0
        elif margin_ratio >= 1.0:
            margin_score = 70.0
        elif margin_ratio >= 0.5:
            margin_score = 40.0
        elif margin_ratio > 0:
            margin_score = 20.0
        else:
            margin_score = 0.0  # loss-making

        # ---- Weighted overall score ----
        overall = (
            credit_score * 0.30
            + delivery_score * 0.25
            + volatility_score * 0.25
            + margin_score * 0.20
        )
        overall = round(min(max(overall, 0), 100), 1)

        # ---- Grade assignment ----
        if overall >= 90:
            grade = "A+"
        elif overall >= 80:
            grade = "A"
        elif overall >= 65:
            grade = "B"
        elif overall >= 45:
            grade = "C"
        else:
            grade = "D"

        # ---- Recommendation ----
        if grade in ("A+", "A"):
            recommendation = "Proceed with confidence. Low overall risk."
        elif grade == "B":
            recommendation = "Acceptable deal. Monitor delivery timelines and margin."
        elif grade == "C":
            recommendation = "Caution advised. Tighten payment terms or reduce exposure."
        else:
            recommendation = "High risk. Require advance payment or reconsider pricing."

        return {
            "overall_score": overall,
            "grade": grade,
            "factors": {
                "credit_risk": {
                    "score": round(credit_score, 1),
                    "weight": "30%",
                    "outstanding_inr": outstanding,
                    "outstanding_formatted": format_inr(outstanding),
                    "payment_reliability": reliability,
                },
                "delivery_risk": {
                    "score": round(delivery_score, 1),
                    "weight": "25%",
                    "distance_km": distance_km,
                    "is_monsoon": is_monsoon,
                },
                "volatility_risk": {
                    "score": round(volatility_score, 1),
                    "weight": "25%",
                    "crude_7d_change_pct": crude_change,
                },
                "margin_risk": {
                    "score": round(margin_score, 1),
                    "weight": "20%",
                    "margin_per_mt": margin_per_mt,
                    "margin_per_mt_formatted": format_inr(margin_per_mt),
                    "min_margin": self.min_margin,
                    "margin_ratio": round(margin_ratio, 2),
                },
            },
            "recommendation": recommendation,
            "timestamp": self._now_ist(),
        }

    # ------------------------------------------------------------------
    # 9.  Sensitivity Analysis
    # ------------------------------------------------------------------

    def sensitivity_analysis(
        self,
        base_landed_cost: float,
        params: dict,
    ) -> list:
        """
        What-if analysis showing how +/-5% changes in key cost drivers
        affect the total landed cost and margin.

        Analyses the following variables:
        - FOB price
        - Ocean freight
        - USD/INR exchange rate
        - Crude oil price proxy (applied to FOB)

        Parameters
        ----------
        base_landed_cost : Current landed cost (INR/MT) as the baseline.
        params           : dict containing the current import parameters:
                           fob_usd, freight_usd, usdinr.  Defaults are
                           pulled from engine settings when keys are absent.

        Returns
        -------
        list of scenario dicts, each with:
        ``{variable, direction, change_pct, new_value, new_landed_cost,
        delta, delta_formatted, margin_impact}``
        """
        fob_usd = float(params.get("fob_usd", self.default_fob_usd))
        freight_usd = float(params.get("freight_usd", self.default_freight_usd))
        usdinr = float(params.get("usdinr", 83.25))

        variables = [
            ("FOB Price", "fob_usd", fob_usd),
            ("Ocean Freight", "freight_usd", freight_usd),
            ("USD/INR Rate", "usdinr", usdinr),
            ("Crude (via FOB)", "fob_usd", fob_usd),  # crude acts on FOB
        ]

        scenarios: List[Dict[str, Any]] = []

        for var_label, param_key, current_val in variables:
            for direction, pct in [("Up", 5.0), ("Down", -5.0)]:
                new_val = current_val * (1 + pct / 100.0)
                modified_params = dict(params)
                modified_params[param_key] = new_val

                result = self.calculate_international_landed_cost(modified_params)
                new_landed = result["total_landed"]
                delta = new_landed - base_landed_cost
                margin_impact = -delta  # if cost goes up, margin shrinks

                scenarios.append({
                    "variable": var_label,
                    "direction": direction,
                    "change_pct": pct,
                    "original_value": self._round2(current_val),
                    "new_value": self._round2(new_val),
                    "new_landed_cost": self._round2(new_landed),
                    "new_landed_formatted": format_inr(round(new_landed, 2)),
                    "delta": self._round2(delta),
                    "delta_formatted": format_inr(round(delta, 2)),
                    "margin_impact": self._round2(margin_impact),
                    "margin_impact_formatted": format_inr(round(margin_impact, 2)),
                })

        return scenarios

    # ------------------------------------------------------------------
    #  Convenience / utility methods
    # ------------------------------------------------------------------

    def reload_prices(self) -> None:
        """Hot-reload live prices from ``live_prices.json``."""
        self._prices = _load_live_prices()

    def reload_settings(self) -> None:
        """Hot-reload business rules from ``settings.json``."""
        self.__init__()

    def get_all_destinations(self) -> List[str]:
        """Return sorted list of all known destination cities."""
        return sorted(DESTINATION_COORDS.keys())

    def get_all_source_names(self) -> List[str]:
        """Return sorted list of all source names."""
        return sorted([s["name"] for s in ALL_SOURCES])

    def get_source_price_map(self) -> Dict[str, float]:
        """Return a copy of the current live price map."""
        return dict(self._prices)

    def summary(self) -> dict:
        """Quick engine health / configuration summary."""
        return {
            "engine_version": "1.0",
            "settings_loaded": bool(self._settings),
            "prices_loaded": len(self._prices),
            "sources_available": len(ALL_SOURCES),
            "destinations_available": len(DESTINATION_COORDS),
            "gst_rate": f"{self.gst_rate * 100:.0f}%",
            "min_margin": format_inr(self.min_margin),
            "bulk_rate_per_km": f"{format_inr(self.bulk_rate_per_km, include_symbol=False)}/km",
            "drum_rate_per_km": f"{format_inr(self.drum_rate_per_km, include_symbol=False)}/km",
            "created_at": self._created_at,
        }


# ===================================================================
#  MODULE-LEVEL CONVENIENCE
# ===================================================================

# Singleton-style engine for quick imports:
#   from calculation_engine import engine
_engine_instance: Optional[BitumenCalculationEngine] = None


def get_engine() -> BitumenCalculationEngine:
    """Return the shared engine instance (lazy-init)."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = BitumenCalculationEngine()
    return _engine_instance


def __getattr__(name: str):
    """Module-level lazy attribute so ``from calculation_engine import engine`` works."""
    if name == "engine":
        return get_engine()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# ===================================================================
#  SELF-TEST  (python calculation_engine.py)
# ===================================================================

if __name__ == "__main__":
    print("=" * 72)
    print("  PPS Anantam — Calculation Engine v1.0  Self-Test")
    print("=" * 72)

    eng = BitumenCalculationEngine()

    # -- Engine summary --
    print("\n--- Engine Summary ---")
    for k, v in eng.summary().items():
        print(f"  {k:30s} : {v}")

    # -- International landed cost --
    print("\n--- International Landed Cost (Iraq -> India) ---")
    intl = eng.calculate_international_landed_cost({
        "fob_usd": 380,
        "freight_usd": 35,
        "usdinr": 83.25,
    })
    for item in intl["breakdown"]:
        print(f"  {item['label']:35s}  {item['formatted']:>18s}")
    print(f"\n  Total Landed  = {intl['total_landed_formatted']}")
    print(f"  Shipment Value = {intl['total_shipment_value_formatted']}")

    # -- Domestic landed cost --
    print("\n--- Domestic: IOCL Koyali -> Ahmedabad (Bulk VG30) ---")
    dom = eng.calculate_domestic_landed_cost(
        base_price=42_000,
        source="IOCL Koyali",
        destination="Ahmedabad",
    )
    for item in dom["breakdown"]:
        print(f"  {item['label']:45s}  {item['formatted']:>18s}")

    # -- Decanter cost --
    print("\n--- Decanter Cost: Jaipur ---")
    dec = eng.calculate_decanter_cost("Jaipur")
    for item in dec["breakdown"]:
        print(f"  {item['label']:45s}  {item['formatted']:>18s}")

    # -- Offer prices --
    print("\n--- Offer Tiers (landed = domestic above) ---")
    offers = eng.generate_offer_prices(dom["landed_cost"], customer_last_price=55_000)
    for tier in ("aggressive", "balanced", "premium"):
        t = offers[tier]
        print(f"  {t['label']:30s}  Price: {t['price_formatted']:>16s}  Margin: {format_inr(t['margin']):>12s}  ({t['margin_pct']:.1f}%)")
    if offers["client_benefit_pct"] is not None:
        print(f"  Client Benefit vs Last Price: {offers['client_benefit_pct']:+.2f}%")

    # -- Best sources --
    print("\n--- Best 5 Sources for Ahmedabad ---")
    best = eng.find_best_sources("Ahmedabad", top_n=5)
    for b in best:
        print(f"  #{b['rank']}  {b['source']:30s}  Landed: {b['landed_cost_formatted']:>16s}  Dist: {b['distance_km']:>6.0f} km  Save vs next: {b['savings_vs_next_formatted']}")

    # -- Deal economics --
    print("\n--- Deal Economics: 100 MT to Jaipur ---")
    econ = eng.calculate_deal_economics({
        "buy_price": 42_000,
        "sell_price": 52_500,
        "quantity_mt": 100,
        "source": "IOCL Koyali",
        "destination": "Jaipur",
        "customer_last_price": 55_000,
    })
    print(f"  Landed Cost    : {econ['landed_cost_formatted']}")
    print(f"  Margin / MT    : {econ['margin_per_mt_formatted']} ({econ['margin_pct']:.1f}%)")
    print(f"  Total Revenue  : {econ['total_revenue_formatted']}")
    print(f"  Total Profit   : {econ['total_profit_formatted']}")
    print(f"  Risk Level     : {econ['risk_level']}")

    # -- Risk scoring --
    print("\n--- Risk Score ---")
    risk = eng.calculate_deal_risk_score({
        "outstanding_inr": 15_00_000,
        "payment_reliability": 72,
        "distance_km": 650,
        "is_monsoon": False,
        "crude_7d_change_pct": 2.1,
        "margin_per_mt": 600,
    })
    print(f"  Overall Score : {risk['overall_score']}/100   Grade: {risk['grade']}")
    for factor_name, factor_data in risk["factors"].items():
        print(f"  {factor_name:20s}  Score: {factor_data['score']:5.1f}  Weight: {factor_data['weight']}")
    print(f"  Recommendation: {risk['recommendation']}")

    # -- Sensitivity analysis --
    print("\n--- Sensitivity Analysis (+/-5%) ---")
    scenarios = eng.sensitivity_analysis(intl["total_landed"], {
        "fob_usd": 380,
        "freight_usd": 35,
        "usdinr": 83.25,
    })
    for sc in scenarios:
        print(
            f"  {sc['variable']:18s} {sc['direction']:4s} ({sc['change_pct']:+.0f}%)  "
            f"New Landed: {sc['new_landed_formatted']:>16s}  "
            f"Delta: {sc['delta_formatted']:>14s}"
        )

    print("\n" + "=" * 72)
    print("  Self-test complete.")
    print("=" * 72)
