"""Stock prices: a one-time history download per company, then one request a day for everyone.

    python -m tremor.prices_job --backfill   (about 40 minutes for 196 companies: 5 requests a minute)
"""
import sys
from datetime import date, timedelta

from . import db
from .sources import prices


def backfill() -> dict:
    have = {r["ticker"] for r in db.select("prices", "ticker", day=f"lte.{(date.today() - timedelta(days=300)).isoformat()}")}
    todo = [c["ticker"] for c in db.select("companies", "ticker", order="ticker") if c["ticker"] not in have]
    done = 0
    for t in todo:
        try:
            rows = prices.backfill(t)
            if rows:
                db.upsert("prices", rows, on_conflict="ticker,day")
                done += 1
            print(f"  {t}: {len(rows)} days", flush=True)
        except Exception as err:
            print(f"  {t}: {err}", flush=True)
    return {"backfilled": done, "skipped_already_had": len(have)}


def backfill_long_history(limit: int = 95) -> dict:
    """Tiingo's longer history (back to 2016). Resumable: skips companies that already have
    prices from before 2024. Run it twice to cover all 196 companies (about 50 an hour)."""
    from collections import defaultdict
    earliest = defaultdict(lambda: "9999")
    for r in db.select("prices", "ticker,day", day="lt.2024-01-01"):
        earliest[r["ticker"]] = min(earliest[r["ticker"]], r["day"])
    todo = [c["ticker"] for c in db.select("companies", "ticker", order="ticker") if c["ticker"] not in earliest][:limit]
    done = 0
    for t in todo:
        try:
            rows = prices.tiingo_history(t)
            for i in range(0, len(rows), 1000):
                db.upsert("prices", rows[i:i + 1000], on_conflict="ticker,day")
            done += bool(rows)
            print(f"  {t}: {len(rows)} days{' (from ' + rows[0]['day'] + ')' if rows else ''}", flush=True)
        except Exception as err:
            print(f"  {t}: {err}", flush=True)
    return {"long_history_added": done, "still_to_do": max(0, len(todo) - done)}


def run() -> dict:
    """Daily: fill in the last few trading days (1 request per day, all companies at once)."""
    tickers = {c["ticker"] for c in db.select("companies", "ticker")}
    latest = db.select("prices", "day", order="day.desc", limit="1")
    start = date.fromisoformat(latest[0]["day"]) + timedelta(days=1) if latest else date.today() - timedelta(days=5)
    added, day = 0, start
    while day < date.today() and (day - start).days < 10:  # catch up at most 10 days per run
        if day.weekday() < 5:  # markets are closed on weekends
            rows = prices.one_day(day.isoformat(), tickers)
            if rows:
                db.upsert("prices", rows, on_conflict="ticker,day")
                added += len(rows)
        day += timedelta(days=1)
    return {"price_rows_added": added}


if __name__ == "__main__":
    if "--backfill" in sys.argv:
        print(backfill())
    if "--long-history" in sys.argv:
        print(backfill_long_history())
