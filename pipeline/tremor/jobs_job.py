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


def find_all():
    existing = {r["ticker"]: r for r in read_boards()}
    rows = []
    for c in db.select("companies", "ticker,name", order="ticker"):
        if c["ticker"] in existing:
            rows.append(existing[c["ticker"]])
            continue
        found = jobs.find_board(c["name"], core_name(c["name"]))
        time.sleep(0.2)  # polite
        if found:
            rows.append({"ticker": c["ticker"], "company": c["name"], "provider": found["provider"],
                         "board": found["board"], "board_name": found["board_name"],
                         "confirmed": "yes" if found["auto_ok"] else ""})
            print(f"  {c['ticker']:<6} {found['provider']:<10} {found['board']:<28} {found['board_name']}")
    with open(BOARDS_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
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
