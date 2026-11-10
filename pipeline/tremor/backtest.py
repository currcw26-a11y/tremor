"""The backtest: what happened after past warning signs?

For each past warning sign at a (smaller) company, look 12 months ahead:
  bad     -> one of the company's trials was stopped early in that window (the spec's definition of bad news)
  fine    -> 12 months passed and no trial was stopped
  unknown -> the sign is less than 12 months old, so it's too early to tell (left out of the counts)

For comparison, the same check from random dates ("baseline"): biotech is risky, so a warning sign only
means something if bad news follows it MORE often than it follows any random day.

Stock move on the news: close the day before -> close the day after the biggest one-day move near the
event (official stop dates and public announcements can differ by weeks).

Everything here is plain math on data it's given, so it's easy to test.
"""
import re
import statistics
from bisect import bisect_left
from datetime import date, timedelta

WINDOW_DAYS = 365
NEWS_BEFORE_DAYS = 14   # look for the news this long before the official date...
NEWS_AFTER_DAYS = 90    # ...and this long after (announcements often come later)

SAFETY_EFFICACY = re.compile(r"safety|toxicit|adverse|efficacy|futility|lack of (benefit|response|activity)|"
                             r"interim analysis|did not meet|unfavorable|insufficient (efficacy|activity)|risk", re.I)
BUSINESS = re.compile(r"business|strateg|portfolio|sponsor('s)? decision|priorit|commercial|funding|financ|"
                      r"company decision|development program|pipeline", re.I)
ENROLLMENT = re.compile(r"enrol|accrual|recruit|slow", re.I)


def stop_reason(why: str | None) -> str:
    """Sort the company's stated reason for stopping a trial into a plain bucket."""
    why = why or ""
    if SAFETY_EFFICACY.search(why):
        return "safety_or_efficacy"
    if BUSINESS.search(why):
        return "business"
    if ENROLLMENT.search(why):
        return "enrollment"
    return "other"


def confidence(n: int) -> str:
    return "low" if n < 10 else "medium" if n < 30 else "high"


class Prices:
    """One company's closing prices, for measuring moves around news."""

    def __init__(self, rows: list[dict]):
        rows = sorted(rows, key=lambda r: r["day"])
        self.days = [date.fromisoformat(str(r["day"])[:10]) for r in rows]
        self.closes = [float(r["close"]) for r in rows]

    def move_around(self, i: int) -> float | None:
        """% change from the close before trading day i to the close after it."""
        if i < 1 or i + 1 >= len(self.closes) or self.closes[i - 1] <= 0:
            return None
        return round((self.closes[i + 1] / self.closes[i - 1] - 1) * 100, 1)

    def biggest_move_near(self, day: date, before: int = NEWS_BEFORE_DAYS, after: int = NEWS_AFTER_DAYS):
        """(news day, % move) for the biggest one-day move between `before` days before and `after` days after."""
        lo = bisect_left(self.days, day - timedelta(days=before))
        hi = bisect_left(self.days, day + timedelta(days=after))
        best = None
        for i in range(max(lo, 1), min(hi, len(self.days) - 1)):
            one_day = self.closes[i] / self.closes[i - 1] - 1 if self.closes[i - 1] > 0 else 0
            if best is None or abs(one_day) > best[0]:
                best = (abs(one_day), i)
        if best is None:
            return None, None
        return self.days[best[1]], self.move_around(best[1])


def outcome_after(day: date, stops: list[date], completions: list[date], today: date):
    """('bad'|'fine'|'unknown', the event day that decided it)."""
    end = day + timedelta(days=WINDOW_DAYS)
    stopped = [s for s in stops if day < s <= end]
    if stopped:
        return "bad", min(stopped)
    if end > today:
        return "unknown", None
    done = [c for c in completions if day < c <= end]
    return "fine", (min(done) if done else None)


def build_cases(signal_type: str, signals: dict[str, list[date]], stops: dict[str, list[date]],
                completions: dict[str, list[date]], prices: dict[str, Prices], today: date) -> list[dict]:
    """One row per past warning sign, with what happened next."""
    cases = []
    for ticker, days in signals.items():
        for d in sorted(set(days)):
            outcome, event_day = outcome_after(d, stops.get(ticker, []), completions.get(ticker, []), today)
            news_day = move = None
            if event_day and ticker in prices:
                news_day, move = prices[ticker].biggest_move_near(event_day)
            cases.append({"signal_type": signal_type, "ticker": ticker, "signal_day": d.isoformat(),
                          "outcome": outcome, "news_day": news_day.isoformat() if news_day else None,
                          "move_pct": move})
    return cases


def baseline_bad_share(tickers: list[str], stops: dict[str, list[date]], start: date, today: date) -> float | None:
    """How often a trial stop follows a RANDOM day (the 1st of every month) within 12 months."""
    bad = total = 0
    for t in tickers:
        d = start
        while d + timedelta(days=WINDOW_DAYS) <= today:
            total += 1
            bad += any(d < s <= d + timedelta(days=WINDOW_DAYS) for s in stops.get(t, []))
            d = (d.replace(day=1) + timedelta(days=32)).replace(day=1)
    return round(bad / total, 3) if total else None


def summarize(signal_type: str, cases: list[dict], baseline: float | None, notes: str = "") -> dict:
    resolved = [c for c in cases if c["outcome"] in ("bad", "fine")]
    bad = [c for c in resolved if c["outcome"] == "bad"]
    fine = [c for c in resolved if c["outcome"] == "fine"]
    median = lambda xs: round(statistics.median(xs), 1) if xs else None  # noqa: E731
    return {
        "signal_type": signal_type, "cases": len(resolved), "bad": len(bad), "fine": len(fine),
        "typical_bad_move": median([c["move_pct"] for c in bad if c["move_pct"] is not None]),
        "typical_fine_move": median([c["move_pct"] for c in fine if c["move_pct"] is not None]),
        "baseline_bad_share": baseline, "confidence": confidence(len(resolved)), "notes": notes or None,
    }
