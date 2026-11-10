"""FDA decision dates ("PDUFA dates") from companies' own SEC filings.

There's no free official list of when the FDA will decide on each drug, but companies announce
the date in their 8-Ks and quarterly reports ("The FDA assigned a PDUFA target action date of
March 15, 2027"). We find those filings with SEC full-text search and pull the date out with
plain pattern matching, not AI, so a date can never be made up. We keep the company's own
sentence so readers can see exactly where it came from.
"""
import re
from datetime import date, timedelta

from ..http import get_json

FULL_TEXT_SEARCH = "https://efts.sec.gov/LATEST/search-index"
MONTHS = ("january february march april may june july august september october november december").split()
MONTH = r"(January|February|March|April|May|June|July|August|September|October|November|December)"
EXACT = re.compile(MONTH + r"\s+(\d{1,2}),?\s+(20\d\d)")
MONTH_ONLY = re.compile(MONTH + r",?\s+(20\d\d)")
TRIGGER = re.compile(r"PDUFA|Prescription Drug User Fee Act|target action date", re.I)
# Sentences about the past ("approved on", "was granted") don't announce an upcoming decision
PAST = re.compile(r"\b(approved|approval was granted|received approval|granted approval)\b", re.I)


def sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text)
    return re.split(r"(?<=[.;])\s+(?=[A-Z(])", text)


def quote(s: str, start: int, end: int, before: int = 180, after: int = 80) -> str:
    """The company's words around the date, cut at word edges (no filing headers or page junk)."""
    lo, hi = max(0, start - before), min(len(s), end + after)
    while lo > 0 and s[lo - 1] != " ":
        lo += 1
    while hi < len(s) and s[hi - 1] != " " and hi < len(s):
        hi -= 1
    text = s[lo:hi].strip(" ;,")
    return ("…" if lo > 0 else "") + text + ("…" if hi < len(s) else "")


def extract_dates(text: str, today: date) -> list[dict]:
    """[{'date': '2027-03-15', 'precision': 'day', 'sentence': ...}] for upcoming FDA decision dates."""
    out, seen = [], set()
    for s in sentences(text):
        if not TRIGGER.search(s) or len(s) > 2000:
            continue
        if PAST.search(s) and not re.search(r"target action date|PDUFA (goal|date)", s, re.I):
            continue
        found = [(m, "day") for m in EXACT.finditer(s)]
        if not found:
            found = [(m, "month") for m in MONTH_ONLY.finditer(s)]
        for m, precision in found:
            month = MONTHS.index(m.group(1).lower()) + 1
            year = int(m.group(3) if precision == "day" else m.group(2))
            day = int(m.group(2)) if precision == "day" else 1
            try:
                d = date(year, month, day)
            except ValueError:
                continue
            # Upcoming only (a month-only date counts while that month isn't over); and not absurdly far out
            last_day = d if precision == "day" else (d.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
            if last_day < today or d > today + timedelta(days=730):
                continue
            key = (d, precision)
            if key not in seen:
                seen.add(key)
                out.append({"date": d.isoformat(), "precision": precision, "sentence": quote(s, m.start(), m.end())})
    return out


def search(ciks: list[str], since: date, until: date) -> list[dict]:
    """8-Ks and quarterly/annual reports from these companies that mention a PDUFA date."""
    hits = []
    for i in range(0, len(ciks), 40):
        batch = ",".join(c.zfill(10) for c in ciks[i:i + 40])
        offset = 0
        while offset < 1000:
            data = get_json(FULL_TEXT_SEARCH, params={
                "q": '"PDUFA" OR "target action date"', "forms": "8-K,10-Q,10-K", "ciks": batch, "from": offset,
                "dateRange": "custom", "startdt": since.isoformat(), "enddt": until.isoformat()}, cache_hours=20)
            page = data.get("hits", {}).get("hits", [])
            for h in page:
                acc, filename = h["_id"].split(":", 1)
                src = h["_source"]
                cik = str(int(src["ciks"][0]))
                hits.append({"cik": src["ciks"][0], "form": src.get("form"), "filed": src["file_date"],
                             "url": f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-', '')}/{filename}"})
            if len(page) < 100:
                break
            offset += 100
    return hits
