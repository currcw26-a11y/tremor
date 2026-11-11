"""Daily: rebuild the "Upcoming" calendar (pipeline/tremor -> upcoming_events table).

    python -m tremor.upcoming_job
"""
from datetime import date, timedelta

from . import db
from .backtest_job import _cached_text
from .sources import fda_dates

RESULTS_AHEAD_DAYS = 183   # show trials whose main results are expected in the next ~6 months


def fda_decisions(companies: dict[str, str], today: date) -> tuple[list[dict], int]:
    hits = fda_dates.search(list(companies), today - timedelta(days=200), today)
    # Each company's NEWEST filing that names an upcoming date wins, so a date the company later
    # moved (the FDA can extend a review by 3 months) doesn't linger from an older filing.
    # Newer filings that say the FDA already decided ("approved ahead of the January 4 date") also cancel
    # that date in older filings.
    rows, done, decided = {}, set(), {}
    for h in sorted(hits, key=lambda h: h["filed"], reverse=True):
        ticker = companies.get(h["cik"].zfill(10))
        if not ticker or ticker in done:
            continue
        try:
            text = _cached_text(h["url"])
            found = fda_dates.extract_dates(text, today, also_decided=decided.get(ticker))
            decided[ticker] = decided.get(ticker, set()) | fda_dates.decided_dates(text)
        except Exception as err:
            print(f"    {ticker}: {err}", flush=True)
            continue
        if not found:
            continue
        done.add(ticker)
        for d in found:
            key = f"fda_decision:{ticker}:{d['date']}"
            if key in rows and d["precision"] != "day":
                continue   # an exact day beats "sometime that month"
            rows[key] = {"kind": "fda_decision", "ticker": ticker, "nct_id": None, "event_date": d["date"],
                         "date_precision": d["precision"], "title": "FDA decision expected", "quote": d["sentence"],
                         "source_url": h["url"], "source_form": h["form"], "filed_at": h["filed"], "dedupe_key": key}
    return list(rows.values()), len(hits)


def fda_meetings(today: date) -> list[dict]:
    rows = []
    for m in db.select("fda_meetings", "document_number,title,meeting_date,url,matched_tickers,publication_date",
                       meeting_date=f"gte.{today.isoformat()}"):
        for t in m.get("matched_tickers") or []:
            rows.append({"kind": "fda_meeting", "ticker": t, "nct_id": None, "event_date": m["meeting_date"],
                         "date_precision": "day", "title": m["title"], "quote": None, "source_url": m["url"],
                         "source_form": "Federal Register", "filed_at": m["publication_date"],
                         "dedupe_key": f"fda_meeting:{m['document_number']}:{t}"})
    return rows


def results_due(today: date) -> list[dict]:
    end = today + timedelta(days=RESULTS_AHEAD_DAYS)
    rows = []
    for t in db.select("trials", "nct_id,ticker,title,primary_completion_date,results_first_posted,overall_status",
                       tracked="eq.true", primary_completion_date=f"gte.{today.isoformat()[:7]}",
                       results_first_posted="is.null"):
        due = str(t["primary_completion_date"])
        precision = "day" if len(due) == 10 else "month"
        d = date.fromisoformat(due if precision == "day" else due + "-01")
        last_day = d if precision == "day" else (d.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        if last_day < today or d > end or t["overall_status"] in ("TERMINATED", "WITHDRAWN", "SUSPENDED"):
            continue
        rows.append({"kind": "results_due", "ticker": t["ticker"], "nct_id": t["nct_id"], "event_date": d.isoformat(),
                     "date_precision": precision, "title": t["title"], "quote": None,
                     "source_url": f"https://clinicaltrials.gov/study/{t['nct_id']}", "source_form": "ClinicalTrials.gov",
                     "filed_at": None, "dedupe_key": f"results_due:{t['nct_id']}"})
    return rows


def run(today: date | None = None) -> dict:
    today = today or date.today()
    # Only companies that still have at least one tracked cancer trial
    with_trials = {t["ticker"] for t in db.select("trials", "ticker", tracked="eq.true")}
    companies = {c["cik"].zfill(10): c["ticker"] for c in db.select("companies", "ticker,cik") if c["ticker"] in with_trials}
    decisions, checked = fda_decisions(companies, today)
    meetings, due = fda_meetings(today), results_due(today)
    db.delete("upcoming_events", id="gt.0")   # small table: rebuilt fresh every day
    rows = decisions + meetings + due
    if rows:
        db.insert("upcoming_events", rows)
    return {"filings_checked": checked, "fda_decisions": len(decisions), "fda_meetings": len(meetings),
            "results_due": len(due)}


if __name__ == "__main__":
    print(run())
