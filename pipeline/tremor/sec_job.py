"""SEC + FDA part of each pipeline run.

- New filings for every tracked company (8-Ks, insider trades, reports, share sales).
- Insider trade details from each new Form 4.
- FDA advisory meetings that mention our companies or drugs.
"""
from datetime import date, timedelta

from . import db
from .sources import federal_register, sec

FIRST_RUN_DAYS = 180  # how far back to look the first time


def run_sec() -> dict:
    companies = db.select("companies", "ticker,cik,name")
    known = {r["accession_number"] for r in db.select("sec_filings", "accession_number")}
    since = date.today() - timedelta(days=FIRST_RUN_DAYS)

    new_filings, trades, errors = [], [], 0
    for c in companies:
        try:
            for f in sec.recent_filings(c, since):
                if f["accession_number"] in known:
                    continue
                if f["form"] in {"4", "4/A"}:
                    trades += sec.insider_trades(f)
                new_filings.append(f)
        except Exception as err:  # one company's bad data shouldn't stop the rest
            errors += 1
            print(f"    {c['ticker']}: {err}")

    rows = [{k: v for k, v in f.items() if not k.startswith("_")} for f in new_filings]
    db.upsert("sec_filings", rows, on_conflict="accession_number")
    db.upsert("insider_trades", trades, on_conflict="accession_number,line_number")
    return {"new_filings": len(rows),
            "new_8k_exec_changes": sum("5.02" in f["items"] for f in rows),
            "new_insider_trade_lines": len(trades),
            "company_errors": errors}


def run_fda() -> dict:
    names_to_tickers: dict[str, set[str]] = {}
    for c in db.select("companies", "ticker,name"):
        names_to_tickers.setdefault(_short_company_name(c["name"]), set()).add(c["ticker"])
    for t in db.select("trials", "ticker,interventions", tracked="eq.true"):
        for drug in federal_register.useful_names(t["interventions"] or []):
            names_to_tickers.setdefault(drug, set()).add(t["ticker"])
    names_to_tickers = {n: t for n, t in names_to_tickers.items() if n and len(n) >= 5}

    meetings = federal_register.find_meetings(names_to_tickers)
    db.upsert("fda_meetings", meetings, on_conflict="document_number")
    return {"names_searched": len(names_to_tickers), "meetings_found": len(meetings)}


def _short_company_name(name: str) -> str:
    """'IOVANCE BIOTHERAPEUTICS, INC.' -> 'Iovance Biotherapeutics' (what notices usually say)."""
    import re
    name = re.sub(r"\s*/\s*[A-Za-z]{2}\s*/?\s*$", "", name)
    name = re.sub(r",?\s+(inc|corp|corporation|co|ltd|plc|sa|ag|se|nv|a/s|holdings|limited)\.?$", "", name, flags=re.I)
    name = name.rstrip(" &,")  # 'ELI LILLY & Co' -> 'ELI LILLY'
    return name.title() if name.isupper() else name
