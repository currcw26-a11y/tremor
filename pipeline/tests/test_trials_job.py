"""Tests for saving snapshots, using a pretend database (no internet needed)."""
from tremor import trials_job


class FakeDB:
    def __init__(self, saved):
        self.saved = saved          # rows already in trial_snapshots
        self.inserted = []

    def select(self, table, columns, **filters):
        return self.saved

    def insert(self, table, rows, returning=None):
        self.inserted += rows
        return [{"id": 100 + i, "nct_id": r["nct_id"]} for i, r in enumerate(rows)]


def test_edited_then_changed_back_reuses_old_snapshot(monkeypatch):
    fake = FakeDB(saved=[{"id": 7, "nct_id": "NCT1", "content_hash": "aaa"}])
    monkeypatch.setattr(trials_job, "db", fake)
    ids = trials_job.save_snapshots([
        {"nct_id": "NCT1", "content_hash": "aaa", "data": {}},   # back to a version we already have
        {"nct_id": "NCT2", "content_hash": "bbb", "data": {}},   # brand new
    ])
    assert ids == {"NCT1": 7, "NCT2": 100}
    assert [r["nct_id"] for r in fake.inserted] == ["NCT2"]
