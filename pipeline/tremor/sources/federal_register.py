"""FDA advisory committee meetings, from the Federal Register API (no key needed).

When the FDA wants outside experts to weigh in on a drug, it holds an advisory
committee meeting, and it must announce it here at least 15 days ahead.

The meeting summaries don't name the drug, but the API's search looks through the
full text. So we search for our companies' names and drug names:
  1. Search 40 names at once ("A | B | C ...").
  2. Only if something comes back, check those 40 one at a time to see which matched.
"""
import re
from datetime import date, datetime, timedelta

from ..http import get_json

API = "https://www.federalregister.gov/api/v1/documents.json"
MEETING_PHRASE = '"Notice of Meeting" "Advisory Committee"'
LOOKBACK_DAYS = 120
CHUNK = 40

# Drug names too common to mean anything (they show up in almost every cancer trial).
GENERIC_DRUGS = {
    "placebo", "chemotherapy", "standard of care", "best supportive care", "investigator s choice",
    "carboplatin", "cisplatin", "paclitaxel", "docetaxel", "gemcitabine", "pemetrexed", "oxaliplatin",
    "fluorouracil", "5 fu", "capecitabine", "irinotecan", "leucovorin", "cyclophosphamide",
    "doxorubicin", "etoposide", "dexamethasone", "prednisone", "saline", "radiation", "radiotherapy",
    "surgery", "pembrolizumab", "nivolumab", "atezolizumab", "durvalumab", "bevacizumab",
    "trastuzumab", "rituximab", "lenalidomide", "bortezomib", "azacitidine", "fulvestrant",
    "letrozole", "anastrozole", "tamoxifen", "enzalutamide", "abiraterone", "observation",
}


# Everyday words. A "drug name" made only of these (e.g. "Background", "Treatment",
# "Study Drug") would match nearly every FDA notice, so we skip it.
EVERYDAY_WORDS = set("""
background treatment therapy therapies control controls arm arms cohort part phase study drug drugs
investigational product products experimental active comparator regimen regimens agent agents
standard care best supportive physician physicians choice investigator investigators treatment
dose doses dosing level levels low high medium escalation expansion maintenance induction
consolidation adjuvant neoadjuvant first second third line lines early late new other usual
procedure procedures device devices imaging scan biopsy blood sample samples test testing
radiation surgical surgery observation monitoring questionnaire survey visit follow up
group groups patient patients participants subject subjects period periods week weeks day days
oral intravenous subcutaneous single multiple combination combined monotherapy alone only
matching matched vehicle sham none no not applicable intervention interventions
""".split())


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()


# A number followed by a dose unit
DOSE = r"\b\d+(\.\d+)?\s*(mg|mcg|ug|g|kg|ml|m\^?2|iu|units?|%)(?![A-Za-z])"

# Words that describe HOW a drug is given, not WHICH drug. Removed before searching.
DESCRIPTOR_WORDS = r"\b(coformulated|coformulation|combination product|chemotherapy|standard of care|" \
                   r"tablets?|capsules?|injection|infusion|oral|iv|sc|bd|bid|qd|tid|q\d+w|mg|kg|m2|ml|dose)\b"


def split_drug_names(entry: str) -> list[str]:
    """'Cisplatin 75mg/m2 + Pemetrexed' -> ['Cisplatin', 'Pemetrexed']

    Trials often cram several drugs and doses into one entry. We split them apart and
    keep only letters, digits and spaces, because symbols like / + : ^ are search
    commands to the Federal Register and would break the whole search.
    """
    entry = re.sub(r"\(.*?\)", " ", entry or "")                 # drop "(LN-145)" style asides
    pieces = re.split(r"\s*(?:\+|/|;|,|:|\bor\b|\band\b|\bwith\b|\bplus\b)\s*", entry, flags=re.I)
    out = []
    for piece in pieces:
        piece = re.sub(DOSE, " ", piece, flags=re.I)                # "75mg", "200 mg", "10 mg/kg"
        piece = re.sub(DESCRIPTOR_WORDS, " ", piece, flags=re.I)
        piece = re.sub(r"[^A-Za-z0-9 ]+", " ", piece)              # symbols -> spaces ("EXB-101" -> "EXB 101")
        piece = " ".join(piece.split())
        if piece:
            out.append(piece)
    return out


def useful_names(entries: list[str]) -> list[str]:
    """Distinct, specific drug names from a trial's intervention list.
    Drops generic drugs and very short names, which would match everything."""
    out = set()
    for entry in entries:
        for name in split_drug_names(entry):
            words = _norm(name).split()
            if len(name) >= 5 and _norm(name) not in GENERIC_DRUGS and not all(w in EVERYDAY_WORDS for w in words):
                out.add(name)
    return sorted(out)


def safe_term(name: str) -> str:
    """Last line of defense: only letters, digits and spaces ever reach the search."""
    return " ".join(re.sub(r"[^A-Za-z0-9 ]+", " ", name).split())


def _search(term: str, since: str) -> list[dict]:
    data = get_json(API, {
        "conditions[agencies][]": "food-and-drug-administration",
        "conditions[type][]": "NOTICE",
        "conditions[term]": term,
        "conditions[publication_date][gte]": since,
        "per_page": 100,
        "fields[]": ["document_number", "title", "abstract", "dates", "publication_date", "html_url"],
    })
    return data.get("results") or []


def parse_meeting_date(dates_text: str | None) -> str | None:
    """'The meeting will be held on April 30, 2026, from 8 a.m...' -> '2026-04-30'"""
    m = re.search(r"(January|February|March|April|May|June|July|August|September|October|November|December)"
                  r"\s+(\d{1,2}),\s+(\d{4})", dates_text or "")
    return datetime.strptime(" ".join(m.groups()), "%B %d %Y").date().isoformat() if m else None


def find_meetings(names_to_tickers: dict[str, set[str]], today: date | None = None) -> list[dict]:
    """Advisory meeting notices that mention any of our names. One row per notice."""
    since = ((today or date.today()) - timedelta(days=LOOKBACK_DAYS)).isoformat()
    names = sorted(n for n in names_to_tickers if safe_term(n))
    found: dict[str, dict] = {}
    for i in range(0, len(names), CHUNK):
        chunk = names[i:i + CHUNK]
        term = f'{MEETING_PHRASE} ({" | ".join(chr(34) + safe_term(n) + chr(34) for n in chunk)})'
        if not _search(term, since):
            continue
        for name in chunk:  # something matched: find out which name(s)
            for doc in _search(f'{MEETING_PHRASE} "{safe_term(name)}"', since):
                row = found.setdefault(doc["document_number"], {
                    "document_number": doc["document_number"],
                    "title": doc["title"],
                    "publication_date": doc["publication_date"],
                    "meeting_date": parse_meeting_date(doc.get("dates")) or parse_meeting_date(doc.get("abstract")),
                    "abstract": doc.get("abstract"),
                    "url": doc["html_url"],
                    "matched_drugs": [], "matched_tickers": [],
                })
                row["matched_drugs"] = sorted(set(row["matched_drugs"]) | {name})
                row["matched_tickers"] = sorted(set(row["matched_tickers"]) | names_to_tickers[name])
    return list(found.values())
