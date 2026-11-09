"""Daily: download state layoff (WARN) notices and save the ones from companies Tremor tracks."""
from datetime import date, timedelta
from pathlib import Path

from . import config, db
from .matching import core_name
from .sources import layoffs

WORK_DIR = Path(__file__).resolve().parents[1] / ".cache" / "warn"


def run() -> dict:
    cfg = config.load()["signals"]
    cores = {}
    for c in db.select("companies", "ticker,name"):
        core = core_name(c["name"])
        if len(core) >= 4:  # very short names would match unrelated employers
            cores.setdefault(core, {"ticker": c["ticker"], "name": c["name"]})
    rows, errors = layoffs.scrape_states(cfg["layoff_states"], WORK_DIR)
    since = date.today() - timedelta(days=cfg["layoff_lookback_days"])
    found = layoffs.match(rows, cores, since)
    # States sometimes list the same notice twice; keep one copy of each
    unique = {}
    for r in found:
        key = f"{r['state']}|{r['company_name']}|{r['notice_date']}|{r['employees']}"
        unique[key] = {
            "ticker": r["ticker"], "state": r["state"], "company_name": r["company_name"],
            "notice_date": r["notice_date"].isoformat() if r["notice_date"] else None,
            "employees": r["employees"], "location": r["location"], "source": "warn-scraper", "dedupe_key": key,
        }
    if unique:
        db.upsert("layoff_notices", list(unique.values()), on_conflict="dedupe_key")
    found = list(unique.values())
    return {"notices_read": len(rows), "tracked_company_notices": len(found),
            "states_ok": len(cfg["layoff_states"]) - len(errors), "states_failed": errors,
            "matches": sorted({f"{r['ticker']} ({r['state']})" for r in found})}
