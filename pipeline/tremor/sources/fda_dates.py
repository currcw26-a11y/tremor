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


JUNK = re.compile(r"\bEX-\d+(\.\d+)?\b|\S+\.htm\b|\bExhibit \d+(\.\d+)?\b|^[\d.]+\s", re.I)
EXACT_REACH = 150   # an exact date must start within this many characters after "PDUFA date"/"target action date"
MONTH_REACH = 40    # a month-only date must be even closer ("target action date in March 2027")


def quote(s: str, start: int, end: int, before: int = 120, after: int = 60) -> str:
    """The company's words around the date, cut at word edges, with filing junk ("EX-99.1", file names) removed."""
    lo, hi = max(0, start - before), min(len(s), end + after)
    while lo > 0 and lo < start and s[lo - 1] != " ":
        lo += 1
    while hi < len(s) and hi > end and s[hi - 1] != " ":
        hi -= 1
    text = " ".join(JUNK.sub(" ", s[lo:hi]).split()).strip(" ;,•")
    return ("…" if lo > 0 else "") + text + ("…" if hi < len(s) else "")


def _date(m, precision: str) -> date | None:
    month = MONTHS.index(m.group(1).lower()) + 1
    year = int(m.group(3) if precision == "day" else m.group(2))
    try:
        return date(year, month, int(m.group(2)) if precision == "day" else 1)
    except ValueError:
        return None


# "approved ..., four months ahead of the January 4, 2027, target action date". Lowercase "approved" only,
# so headlines like "Could Become the First FDA-Approved Therapy" don't count.
DECIDED = re.compile(r"\bapproved\b[^.]{0,200}?\b(?:ahead of|prior to|before)\b[^.]{0,40}?" + EXACT.pattern)


def decided_dates(text: str) -> set[date]:
    """Dates the filing says the FDA already acted on early."""
    out = set()
    for m in DECIDED.finditer(re.sub(r"\s+", " ", text)):
        d = _date(EXACT.search(m.group(0)[m.group(0).rfind(m.group(1)):]), "day")
        if d:
            out.add(d)
    return out


def extract_dates(text: str, today: date, also_decided: set[date] | None = None) -> list[dict]:
    """[{'date': '2027-03-15', 'precision': 'day', 'sentence': ...}] for upcoming FDA decision dates.

    Strict on purpose: the date must come right AFTER the words, the way companies announce it
    ("PDUFA target action date of March 15, 2027"). That skips dates of other things in the same
    sentence (an FDA letter, a filing) and drugs approved early ("approved ahead of its January 4 date")."""
    out, seen = [], set()
    parts = sentences(text)
    # A date the filing says the FDA already acted on ("approved ... ahead of the January 4, 2027 date")
    # is dropped everywhere in the filing, even where another sentence still lists it as upcoming.
    decided = decided_dates(text) | (also_decided or set())
    for s in parts:
        if len(s) > 2000:
            continue
        for t in TRIGGER.finditer(s):
            if PAST.search(s[:t.start()]):
                continue   # "...was approved, ahead of its PDUFA date of ..."
            window = s[t.end():t.end() + EXACT_REACH]
            m, precision = EXACT.search(window), "day"
            if not m:
                m, precision = MONTH_ONLY.search(window[:MONTH_REACH + 20]), "month"
                if not m or m.start() > MONTH_REACH:
                    continue
            d = _date(m, precision)
            if not d or d in decided:
                continue
            # Upcoming only (a month-only date counts while that month isn't over); and not absurdly far out
            last_day = d if precision == "day" else (d.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
            if last_day < today or d > today + timedelta(days=730) or (d, precision) in seen:
                continue
            seen.add((d, precision))
            out.append({"date": d.isoformat(), "precision": precision,
                        "sentence": quote(s, t.start(), t.end() + m.end())})
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
