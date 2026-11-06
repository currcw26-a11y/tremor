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

Write 2 or 3 short sentences:
1. What changed, in everyday words.
2. Why it might matter, OR why it is often harmless. Be honest: many trial edits are routine.

Rules (never break these):
- Use ONLY the facts given. Never add a number, percentage, date, price, prediction, or statistic that is not in the facts.
- Never say or hint that anyone should buy, sell, or hold a stock.
- No jargon. If you must use a term like "Phase 3" or "enrollment", explain it in a few words.
- Use words like "might", "can", and "often", not certainty. Don't guess about the company's reasons.
- Plain text only: no headings, bullet points, or emojis."""

SHORT_SYSTEM = SYSTEM.replace("Write 2 or 3 short sentences:", "Write ONE short sentence covering:")


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


def facts_for(change: dict, trial: dict) -> str:
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
    return "\n".join(lines)


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

    short = ai.over_budget()  # over budget: explanations are essential (alerts use them) but shorter
    done = failed = 0
    for c in todo:
        text = ai.write("explanation", SHORT_SYSTEM if short else SYSTEM, facts_for(c, trials[c["nct_id"]]),
                        essential=True, max_tokens=1500 if short else 2500)
        if text:
            db.update("trial_changes", {"explanation": text, "explanation_model": ai.MODEL}, id=f"eq.{c['id']}")
            done += 1
        else:
            failed += 1
    return {"explained": done, "not_explained": failed, "short_mode": short,
            "spent_this_month_usd": round(ai.spent_this_month(), 4)}
