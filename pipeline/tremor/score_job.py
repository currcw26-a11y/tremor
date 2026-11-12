"""Scoring part of each pipeline run: recompute every tracked trial's worry score.

Saves the current score on the trial, and adds a score_history row whenever the score
moves by 2+ points, changes color, or a new signal appears.
"""
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from . import db, outlook, scoring
from .sources.federal_register import safe_term, useful_names


def _backtest_summaries() -> dict | None:
    """Backtest results by signal type, or None if migration 009 hasn't been run yet."""
    try:
        return {s["signal_type"]: s for s in db.select("backtest_summary", "*") if "bad_moves" in s}
    except RuntimeError as err:
        print(f"  (no backtest results yet: {err})")
        return None


def run(today: date | None = None) -> dict:
    today = today or date.today()
    since = (today - timedelta(days=400)).isoformat()

    summaries = _backtest_summaries()
    fields = ("nct_id,ticker,overall_status,primary_completion_date,results_first_posted,"
              "interventions,score,score_label,score_breakdown,score_updated_at,latest_snapshot_id")
    trials = db.select("trials", fields + (",outlook" if summaries is not None else ""), tracked="eq.true")
    changes = defaultdict(list)
    for c in db.select("trial_changes", "id,nct_id,change_type,details,is_paperwork,detected_at",
                       is_paperwork="eq.false", detected_at=f"gte.{since}"):
        changes[c["nct_id"]].append(c)
    filings = defaultdict(list)
    for f in db.select("sec_filings", "ticker,filed_at,items,url,key_exec_departure,departure_details",
                       filed_at=f"gte.{since}", form="in.(8-K,8-K/A,6-K,6-K/A)"):   # 6-K = non-US companies
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

    # The company's stated reason for stopping, from Tremor's saved copy of the record
    why_stopped = {}
    stopped = [t for t in trials if t["overall_status"] in ("TERMINATED", "SUSPENDED", "WITHDRAWN")]
    snap_ids = [str(t["latest_snapshot_id"]) for t in stopped if t.get("latest_snapshot_id")]
    if snap_ids and summaries is not None:
        for r in db.select("trial_snapshots", "nct_id,why:data->protocolSection->statusModule->>whyStopped",
                           id=f"in.({','.join(snap_ids)})"):
            why_stopped[r["nct_id"]] = r.get("why")

    # Rival drugs (rivals_job): each trial's targets/cancer, and recent rival failures. Skipped until migration 012.
    try:
        profiles = {p["nct_id"]: p for p in db.select("trial_profiles", "nct_id,targets,drug_ids,cancer_types")}
        failures = db.select("rival_failures", "*")
    except RuntimeError:
        profiles, failures = {}, []

    try:   # FDA-approved medicines still on the market, per company (approvals_job, weekly)
        approved = defaultdict(set)
        for m in db.select("approved_medicines", "ticker,brand_name", still_sold="eq.true"):
            approved[m["ticker"]].add(m["brand_name"].split(",")[0].split()[0].lower())
    except RuntimeError:
        approved = defaultdict(set)
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
                   + scoring.fda_signals(drugs, meetings, today)
                   + scoring.rival_signals(profiles.get(t["nct_id"]), failures, today))
        value, label, kept = scoring.score(signals, t["overall_status"], today)
        bd = scoring.breakdown(kept)

        old_types = {(s["type"], s["occurred"]) for s in (t.get("score_breakdown") or [])}
        new_types = {(s["type"], s["occurred"]) for s in bd}
        first_time = t.get("score_breakdown") is None
        moved = abs(value - (t["score"] or 0)) >= 2 or label != t["score_label"]
        new_signal = bool(new_types - old_types)
        row = {"nct_id": t["nct_id"], "score": value, "score_label": label, "score_breakdown": bd,
               "score_updated_at": now}
        changed = first_time or moved or new_signal or old_types != new_types
        if summaries is not None:
            row["outlook"] = outlook.build({**t, "why_stopped": why_stopped.get(t["nct_id"])}, [b["type"] for b in bd],
                                           summaries, trials_per_company[tk], today, len(approved[tk]))
            changed = changed or row["outlook"] != t.get("outlook")
            if not (first_time or moved or new_signal or old_types != new_types):
                row["score_updated_at"] = t.get("score_updated_at") or now
        if changed:
            updates.append(row)
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
