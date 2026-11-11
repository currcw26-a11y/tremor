"""Weekly: which medicines each tracked company already has FDA approval for (openFDA Drugs@FDA).

    python -m tremor.approvals_job          # fetch approvals for confirmed sponsor names
    python -m tremor.approvals_job --scan   # suggest FDA sponsor names for companies not in the CSV yet

pipeline/data/fda_sponsors.csv holds the company -> FDA sponsor name matches:
  confirmed = used; suggested = waiting for a person to check (change to confirmed or rejected);
  none = we looked and found nothing (so we don't look again every week).
"""
import csv
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from . import db
from .sources import openfda

CSV_PATH = Path(__file__).resolve().parents[1] / "data" / "fda_sponsors.csv"
FIELDS = ["ticker", "fda_sponsor", "status", "note"]
EVERY_DAYS = 7


def load() -> list[dict]:
    if not CSV_PATH.exists():
        return []
    with CSV_PATH.open() as f:
        return list(csv.DictReader(f))


def save(rows: list[dict]):
    rows = sorted(rows, key=lambda r: (r["ticker"], r["status"] != "confirmed", r["fda_sponsor"]))
    with CSV_PATH.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows({k: r.get(k, "") for k in FIELDS} for r in rows)


def suggest(company_name: str, names: dict[str, int]) -> list[dict]:
    """Sort FDA sponsor names found by prefix into confirmed (same name) and suggested (same first word)."""
    mine = openfda.core(company_name)
    first = mine.split()[0] if mine else ""
    out = []
    for sponsor, n in sorted(names.items()):
        theirs = openfda.core(sponsor)
        if theirs == mine:
            out.append({"fda_sponsor": sponsor, "status": "confirmed", "note": f"same name ({n} applications)"})
        elif theirs.split()[:1] == [first]:
            out.append({"fda_sponsor": sponsor, "status": "suggested", "note": f"{n} applications; check it's the same company"})
    return out


def _companies() -> list[dict]:
    tracked = {t["ticker"] for t in db.select("trials", "ticker", tracked="eq.true") if t.get("ticker")}
    return [c for c in db.select("companies", "ticker,name") if c["ticker"] in tracked]


def scan() -> dict:
    rows = load()
    known = {r["ticker"] for r in rows}
    added = 0
    for c in _companies():
        if c["ticker"] in known:
            continue
        found = suggest(c["name"], openfda.sponsor_names(openfda.first_word(c["name"])))
        rows += [{"ticker": c["ticker"], **f} for f in found] or [{"ticker": c["ticker"], "fda_sponsor": "", "status": "none",
                                                                   "note": "no FDA sponsor with this name"}]
        added += len(found)
    save(rows)
    return {"companies": len({r["ticker"] for r in rows}), "names_added": added,
            "waiting_for_review": sum(r["status"] == "suggested" for r in rows)}


def run(today: date | None = None, force: bool = False) -> dict:
    today = today or date.today()
    try:
        last = db.select("approved_medicines", "updated_at", order="updated_at.desc", limit="1")
    except RuntimeError as err:
        return {"skipped": f"approved_medicines table missing (run migration 013): {str(err)[:80]}"}
    if last and not force and str(last[0]["updated_at"])[:10] > (today - timedelta(days=EVERY_DAYS)).isoformat():
        return {"skipped": "updated this week"}
    by_ticker: dict[str, list[str]] = {}
    for r in load():
        if r["status"] == "confirmed" and r["fda_sponsor"]:
            by_ticker.setdefault(r["ticker"], []).append(r["fda_sponsor"])
    now = datetime.now(timezone.utc).isoformat()
    rows, errors = [], 0
    for ticker, sponsors in by_ticker.items():
        for sponsor in sponsors:
            try:
                meds = openfda.approved_medicines(openfda.applications(sponsor))
            except Exception as err:
                print(f"    openFDA {sponsor}: {err}", flush=True)
                errors += 1
                continue
            rows += [{**m, "ticker": ticker, "sponsor_name": sponsor, "updated_at": now} for m in meds]
    if errors and not rows:
        return {"skipped": f"openFDA unreachable ({errors} errors)"}
    if rows:
        db.upsert("approved_medicines", rows, on_conflict="application_number")
    if not errors:   # remove medicines from names no longer confirmed (only after a complete run)
        db.delete("approved_medicines", updated_at=f"lt.{now}")
    return {"companies": len(by_ticker), "medicines": len(rows), "still_sold": sum(r["still_sold"] for r in rows),
            "errors": errors}


if __name__ == "__main__":
    print(scan() if "--scan" in sys.argv else run(force="--force" in sys.argv))
