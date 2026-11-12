"""SEC EDGAR data (no key needed, max 10 requests/second, contact email required in User-Agent).

Week 1 Step 4 only needs the list of US-listed companies. Filings and insider
trades get added in Step 6.
"""
from ..http import get_json

US_EXCHANGES = {"Nasdaq", "NYSE"}  # skip OTC ("over the counter") listings: not major exchanges

# SEC industry codes ("SIC codes") that count as healthcare: drugs, biotech, devices, labs, research.
HEALTH_SIC_CODES = {
    "2833", "2834", "2835", "2836",          # medicines, diagnostics, biological products
    "3826", "3841", "3842", "3844", "3845",  # lab instruments and medical devices
    "5122",                                  # drug wholesalers
    "8000", "8071", "8090", "8093",          # health services and labs
    "8731", "8733",                          # research labs (many biotechs file under these)
}


def listed_companies() -> list[dict]:
    """Every company on Nasdaq or NYSE, one row per company: {cik, name, ticker, exchange}."""
    raw = get_json("https://www.sec.gov/files/company_tickers_exchange.json", cache_hours=24)
    by_cik: dict[int, dict] = {}
    for cik, name, ticker, exchange in raw["data"]:
        if exchange not in US_EXCHANGES or not ticker or "-" in ticker:
            continue  # tickers with "-" are things like rights or preferred shares, not the main stock
        current = by_cik.get(cik)
        # A company can have several tickers; keep the shortest (usually the main common stock)
        if current is None or len(ticker) < len(current["ticker"]):
            by_cik[cik] = {"cik": str(cik).zfill(10), "name": name, "ticker": ticker, "exchange": exchange}
    return list(by_cik.values())


def submissions(cik: str) -> dict:
    """A company's profile + recent filings list. Cached for 4 hours."""
    return get_json(f"https://data.sec.gov/submissions/CIK{cik}.json", cache_hours=4)


def is_healthcare(cik: str) -> bool:
    return str(submissions(cik).get("sic", "")) in HEALTH_SIC_CODES


# ---------------------------------------------------------------------------
# Step 6: filings and insider trades
# ---------------------------------------------------------------------------
import re
import xml.etree.ElementTree as ET
from datetime import date, timedelta

from ..http import get_text

# Forms we keep. 8-K = "something important happened"; 4 = insider trade;
# 10-Q / 10-K = quarterly / yearly report (cash numbers); S-3 / S-1 / 424B5 = selling new shares.
# Companies based outside the US file different forms: 6-K (news), 20-F / 40-F (yearly report), F-1 / F-3 (share sales).
# 6-Ks carry no item codes, so executive departures are only detected from 8-Ks.
KEEP_FORMS = {"8-K", "8-K/A", "4", "4/A", "10-Q", "10-K", "S-3", "S-1", "424B5",
              "6-K", "6-K/A", "20-F", "40-F", "F-1", "F-3"}

# What each 8-K item number means (only the ones Tremor cares about)
ITEM_MEANINGS = {
    "1.01": "Signed a major agreement",
    "1.02": "Ended a major agreement",
    "2.02": "Shared quarterly results",
    "2.05": "Layoffs or restructuring costs",
    "3.01": "Warning about being removed from the stock exchange",
    "5.02": "An executive or board member joined or left",
    "7.01": "Shared information with investors",
    "8.01": "Other news",
}


def recent_filings(company: dict, since: date) -> list[dict]:
    """A company's filings since `since`, as rows for the sec_filings table."""
    recent = submissions(company["cik"])["filings"]["recent"]
    rows = []
    for i, form in enumerate(recent["form"]):
        filed = recent["filingDate"][i]
        if filed < since.isoformat():
            break  # newest first, so we can stop here
        if form not in KEEP_FORMS:
            continue
        acc = recent["accessionNumber"][i]
        doc = recent["primaryDocument"][i]
        items = [x for x in (recent["items"][i] or "").split(",") if x]
        rows.append({
            "accession_number": acc,
            "ticker": company["ticker"],
            "form": form,
            "filed_at": filed,
            "items": items,
            "url": f"https://www.sec.gov/Archives/edgar/data/{int(company['cik'])}/{acc.replace('-', '')}/{doc}",
            "description": "; ".join(ITEM_MEANINGS[x] for x in items if x in ITEM_MEANINGS) or None,
            # not stored: used to find the raw Form 4 XML
            "_raw_doc": re.sub(r"^xsl[^/]+/", "", doc),
            "_cik": int(company["cik"]),
        })
    return rows


def _text(node, path):
    el = node.find(path)
    return el.text.strip() if el is not None and el.text and el.text.strip() else None


def _flag(node, path) -> bool:
    return (_text(node, path) or "0").lower() in {"1", "true"}


def parse_form4(xml_text: str) -> list[dict]:
    """Turn a Form 4 XML into one row per stock transaction.

    Only 'non-derivative' transactions (actual shares), not options, to keep it simple.
    """
    root = ET.fromstring(xml_text)
    owner = root.find("reportingOwner")
    rel = owner.find("reportingOwnerRelationship") if owner is not None else None
    footnotes = " ".join((f.text or "") for f in root.iter("footnote")).lower()
    # The official checkbox (since April 2023), or a footnote mentioning a 10b5-1 plan
    planned = _flag(root, "aff10b5One") or "10b5-1" in footnotes

    rows = []
    for n, tx in enumerate(root.findall("nonDerivativeTable/nonDerivativeTransaction")):
        shares = _text(tx, "transactionAmounts/transactionShares/value")
        price = _text(tx, "transactionAmounts/transactionPricePerShare/value")
        rows.append({
            "line_number": n,
            "insider_name": _text(owner, "reportingOwnerId/rptOwnerName") if owner is not None else None,
            "insider_title": _text(rel, "officerTitle") if rel is not None else None,
            "is_officer": _flag(rel, "isOfficer") if rel is not None else None,
            "is_director": _flag(rel, "isDirector") if rel is not None else None,
            "transaction_date": _text(tx, "transactionDate/value"),
            "transaction_code": _text(tx, "transactionCoding/transactionCode"),
            "shares": float(shares) if shares else None,
            "price": float(price) if price else None,
            "acquired_disposed": _text(tx, "transactionAmounts/transactionAcquiredDisposedCode/value"),
            "is_10b5_1": planned,
        })
    return rows


def insider_trades(filing: dict) -> list[dict]:
    """Download and parse one Form 4 filing."""
    acc = filing["accession_number"].replace("-", "")
    base = f"https://www.sec.gov/Archives/edgar/data/{filing['_cik']}/{acc}"
    try:
        xml_text = get_text(f"{base}/{filing['_raw_doc']}")
    except Exception:
        # Filenames vary: fall back to reading the filing's index to find the XML
        index = get_json(f"{base}/index.json")
        name = next(i["name"] for i in index["directory"]["item"] if i["name"].endswith(".xml"))
        xml_text = get_text(f"{base}/{name}")
    return [{**row, "accession_number": filing["accession_number"], "ticker": filing["ticker"],
             "url": filing["url"]} for row in parse_form4(xml_text)]
