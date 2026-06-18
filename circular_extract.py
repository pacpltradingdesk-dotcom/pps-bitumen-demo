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
    "Extract ONLY the 'Bitumen (Bulk) Basic Prices' table. "
    "For every location row, emit one object per grade column. "
    "Return STRICT JSON only (no prose, no markdown): a JSON array of objects "
    '{"location": <str as printed>, "grade": "60/70-VG30" or "80/100-VG10", '
    '"price": <integer Rs/MT, no commas>}. '
    "Skip cells marked NA. Do not include any other table."
)


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
        return {"rows": [], "error": "No Anthropic API key configured (Settings → AI Setup)."}
    try:
        import anthropic
    except ImportError:
        return {"rows": [], "error": "anthropic package not installed."}

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
        return {"rows": parse_rows_json(raw), "error": None}
    except Exception as e:  # network / auth / model errors — degrade to manual
        return {"rows": [], "error": str(e)}
