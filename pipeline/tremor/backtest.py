"""The backtest: what happened after past warning signs?

For each past warning sign at a (smaller) company, look 12 months ahead:
  bad     -> one of the company's trials was stopped early in that window (the spec's definition of bad news)
  fine    -> 12 months passed and no trial was stopped
  unknown -> the sign is less than 12 months old, so it's too early to tell (left out of the counts)

For comparison, the same check from random dates ("baseline"): biotech is risky, so a warning sign only
means something if bad news follows it MORE often than it follows any random day.

Stock move on the news: official trial dates and public announcements can differ by weeks, so the news
day comes from the company's own 8-K filings that mention the drug (found with SEC full-text search).
Among those filing days, the one the stock reacted to most is the news day, and the move is measured
from the close the day before to the close the day after. No matching filing -> move unknown (we don't guess).

Everything here is plain math on data it's given, so it's easy to test.
"""
import re
import statistics
from bisect import bisect_left
from datetime import date, timedelta

WINDOW_DAYS = 365
FILING_LAG_DAYS = 4
# Where to look for the announcement, around the trial's official date (days before, days after)
STOP_NEWS_WINDOW = (60, 120)        # stops are often announced before the record changes, sometimes after
RESULTS_NEWS_WINDOW = (30, 365)     # results usually come out in the months after a trial finishes

SAFETY_EFFICACY = re.compile(r"safety|toxicit|adverse|efficacy|futility|lack of (benefit|response|activity)|"
                             r"interim analysis|did not meet|unfavorable|insufficient (efficacy|activity)|risk", re.I)
BUSINESS = re.compile(r"business|strateg|portfolio|sponsor('s)? decision|priorit|commercial|funding|financ|"
                      r"company decision|development program|pipeline", re.I)
ENROLLMENT = re.compile(r"enrol|accrual|recruit|slow", re.I)


# "not related to safety", "not due to any safety concerns": these say the OPPOSITE of a safety problem
NOT_SAFETY = re.compile(r"\b(not|no|unrelated to|without)\b[^.;]{0,60}?\b(safety|efficacy|toxicit\w*|adverse)\w*", re.I)


def stop_reason(why: str | None) -> str:
    """Sort the company's stated reason for stopping a trial into a plain bucket."""
    why = NOT_SAFETY.sub(" ", why or "")
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

    def biggest_move_near(self, day: date, before: int, after: int):
        """(trading day, % move) for the biggest one-day move from `before` days before to `after` days after."""
        lo = bisect_left(self.days, day - timedelta(days=before))
        hi = bisect_left(self.days, day + timedelta(days=after + 1))
        best = None
        for i in range(max(lo, 1), min(hi, len(self.days) - 1)):
            one_day = self.closes[i] / self.closes[i - 1] - 1 if self.closes[i - 1] > 0 else 0
            if best is None or abs(one_day) > best[0]:
                best = (abs(one_day), i)
        if best is None:
            return None, None
        return self.days[best[1]], self.move_around(best[1])

    def move_on_filing(self, filed: date):
        """A press release usually comes out the same day as its 8-K, or up to 4 days before it (8-Ks are
        due within 4 business days), and after-hours news moves the stock the next morning."""
        return self.biggest_move_near(filed, before=FILING_LAG_DAYS, after=1)


def news_move(filing_days: list[date], prices: "Prices | None"):
    """(news day, % move): of the company's filings about this drug, the one the stock reacted to most."""
    if not prices or not filing_days:
        return None, None
    best = (None, None)
    for f in sorted(set(filing_days)):
        day, move = prices.move_on_filing(f)
        if move is not None and (best[1] is None or abs(move) > abs(best[1])):
            best = (day, move)
    return best


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
                completions: dict[str, list[date]], news: dict[tuple[str, date], tuple], today: date) -> list[dict]:
    """One row per past warning sign, with what happened next.
    `news` maps (ticker, official trial date) -> (news day, % move) from news_move()."""
    cases = []
    for ticker, days in signals.items():
        for d in sorted(set(days)):
            outcome, event_day = outcome_after(d, stops.get(ticker, []), completions.get(ticker, []), today)
            news_day, move = news.get((ticker, event_day), (None, None)) if event_day else (None, None)
            cases.append({"signal_type": signal_type, "ticker": ticker, "signal_day": d.isoformat(),
                          "outcome": outcome, "news_day": news_day.isoformat() if news_day else None,
                          "move_pct": move,
                          # for 'bad': the day the trial was stopped (official record); for 'fine': first completion
                          "detail": event_day.isoformat() if event_day else None})
    return cases


def baseline_bad_share(tickers: list[str], stops: dict[str, list[date]], starts: dict[str, date],
                       today: date) -> float | None:
    """How often a trial stop follows a RANDOM day (the 1st of every month) within 12 months.
    Each company counts only from `starts[ticker]` (when it was trading), so years before a company
    existed don't make random days look safer than they are."""
    bad = total = 0
    for t in tickers:
        if t not in starts:
            continue
        d = (starts[t].replace(day=1) + timedelta(days=32)).replace(day=1) if starts[t].day > 1 else starts[t]
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
    bad_moves = [c["move_pct"] for c in bad if c["move_pct"] is not None]
    fine_moves = [c["move_pct"] for c in fine if c["move_pct"] is not None]
    return {
        "signal_type": signal_type, "cases": len(resolved), "bad": len(bad), "fine": len(fine),
        "typical_bad_move": median(bad_moves), "typical_fine_move": median(fine_moves),
        "bad_moves": len(bad_moves), "fine_moves": len(fine_moves),
        "baseline_bad_share": baseline, "confidence": confidence(len(resolved)), "notes": notes or None,
    }
