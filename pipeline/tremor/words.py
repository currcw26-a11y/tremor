"""Plain-English helpers shared by emails (and anything else in the pipeline)."""
from datetime import date

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def nice_date(d) -> str:
    """'2027-06' -> 'Jun 2027', '2027-06-15' -> 'Jun 15, 2027'"""
    if not d:
        return "an unknown date"
    parts = str(d)[:10].split("-")
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2:
        return f"{MONTHS[int(parts[1]) - 1]} {parts[0]}"
    return f"{MONTHS[int(parts[1]) - 1]} {int(parts[2])}, {parts[0]}"


def money_left(company: dict) -> str | None:
    """'About 24 months, based on its spending over 9 months up to Sep 30, 2026. ...' (all numbers from SEC data)"""
    months = company.get("runway_months")
    burn = company.get("monthly_burn_usd")
    if company.get("finances_as_of") is None:
        return None
    as_of = nice_date(company["finances_as_of"])
    if months is None:
        if burn is not None and burn <= 0:
            return f"It brings in more cash than it spends on running the business (as of {as_of})."
        return None
    m = round(float(months))
    text = (f"About {m} months, based on its spending over the {company.get('burn_period_months')} months "
            f"up to {as_of}.")
    if m < 18:
        text += (" Companies running low on money often raise more by creating and issuing new shares, "
                 "which usually makes each existing share worth less.")
    return text
