"""Date-sensitivity for the circular upload.

A fortnightly circular carries an effective date. If a user uploads an OLD
circular (date earlier than the one currently applied) the prices would roll
backward — so the system must detect and warn. We also flag a future-dated
circular (likely a misread) and an unparseable date.
"""
import datetime

from circular_parser import parse_circular_date, circular_date_status

TODAY = datetime.date(2026, 6, 18)


# ── parse_circular_date ──────────────────────────────────────────────────────
def test_parse_dash_ddmmyyyy():
    assert parse_circular_date("16-06-2026") == datetime.date(2026, 6, 16)


def test_parse_dotted_and_slashed():
    assert parse_circular_date("16.06.2026") == datetime.date(2026, 6, 16)
    assert parse_circular_date("16/06/2026") == datetime.date(2026, 6, 16)


def test_parse_iso():
    assert parse_circular_date("2026-06-16") == datetime.date(2026, 6, 16)


def test_parse_long_month_name():
    assert parse_circular_date("16 June 2026") == datetime.date(2026, 6, 16)
    assert parse_circular_date("1 Jan 2026") == datetime.date(2026, 1, 1)


def test_parse_returns_none_on_garbage():
    assert parse_circular_date(None) is None
    assert parse_circular_date("") is None
    assert parse_circular_date("not a date") is None


# ── circular_date_status ─────────────────────────────────────────────────────
def test_status_unknown_when_date_unparseable():
    assert circular_date_status(None, datetime.date(2026, 6, 1), TODAY) == "unknown"


def test_status_future_circular_flagged():
    # dated after today -> suspicious (likely OCR misread)
    future = datetime.date(2026, 7, 1)
    assert circular_date_status(future, datetime.date(2026, 6, 1), TODAY) == "future"


def test_status_past_when_older_than_last_applied():
    circ = datetime.date(2026, 6, 1)
    last = datetime.date(2026, 6, 16)
    assert circular_date_status(circ, last, TODAY) == "past"


def test_status_ok_when_newer_than_last_applied():
    circ = datetime.date(2026, 6, 16)
    last = datetime.date(2026, 6, 1)
    assert circular_date_status(circ, last, TODAY) == "ok"


def test_status_ok_when_same_as_last_applied():
    d = datetime.date(2026, 6, 16)
    assert circular_date_status(d, d, TODAY) == "ok"


def test_status_ok_when_no_prior_circular():
    # first ever circular, nothing to compare against
    assert circular_date_status(datetime.date(2026, 6, 16), None, TODAY) == "ok"
