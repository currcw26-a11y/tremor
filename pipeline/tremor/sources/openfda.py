"""Which medicines a company already has FDA approval for, from openFDA's Drugs@FDA (free, no key).

Used for "how much rides on this trial": a company with no approved medicines lives or dies by its trials.

Matching companies to the FDA's sponsor names is tricky (the FDA writes "KARYOPHARM THERAPS", "MERCK SHARP
DOHME"...), so names are kept in pipeline/data/fda_sponsors.csv. A name is used only when its status is
"confirmed": automatically when it's the same name once abbreviations and legal endings are removed, otherwise
after a person checks it.

Limit: Drugs@FDA covers medicines approved by the FDA's drug center. Cell and gene therapies (like CAR-T) and
vaccines are approved by a different office and aren't in it.
"""
import re

from ..http import get_json

BASE = "https://api.fda.gov/drug/drugsfda.json"

# FDA abbreviations -> full words, then words that don't identify a company
_ABBREV = {"PHARMS": "PHARMACEUTICALS", "PHARM": "PHARMACEUTICALS", "THERAPS": "THERAPEUTICS",
           "THERAP": "THERAPEUTICS", "BIOPHARMS": "BIOPHARMACEUTICALS", "BIOTECH": "BIOTECHNOLOGY", "LABS": "LABORATORIES"}
_GENERIC = {"THE", "AND", "INC", "CORP", "CORPORATION", "CO", "COMPANY", "LTD", "LIMITED", "LLC", "LP", "PLC", "SA", "AG",
            "NV", "AB", "AS", "SE", "GMBH", "US", "USA", "NA", "HOLDINGS", "GROUP", "GLOBAL", "PHARMACEUTICALS", "PHARMACEUTICAL", "PHARMA", "BIO",
            "THERAPEUTICS", "BIOPHARMACEUTICALS", "BIOPHARMA", "BIOSCIENCES", "BIOSCIENCE", "BIOTHERAPEUTICS",
            "BIOTECHNOLOGY", "BIOLOGICS", "ONCOLOGY", "MEDICINES", "LABORATORIES", "RESEARCH", "SCIENCES", "SYSTEMS"}


def core(name: str) -> str:
    """'KARYOPHARM THERAPS' and 'Karyopharm Therapeutics Inc.' -> 'KARYOPHARM'."""
    words = re.sub(r"[^A-Z0-9 ]", " ", (name or "").upper().replace("&", " AND ").replace("A/S", "AS")).split()
    words = [_ABBREV.get(w, w) for w in words]
    kept = [w for w in words if w not in _GENERIC]
    return " ".join(kept or words)


def first_word(company_name: str) -> str:
    """The word to search the FDA's sponsor list by."""
    words = core(company_name).split()
    return next((w for w in words if len(w) > 2), words[0] if words else "")


def sponsor_names(prefix: str) -> dict[str, int]:
    """FDA sponsor names starting with `prefix`, with how many applications each has."""
    try:
        data = get_json(BASE, params={"search": f"sponsor_name:{prefix.upper()}*", "limit": 1000}, cache_hours=24 * 7)
    except Exception as err:
        if "404" in str(err) or "NOT_FOUND" in str(err):
            return {}
        raise
    out: dict[str, int] = {}
    for app in data.get("results", []):
        out[app["sponsor_name"]] = out.get(app["sponsor_name"], 0) + 1
    return out


def applications(sponsor: str) -> list[dict]:
    """Every application filed under exactly this sponsor name."""
    try:
        data = get_json(BASE, params={"search": f'sponsor_name:"{sponsor}"', "limit": 1000}, cache_hours=24 * 6)
    except Exception as err:
        if "404" in str(err) or "NOT_FOUND" in str(err):
            return []
        raise
    return [a for a in data.get("results", []) if a.get("sponsor_name") == sponsor]


def approved_medicines(apps: list[dict]) -> list[dict]:
    """New medicines (NDA or BLA, not generic copies) whose original application was approved.
    One row per application: brand name(s), ingredient, first approval date, and whether any version is still sold."""
    out = []
    for a in apps:
        num = a.get("application_number", "")
        if not num.startswith(("NDA", "BLA")):
            continue   # ANDA = a generic copy of someone else's drug
        orig = [s for s in a.get("submissions") or [] if s.get("submission_type") == "ORIG" and s.get("submission_status") == "AP"]
        if not orig:
            continue
        day = min(s.get("submission_status_date", "") for s in orig)
        products = a.get("products") or []
        brands = sorted({(p.get("brand_name") or "").strip().title() for p in products if p.get("brand_name")})
        ingredients = sorted({(i.get("name") or "").strip().lower() for p in products for i in p.get("active_ingredients") or []})
        sold = any((p.get("marketing_status") or "") in ("Prescription", "Over-the-counter") for p in products)
        if not brands or len(day) != 8:
            continue
        out.append({"application_number": num, "brand_name": ", ".join(brands)[:200],
                    "ingredient": ", ".join(ingredients)[:300] or None,
                    "approved_on": f"{day[:4]}-{day[4:6]}-{day[6:]}", "still_sold": sold})
    return out
