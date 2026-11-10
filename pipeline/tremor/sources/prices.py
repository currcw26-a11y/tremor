"""Daily closing prices from Massive (formerly Polygon.io). Free plan: about 2 years of history,
5 requests a minute.

- backfill(ticker): one request gets a stock's whole available history (pulled once, then stored).
- one_day(day): one request gets EVERY US stock's close for that day (used for daily updates).
"""
import os
import time
from datetime import date, datetime, timezone

import requests

BASE = "https://api.massive.com"
MIN_GAP = 12.5  # seconds between requests: stays under 5 a minute
_last = 0.0


def _get(path: str, params: dict | None = None) -> dict:
    global _last
    wait = _last + MIN_GAP - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    _last = time.monotonic()
    key = os.getenv("MASSIVE_API_KEY", "proxy-injected")
    for attempt in range(4):
        resp = requests.get(BASE + path, params=params, timeout=60, headers={"Authorization": f"Bearer {key}"})
        if resp.status_code == 429:  # too fast: wait a minute and retry
            time.sleep(61)
            continue
        resp.raise_for_status()
        return resp.json()
    raise RuntimeError(f"Massive kept saying 'too many requests' for {path}")


def _day(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, timezone.utc).date().isoformat()


def backfill(ticker: str, start: str = "2015-01-01") -> list[dict]:
    """All available daily closes for one stock: [{ticker, day, close}] (split-adjusted)."""
    data = _get(f"/v2/aggs/ticker/{ticker}/range/1/day/{start}/{date.today().isoformat()}",
                {"adjusted": "true", "sort": "asc", "limit": 50000})
    return [{"ticker": ticker, "day": _day(r["t"]), "close": r["c"]} for r in data.get("results") or []]


def one_day(day: str, tickers: set[str]) -> list[dict]:
    """Every tracked stock's close on one trading day, in a single request."""
    data = _get(f"/v2/aggs/grouped/locale/us/market/stocks/{day}", {"adjusted": "true"})
    return [{"ticker": r["T"], "day": day, "close": r["c"]} for r in data.get("results") or [] if r["T"] in tickers]
