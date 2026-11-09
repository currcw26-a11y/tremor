"""Layoff notices ("WARN notices"): most states make big employers file a public notice before mass
layoffs. The open-source warn-scraper package downloads each state's list; we keep the ones that
match a company Tremor tracks.

Each state names its columns differently, so we find columns by keywords.
"""
import csv
import re
from datetime import date, datetime
from pathlib import Path

COMPANY = re.compile(r"company|employer|business|organization|^name$", re.I)
DATE = re.compile(r"notice.*date|date.*notice|received|date", re.I)
EMPLOYEES = re.compile(r"employees|affected|workers|layoff|number|total", re.I)
LOCATION = re.compile(r"city|location|county|address|region", re.I)
NOT_EMPLOYEES = re.compile(r"union|represented|bumping|date", re.I)

DATE_FORMATS = ["%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y", "%Y-%m-%d %H:%M:%S", "%m-%d-%Y", "%B %d, %Y", "%d-%b-%y", "%b %d, %Y"]


def _pick(headers: list[str], pattern, exclude=None) -> str | None:
    for h in headers:
        if pattern.search(h or "") and not (exclude and exclude.search(h or "")):
            return h
    return None


def parse_date(text: str) -> date | None:
    text = (text or "").strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text[:len(datetime.now().strftime(fmt)) + 4].strip(), fmt).date()
        except ValueError:
            continue
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", text)
    return date(int(m[3]), int(m[1]), int(m[2])) if m else None


def parse_int(text: str) -> int | None:
    m = re.search(r"\d[\d,]*", str(text or ""))
    return int(m.group().replace(",", "")) if m else None


def read_state_csv(path: Path, state: str) -> list[dict]:
    """Rows as {state, company_name, notice_date, employees, location} from one state's file."""
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        company = _pick(headers, COMPANY, re.compile(r"union|address|city", re.I))
        when = _pick(headers, re.compile(r"notice.*date|date.*notice|received", re.I)) or _pick(headers, DATE)
        count = _pick(headers, EMPLOYEES, NOT_EMPLOYEES)
        where = _pick(headers, LOCATION)
        if not company:
            return []
        rows = []
        for r in reader:
            name = (r.get(company) or "").strip()
            if name:
                rows.append({"state": state.upper(), "company_name": name,
                             "notice_date": parse_date(r.get(when, "")) if when else None,
                             "employees": parse_int(r.get(count, "")) if count else None,
                             "location": (r.get(where) or "").strip()[:120] if where else None})
        return rows


INDUSTRY_WORDS = re.compile(r"therapeutic|bio|pharma|science|medicine|oncology|immuno|genetic", re.I)


def _plain(name: str) -> str:
    """'Merck & Co., Inc.' -> 'merck' ; 'Novartis Group' -> 'novartis' (drops legal words like Inc, Co, Group)."""
    from ..matching import LEGAL_WORDS
    words = re.sub(r"[^a-z0-9 ]", " ", name.lower().replace("&", " ")).split()
    return " ".join(w for w in words if w not in LEGAL_WORDS | {"group", "usa", "us", "and", "corp", "corporation"})


def match(rows: list[dict], companies: dict[str, dict], since: date) -> list[dict]:
    """Keep recent notices from tracked companies.

    companies: {core_name: {"ticker": ..., "name": official SEC name}}
    A notice counts only if its name matches the company's official name, or it shares the core name AND
    sounds like a drug company. (Bare "Compass" or "Obsidian" turned out to be other companies.)
    """
    from ..matching import core_name
    out = []
    for r in rows:
        if r["notice_date"] and r["notice_date"] < since:
            continue
        c = companies.get(core_name(r["company_name"]))
        if not c:
            continue
        same_name = _plain(r["company_name"]) == _plain(c["name"])
        if same_name or INDUSTRY_WORDS.search(r["company_name"]):
            out.append({**r, "ticker": c["ticker"]})
    return out


def scrape_states(states: list[str], work_dir: Path) -> tuple[list[dict], dict[str, str]]:
    """Run warn-scraper for each state. Returns (rows, {state: error}) — one broken state never stops the rest."""
    from warn.runner import Runner
    runner = Runner(data_dir=work_dir / "data", cache_dir=work_dir / "cache")
    rows, errors = [], {}
    for st in states:
        try:
            rows += read_state_csv(Path(runner.scrape(st)), st)
        except Exception as err:  # state websites change often
            errors[st] = str(err)[:200]
    return rows, errors
