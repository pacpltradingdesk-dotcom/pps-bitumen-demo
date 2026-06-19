"""
Regression tests for the stale-news bug.

Symptom: News page showed months-old articles at the top while fresh
articles were buried. Root cause was a mix of date formats in storage
(ISO ``YYYY-MM-DD`` for freshly-fetched articles, legacy ``DD-MM-YYYY``
for older ones) combined with:
  1. ``_parse_ist`` only understanding the ISO format, so legacy dates
     parsed to ``None`` and skipped the age filter (fail-open).
  2. ``get_articles`` sorting by the raw date *string* rather than a
     parsed datetime, so "28-..." sorted above "2026-..." lexically.
"""

import datetime

import news_engine as ne


def test_parse_ist_handles_dd_mm_yyyy():
    """Legacy DD-MM-YYYY timestamps must parse to the correct date."""
    dt = ne._parse_ist("28-02-2026 14:20 IST")
    assert dt is not None, "DD-MM-YYYY format should parse, not return None"
    assert (dt.year, dt.month, dt.day) == (2026, 2, 28)


def test_parse_ist_handles_iso():
    """ISO YYYY-MM-DD timestamps must still parse."""
    dt = ne._parse_ist("2026-06-18 15:19 IST")
    assert dt is not None
    assert (dt.year, dt.month, dt.day) == (2026, 6, 18)


def test_rss_request_uses_browser_like_headers():
    """Many feeds 403 a non-browser UA. Requests must look like a browser."""
    h = ne._browser_headers()
    assert "Mozilla" in h["User-Agent"]
    assert "PPS-Anantams" not in h["User-Agent"], "old blocked UA still in use"
    assert h.get("Accept"), "Accept header required to avoid some 403s"


def _fixed_articles():
    """Two genuinely-fresh ISO articles + two stale legacy DD-MM articles."""
    today = ne._now_ist()
    fresh_iso = today.strftime("%Y-%m-%d %H:%M IST")
    yesterday_iso = (today - datetime.timedelta(days=1)).strftime("%Y-%m-%d %H:%M IST")
    return [
        # Stale legacy article — ~4 months old, lexically-large day "28"
        {"article_id": "old1", "region": "International", "impact_score": 50,
         "headline": "STALE Feb article", "published_at_ist": "28-02-2026 21:30 IST",
         "fetched_at_ist": "28-02-2026 21:32 IST", "status": "new", "tags": []},
        # Fresh ISO article — today
        {"article_id": "new1", "region": "International", "impact_score": 50,
         "headline": "FRESH today article", "published_at_ist": fresh_iso,
         "fetched_at_ist": fresh_iso, "status": "new", "tags": []},
        # Fresh ISO article — yesterday
        {"article_id": "new2", "region": "International", "impact_score": 50,
         "headline": "FRESH yesterday article", "published_at_ist": yesterday_iso,
         "fetched_at_ist": yesterday_iso, "status": "new", "tags": []},
    ]


def test_get_articles_excludes_stale_legacy_dates(monkeypatch):
    """A ~4-month-old DD-MM article must not appear in a 30-day window."""
    monkeypatch.setattr(ne, "load_articles", _fixed_articles)
    arts = ne.get_articles(region="International", max_age_hours=720)  # 30 days
    headlines = [a["headline"] for a in arts]
    assert "STALE Feb article" not in headlines, (
        "Legacy DD-MM dated article leaked through the 30-day age filter"
    )
    assert len(arts) == 2


def test_last_fetch_time_falls_back_to_newest_article(monkeypatch):
    """After a restart the in-memory fetch global is empty; the pill must
    still show a real time derived from the newest stored article."""
    monkeypatch.setattr(ne, "_G_fetch", {}, raising=False)
    monkeypatch.setattr(ne, "load_articles", _fixed_articles)
    out = ne.get_last_fetch_time()
    assert out, "last fetch time should never be blank when articles exist"
    assert "Not yet" not in out
    # newest fetched_at among the fixtures is 'today'
    assert out.startswith(ne._now_ist().strftime("%Y-%m-%d"))


def test_get_articles_sorts_newest_first_by_real_date(monkeypatch):
    """Sorting must use parsed datetimes, not raw strings."""
    monkeypatch.setattr(ne, "load_articles", _fixed_articles)
    arts = ne.get_articles(region="International", max_age_hours=99999)  # All Time
    # Newest (today) must come first, stale Feb article last — NOT first.
    assert arts[0]["headline"] == "FRESH today article", (
        f"Expected fresh article first, got {arts[0]['headline']!r}"
    )
    assert arts[-1]["headline"] == "STALE Feb article"
