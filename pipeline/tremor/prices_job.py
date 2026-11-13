"""Stock prices: a one-time history download per company, then one request a day for everyone.

    python -m tremor.prices_job --backfill   (about 40 minutes for 196 companies: 5 requests a minute)
"""
import sys
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import requests

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


def new_york_today(now: datetime | None = None) -> date:
    """Today's date in New York, where the market is. A day's prices exist only once that day is over there:
    at 01:00 UTC it is still the evening of the previous day in New York."""
    return (now or datetime.now(timezone.utc)).astimezone(ZoneInfo("America/New_York")).date()


def run(now: datetime | None = None) -> dict:
    """Daily: fill in the last few finished trading days (1 request per day, all companies at once)."""
    tickers = {c["ticker"] for c in db.select("companies", "ticker")}
    today = new_york_today(now)
    latest = db.select("prices", "day", order="day.desc", limit="1")
    start = date.fromisoformat(latest[0]["day"]) + timedelta(days=1) if latest else today - timedelta(days=5)
    added, day, waiting = 0, start, None
    while day < today and (day - start).days < 10:  # catch up at most 10 days per run
        if day.weekday() < 5:  # markets are closed on weekends
            try:
                rows = prices.one_day(day.isoformat(), tickers)
            except requests.HTTPError as err:
                if err.response is not None and err.response.status_code == 403:
                    waiting = day.isoformat()   # the price service hasn't released this day yet: next run tries again
                    break
                raise
            if rows:
                db.upsert("prices", rows, on_conflict="ticker,day")
                added += len(rows)
        day += timedelta(days=1)
    return {"price_rows_added": added, **({"waiting_for": waiting} if waiting else {})}


if __name__ == "__main__":
    if "--backfill" in sys.argv:
        print(backfill())
    if "--long-history" in sys.argv:
        print(backfill_long_history())
