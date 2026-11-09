from datetime import date

from tremor.runway import compute

TODAY = date(2026, 11, 9)


def facts(cash, short_term, ocf_ytd, start="2026-01-01", end="2026-09-30", tax="us-gaap"):
    names = {"us-gaap": ("CashAndCashEquivalentsAtCarryingValue", "NetCashProvidedByUsedInOperatingActivities"),
             "ifrs-full": ("CashAndCashEquivalents", "CashFlowsFromUsedInOperatingActivities")}[tax]
    f = {tax: {
        names[0]: {"units": {"USD": [{"end": "2023-12-31", "val": cash * 2, "form": "10-K"},  # an older balance
                                     {"end": end, "val": cash, "form": "10-Q", "filed": "2026-11-05"}]}},
        names[1]: {"units": {"USD": [{"start": start, "end": "2026-03-31", "val": ocf_ytd / 3},  # too short, ignored
                                     {"start": start, "end": end, "val": ocf_ytd}]}},
    }}
    if short_term is not None:
        f["us-gaap"] = f.get("us-gaap", {})
        f["us-gaap"]["ShortTermInvestments"] = {"units": {"USD": [{"end": end, "val": short_term}]}}
        f["us-gaap"]["AvailableForSaleSecuritiesDebtSecuritiesCurrent"] = {"units": {"USD": [{"end": end, "val": short_term}]}}
    return f


def test_small_biotech_runway():
    # Iovance-like: $58M cash + $318M short-term, spent $137M over 9 months
    r = compute(facts(58_000_000, 318_000_000, -137_000_000), TODAY)
    assert r["cash_usd"] == 376_000_000                 # short-term counted once, not twice
    assert 15.0 <= r["monthly_burn_usd"] / 1e6 <= 15.5   # $137M over about 9 months
    assert 24 <= r["runway_months"] <= 25.5
    assert r["burn_period_months"] == 9


def test_profitable_company_has_no_runway_number():
    r = compute(facts(5_000_000_000, None, 1_100_000_000), TODAY)
    assert r["runway_months"] is None and r["monthly_burn_usd"] < 0


def test_foreign_company_reporting_format():
    r = compute(facts(5_700_000_000, None, 14_000_000_000, start="2025-01-01", end="2025-12-31", tax="ifrs-full"), TODAY)
    assert r["cash_usd"] == 5_700_000_000 and r["runway_months"] is None


def test_old_data_is_ignored():
    assert compute(facts(1, None, -1, start="2024-01-01", end="2024-09-30"), TODAY) is None
