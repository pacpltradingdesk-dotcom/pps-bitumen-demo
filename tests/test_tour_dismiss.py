"""Guided tour must dismiss reliably and stay dismissed.

Live audit 09-07-2026: the welcome tour re-popped on EVERY page navigation
(always STEP 1/10). Root cause: dismissal relied entirely on a fragile
cross-frame JS bridge (iframe-injected tooltip → hidden Streamlit button →
_end_tour). When that bridge missed, _show_tutorial stayed True and the tour
re-injected on every rerun. There was no persistent per-user "seen" flag and
no Python-side dismissal path.

These tests cover the two JS-independent guards that fix it:
  1. Navigating to a different page while the tour is open ends the tour
     (the Next button does NOT change the page, so the walk-through survives).
  2. A persistent per-user "seen" flag stops the tour auto-opening again in
     later sessions.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import tutorial_engine as te  # noqa: E402


# ── Navigation-ends-tour (within-session, no JS needed) ──────────────────────

def test_nav_to_different_page_ends_tour():
    # Tour opened on "Command Center", user clicked a real nav button.
    assert te.should_end_tour_on_nav(True, "Command Center", "Live Market") is True


def test_next_button_same_page_keeps_tour():
    # Next only advances _tour_step; selected_page is unchanged → tour survives.
    assert te.should_end_tour_on_nav(True, "Command Center", "Command Center") is False


def test_tour_not_open_never_ends():
    assert te.should_end_tour_on_nav(False, "Command Center", "Live Market") is False


def test_missing_opened_page_does_not_end():
    # No recorded open-page yet (first render) → never treat as navigation.
    assert te.should_end_tour_on_nav(True, None, "Command Center") is False


# ── Persistent per-user "seen" flag (cross-session) ──────────────────────────

def test_seen_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(te, "_TOUR_SEEN_FILE", tmp_path / "tour_seen.json")
    assert te.has_seen_tour("janki") is False
    te.mark_tour_seen("janki")
    assert te.has_seen_tour("janki") is True
    # other users unaffected
    assert te.has_seen_tour("admin") is False


def test_seen_is_case_insensitive(tmp_path, monkeypatch):
    monkeypatch.setattr(te, "_TOUR_SEEN_FILE", tmp_path / "tour_seen.json")
    te.mark_tour_seen("Admin")
    assert te.has_seen_tour("admin") is True


def test_should_open_welcome_only_when_unseen(tmp_path, monkeypatch):
    monkeypatch.setattr(te, "_TOUR_SEEN_FILE", tmp_path / "tour_seen.json")
    assert te.should_open_welcome_tour("renuka") is True
    te.mark_tour_seen("renuka")
    assert te.should_open_welcome_tour("renuka") is False


def test_blank_username_never_blocks_and_never_crashes(tmp_path, monkeypatch):
    monkeypatch.setattr(te, "_TOUR_SEEN_FILE", tmp_path / "tour_seen.json")
    # Empty username: don't persist junk, and default to showing (unseen).
    assert te.has_seen_tour("") is False
    te.mark_tour_seen("")  # must not raise
    assert te.should_open_welcome_tour("") is True


def test_corrupt_seen_file_is_tolerated(tmp_path, monkeypatch):
    f = tmp_path / "tour_seen.json"
    f.write_text("{ this is not json", encoding="utf-8")
    monkeypatch.setattr(te, "_TOUR_SEEN_FILE", f)
    # Corrupt store must not crash — treat as "nobody has seen it".
    assert te.has_seen_tour("janki") is False
    te.mark_tour_seen("janki")  # should heal the file
    assert te.has_seen_tour("janki") is True
