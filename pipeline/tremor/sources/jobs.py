"""Job postings from public job-board APIs (no key): Greenhouse, Lever, Ashby.

Hiring for clinical roles slowing sharply can be an early sign a company is pulling back on a trial.
We count each company's open jobs once a day: all jobs, and "clinical" ones (trials, medical,
regulatory, drug safety, biostatistics).
"""
import re

import requests

from .. import settings
from ..http import get_json

CLINICAL = re.compile(r"clinical|medical|regulatory|trial|biostat|pharmacovigilance|drug safety|"
                      r"\bcra\b|\bmsl\b|patient safety|clin ops|translational", re.I)


def _get(url: str):
    """Returns parsed JSON, or None if the board doesn't exist."""
    resp = requests.get(url, headers={"User-Agent": settings.user_agent()}, timeout=30)
    if resp.status_code in (404, 400):
        return None
    resp.raise_for_status()
    return resp.json()


def fetch_jobs(provider: str, board: str) -> list[dict]:
    """[{title, department}] for every open job on a company's board."""
    if provider == "greenhouse":
        data = get_json(f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs")
        return [{"title": j.get("title", ""), "department": " ".join(d.get("name", "") for d in j.get("departments") or [])}
                for j in data.get("jobs", [])]
    if provider == "lever":
        data = get_json(f"https://api.lever.co/v0/postings/{board}", {"mode": "json"})
        return [{"title": j.get("text", ""), "department": (j.get("categories") or {}).get("team") or ""} for j in data]
    if provider == "ashby":
        data = get_json(f"https://api.ashbyhq.com/posting-api/job-board/{board}")
        return [{"title": j.get("title", ""), "department": j.get("department") or ""} for j in data.get("jobs", [])]
    raise ValueError(provider)


def count(jobs: list[dict]) -> tuple[int, int]:
    """(all jobs, clinical jobs)"""
    clinical = sum(bool(CLINICAL.search(f"{j['title']} {j['department']}")) for j in jobs)
    return len(jobs), clinical


def slug_candidates(company_name: str, core: str) -> list[str]:
    """Board names to try, e.g. 'Iovance Biotherapeutics, Inc.' -> ['iovancebiotherapeutics', 'iovance', ...]"""
    legal = re.sub(r"\b(inc|incorporated|corp|corporation|co|ltd|limited|llc|plc|sa|ag|nv|se|holdings|group)\b\.?", "",
                   company_name.lower())
    full = re.sub(r"[^a-z0-9]", "", legal)
    core_slug = re.sub(r"[^a-z0-9]", "", core)
    out = [full, core_slug, core_slug + "therapeutics"]
    return list(dict.fromkeys(s for s in out if len(s) >= 4))


def find_board(company_name: str, core: str) -> dict | None:
    """Try each job site with each likely board name. Greenhouse tells us the company's name, so those
    matches can be checked automatically; Lever/Ashby matches need a human to confirm."""
    for slug in slug_candidates(company_name, core):
        gh = _get(f"https://boards-api.greenhouse.io/v1/boards/{slug}")
        if gh:
            auto = auto_confirm(company_name, slug, gh.get("name") or "")
            return {"provider": "greenhouse", "board": slug, "board_name": gh.get("name"), "auto_ok": auto}
        lv = _get(f"https://api.lever.co/v0/postings/{slug}?mode=json")
        if lv:
            return {"provider": "lever", "board": slug, "board_name": "", "auto_ok": False}
        ab = _get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}")
        if ab and ab.get("jobs") is not None:
            return {"provider": "ashby", "board": slug, "board_name": "", "auto_ok": False}
    return None


BIOTECH_WORDS = re.compile(r"therapeutic|bio|pharma|medicine|oncology|science|immuno|genetic|thera", re.I)


def auto_confirm(company_name: str, slug: str, board_name: str) -> bool:
    """Only trust a match without a human check if the board uses the company's FULL name, or the board's
    own name sounds like a biotech. Short names like "Aura" or "Kodiak" belong to many companies
    (a tech startup and a self-driving truck company, in Tremor's first search)."""
    full = slug_candidates(company_name, "")[0] if slug_candidates(company_name, "") else ""
    return slug == full or bool(BIOTECH_WORDS.search(board_name))
