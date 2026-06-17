"""
PPS Anantam — AIS collector daemon.
Holds a persistent AISStream.io WebSocket, builds a tanker registry via
ais_parser, and writes tbl_live_vessels.json every FLUSH_SECONDS.
Run as a systemd service (see deploy/pps-ais-collector.service).

Env:
  AISSTREAM_API_KEY   (required)  free key from https://aisstream.io
"""
from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import websocket  # websocket-client

import ais_parser as ap

BASE = Path(__file__).parent
OUT_PATH = BASE / "tbl_live_vessels.json"

WS_URL = "wss://stream.aisstream.io/v0/stream"
FLUSH_SECONDS = 30          # how often we write the snapshot
PRUNE_MAX_AGE_MIN = 60      # drop vessels not seen for this long

# Bounding boxes [[[lat,lon],[lat,lon]], ...] — Gulf supply + Indian coasts + Singapore.
BOUNDING_BOXES = [
    [[30.0, 47.0], [22.5, 60.0]],   # Arabian/Persian Gulf + Gulf of Oman
    [[25.0, 60.0], [8.0, 76.5]],    # Arabian Sea / India west coast
    [[22.5, 80.0], [8.0, 92.0]],    # Bay of Bengal / India east coast
    [[5.0, 95.0], [0.0, 105.0]],    # Singapore Strait
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [ais-collector] %(levelname)s %(message)s",
)
log = logging.getLogger("ais_collector")


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _subscription(api_key: str) -> str:
    return json.dumps({
        "APIKey": api_key,
        "BoundingBoxes": BOUNDING_BOXES,
        "FilterMessageTypes": ["PositionReport", "ShipStaticData"],
    })


def _flush(registry: dict) -> None:
    ap.prune_registry(registry, datetime.now(timezone.utc), PRUNE_MAX_AGE_MIN)
    snap = ap.build_snapshot(registry, _now_iso())
    ap.atomic_write_json(OUT_PATH, snap)
    log.info("flushed %d tankers (%d tracked)", len(snap["vessels"]), len(registry))


def run() -> None:
    api_key = os.environ.get("AISSTREAM_API_KEY", "").strip()
    if not api_key:
        log.error("AISSTREAM_API_KEY not set — exiting (systemd will retry).")
        raise SystemExit(1)

    registry: dict = {}
    backoff = 1
    while True:
        ws = None
        try:
            log.info("connecting to %s", WS_URL)
            ws = websocket.create_connection(WS_URL, timeout=30)
            ws.send(_subscription(api_key))
            log.info("subscribed (%d bounding boxes)", len(BOUNDING_BOXES))
            backoff = 1
            last_flush = time.monotonic()

            while True:
                raw = ws.recv()
                if not raw:
                    continue
                try:
                    msg = json.loads(raw)
                    rec = ap.parse_message(msg)
                    if rec:
                        ap.update_registry(registry, rec, _now_iso())
                except Exception as e:  # one bad message must not kill the loop
                    log.debug("skip message: %s", e)

                if time.monotonic() - last_flush >= FLUSH_SECONDS:
                    _flush(registry)
                    last_flush = time.monotonic()

        except Exception as e:
            log.warning("connection error: %s — reconnect in %ss", e, backoff)
            try:
                if ws is not None:
                    ws.close()
            except Exception:
                pass
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)


if __name__ == "__main__":
    run()
