"""Money left ("cash runway"): how many months a company could keep going at its recent spending rate.

    months left = (cash + short-term investments) / cash used by operations per month

All numbers come from the company's own SEC financial reports (the XBRL "company facts" API).
Companies that bring in more cash from operations than they spend aren't "burning" cash,
so they get no runway number.
"""
from datetime import date

from .http import get_json

# Different companies report the same thing under different names. US companies use "us-gaap",
# foreign companies (like AstraZeneca) use "ifrs-full". We try each in order.
# Companies use different labels for the same thing, and some leave a label at $0 while reporting the
# real number under another one. So we read EVERY cash label on the newest date and take the largest.
CASH = [("us-gaap", "CashAndCashEquivalentsAtCarryingValue"),
        ("us-gaap", "Cash"),
        ("us-gaap", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"),
        ("us-gaap", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsIncludingDisposalGroupAndDiscontinuedOperations"),
        ("ifrs-full", "CashAndCashEquivalents")]
SHORT_TERM = [("us-gaap", "ShortTermInvestments"),
              ("us-gaap", "AvailableForSaleSecuritiesDebtSecuritiesCurrent"),
              ("us-gaap", "MarketableSecuritiesCurrent"),
              ("ifrs-full", "CurrentInvestments")]
# Some companies report "cash + short-term investments" as one number
CASH_AND_SHORT_TERM = [("us-gaap", "CashCashEquivalentsAndShortTermInvestments")]
OPERATING_CASH_FLOW = [("us-gaap", "NetCashProvidedByUsedInOperatingActivities"),
                       ("ifrs-full", "CashFlowsFromUsedInOperatingActivities")]
MAX_AGE_DAYS = 460  # ignore numbers older than ~15 months


def _values(facts: dict, options: list) -> list[dict]:
    for tax, concept in options:
        units = facts.get(tax, {}).get(concept, {}).get("units", {})
        if "USD" in units:
            return units["USD"]
    return []


def _latest_point(values: list[dict]) -> dict | None:
    """Most recent balance (a value at one date), preferring the latest filing for that date."""
    pts = [v for v in values if "start" not in v]
    return max(pts, key=lambda v: (v["end"], v.get("filed", ""))) if pts else None


def _months(start: str, end: str) -> float:
    return (date.fromisoformat(end) - date.fromisoformat(start)).days / 30.44


def _recent_spending(values: list[dict]) -> dict | None:
    """The most recent period of 6-12 months (e.g. 'Jan-Sep this year' or 'last full year')."""
    periods = [v for v in values if "start" in v and 5.5 <= _months(v["start"], v["end"]) <= 12.5]
    return max(periods, key=lambda v: (v["end"], _months(v["start"], v["end"]), v.get("filed", ""))) if periods else None


def _balances_on(facts: dict, options: list, day: str) -> list[float]:
    return [v["val"] for opt in options for v in _values(facts, [opt]) if "start" not in v and v["end"] == day]


def compute(facts: dict, today: date) -> dict | None:
    """Returns the numbers to store on the company, or None if the data is missing or too old."""
    latest = [_latest_point(_values(facts, [opt])) for opt in CASH]
    latest = [p for p in latest if p]
    if not latest:
        return None
    day = max(p["end"] for p in latest)
    if (today - date.fromisoformat(day)).days > MAX_AGE_DAYS:
        return None
    form = next(p.get("form") for p in latest if p["end"] == day)
    cash_now = max(_balances_on(facts, CASH, day))
    short_term = max(_balances_on(facts, SHORT_TERM, day) or [0])
    combined = max(_balances_on(facts, CASH_AND_SHORT_TERM, day) or [0])
    total_cash = max(cash_now + short_term, combined)
    cash = {"end": day, "form": form}

    spending = _recent_spending(_values(facts, OPERATING_CASH_FLOW))
    if not spending or (today - date.fromisoformat(spending["end"])).days > MAX_AGE_DAYS:
        return {"cash_usd": total_cash, "monthly_burn_usd": None, "runway_months": None,
                "finances_as_of": cash["end"], "burn_period_months": None, "finances_form": cash.get("form")}
    months = _months(spending["start"], spending["end"])
    burn = -spending["val"] / months  # operating cash flow is negative when a company is spending
    return {
        "cash_usd": total_cash,
        "monthly_burn_usd": round(burn),
        "runway_months": round(total_cash / burn, 1) if burn > 0 else None,
        "finances_as_of": cash["end"],
        "burn_period_months": round(months),
        "finances_form": cash.get("form"),
    }


def fetch_and_compute(cik: str, today: date | None = None) -> dict | None:
    facts = get_json(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json", cache_hours=24)["facts"]
    return compute(facts, today or date.today())
