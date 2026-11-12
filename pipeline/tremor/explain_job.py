"""Plain-English explanations of important trial changes, written by Claude.

Each change is explained ONCE and saved (that's our cache). Code supplies every fact and
number; Claude only rewords them for someone who has never bought a stock.
"""
from . import ai, db
from .diff import parse_date

# Change types worth a Claude explanation. Minor ones (status progress, small date moves,
# paperwork) get the simple code-written sentence on the site instead.
EXPLAIN_TYPES = ("primary_outcome_changed", "primary_outcome_added", "enrollment_cut", "date_delayed",
                 "trial_stopped", "results_posted", "interventions_changed", "phase_changed")
MAX_PER_RUN = 60  # a safety limit on cost per run

STATUS_WORDS = {
    "RECRUITING": "signing up patients", "NOT_YET_RECRUITING": "not started yet",
    "ACTIVE_NOT_RECRUITING": "running, no longer signing up patients", "COMPLETED": "finished",
    "SUSPENDED": "paused", "TERMINATED": "stopped early", "WITHDRAWN": "cancelled before it started",
    "ENROLLING_BY_INVITATION": "signing up invited patients",
}

SYSTEM = """You explain changes to cancer drug trials for Tremor, a website for college students who have never bought a stock.

Write 3 short sentences:
1. What changed, in everyday words.
2. Why investors pay attention to this kind of change: what worry it can point to.
3. That it can also have ordinary reasons, so on its own it doesn't prove anything.
Keep sentences 2 and 3 balanced. Don't reassure the reader and don't alarm them.
A trial being stopped early, a main goal being changed, or a big cut in patients are more serious than a date moving, so say so plainly when that's the change.

Rules (never break these):
- Use ONLY the facts given. Never add a number, percentage, date, price, prediction, or statistic that is not in the facts.
- Write every number as digits (write 2, not two).
- Never say or hint that anyone should buy, sell, or hold a stock.
- No jargon. If you must use a term like "Phase 3" or "enrollment", explain it in a few words.
- Don't guess the company's reasons. If the facts include the company's stated reason, say it plainly in everyday words.
  If they don't, you may say "the company hasn't said why".
- Plain text only: no headings, bullet points, or emojis."""

SHORT_SYSTEM = SYSTEM.replace("Write 3 short sentences:", "Write ONE short sentence covering, briefly:")


def describe(change: dict) -> str:
    """The code-written fact sentence (same idea as the website's describeChange)."""
    t, d = change["change_type"], change.get("details") or {}
    old, new = change.get("old_value"), change.get("new_value")
    date_name = "main results date" if change.get("field") == "primary_completion_date" else "final finish date"
    if t == "enrollment_cut":
        return f"The planned number of patients went from {old} to {new} ({round(d.get('percent_cut', 0))}% fewer)."
    if t == "date_delayed":
        return (f"The {date_name} moved from {old} to {new}, about {round(abs(d.get('months', 0)))} months later.")
    if t == "trial_stopped":
        return f"The trial's status changed from {STATUS_WORDS.get(old, old)} to {STATUS_WORDS.get(new, new)}."
    if t in ("primary_outcome_changed", "primary_outcome_added"):
        before = "; ".join(o.get("measure", "") for o in old or [])
        after = "; ".join(o.get("measure", "") for o in new or [])
        return f"The trial's main goal (what counts as success) changed. Before: {before}. Now: {after}."
    if t == "results_posted":
        return f"The company posted the trial's results for the first time on {new}."
    if t == "interventions_changed":
        return f"The drugs in the trial changed. Before: {', '.join(old or [])}. Now: {', '.join(new or [])}."
    if t == "phase_changed":
        return f"The trial's phase changed from {', '.join(old or [])} to {', '.join(new or [])}."
    return t.replace("_", " ")


def facts_for(change: dict, trial: dict, why_stopped: str | None = None) -> str:
    phases = "/".join(p.replace("PHASE", "") for p in trial.get("phases") or []) or "not listed"
    lines = [
        f"Company: {trial['sponsor_name']} (stock ticker {trial['ticker']})",
        f"Trial: {trial['title']}",
        f"Stage: Phase {phases}",
        f"Cancer type: {', '.join(trial.get('conditions') or [])}",
        f"Current status: {STATUS_WORDS.get(trial.get('overall_status'), trial.get('overall_status'))}",
        f"Planned patients: {trial.get('enrollment')}",
        f"What changed: {describe(change)}",
    ]
    if change["change_type"] == "trial_stopped":
        lines.append(f'The company\'s stated reason for stopping, from the trial record: "{why_stopped.strip()}"'
                     if why_stopped and why_stopped.strip() else "The trial record gives no reason for stopping.")
    return "\n".join(lines)


def stated_reasons(nct_ids: list[str]) -> dict[str, str]:
    """Each stopped trial's reason for stopping (whyStopped), read from its latest saved record."""
    if not nct_ids:
        return {}
    rows = db.select("trials", "nct_id,latest_snapshot_id", nct_id=f"in.({','.join(nct_ids)})")
    snap_ids = [str(r["latest_snapshot_id"]) for r in rows if r.get("latest_snapshot_id")]
    if not snap_ids:
        return {}
    return {r["nct_id"]: r["why"] for r in db.select(
        "trial_snapshots", "nct_id,why:data->protocolSection->statusModule->>whyStopped",
        id=f"in.({','.join(snap_ids)})") if r.get("why")}


def run() -> dict:
    if not ai.available():
        return {"skipped": "no ANTHROPIC_API_KEY"}
    todo = db.select("trial_changes", "id,nct_id,change_type,field,old_value,new_value,details",
                     explanation="is.null", is_paperwork="eq.false",
                     change_type=f"in.({','.join(EXPLAIN_TYPES)})", order="detected_at.desc",
                     limit=str(MAX_PER_RUN))
    if not todo:
        return {"explained": 0}
    ids = ",".join(sorted({c["nct_id"] for c in todo}))
    trials = {t["nct_id"]: t for t in db.select(
        "trials", "nct_id,title,sponsor_name,ticker,phases,conditions,overall_status,enrollment", nct_id=f"in.({ids})")}

    why = stated_reasons(sorted({c["nct_id"] for c in todo if c["change_type"] == "trial_stopped"}))
    short = ai.over_budget()  # over budget: explanations are essential (alerts use them) but shorter
    done = failed = 0
    for c in todo:
        text = ai.write("explanation", SHORT_SYSTEM if short else SYSTEM, facts_for(c, trials[c["nct_id"]], why.get(c["nct_id"])),
                        essential=True, max_tokens=1500 if short else 2500)
        if text:
            db.update("trial_changes", {"explanation": text, "explanation_model": ai.MODEL}, id=f"eq.{c['id']}")
            done += 1
        else:
            failed += 1
    return {"explained": done, "not_explained": failed, "short_mode": short,
            "spent_this_month_usd": round(ai.spent_this_month(), 4)}
