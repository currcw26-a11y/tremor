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
