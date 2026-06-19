"""
Regression: get_due_tasks compared due_date as a raw STRING. Storage holds
mixed formats (ISO + legacy DD-MM-YYYY), so a long-overdue '28-02-2026' task
string-sorted ABOVE '2026-...' and got mis-bucketed into Upcoming instead of
Overdue (the client-reported "vanishing tasks"). Must compare parsed dates.
"""

import crm_engine as ce


def _tasks():
    return [
        # legacy DD-MM-YYYY, long past → must be Overdue
        {"id": "legacy", "status": "Pending", "due_date": "28-02-2026 14:00", "client": "A"},
        # ISO far-future → must be Upcoming
        {"id": "future", "status": "Pending", "due_date": "2099-01-01 10:00", "client": "B"},
    ]


def test_legacy_ddmmyyyy_overdue_task_buckets_as_overdue(monkeypatch):
    monkeypatch.setattr(ce, "get_tasks", _tasks)
    overdue_ids = [t["id"] for t in ce.get_due_tasks("Overdue")]
    upcoming_ids = [t["id"] for t in ce.get_due_tasks("Upcoming")]
    assert "legacy" in overdue_ids, "Feb DD-MM task should be Overdue"
    assert "legacy" not in upcoming_ids, "Feb task must NOT show as Upcoming"
    assert "future" in upcoming_ids
    assert "future" not in overdue_ids
