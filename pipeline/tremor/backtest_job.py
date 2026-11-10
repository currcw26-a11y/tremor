"""Collect past events since 2016 and run the backtest. Heavy, so run occasionally (weekly), not every 4 hours.

    python -m tremor.backtest_job
"""
import hashlib
from collections import Counter, defaultdict
from datetime import date, timedelta

from . import backtest as bt
from . import db, matching, outlook
from .exec_changes import find_key_departure, html_to_text
from .http import CACHE_DIR, get_json, get_text
from .sources import clinicaltrials as ct
from .sources import sec
from .sources.federal_register import safe_term, useful_names

FULL_TEXT_SEARCH = "https://efts.sec.gov/LATEST/search-index"

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
        # Best guess at when it happened: the actual end date, else the last record update.
        # Some stopped trials still list a planned (future) end date; the last update is closer then.
        day = _iso(sm["primary_completion_date"]) or _iso(sm["last_update_posted"])
        if not day or len(day) < 7:
            continue
        day = day if len(day) == 10 else day + "-15"
        last_update = _iso(sm["last_update_posted"])
        if last_update and day > last_update:
            day = last_update
        stopped = sm["overall_status"] != "COMPLETED"
        why = st.get("whyStopped")
        rows.append({"ticker": ticker, "kind": "trial_stopped" if stopped else "trial_completed", "day": day,
                     "nct_id": sm["nct_id"], "detail": (why or "")[:300] or None,
                     "stop_reason": bt.stop_reason(why) if stopped else None,
                     "source_url": f"https://clinicaltrials.gov/study/{sm['nct_id']}",
                     "dedupe_key": f"trial:{sm['nct_id']}",
                     "drugs": useful_names(sm["interventions"])})   # used to find the news; not saved
    return rows


# A filing only counts as "the news" if it mentions the drug AND talks about results or stopping.
# (Share sales and quarterly reports mention drugs too, and they move the stock for other reasons.)
RESULTS_WORDS = ["topline", "top-line", "primary endpoint", "primary efficacy endpoint", "data readout",
                 "met its primary", "did not meet", "statistically significant"]
STOP_WORDS = RESULTS_WORDS + ["discontinue", "discontinued", "discontinuation", "terminate", "terminated",
                              "termination of", "futility", "halt", "halted", "deprioritize", "wind down", "clinical hold"]


def _hits(cik: str, terms: list[str], start: date, end: date) -> dict[str, date]:
    """accession number -> filing date, for this company's 8-Ks mentioning any of `terms`.
    Quarterly earnings releases (item 2.02) are left out: the stock moves on the whole quarter's
    news that day, so the move can't be pinned on the trial."""
    out, offset = {}, 0
    while offset < 500:
        data = get_json(FULL_TEXT_SEARCH, params={
            "q": " OR ".join(f'"{t}"' for t in terms), "forms": "8-K", "ciks": cik.zfill(10), "from": offset,
            "dateRange": "custom", "startdt": start.isoformat(), "enddt": end.isoformat()}, cache_hours=24 * 30)
        hits = data.get("hits", {}).get("hits", [])
        for h in hits:
            if "2.02" in (h["_source"].get("items") or []):
                continue
            out[h["_id"].split(":")[0]] = date.fromisoformat(h["_source"]["file_date"])
        if len(hits) < 100:
            break
        offset += 100
    return out


def filing_days_about(cik: str, drugs: list[str], day: date, window: tuple[int, int], words: list[str]) -> list[date]:
    """Days this company filed an 8-K that mentions the drug (or trial ID) AND uses `words`,
    from window[0] days before `day` to window[1] days after (SEC full-text search covers 2001 onward)."""
    drugs = [t for t in (safe_term(t) for t in drugs) if t][:8]
    if not drugs:
        return []
    start, end = day - timedelta(days=window[0]), min(day + timedelta(days=window[1]), date.today())
    about_drug = _hits(cik, drugs, start, end)
    if not about_drug:
        return []
    with_words = _hits(cik, words, start, end)
    return sorted({d for acc, d in about_drug.items() if acc in with_words})


