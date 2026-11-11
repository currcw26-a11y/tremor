"""Once a week (first daily run on or after Monday): write Tremor Weekly for the week that just ended.

    python -m tremor.weekly_job            # writes last week's issue if it doesn't exist yet
    python -m tremor.weekly_job --force    # rewrites it
"""
import sys
from datetime import date, datetime, timedelta, timezone

from . import ai, db, weekly
from .alert_job import _short_name

# Changes worth listing by name; everything else is routine (and paperwork never counts)
IMPORTANT = {"primary_outcome_changed", "primary_outcome_added", "enrollment_cut", "date_delayed", "trial_stopped",
             "results_posted", "interventions_changed", "phase_changed"}
FIELD = {"primary_completion_date": "main results date", "completion_date": "final finish date"}


def describe(c: dict) -> str:
    d = c.get("details") or {}
    t = c["change_type"]
    if t == "primary_outcome_changed":
        return "changed the trial's main goal"
    if t == "primary_outcome_added":
        return "added a new main goal"
    if t == "enrollment_cut":
        return f"cut the planned number of patients from {c['old_value']} to {c['new_value']}"
    if t == "date_delayed":
        return f"pushed back the {FIELD.get(c.get('field'), 'finish date')} by about {round(abs(float(d.get('months') or 0)))} months"
    if t == "trial_stopped":
        return f"stopped the trial (status now {str(c['new_value']).replace('_', ' ').lower()})"
    if t == "results_posted":
        return "posted results for the first time"
    if t == "interventions_changed":
        return "changed which drugs are in the trial"
    if t == "phase_changed":
        return "changed the trial's phase"
    return t.replace("_", " ")


def gather(today: date) -> dict:
    start, end = weekly.week_bounds(today)
    since, until = start.isoformat(), (end + timedelta(days=1)).isoformat()
    trials = {t["nct_id"]: t for t in db.select("trials", "nct_id,ticker,title", tracked="eq.true")}
    names = {c["ticker"]: _short_name(c["name"]) for c in db.select("companies", "ticker,name")}

    changes = [c for c in db.select("trial_changes",
                                    "nct_id,change_type,field,old_value,new_value,details,is_paperwork,detected_at",
                                    detected_at=f"gte.{since}", order="detected_at")
               if c["nct_id"] in trials and c["detected_at"] < until]
    important = [c for c in changes if c["change_type"] in IMPORTANT and not c["is_paperwork"]]
    listed = [{"ticker": trials[c["nct_id"]]["ticker"], "company": names.get(trials[c["nct_id"]]["ticker"], trials[c["nct_id"]]["ticker"]),
               "trial": trials[c["nct_id"]]["title"][:120], "what": describe(c)} for c in important[:8]]

    alerts = [a["headline"] for a in db.select("alerts", "headline,kind,signal_type,nct_id,detected_at",
                                               detected_at=f"gte.{since}", baseline="eq.false", order="detected_at")
              if a["detected_at"] < until and a["kind"] in ("critical", "big_jump") and not a.get("nct_id")][:6]

    rises = []
    for h in db.select("score_history", "nct_id,old_score,new_score,computed_at", computed_at=f"gte.{since}"):
        if h["computed_at"] < until and h.get("old_score") is not None and h["nct_id"] in trials and h["new_score"] - h["old_score"] >= 5:
            t = trials[h["nct_id"]]
            rises.append({"ticker": t["ticker"], "company": names.get(t["ticker"], t["ticker"]), "trial": t["title"][:120],
                          "old": h["old_score"], "new": h["new_score"]})
    rises = sorted(rises, key=lambda r: r["old"] - r["new"])[:3]

    soon = (today + timedelta(days=14)).isoformat()
    coming = []
    try:
        events = db.select("upcoming_events", "kind,ticker,event_date,date_precision", event_date=f"gte.{today.isoformat()}",
                           order="event_date")
    except RuntimeError:
        events = []
    for e in events:
        if e["event_date"] > soon or e["date_precision"] != "day":
            continue
        d = date.fromisoformat(e["event_date"])
        who = names.get(e["ticker"], e["ticker"])
        if e["kind"] == "fda_decision":
            coming.append(f"FDA decision expected for {who} ({e['ticker']}) by {weekly.nice(d)}")
        elif e["kind"] == "fda_meeting":
            coming.append(f"FDA advisory meeting about {who}'s drug on {weekly.nice(d)}")
    due = sum(1 for e in events if e["kind"] == "results_due" and e["event_date"] <= soon)
    if due:
        coming.append(f"{due} tracked trials expect their main results by then (the companies' own estimates, which often slip)")

    return {"start": start, "end": end, "trials_tracked": len(trials), "important_changes": len(important),
            "routine_changes": len(changes) - len(important), "changes": listed, "alerts": alerts,
            "score_rises": rises, "coming": coming[:6]}


def run(today: date | None = None, force: bool = False) -> dict:
    today = today or datetime.now(timezone.utc).date()
    start, end = weekly.week_bounds(today)
    try:
        exists = db.select("weekly_issues", "week_start", week_start=f"eq.{start.isoformat()}")
    except RuntimeError as err:
        return {"skipped": f"weekly_issues table missing (run migration 011): {str(err)[:80]}"}
    if exists and not force:
        return {"skipped": f"issue for week of {start} already written"}

    f = gather(today)
    facts = weekly.facts_text(f)
    body, by = None, "code"
    for _ in range(2):   # one retry if the draft fails a check
        draft = ai.write("weekly", weekly.SYSTEM, facts, essential=False, max_tokens=1500)
        if weekly.acceptable(draft):
            body, by = draft, "ai"
            break
    if body is None:
        body = weekly.fallback_body(f)
    row = {"week_start": start.isoformat(), "week_end": end.isoformat(), "title": weekly.title_for(start, end),
           "body": body, "written_by": by, "facts": {**f, "start": start.isoformat(), "end": end.isoformat()}}
    db.upsert("weekly_issues", [row], on_conflict="week_start")
    return {"week": f"{start} to {end}", "written_by": by, "important_changes": f["important_changes"]}


if __name__ == "__main__":
    print(run(force="--force" in sys.argv))
