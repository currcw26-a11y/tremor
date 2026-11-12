"""Why the FDA says no: the FDA's published rejection letters ("complete response letters"), sorted by what
each letter asks the company to fix. Not a live signal (the spec says so); it feeds the "When the FDA says no"
step of the Learn page.

    python -m tremor.crl     # downloads the letters and writes web/lib/fda-letters.json (commit it)

Re-run now and then (the FDA publishes new letters in batches). Sorting uses the FDA's own section headings, plus a
few unmistakable phrases for letters whose headings didn't survive the scan. "Safety update" and labeling sections
are left out: almost every letter has them as routine instructions.
"""
import json
import re
from datetime import date
from pathlib import Path

from .http import get_json

URL = "https://api.fda.gov/transparency/crl.json"
OUT = Path(__file__).resolve().parents[2] / "web" / "lib" / "fda-letters.json"

# How the medicine is made: factory inspections, product quality, sterility, the device that delivers it
MAKING_HEADINGS = {"FACILITY INSPECTIONS", "FACILITIES", "PRODUCT QUALITY", "PRODUCT QUALITY MICROBIOLOGY",
                   "MICROBIOLOGY", "DEVICE", "HUMAN FACTORS", "DRUG PRODUCT", "DRUG SUBSTANCE", "MANUFACTURING"}
MAKING_WORDS = re.compile(r"objectionable conditions|Form FDA 483|deficiencies (were )?(observed|identified) during "
                          r"(the )?inspection", re.I)
# The evidence: whether the trials (or lab and animal studies) show the drug works and is safe enough
EVIDENCE_HEADINGS = {"CLINICAL", "CLINICAL/STATISTICAL", "CLINICAL PHARMACOLOGY", "CLINICAL/CLINICAL PHARMACOLOGY",
                     "NONCLINICAL", "SAFETY", "EFFICACY", "STATISTICAL", "CLINICAL SAFETY", "CLINICAL EFFICACY",
                     "BIOPHARMACEUTICS", "PHARMACOLOGY/TOXICOLOGY"}
EVIDENCE_WORDS = re.compile(r"substantial evidence of effectiveness|adequate and well[- ]controlled|"
                            r"(did not|failed to) (meet|demonstrate|show|establish)|"
                            r"(conduct|need|require)\w* (an )?(additional|new|another) (adequate and well-controlled |"
                            r"randomized |clinical )?(trial|study)", re.I)


def headings(text: str) -> set[str]:
    return {m.strip() for m in re.findall(r"\n\s*([A-Z][A-Z /&,\-]{3,60})\n", text or "")}


def reasons(letter: dict) -> set[str]:
    """{'making', 'evidence'}, either, or neither, for one letter."""
    text = letter.get("text") or ""
    h = headings(text)
    out = set()
    if h & MAKING_HEADINGS or MAKING_WORDS.search(text):
        out.add("making")
    if h & EVIDENCE_HEADINGS or EVIDENCE_WORDS.search(text):
        out.add("evidence")
    return out


def summarize(letters: list[dict], today: date | None = None) -> dict:
    today = today or date.today()
    sorted_ = [reasons(x) for x in letters]
    years = sorted(int(x["letter_year"]) for x in letters if str(x.get("letter_year") or "").isdigit())
    unapproved = [x for x in letters if x.get("approval_status") == "Unapproved"]
    recent_from = today.year - 2
    return {
        "total": len(letters),
        "first_year": years[0] if years else None, "last_year": years[-1] if years else None,
        "making": sum("making" in r for r in sorted_),
        "evidence": sum("evidence" in r for r in sorted_),
        "both": sum(r == {"making", "evidence"} for r in sorted_),
        "neither": sum(not r for r in sorted_),
        "approved_later": sum(x.get("approval_status") == "Approved" for x in letters),
        "not_yet_approved": len(unapproved),
        "not_yet_recent": sum(str(x.get("letter_year") or "") >= str(recent_from) for x in unapproved),
        "recent_from": recent_from,
        "updated": today.isoformat(),
    }


def fetch() -> list[dict]:
    out, skip = [], 0
    while True:
        data = get_json(URL, params={"limit": 1000, "skip": skip}, cache_hours=24)
        out += data.get("results", [])
        total = data.get("meta", {}).get("results", {}).get("total", 0)
        skip += 1000
        if skip >= total:
            return out


if __name__ == "__main__":
    summary = summarize(fetch())
    OUT.write_text(json.dumps(summary, indent=2) + "\n")
    print(summary)
