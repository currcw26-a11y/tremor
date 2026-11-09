"""Daily job-posting counts for companies with a confirmed job board, plus a one-time finder.

Finder (run by hand):  python -m tremor.jobs_job --find
  -> writes pipeline/data/job_boards.csv. Greenhouse boards whose own company name matches are
     marked confirmed=yes automatically; others need a human to mark yes.
"""
import csv
import sys
import time
from datetime import date
from pathlib import Path

from . import db
from .matching import core_name
from .sources import jobs

BOARDS_CSV = Path(__file__).resolve().parents[1] / "data" / "job_boards.csv"
COLUMNS = ["ticker", "company", "provider", "board", "board_name", "confirmed"]


def read_boards() -> list[dict]:
    if not BOARDS_CSV.exists():
        return []
    with open(BOARDS_CSV, newline="") as f:
        return list(csv.DictReader(f))


def _write(rows: list[dict]):
    with open(BOARDS_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: r["ticker"]))


def find_all(workers: int = 8):
    """Look for every company's job board, 8 companies at a time, saving after each find."""
    from collections import Counter
    from concurrent.futures import ThreadPoolExecutor, as_completed
    existing = {r["ticker"]: r for r in read_boards()}
    trial_counts = Counter(t["ticker"] for t in db.select("trials", "ticker", tracked="eq.true"))
    todo = [c for c in db.select("companies", "ticker,name", order="ticker")
            if c["ticker"] not in existing and trial_counts[c["ticker"]] < 15]  # giant companies use other hiring systems
    rows = list(existing.values())

    def look(c):
        return c, jobs.find_board(c["name"], core_name(c["name"]))

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for fut in as_completed([pool.submit(look, c) for c in todo]):
            try:
                c, found = fut.result()
            except Exception as err:
                print(f"  error: {err}")
                continue
            if found:
                rows.append({"ticker": c["ticker"], "company": c["name"], "provider": found["provider"],
                             "board": found["board"], "board_name": found["board_name"],
                             "confirmed": "yes" if found["auto_ok"] else ""})
                print(f"  {c['ticker']:<6} {found['provider']:<10} {found['board']:<28} {found['board_name']}", flush=True)
                _write(rows)
    _write(rows)
    return rows


def run() -> dict:
    """Count today's open jobs for every confirmed board (run once a day)."""
    boards = [b for b in read_boards() if b.get("confirmed", "").strip().lower() in {"yes", "y", "true"}]
    db.upsert("job_boards", [{"ticker": b["ticker"], "provider": b["provider"], "board": b["board"], "confirmed": True}
                             for b in boards], on_conflict="ticker")
    today, rows, errors = date.today().isoformat(), [], 0
    for b in boards:
        try:
            total, clinical = jobs.count(jobs.fetch_jobs(b["provider"], b["board"]))
            rows.append({"ticker": b["ticker"], "day": today, "total_jobs": total, "clinical_jobs": clinical})
        except Exception as err:
            errors += 1
            print(f"    {b['ticker']} jobs: {err}")
    db.upsert("job_counts", rows, on_conflict="ticker,day")
    return {"companies_counted": len(rows), "clinical_jobs_total": sum(r["clinical_jobs"] for r in rows), "errors": errors}


if __name__ == "__main__":
    if "--find" in sys.argv:
        found = find_all()
        print(f"\n{len(found)} boards found; {sum(r['confirmed'] == 'yes' for r in found)} auto-confirmed.")
