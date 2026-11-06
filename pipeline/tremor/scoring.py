"""The worry score: 0-100 for each trial, rules-based and transparent.

How it works:
  1. Collect SIGNALS for a trial (record edits, insider sales, executives leaving, ...).
  2. Each signal is worth points from config/tremor.yaml.
  3. Points fade over time (half-life), so old news counts less.
  4. Add them up, cap at 100. A stopped trial jumps to at least the "stopped floor" (red).

This file only does math on data it's given, so it's easy to test.
"""
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta

from . import config
from .diff import STOPPED_STATUSES, parse_date


@dataclass
class Signal:
    type: str                 # key in config weights, e.g. "date_delayed"
    label: str                # short plain-English description
    occurred: date            # when it happened (for fading)
    base_points: float        # points before fading (already includes factors like big-company)
    fades: bool = True        # some signals are ongoing states and don't fade
    source: dict = field(default_factory=dict)  # links/ids so the site can show proof
    points: float = 0.0       # filled in by score()


def label_for(score: int, cfg: dict | None = None) -> str:
    labels = (cfg or config.load())["score"]["labels"]
    best = "calm"
    for key, spec in sorted(labels.items(), key=lambda kv: kv[1]["min"]):
        if score >= spec["min"]:
            best = key
    return best


def faded(points: float, occurred: date, today: date, half_life_days: float) -> float:
    age = max(0, (today - occurred).days)
    return points * 0.5 ** (age / half_life_days)


def score(signals: list[Signal], overall_status: str | None, today: date, cfg: dict | None = None):
    """Returns (score 0-100, label, signals with their current points filled in)."""
    cfg = cfg or config.load()
    s = cfg["score"]
    kept = []
    for sig in signals:
        if (today - sig.occurred).days > s["max_age_days"] and sig.fades:
            continue
        sig.points = round(faded(sig.base_points, sig.occurred, today, s["half_life_days"]) if sig.fades
                           else sig.base_points, 1)
        if sig.points >= 0.5:
            kept.append(sig)
    total = sum(sig.points for sig in kept)
    if overall_status in STOPPED_STATUSES:
        total = max(total, s["stopped_floor"])
    value = int(round(min(100, total)))
    kept.sort(key=lambda x: -x.points)
    return value, label_for(value, cfg), kept


# ---------------------------------------------------------------------------
# Turning raw database rows into signals
# ---------------------------------------------------------------------------

def _d(value) -> date | None:
    return parse_date(str(value)[:10]) if value else None


def trial_signals(trial: dict, changes: list[dict], today: date, cfg: dict | None = None) -> list[Signal]:
    """Signals from the trial's own record: edits Tremor detected + its current state."""
    cfg = cfg or config.load()
    w = cfg["score"]["weights"]
    signals = []
    seen = set()  # one signal per type per day (two dates delayed in one edit = one delay)
    for c in changes:
        if c.get("is_paperwork"):
            continue
        kind, when = c["change_type"], _d(c["detected_at"])
        details = c.get("details") or {}
        if kind not in ("primary_outcome_changed", "enrollment_cut", "date_delayed") or (kind, when) in seen:
            continue
        seen.add((kind, when))
        points = w[kind]
        if kind == "primary_outcome_changed":
            label = "Changed the trial's main goal"
        elif kind == "enrollment_cut":
            label = f"Cut patients by {round(details.get('percent_cut', 0))}%"
            if details.get("old_type") == "ESTIMATED" and details.get("new_type") == "ACTUAL":
                points *= cfg["score"]["enrollment_final_count_factor"]
                label += " (final count when sign-up ended)"
        else:
            label = f"Pushed back a key date by about {round(abs(details.get('months', 0)))} months"
        signals.append(Signal(kind, label, when, points, source={"change_id": c.get("id")}))

    # Ongoing state: results overdue (doesn't fade; it lasts until results are posted)
    pcd = _d(trial.get("primary_completion_date"))
    months = cfg["detection"]["results_overdue_months"]
    if pcd and not trial.get("results_first_posted") and pcd <= today - timedelta(days=round(months * 30.44)):
        signals.append(Signal("results_overdue", f"Main results were due {pcd:%b %Y}, none posted yet",
                              pcd, w["results_overdue"], fades=False))
    return signals


def insider_clusters(sales: list[dict], cfg: dict | None = None) -> list[dict]:
    """Groups of 2+ different insiders selling within N days (pre-planned sales already excluded).

    Returns [{"end": date, "insiders": [...], "accessions": [...]}]. Clusters don't overlap.
    """
    cfg = cfg or config.load()
    days = cfg["detection"]["insider_cluster_days"]
    need = cfg["detection"]["insider_cluster_min_people"]
    sales = sorted((s for s in sales if s.get("transaction_date")), key=lambda s: s["transaction_date"])
    clusters, i = [], 0
    while i < len(sales):
        start = _d(sales[i]["transaction_date"])
        window = [s for s in sales[i:] if _d(s["transaction_date"]) <= start + timedelta(days=days)]
        names = sorted({s["insider_name"] for s in window if s.get("insider_name")})
        if len(names) >= need:
            clusters.append({"end": _d(window[-1]["transaction_date"]), "insiders": names,
                             "accessions": sorted({s["accession_number"] for s in window})})
            i += len(window)  # skip past this cluster
        else:
            i += 1
    return clusters


def company_signals(filings: list[dict], sales: list[dict], trial_count: int, cfg: dict | None = None) -> list[Signal]:
    """Company-wide signals (apply to every trial the company runs)."""
    cfg = cfg or config.load()
    w, s = cfg["score"]["weights"], cfg["score"]
    factor = s["big_company_factor"] if trial_count >= s["big_company_trial_count"] else 1.0
    signals = []
    for c in insider_clusters(sales, cfg):
        signals.append(Signal("insider_selling_cluster", f"{len(c['insiders'])} insiders sold shares within a month",
                              c["end"], w["insider_selling_cluster"] * factor,
                              source={"insiders": c["insiders"], "accessions": c["accessions"]}))
    for f in filings:
        when = _d(f["filed_at"])
        if f.get("key_exec_departure"):
            signals.append(Signal("key_exec_departure", "A key executive is leaving", when,
                                  w["key_exec_departure"] * factor,
                                  source={"url": f.get("url"), "text": f.get("departure_details")}))
        if "2.05" in (f.get("items") or []):
            signals.append(Signal("layoffs", "Announced layoffs or restructuring", when, w["layoffs"] * factor,
                                  source={"url": f.get("url")}))
    return signals


def fda_signals(trial_drugs: set[str], meetings: list[dict], today: date, cfg: dict | None = None) -> list[Signal]:
    """FDA advisory meetings about THIS trial's drug (company-name-only matches don't count)."""
    cfg = cfg or config.load()
    after = cfg["detection"]["fda_meeting_days_after"]
    signals = []
    for m in meetings:
        drugs = {d.lower() for d in m.get("matched_drugs") or []} & trial_drugs
        meeting_day = _d(m.get("meeting_date"))
        if not drugs or (meeting_day and today > meeting_day + timedelta(days=after)):
            continue
        signals.append(Signal("fda_advisory_meeting", "FDA scheduled an expert meeting about this drug",
                              _d(m["publication_date"]), cfg["score"]["weights"]["fda_advisory_meeting"],
                              source={"url": m.get("url"), "meeting_date": m.get("meeting_date")}))
    return signals


def breakdown(signals: list[Signal]) -> list[dict]:
    """JSON-friendly list for the database."""
    out = []
    for sig in signals:
        d = asdict(sig)
        d["occurred"] = sig.occurred.isoformat()
        out.append(d)
    return out
