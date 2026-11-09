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
CASH = [("us-gaap", "CashAndCashEquivalentsAtCarryingValue"),
        ("us-gaap", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"),
        ("ifrs-full", "CashAndCashEquivalents")]
SHORT_TERM = [("us-gaap", "ShortTermInvestments"),
              ("us-gaap", "AvailableForSaleSecuritiesDebtSecuritiesCurrent"),
              ("us-gaap", "MarketableSecuritiesCurrent"),
              ("ifrs-full", "CurrentInvestments")]
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


def compute(facts: dict, today: date) -> dict | None:
    """Returns the numbers to store on the company, or None if the data is missing or too old."""
    cash = _latest_point(_values(facts, CASH))
    if not cash or (today - date.fromisoformat(cash["end"])).days > MAX_AGE_DAYS:
        return None
    # Short-term investments on the SAME date. Several names can hold the same number, so take the largest, never add.
    same_day = [v["val"] for opt in SHORT_TERM for v in _values(facts, [opt])
                if "start" not in v and v["end"] == cash["end"]]
    total_cash = cash["val"] + (max(same_day) if same_day else 0)

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
