"""
PPS Anantam — circular Vision extraction adapter.

Sends an uploaded Multi Energy price-circular image to Claude (vision) and gets
back structured rows [{location, grade, price}] for circular_parser to map.

Reuses the dashboard's existing Anthropic key (ai_assistant_engine.get_api_key)
and Sonnet model. Degrades gracefully — returns an empty row list + an error
string when there is no key / anthropic isn't installed / the call fails, so the
UI can fall back to manual entry. Only `parse_rows_json` is pure/unit-tested.
"""
from __future__ import annotations

import base64
import json
import re

_PROMPT = (
    "This image is an Indian petroleum 'Price Revision' circular. "
    "Extract ONLY the 'Bitumen (Bulk) Basic Prices' table, and the circular's "
    "effective / revision date (usually printed in the header, e.g. 'w.e.f "
    "16-06-2026'). "
    "Return STRICT JSON only (no prose, no markdown) as a single object: "
    '{"effective_date": "<DD-MM-YYYY as printed, or null if absent>", '
    '"rows": [ {"location": <str as printed>, '
    '"grade": "60/70-VG30" or "80/100-VG10", '
    '"price": <integer Rs/MT, no commas>} ]}. '
    "Emit one row object per location per grade column. Skip cells marked NA. "
    "Do not include any other table."
)


def find_effective_date(text: str | None) -> str | None:
    """Pull the circular's effective-date string from an LLM reply.

    Prefers the JSON 'effective_date' field; falls back to a date near an
    'effective'/'w.e.f'/'revision' cue in prose. Returns the raw date string
    (circular_parser.parse_circular_date handles the format). None if absent.
    """
    if not text:
        return None
    s = str(text)
    # 1) JSON object field
    m = re.search(r'"effective_date"\s*:\s*"([^"]+)"', s)
    if m:
        return m.group(1).strip()
    # 2) prose cue → nearest date token on the same line
    for line in s.splitlines():
        if re.search(r"effective|w\.?e\.?f|revision|dated", line, re.IGNORECASE):
            d = re.search(r"\d{1,2}[-./]\d{1,2}[-./]\d{4}|\d{4}-\d{1,2}-\d{1,2}"
                          r"|\d{1,2}\s+[A-Za-z]{3,9}\.?\s+\d{4}", line)
            if d:
                return d.group(0).strip()
    return None


def parse_rows_json(text: str | None) -> list[dict]:
    """Pull the first JSON array out of an LLM reply and keep only dict rows.

    Tolerates markdown fences and surrounding prose. Returns [] on any failure.
    """
    if not text:
        return []
    m = re.search(r"\[.*\]", str(text), re.DOTALL)
    if not m:
        return []
    try:
        data = json.loads(m.group(0))
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    return [d for d in data if isinstance(d, dict)]


def extract_rows(image_bytes: bytes, media_type: str = "image/jpeg",
                 api_key: str | None = None) -> dict:
    """Vision-extract circular rows. Returns {"rows": [...], "error": str|None}."""
    try:
        from ai_assistant_engine import get_api_key, MODEL_DEEP
    except Exception:
        get_api_key, MODEL_DEEP = (lambda: None), "claude-sonnet-4-6"

    key = api_key or get_api_key()
    if not key:
        return {"rows": [], "effective_date": None,
                "error": "No Anthropic API key configured (Settings → AI Setup)."}
    try:
        import anthropic
    except ImportError:
        return {"rows": [], "effective_date": None,
                "error": "anthropic package not installed."}

    try:
        client = anthropic.Anthropic(api_key=key)
        resp = client.messages.create(
            model=MODEL_DEEP,
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {
                        "type": "base64", "media_type": media_type,
                        "data": base64.standard_b64encode(image_bytes).decode("ascii"),
                    }},
                    {"type": "text", "text": _PROMPT},
                ],
            }],
        )
        raw = resp.content[0].text if resp.content else ""
        return {"rows": parse_rows_json(raw),
                "effective_date": find_effective_date(raw), "error": None}
    except Exception as e:  # network / auth / model errors — degrade to manual
        return {"rows": [], "effective_date": None, "error": str(e)}
