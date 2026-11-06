"""Suggest which stock ticker each trial sponsor belongs to.

Trial sponsors and SEC companies spell names differently:
    "Regeneron Pharmaceuticals"  vs  "REGENERON PHARMACEUTICALS, INC."
So we boil each name down to its "core" (drop Inc, Ltd, Pharmaceuticals...) and compare.

These are only SUGGESTIONS. Nothing is used for tracking until you mark it confirmed=yes
in pipeline/data/sponsor_tickers.csv.

Run:  python -m tremor.matching
"""
import csv
import re
from collections import Counter
from pathlib import Path

from rapidfuzz import fuzz

DATA = Path(__file__).resolve().parents[1] / "data"
SUGGESTIONS_CSV = DATA / "sponsor_tickers.csv"
UNMATCHED_CSV = DATA / "unmatched_sponsors.csv"
ALIASES_CSV = DATA / "sponsor_aliases.csv"
CSV_COLUMNS = ["sponsor_name", "trials", "ticker", "sec_company_name", "how_matched", "score", "confirmed", "notes"]

# Words that don't help tell companies apart. Removed before comparing.
FILLER_WORDS = {
    "inc", "incorporated", "corp", "corporation", "co", "company", "ltd", "limited", "llc", "lp", "plc",
    "sa", "ag", "ab", "nv", "se", "spa", "as", "gmbh", "kk", "the", "and",
    "holdings", "holding", "group", "global", "international", "us", "usa",
    "pharmaceutical", "pharmaceuticals", "pharma", "therapeutics", "biotherapeutics", "biosciences",
    "bioscience", "biotech", "biotechnology", "biopharma", "biopharmaceuticals", "biologics", "bio",
    "oncology", "medicines", "medical", "sciences", "research", "development", "labs", "laboratories",
}
FUZZY_CUTOFF = 92  # out of 100. Lower = more matches but more wrong ones.


def _clean(name: str) -> str:
    """Lowercase, drop SEC state tags like ' / MA' or '/DE/', turn punctuation into spaces."""
    name = re.sub(r"\s*/\s*[a-z]{2}\s*/?\s*$", "", name.lower())
    return re.sub(r"[^a-z0-9 ]", " ", name.replace("&", " and "))


def core_name(name: str) -> str:
    """'Regeneron Pharmaceuticals, Inc.' -> 'regeneron'"""
    words = _clean(name).split()
    return " ".join(w for w in words if w not in FILLER_WORDS)


def load_aliases() -> list[dict]:
    with open(ALIASES_CSV, newline="") as f:
        return list(csv.DictReader(f))


LEGAL_WORDS = {"inc", "incorporated", "corp", "corporation", "co", "company", "ltd", "limited", "llc",
               "lp", "plc", "sa", "ag", "ab", "nv", "se", "spa", "as", "gmbh", "kk", "the", "holdings"}


def _legal_stripped(name: str) -> str:
    """'Compass Therapeutics, Inc.' -> 'compass therapeutics' (keeps words like Therapeutics)."""
    words = _clean(name).split()
    return " ".join(w for w in words if w not in LEGAL_WORDS)


