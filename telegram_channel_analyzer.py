"""
PPS Anantam — Telegram Channel Analyzer v1.0
===============================================
Connects to user's Telegram account via Telethon.
Reads messages from joined channels/groups.
Auto-translates all languages to English.
Filters price/market related messages.
Generates alerts for price intelligence.

Setup: Requires API ID + API Hash from https://my.telegram.org
"""
import json
import re
import asyncio
from pathlib import Path
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))
_BASE = Path(__file__).parent
_CONFIG_FILE = _BASE / "telegram_account_config.json"
_CHANNEL_DATA_FILE = _BASE / "telegram_channel_messages.json"
_PRICE_INTEL_FILE = _BASE / "telegram_price_intel.json"
_ALERTS_FILE = _BASE / "sre_alerts.json"

# Price detection patterns (multi-currency)
PRICE_PATTERNS = [
    re.compile(r'[\₹]\s*[\d,]+(?:\.\d+)?', re.UNICODE),           # ₹42,000
    re.compile(r'\$\s*[\d,]+(?:\.\d+)?'),                          # ₹ 109.55
    re.compile(r'[\d,]+(?:\.\d+)?\s*/?\s*(?:MT|mt|KL|kl|PMT|pmt)', re.IGNORECASE),  # 42000/MT
    re.compile(r'(?:price|rate|cost|قیمت|цена|narx)\s*[:=]?\s*[\d,]+', re.IGNORECASE),  # price: 42000
    re.compile(r'[\d]{4,6}\s*(?:per|\/)\s*(?:ton|mt|kl)', re.IGNORECASE),  # 42000 per ton
]

# Business keywords (multi-language)
BIZ_KEYWORDS = [
    # English
    "bitumen", "crude", "price", "rate", "cost", "supply", "demand", "tender",
    "refinery", "import", "export", "freight", "vessel", "cargo", "delivery",
    "iocl", "bpcl", "hpcl", "vg30", "vg10", "vg-30", "vg-10", "crmb",
    "fob", "cif", "landed", "paving", "asphalt", "petroleum",
    # Persian/Farsi
    "قیر", "قیمت", "نفت", "پالایشگاه", "بیتومن", "صادرات", "واردات",
    # Russian
    "битум", "цена", "нефть", "поставка", "экспорт",
    # Uzbek
    "bitum", "narx", "neft",
    # Hindi
    "बिटुमेन", "कीमत", "तेल", "रिफाइनरी",
]


def _load_config() -> dict:
    """Load Telegram account configuration."""
    try:
        if _CONFIG_FILE.exists():
            with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {"api_id": "", "api_hash": "", "phone": "", "channels": [], "enabled": False}


