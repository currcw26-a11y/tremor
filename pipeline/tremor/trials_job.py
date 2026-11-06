"""The ClinicalTrials.gov part of each pipeline run: fetch -> snapshot -> diff -> save.

1. Make sure every confirmed company is in the database.
2. Download the cancer trials; keep only those run by confirmed sponsors ("tracked").
3. Also re-download tracked trials that fell out of the search (e.g. just terminated).
4. For each tracked trial, compare its fingerprint to last time:
     same      -> nothing changed, just note that we checked
     different -> save a new snapshot and record what changed
     new trial -> save its first snapshot (nothing to compare yet)
"""
from datetime import datetime, timezone

from . import db, matching
from .diff import compare
from .snapshot import changed_sections, content_hash, record_for_snapshot
from .sources import clinicaltrials, sec

TRIAL_FIELDS = ["nct_id", "title", "sponsor_name", "ticker", "phases", "overall_status", "conditions",
                "interventions", "primary_outcomes", "enrollment", "enrollment_type", "start_date",
                "primary_completion_date", "completion_date", "results_first_posted", "last_update_posted"]


def sync_companies(confirmed: dict[str, str]) -> int:
    by_ticker = {c["ticker"]: c for c in sec.listed_companies()}
    tickers = sorted(set(confirmed.values()) & set(by_ticker))
    db.upsert("companies", [{"ticker": t, "name": by_ticker[t]["name"], "cik": by_ticker[t]["cik"]} for t in tickers],
              on_conflict="ticker")
    rows = [{"sponsor_name": r["sponsor_name"], "ticker": r["ticker"] if r["ticker"] in by_ticker else None,
             "confirmed": r.get("confirmed", "").strip().lower() in {"yes", "y", "true"},
             "match_score": float(r["score"] or 0), "notes": r.get("notes") or None}
            for r in matching._read_existing().values()]
    db.upsert("sponsor_tickers", rows, on_conflict="sponsor_name")
    return len(tickers)


def run() -> dict:
    now = datetime.now(timezone.utc).isoformat()
    confirmed = matching.confirmed_matches()
    stats = {"companies": sync_companies(confirmed)}

    studies = {clinicaltrials.nct_id(s): s for s in clinicaltrials.fetch_cancer_trials()
               if clinicaltrials.summarize(s)["sponsor_name"] in confirmed}
    known = {r["nct_id"]: r for r in db.select("trials", ",".join(TRIAL_FIELDS + ["content_hash", "latest_snapshot_id"]),
                                                tracked="eq.true")}
    dropped_out = [n for n in known if n not in studies]
    for s in clinicaltrials.fetch_by_ids(dropped_out):
        studies[clinicaltrials.nct_id(s)] = s
    stats.update(trials_tracked=len(studies), refetched_by_id=len(dropped_out))

    trial_rows, new_snapshots, pending_changes = [], [], {}
    for nct, study in studies.items():
        summary = clinicaltrials.summarize(study)
        record = record_for_snapshot(study)
        fingerprint = content_hash(record)
        prev = known.get(nct)
        trial_rows.append({**summary, "ticker": confirmed.get(summary["sponsor_name"], prev and prev["ticker"]),
                           "tracked": True, "content_hash": fingerprint, "last_checked_at": now})
        if prev and prev["content_hash"] == fingerprint:
            continue  # unchanged since last run
        new_snapshots.append({"nct_id": nct, "content_hash": fingerprint,
                              "last_update_posted": summary["last_update_posted"], "data": record})
        if prev and prev.get("latest_snapshot_id"):
            old = db.select("trial_snapshots", "data", id=f"eq.{prev['latest_snapshot_id']}")
            sections = changed_sections(old[0]["data"], record) if old else []
            pending_changes[nct] = (prev["latest_snapshot_id"], compare(prev, summary, sections))

    db.upsert("trials", trial_rows, on_conflict="nct_id")
    saved = db.insert("trial_snapshots", new_snapshots, returning="id,nct_id") if new_snapshots else []
    snapshot_ids = {r["nct_id"]: r["id"] for r in saved}
    if snapshot_ids:
        db.upsert("trials", [{"nct_id": n, "latest_snapshot_id": i} for n, i in snapshot_ids.items()],
                  on_conflict="nct_id")

    change_rows = [{"nct_id": nct, **c, "snapshot_before_id": before, "snapshot_after_id": snapshot_ids.get(nct)}
                   for nct, (before, changes) in pending_changes.items() for c in changes]
    if change_rows:
        db.insert("trial_changes", change_rows)
    stats.update(new_trials=len([n for n in snapshot_ids if n not in known]), changed_trials=len(pending_changes),
                 changes_found=len(change_rows),
                 important_changes=len([c for c in change_rows if not c["is_paperwork"]]))
    return stats