def suggest(sponsor: str, companies: list[dict], aliases: list[dict], core_index: dict,
            is_healthcare=lambda cik: True) -> dict | None:
    """Return {ticker, sec_company_name, how_matched, score, notes} or None if no good match.

    is_healthcare(cik) checks the SEC industry code, so a biotech never matches an airline.
    """
    lowered = sponsor.lower()
    by_ticker = {c["ticker"]: c for c in companies}

    # 1. Known subsidiaries / old names (hand-written list). Whole words only,
    #    so "immunogen" doesn't match "ImmunoGenesis".
    for a in aliases:
        if re.search(rf"\b{re.escape(a['sponsor_name_contains'])}\b", lowered) and a["ticker"] in by_ticker:
            return {"ticker": a["ticker"], "sec_company_name": by_ticker[a["ticker"]]["name"],
                    "how_matched": "known alias", "score": 100, "notes": a["why"]}

    core = core_name(sponsor)
    if len(core) < 3:
        return None  # nothing distinctive left to compare

    # 2. Same core name, or 3. very similar core name (typos, "Bristol-Myers" vs "Bristol Myers")
    candidates = [(c, "same name") for c in core_index.get(core, [])]
    if not candidates:
        for c_core, cs in core_index.items():
            if abs(len(c_core) - len(core)) <= 6 and fuzz.ratio(core, c_core) >= FUZZY_CUTOFF:
                candidates += [(c, "similar name") for c in cs]

    # Several companies can share a core name ("Vertex Pharmaceuticals" vs "Vertex, Inc.").
    # Keep healthcare companies only, then pick the one whose full name is closest.
    best, best_score, how = None, -1, ""
    for c, method in candidates:
        if not is_healthcare(c["cik"]):
            continue
        score = fuzz.token_sort_ratio(_legal_stripped(sponsor), _legal_stripped(c["name"]))
        if score > best_score:
            best, best_score, how = c, score, method
    if best is None:
        return None
    note = "" if best_score >= 70 else "names only partly match, double-check"
    return {"ticker": best["ticker"], "sec_company_name": best["name"], "how_matched": how,
            "score": round(best_score), "notes": note}


def _read_existing() -> dict[str, dict]:
    if not SUGGESTIONS_CSV.exists():
        return {}
    with open(SUGGESTIONS_CSV, newline="") as f:
        return {row["sponsor_name"]: row for row in csv.DictReader(f)}


def build_suggestions(sponsor_counts: Counter, companies: list[dict],
                      is_healthcare=lambda cik: True) -> tuple[list[dict], list[dict]]:
    aliases = load_aliases()
    core_index: dict[str, list[dict]] = {}
    for c in companies:
        core_index.setdefault(core_name(c["name"]), []).append(c)
    core_index.pop("", None)

    existing = _read_existing()
    matched, unmatched = [], []
    for sponsor, n in sponsor_counts.most_common():
        if sponsor in existing and existing[sponsor].get("confirmed", "").strip():
            row = existing[sponsor]          # keep your decision; never overwrite it
            row["trials"] = n
            matched.append(row)
            continue
        s = suggest(sponsor, companies, aliases, core_index, is_healthcare)
        if s:
            matched.append({"sponsor_name": sponsor, "trials": n, "confirmed": "", **s})
        else:
            unmatched.append({"sponsor_name": sponsor, "trials": n})
    return matched, unmatched


def write_csv(path: Path, rows: list[dict], columns: list[str]):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def confirmed_matches() -> dict[str, str]:
    """{sponsor_name: ticker} for rows YOU marked confirmed=yes. The only ones used for tracking."""
    return {name: row["ticker"] for name, row in _read_existing().items()
            if row.get("confirmed", "").strip().lower() in {"yes", "y", "true"}}


if __name__ == "__main__":
    from .sources import clinicaltrials, sec

    print("Downloading trials and the SEC company list...")
    counts = Counter(clinicaltrials.summarize(s)["sponsor_name"] for s in clinicaltrials.fetch_cancer_trials())
    companies = sec.listed_companies()
    print("Checking each candidate's SEC industry code (first run takes a minute)...")
    matched, unmatched = build_suggestions(counts, companies, sec.is_healthcare)
    write_csv(SUGGESTIONS_CSV, matched, CSV_COLUMNS)
    write_csv(UNMATCHED_CSV, unmatched, ["sponsor_name", "trials"])
    n_trials = sum(int(r["trials"]) for r in matched)
    print(f"\n{len(matched)} sponsors matched to a Nasdaq/NYSE ticker ({n_trials:,} trials).")
    print(f"{len(unmatched)} sponsors had no match (mostly private or non-US companies).")
    print(f"Suggestions written to {SUGGESTIONS_CSV.relative_to(DATA.parents[1])}")
