"""Scoring part of each pipeline run: recompute every tracked trial's worry score.

Saves the current score on the trial, and adds a score_history row whenever the score
moves by 2+ points, changes color, or a new signal appears.
"""
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from . import db, scoring
from .sources.federal_register import safe_term, useful_names


def run(today: date | None = None) -> dict:
    today = today or date.today()
    since = (today - timedelta(days=400)).isoformat()

    trials = db.select("trials", "nct_id,ticker,overall_status,primary_completion_date,results_first_posted,"
                                 "interventions,score,score_label,score_breakdown", tracked="eq.true")
    changes = defaultdict(list)
    for c in db.select("trial_changes", "id,nct_id,change_type,details,is_paperwork,detected_at",
                       is_paperwork="eq.false", detected_at=f"gte.{since}"):
        changes[c["nct_id"]].append(c)
    filings = defaultdict(list)
    for f in db.select("sec_filings", "ticker,filed_at,items,url,key_exec_departure,departure_details",
                       filed_at=f"gte.{since}", form="in.(8-K,8-K/A)"):
        filings[f["ticker"]].append(f)
    sales = defaultdict(list)
    for s in db.select("insider_trades", "ticker,accession_number,insider_name,transaction_date",
                       transaction_code="eq.S", acquired_disposed="eq.D", is_10b5_1="eq.false",
                       transaction_date=f"gte.{since}"):
        sales[s["ticker"]].append(s)
    meetings = db.select("fda_meetings", "*")
    notices, job_counts = defaultdict(list), defaultdict(list)
    for n in db.select("layoff_notices", "ticker,state,notice_date,employees,location", notice_date=f"gte.{since}"):
        notices[n["ticker"]].append(n)
    for j in db.select("job_counts", "ticker,day,clinical_jobs", day=f"gte.{(today - timedelta(days=60)).isoformat()}"):
        job_counts[j["ticker"]].append(j)

    trials_per_company = defaultdict(int)
    for t in trials:
        trials_per_company[t["ticker"]] += 1
    company_cache = {}

    now = datetime.now(timezone.utc).isoformat()
    updates, history = [], []
    for t in trials:
        tk = t["ticker"]
        if tk not in company_cache:
            company_cache[tk] = scoring.company_signals(filings[tk], sales[tk], trials_per_company[tk],
                                                        layoff_notices=notices[tk], job_counts=job_counts[tk])
        drugs = {safe_term(d).lower() for d in useful_names(t.get("interventions") or [])}
        signals = (scoring.trial_signals(t, changes[t["nct_id"]], today)
                   + [scoring.Signal(**{**vars(s)}) for s in company_cache[tk]]  # copies: points differ per call
                   + scoring.fda_signals(drugs, meetings, today))
        value, label, kept = scoring.score(signals, t["overall_status"], today)
        bd = scoring.breakdown(kept)

        old_types = {(s["type"], s["occurred"]) for s in (t.get("score_breakdown") or [])}
        new_types = {(s["type"], s["occurred"]) for s in bd}
        first_time = t.get("score_breakdown") is None
        moved = abs(value - (t["score"] or 0)) >= 2 or label != t["score_label"]
        new_signal = bool(new_types - old_types)
        if first_time or moved or new_signal or old_types != new_types:
            updates.append({"nct_id": t["nct_id"], "score": value, "score_label": label,
                            "score_breakdown": bd, "score_updated_at": now})
        if (moved or new_signal) and not (first_time and value == 0):
            history.append({"nct_id": t["nct_id"], "old_score": None if first_time else t["score"],
                            "new_score": value, "old_label": None if first_time else t["score_label"],
                            "new_label": label, "breakdown": bd,
                            "reason": "first score" if first_time else ("new signal" if new_signal else "points faded")})

    db.upsert("trials", updates, on_conflict="nct_id")
    if history:
        db.insert("score_history", history)
    latest = {t["nct_id"]: t["score_label"] for t in trials} | {u["nct_id"]: u["score_label"] for u in updates}
    labels = defaultdict(int)
    for label in latest.values():
        labels[label] += 1
    return {"scores_updated": len(updates), "history_rows": len(history), **{f"now_{k}": v for k, v in labels.items()}}