def save_config(config: dict):
    """Save configuration."""
    with open(_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def _translate_to_english(text: str) -> str:
    """Translate any language to English. Returns original if already English or translation fails."""
    if not text or len(text.strip()) < 3:
        return text

    # Quick check if already mostly English/numbers
    ascii_ratio = sum(1 for c in text if ord(c) < 128) / max(len(text), 1)
    if ascii_ratio > 0.85:
        return text  # Already English

    try:
        from deep_translator import GoogleTranslator
        translated = GoogleTranslator(source='auto', target='en').translate(text[:500])
        return translated if translated else text
    except Exception:
        return text


def _is_price_related(text: str) -> bool:
    """Check if message is about prices/market/bitumen."""
    text_lower = text.lower()
    # Check for price patterns
    for pattern in PRICE_PATTERNS:
        if pattern.search(text):
            return True
    # Check for business keywords
    for kw in BIZ_KEYWORDS:
        if kw.lower() in text_lower:
            return True
    return False


def _extract_prices(text: str) -> list:
    """Extract all price mentions from text."""
    prices = []
    for pattern in PRICE_PATTERNS:
        for match in pattern.finditer(text):
            prices.append(match.group().strip())
    return prices


class TelegramOTPRequired(Exception):
    """Raised when Telegram needs OTP verification."""
    pass


class TelegramPasswordRequired(Exception):
    """Raised when Telegram needs 2FA password."""
    pass


def _get_client(config: dict):
    """Create a TelegramClient instance."""
    from telethon import TelegramClient
    api_id = int(config.get("api_id", 0))
    api_hash = config.get("api_hash", "")
    session_path = str(_BASE / "telegram_session")
    return TelegramClient(session_path, api_id, api_hash)


async def send_otp(config: dict) -> str:
    """Send OTP to the phone number. Returns phone_code_hash."""
    client = _get_client(config)
    phone = config.get("phone", "")
    try:
        await client.connect()
        if await client.is_user_authorized():
            await client.disconnect()
            return "already_authorized"
        result = await client.send_code_request(phone)
        await client.disconnect()
        return result.phone_code_hash
    except Exception as e:
        try:
            await client.disconnect()
        except Exception:
            pass
        raise e


async def verify_otp(config: dict, code: str, phone_code_hash: str) -> bool:
    """Verify OTP code and complete sign-in."""
    from telethon.errors import SessionPasswordNeededError
    client = _get_client(config)
    phone = config.get("phone", "")
    try:
        await client.connect()
        await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
        authorized = await client.is_user_authorized()
        await client.disconnect()
        return authorized
    except SessionPasswordNeededError:
        await client.disconnect()
        raise TelegramPasswordRequired("2FA password required")
    except Exception as e:
        try:
            await client.disconnect()
        except Exception:
            pass
        raise e


async def verify_2fa(config: dict, password: str) -> bool:
    """Verify 2FA password."""
    client = _get_client(config)
    try:
        await client.connect()
        await client.sign_in(password=password)
        authorized = await client.is_user_authorized()
        await client.disconnect()
        return authorized
    except Exception as e:
        try:
            await client.disconnect()
        except Exception:
            pass
        raise e


async def fetch_channel_messages(config: dict, limit_per_channel: int = 50) -> list:
    """Fetch messages from all configured channels using Telethon."""
    from telethon.tl.types import Channel, Chat

    client = _get_client(config)
    api_id = int(config.get("api_id", 0))
    api_hash = config.get("api_hash", "")

    if not api_id or not api_hash:
        return []

    all_messages = []

    try:
        await client.connect()

        # Check if authorized — if not, trigger OTP flow
        if not await client.is_user_authorized():
            await client.disconnect()
            raise TelegramOTPRequired("Session expired. Please verify OTP.")

        # Get all dialogs (channels + groups)
        channel_names = config.get("channels", [])

        async for dialog in client.iter_dialogs():
            entity = dialog.entity

            # Filter: only channels and groups
            if not isinstance(entity, (Channel, Chat)):
                continue

            title = dialog.title or ""

            # If specific channels configured, filter by name
            if channel_names and not any(cn.lower() in title.lower() for cn in channel_names):
                continue

            # Fetch recent messages
            try:
                async for msg in client.iter_messages(entity, limit=limit_per_channel):
                    if not msg.text:
                        continue

                    all_messages.append({
                        "channel": title,
                        "channel_id": dialog.id,
                        "sender": getattr(msg.sender, 'first_name', '') if msg.sender else "Channel",
                        "text_original": msg.text,
                        "text_english": "",  # Will be translated later
                        "date": msg.date.astimezone(IST).strftime("%Y-%m-%d %H:%M") if msg.date else "",
                        "timestamp": msg.date.timestamp() if msg.date else 0,
                        "message_id": msg.id,
                    })
            except Exception:
                continue

        await client.disconnect()
    except TelegramOTPRequired:
        raise
    except Exception as e:
        try:
            await client.disconnect()
        except Exception:
            pass
        raise e

    return all_messages


def _generate_conclusion(price_messages: list, all_messages: list, summary: dict) -> dict:
    """Analyze all messages and generate a structured conclusion with key insights."""
    conclusion = {
        "headline": "",
        "key_prices": [],
        "fx_update": "",
        "supply_signals": [],
        "bitumen_grades": [],
        "product_mentions": {},
        "channel_insights": [],
        "market_mood": "neutral",
        "action_items": [],
    }

    all_english = []
    for m in all_messages:
        eng = m.get("text_english", m.get("text_original", ""))
        all_english.append(eng.lower())

    combined_text = " ".join(all_english)

    # ── Extract specific prices ──
    dollar_prices = []
    mt_prices = []
    rial_rates = []
    for m in price_messages:
        eng = m.get("text_english", m.get("text_original", ""))
        # Dollar amounts
        for match in re.finditer(r'\$\s*([\d,]+(?:\.\d+)?)', eng):
            val = match.group(1).replace(",", "")
            try:
                dollar_prices.append(float(val))
            except ValueError:
                pass
        # Per MT prices
        for match in re.finditer(r'([\d,]+(?:\.\d+)?)\s*/?\s*(?:MT|mt|PMT|pmt)', eng):
            val = match.group(1).replace(",", "")
            try:
                mt_prices.append(float(val))
            except ValueError:
                pass
        # Rial/Dollar exchange
        for match in re.finditer(r'([\d,]{7,})\s*(?:rial|ریال)', eng, re.IGNORECASE):
            val = match.group(1).replace(",", "")
            try:
                rial_rates.append(float(val))
            except ValueError:
                pass

    if dollar_prices:
        conclusion["key_prices"].append(f"${min(dollar_prices):,.0f} – ${max(dollar_prices):,.0f}/MT range detected")
    if mt_prices:
        conclusion["key_prices"].append(f"{min(mt_prices):,.0f} – {max(mt_prices):,.0f} per MT range")

    # ── FX / Dollar rate ──
    if rial_rates:
        latest = rial_rates[0]
        conclusion["fx_update"] = f"USD/IRR: {latest:,.0f} Rials"
        if len(rial_rates) > 1:
            prev = rial_rates[1]
            change_pct = ((latest - prev) / prev) * 100
            direction = "▲" if change_pct > 0 else "▼" if change_pct < 0 else "→"
            conclusion["fx_update"] += f" ({direction} {abs(change_pct):.1f}% vs prev)"

    # ── Crude oil mentions ──
    brent_match = re.search(r'brent\s+(?:above|at|near|below)?\s*(\d+)', combined_text)
    if brent_match:
        conclusion["key_prices"].append(f"Brent Crude: ${brent_match.group(1)}")

    # ── Bitumen grades ──
    grade_patterns = [
        (r'(?:vg[\s-]?30|vg30)', "VG-30"),
        (r'(?:vg[\s-]?10|vg10)', "VG-10"),
        (r'(?:bitumen\s*60\s*/?70|قیر\s*6070|6070)', "Bitumen 60/70"),
        (r'(?:bitumen\s*40\s*/?60|قیر\s*4060|4060)', "Bitumen 40/60"),
        (r'(?:bitumen\s*80\s*/?100|80100)', "Bitumen 80/100"),
        (r'(?:bitumen\s*200\s*/?300|قیر\s*200300|200300)', "Bitumen 200/300"),
        (r'(?:crmb|crumb)', "CRMB"),
        (r'(?:oxidized|oxidised)\s*bitumen', "Oxidized Bitumen"),
        (r'emulsion', "Bitumen Emulsion"),
    ]
    found_grades = set()
    for pattern, grade in grade_patterns:
        if re.search(pattern, combined_text, re.IGNORECASE):
            found_grades.add(grade)
    conclusion["bitumen_grades"] = sorted(found_grades)

    # ── Product categories ──
    product_cats = {
        "LPG/Gas": ["lpg", "propane", "butane", "liquefied gas", "گاز مایع", "gas liquid"],
        "Naphtha": ["naphtha", "نفتا", "nafta"],
        "Bitumen": ["bitumen", "قیر", "asphalt", "lami"],
        "Crude Oil": ["crude", "brent", "wti", "نفت"],
        "Methanol": ["methanol", "متانول"],
        "Petrochemicals": ["petrochemical", "پتروشیمی", "refinery", "پالایش"],
    }
    for cat, keywords in product_cats.items():
        count = sum(1 for txt in all_english if any(kw in txt for kw in keywords))
        if count > 0:
            conclusion["product_mentions"][cat] = count

    # ── Supply signals ──
    supply_keywords = {
        "export": ["export", "صادرات", "صادراتی"],
        "domestic": ["domestic", "داخلی"],
        "tender": ["tender", "عرضه", "supply", "supplies"],
        "delivery": ["delivery", "cargo", "vessel", "shipment"],
    }
    for signal, keywords in supply_keywords.items():
        count = sum(1 for txt in all_english if any(kw in txt for kw in keywords))
        if count > 0:
            conclusion["supply_signals"].append({"type": signal, "mentions": count})

    # ── Channel-wise insights ──
    channel_groups = {}
    for m in all_messages:
        ch = m.get("channel", "Unknown")
        if ch not in channel_groups:
            channel_groups[ch] = {"total": 0, "price": 0, "topics": set()}
        channel_groups[ch]["total"] += 1
        eng = m.get("text_english", "").lower()
        if m.get("is_price"):
            channel_groups[ch]["price"] += 1
        for cat, keywords in product_cats.items():
            if any(kw in eng for kw in keywords):
                channel_groups[ch]["topics"].add(cat)

    for ch, info in channel_groups.items():
        short_name = ch if len(ch) <= 30 else ch[:27] + "..."
        topics_str = ", ".join(sorted(info["topics"])) if info["topics"] else "General"
        conclusion["channel_insights"].append({
            "channel": short_name,
            "messages": info["total"],
            "price_msgs": info["price"],
            "focus": topics_str,
        })

    # ── Market mood ──
    bullish_words = ["above", "increase", "rise", "bullish", "up", "higher", "surge", "rally"]
    bearish_words = ["below", "decrease", "fall", "bearish", "down", "lower", "drop", "decline"]
    bull_count = sum(1 for w in bullish_words if w in combined_text)
    bear_count = sum(1 for w in bearish_words if w in combined_text)
    if bull_count > bear_count + 2:
        conclusion["market_mood"] = "bullish"
    elif bear_count > bull_count + 2:
        conclusion["market_mood"] = "bearish"
    else:
        conclusion["market_mood"] = "neutral"

    # ── Headline ──
    parts = []
    if conclusion["key_prices"]:
        parts.append(conclusion["key_prices"][0])
    if conclusion["bitumen_grades"]:
        parts.append(f"Grades: {', '.join(conclusion['bitumen_grades'][:3])}")
    if conclusion["fx_update"]:
        parts.append(conclusion["fx_update"])
    conclusion["headline"] = " | ".join(parts) if parts else "Channel intel analyzed — no major price signals"

    # ── Action items ──
    if dollar_prices:
        conclusion["action_items"].append(f"Track FOB pricing around ${max(dollar_prices):,.0f}/MT")
    if found_grades:
        conclusion["action_items"].append(f"Active grades in market: {', '.join(sorted(found_grades)[:4])}")
    supply_export = [s for s in conclusion["supply_signals"] if s["type"] == "export"]
    if supply_export and supply_export[0]["mentions"] >= 3:
        conclusion["action_items"].append("Heavy export supply activity — check import parity impact")
    if conclusion["market_mood"] == "bullish":
        conclusion["action_items"].append("Bullish sentiment — consider locking supply at current levels")
    elif conclusion["market_mood"] == "bearish":
        conclusion["action_items"].append("Bearish sentiment — delay large purchases if possible")

    return conclusion


def analyze_messages(messages: list) -> dict:
    """Analyze fetched messages: translate, filter price-related, extract intel."""

    price_messages = []
    all_translated = []
    price_alerts = []

    for msg in messages:
        original = msg.get("text_original", "")

        # Translate to English
        english = _translate_to_english(original)
        msg["text_english"] = english
        all_translated.append(msg)

        # Check if price-related (check both original and translated)
        if _is_price_related(original) or _is_price_related(english):
            msg["prices_found"] = _extract_prices(original + " " + english)
            msg["is_price"] = True
            price_messages.append(msg)

            # Generate alert if significant price info
            prices = msg["prices_found"]
            if prices:
                price_alerts.append({
                    "title": f"Price Intel: {msg['channel']} — {', '.join(prices[:3])}",
                    "message": english[:150],
                    "source": msg["channel"],
                    "date": msg["date"],
                    "severity": "info",
                    "status": "Open",
                    "type": "telegram_price_intel",
                    "created_at": datetime.now(IST).strftime("%Y-%m-%d %H:%M IST"),
                })

    # Generate summary
    channels_with_prices = set(m["channel"] for m in price_messages)
    all_prices = []
    for m in price_messages:
        all_prices.extend(m.get("prices_found", []))

    summary = {
        "total_messages": len(messages),
        "translated": len(all_translated),
        "price_related": len(price_messages),
        "channels_analyzed": len(set(m["channel"] for m in messages)),
        "channels_with_prices": len(channels_with_prices),
        "unique_prices_found": len(set(all_prices)),
        "top_prices": list(set(all_prices))[:20],
        "analyzed_at": datetime.now(IST).strftime("%Y-%m-%d %H:%M IST"),
    }

    # Generate AI conclusion from all messages
    conclusion = _generate_conclusion(price_messages, all_translated, summary)
    summary["conclusion"] = conclusion

    return {
        "summary": summary,
        "price_messages": price_messages,
        "all_messages": all_translated,
        "alerts": price_alerts,
    }


def save_analysis(result: dict):
    """Save analysis results and push alerts."""
    # Save price intel
    with open(_PRICE_INTEL_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "summary": result["summary"],
            "price_messages": result["price_messages"][:100],  # Keep top 100
        }, f, indent=2, ensure_ascii=False)

    # Save all messages
    with open(_CHANNEL_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(result["all_messages"][:500], f, indent=2, ensure_ascii=False)

    # Push alerts to dashboard alert system
    if result["alerts"]:
        existing_alerts = []
        try:
            if _ALERTS_FILE.exists():
                with open(_ALERTS_FILE, "r", encoding="utf-8") as f:
                    existing_alerts = json.load(f)
        except Exception:
            pass

        # Add new alerts (avoid duplicates by title)
        existing_titles = set(a.get("title", "") for a in existing_alerts)
        new_alerts = [a for a in result["alerts"][:10] if a["title"] not in existing_titles]

        if new_alerts:
            existing_alerts = new_alerts + existing_alerts
            # Keep last 200 alerts
            existing_alerts = existing_alerts[:200]
            with open(_ALERTS_FILE, "w", encoding="utf-8") as f:
                json.dump(existing_alerts, f, indent=2, ensure_ascii=False)

    return len(result.get("alerts", []))


def load_price_intel() -> dict:
    """Load saved price intelligence."""
    try:
        if _PRICE_INTEL_FILE.exists():
            with open(_PRICE_INTEL_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {"summary": {}, "price_messages": []}


def load_channel_messages() -> list:
    """Load saved channel messages."""
    try:
        if _CHANNEL_DATA_FILE.exists():
            with open(_CHANNEL_DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return []