def find_news(trial_events: list[dict], ciks: dict[str, str], prices: dict[str, bt.Prices]) -> dict:
    """(ticker, official date) -> (news day, % move) for each past trial stop or completion."""
    news = {}
    for e in trial_events:
        key = (e["ticker"], date.fromisoformat(e["day"]))
        if news.get(key, (None, None))[1] is not None or e["ticker"] not in ciks:
            continue
        stopped = e["kind"] == "trial_stopped"
        window, words = (bt.STOP_NEWS_WINDOW, STOP_WORDS) if stopped else (bt.RESULTS_NEWS_WINDOW, RESULTS_WORDS)
        try:
            days = filing_days_about(ciks[e["ticker"]], e.get("drugs", []) + [e["nct_id"]], key[1], window, words)
        except Exception as err:
            print(f"    {e['nct_id']}: {err}", flush=True)
            continue
        news[key] = bt.news_move(days, prices.get(e["ticker"]))
    return news


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
    db.upsert("past_events", [{k: v for k, v in e.items() if k != "drugs"} for e in unique.values()],
              on_conflict="dedupe_key")

    by = defaultdict(lambda: defaultdict(list))
    for e in unique.values():
        by[e["kind"]][e["ticker"]].append(date.fromisoformat(e["day"]))
    stops, completions = by["trial_stopped"], by["trial_completed"]
    prices = {t: _prices_for(t) for t in sorted(small)}

    # Random-day comparison starts when each company was trading (first price), else its first event
    first_event = {}
    for e in unique.values():
        d = date.fromisoformat(e["day"])
        first_event[e["ticker"]] = min(first_event.get(e["ticker"], d), d)
    starts = {t: max(START, prices[t].days[0] if prices[t].days else first_event.get(t, START)) for t in small}
    baseline = bt.baseline_bad_share(sorted(small), stops, starts, today)

    trial_events = [e for e in unique.values() if e["kind"] in ("trial_stopped", "trial_completed")]
    news = find_news(trial_events, {c["ticker"]: c["cik"] for c in companies}, prices)
    found = sum(1 for v in news.values() if v[1] is not None)
    print(f"  announcement day + stock move found for {found} of {len(trial_events)} trial events", flush=True)

    all_cases, summaries = [], []
    for kind in ("layoffs", "key_exec_departure"):
        cases = bt.build_cases(kind, by[kind], stops, completions, news, today)
        all_cases += cases
        summaries.append(bt.summarize(kind, cases, baseline))
    # A stopped trial is itself the bad news: its "past cases" are how the stock moved when earlier stops came out
    note = ("Every case here is a stopped trial, so all count as bad news; the number that matters is the stock move. "
            "Move = close the day before to close the day after the company's announcement.")
    for signal_type, keep in (("trial_stopped", lambda e: True),
                              ("trial_stopped_safety", lambda e: e["stop_reason"] == "safety_or_efficacy")):
        stop_cases, seen_news = [], set()
        for e in trial_events:
            if e["kind"] != "trial_stopped" or not keep(e):
                continue
            news_day, move = news.get((e["ticker"], date.fromisoformat(e["day"])), (None, None))
            if news_day and (e["ticker"], news_day) in seen_news:
                news_day = move = None   # two trials stopped in one announcement: count the stock move once
            seen_news.add((e["ticker"], news_day))
            stop_cases.append({"signal_type": signal_type, "ticker": e["ticker"], "signal_day": e["day"],
                               "outcome": "bad", "news_day": news_day.isoformat() if news_day else None,
                               "move_pct": move, "detail": e["nct_id"]})
        all_cases += stop_cases
        summaries.append(bt.summarize(signal_type, stop_cases, None, note))
    stopped = [e for e in trial_events if e["kind"] == "trial_stopped"]
    safety = next(s for s in summaries if s["signal_type"] == "trial_stopped_safety")
    safety_moves = [c["move_pct"] for c in all_cases if c["signal_type"] == "trial_stopped_safety" and c["move_pct"] is not None]
    for s in summaries:
        s["extra"] = None
        if s["signal_type"] == "trial_stopped":
            s["extra"] = {"reasons": dict(Counter(e["stop_reason"] for e in stopped)),
                          "safety": {"moves": safety["bad_moves"], "typical_move": safety["typical_bad_move"],
                                     "worst_move": min(safety_moves) if safety_moves else None}}
        if s["signal_type"] in outlook.BACKTESTED:   # the same plain sentences the trial pages and emails use
            s["extra"] = {**(s["extra"] or {}), "plain": outlook.past_cases(s["signal_type"], s)["sentences"]}

    unique_cases = {(c["signal_type"], c["ticker"], c["signal_day"]): c for c in all_cases}
    db.delete("backtest_cases", signal_type="not.is.null")   # start fresh: old rows used the old news-day method
    db.upsert("backtest_cases", list(unique_cases.values()), on_conflict="signal_type,ticker,signal_day")
    db.upsert("backtest_summary", summaries, on_conflict="signal_type")
    return {"events": len(unique), "cases": len(unique_cases), "baseline_bad_share": baseline,
            "summary": {s["signal_type"]: f"{s['bad']} bad / {s['fine']} fine (n={s['cases']}), "
                                          f"typical bad move {s['typical_bad_move']}%, typical fine move {s['typical_fine_move']}%"
                for s in summaries}}


if __name__ == "__main__":
    print(run())
