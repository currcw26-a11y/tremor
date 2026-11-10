"""Collect past events since 2016 and run the backtest. Heavy, so run occasionally (weekly), not every 4 hours.

    python -m tremor.backtest_job
"""
import hashlib
from collections import Counter, defaultdict
from datetime import date

from . import backtest as bt
from . import db, matching
from .exec_changes import find_key_departure, html_to_text
from .http import CACHE_DIR, get_json, get_text
from .sources import clinicaltrials as ct
from .sources import sec

START = date(2016, 1, 1)
SMALL_COMPANY_TRIALS = 15  # same cutoff as the score's big-company rule


def _iso(d) -> str | None:
    return str(d)[:10] if d else None


def collect_trial_events(confirmed: dict[str, str]) -> list[dict]:
    """Past trials from our companies: stopped early (bad news) or ran to completion."""
    params = {"query.cond": ct.CANCER_WORDS, "filter.overallStatus": "TERMINATED,SUSPENDED,WITHDRAWN,COMPLETED",
              "filter.advanced": f"{ct.PHASE_AND_SPONSOR} AND AREA[LastUpdatePostDate]RANGE[{START.isoformat()},MAX]"}
    rows = []
    for s in ct._paged(params):
        sm = ct.summarize(s)
        ticker = confirmed.get(sm["sponsor_name"])
        if not ticker:
            continue
        st = s["protocolSection"]["statusModule"]
        # Best guess at when it happened: the actual end date, else the last record update
        day = _iso(sm["primary_completion_date"]) or _iso(sm["last_update_posted"])
        if not day or len(day) < 7:
            continue
        day = day if len(day) == 10 else day + "-15"
        stopped = sm["overall_status"] != "COMPLETED"
        why = st.get("whyStopped")
        rows.append({"ticker": ticker, "kind": "trial_stopped" if stopped else "trial_completed", "day": day,
                     "nct_id": sm["nct_id"], "detail": (why or "")[:300] or None,
                     "stop_reason": bt.stop_reason(why) if stopped else None,
                     "source_url": f"https://clinicaltrials.gov/study/{sm['nct_id']}",
                     "dedupe_key": f"trial:{sm['nct_id']}"})
    return rows


def _all_filings(cik: str) -> list[tuple[str, str, str, str]]:
    """(form, filed date, items, url) for every filing since 2016, including SEC's older 'pages'."""
    sub = sec.submissions(cik)
    pages = [sub["filings"]["recent"]] + [get_json(f"https://data.sec.gov/submissions/{f['name']}", cache_hours=24 * 30)
                                          for f in sub["filings"].get("files", [])]
    out = []
    for p in pages:
        for i, form in enumerate(p["form"]):
            if p["filingDate"][i] < START.isoformat() or form not in ("8-K", "8-K/A"):
                continue
            acc = p["accessionNumber"][i]
            out.append((form, p["filingDate"][i], p["items"][i] or "",
                        f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace('-', '')}/{p['primaryDocument'][i]}"))
    return out


def _cached_text(url: str) -> str:
    path = CACHE_DIR / "8k" / (hashlib.sha1(url.encode()).hexdigest() + ".txt")
    if path.exists():
        return path.read_text()
    text = html_to_text(get_text(url))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return text


def collect_sec_events(companies: list[dict]) -> list[dict]:
    """Past layoffs (8-K item 2.05) and key executives leaving (8-K item 5.02, read with the same reader as live)."""
    rows = []
    for c in companies:
        try:
            for form, filed, items, url in _all_filings(c["cik"]):
                its = items.split(",")
                if "2.05" in its:
                    rows.append({"ticker": c["ticker"], "kind": "layoffs", "day": filed, "source_url": url,
                                 "dedupe_key": f"8k:{url}:layoffs"})
                if "5.02" in its:
                    sentence = find_key_departure(_cached_text(url))
                    if sentence:
                        rows.append({"ticker": c["ticker"], "kind": "key_exec_departure", "day": filed,
                                     "detail": sentence[:300], "source_url": url, "dedupe_key": f"8k:{url}:exec"})
        except Exception as err:
            print(f"    {c['ticker']}: {err}", flush=True)
    return rows


def _prices_for(ticker: str) -> bt.Prices:
    # db.select already reads every page (1,000 rows at a time)
    return bt.Prices(db.select("prices", "day,close", ticker=f"eq.{ticker}", order="day"))


def run(today: date | None = None) -> dict:
    today = today or date.today()
    confirmed = matching.confirmed_matches()
    trial_counts = Counter(t["ticker"] for t in db.select("trials", "ticker", tracked="eq.true"))
    companies = [c for c in db.select("companies", "ticker,cik,name") if trial_counts[c["ticker"]] < SMALL_COMPANY_TRIALS]
    small = {c["ticker"] for c in companies}
    print(f"  {len(small)} smaller companies (under {SMALL_COMPANY_TRIALS} tracked trials)", flush=True)

    events = [e for e in collect_trial_events(confirmed) if e["ticker"] in small]
    print(f"  trial events: {Counter(e['kind'] for e in events)}", flush=True)
    events += collect_sec_events(companies)
    print(f"  all events: {Counter(e['kind'] for e in events)}", flush=True)
    unique = {e["dedupe_key"]: {"nct_id": None, "detail": None, "stop_reason": None, "source_url": None, **e} for e in events}
    db.upsert("past_events", list(unique.values()), on_conflict="dedupe_key")

    by = defaultdict(lambda: defaultdict(list))
    for e in unique.values():
        by[e["kind"]][e["ticker"]].append(date.fromisoformat(e["day"]))
    stops, completions = by["trial_stopped"], by["trial_completed"]
    tickers_needed = {t for kind in ("layoffs", "key_exec_departure", "trial_stopped") for t in by[kind]}
    prices = {t: _prices_for(t) for t in sorted(tickers_needed)}

    baseline = bt.baseline_bad_share(sorted(small), stops, START, today)
    all_cases, summaries = [], []
    for kind in ("layoffs", "key_exec_departure"):
        cases = bt.build_cases(kind, by[kind], stops, completions, prices, today)
        all_cases += cases
        summaries.append(bt.summarize(kind, cases, baseline))
    # A stopped trial is itself the bad news: its "past cases" are how the stock moved when earlier stops came out
    stop_cases = []
    for t, days in stops.items():
        for d in sorted(set(days)):
            news_day, move = prices[t].biggest_move_near(d) if t in prices else (None, None)
            stop_cases.append({"signal_type": "trial_stopped", "ticker": t, "signal_day": d.isoformat(), "outcome": "bad",
                               "news_day": news_day.isoformat() if news_day else None, "move_pct": move})
    all_cases += stop_cases
    summaries.append(bt.summarize("trial_stopped", stop_cases, None,
                                  "Every case here is a stopped trial, so all count as bad news; the number that matters is the stock move."))

    unique_cases = {(c["signal_type"], c["ticker"], c["signal_day"]): c for c in all_cases}
    db.upsert("backtest_cases", list(unique_cases.values()), on_conflict="signal_type,ticker,signal_day")
    db.upsert("backtest_summary", summaries, on_conflict="signal_type")
    return {"events": len(unique), "cases": len(unique_cases), "baseline_bad_share": baseline,
            "summary": {s["signal_type"]: f"{s['bad']} bad / {s['fine']} fine (n={s['cases']}), "
                                          f"typical bad move {s['typical_bad_move']}%" for s in summaries}}


if __name__ == "__main__":
    print(run())
