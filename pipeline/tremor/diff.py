"""Compare two versions of a trial and describe what changed.

This is the heart of Tremor. Given the OLD and NEW summary of a trial (see
clinicaltrials.summarize), it returns a list of changes like:
    {"change_type": "enrollment_cut", "field": "enrollment", "old_value": 300,
     "new_value": 240, "is_paperwork": False, "details": {"percent_cut": 20.0}}

Change types (the scoring engine in Week 2 turns these into points):
    primary_outcome_changed    a main goal was removed or replaced            (big deal)
    primary_outcome_added      a new main goal was added, none removed
    primary_outcome_reworded   same goals, different description/time frame
    enrollment_cut             patients cut by 15% or more                   (big deal)
    enrollment_small_cut       patients cut by less than 15%
    enrollment_increased
    date_delayed               a completion date pushed back 3+ months       (big deal)
    date_small_change          a completion date moved less than 3 months
    date_moved_earlier
    trial_stopped              suspended, terminated, or withdrawn          (big deal)
    status_changed             other status moves (often normal progress)
    results_posted             results appeared for the first time
    interventions_changed      drugs in the trial changed
    phase_changed
    paperwork                  only other parts of the record changed (contacts, locations...)
"""
import re
from datetime import date

ENROLLMENT_CUT_PERCENT = 15  # TODO Week 2: move into config/tremor.yaml with the score weights
DATE_DELAY_MONTHS = 3
STOPPED_STATUSES = {"SUSPENDED", "TERMINATED", "WITHDRAWN"}
DATE_FIELDS = ("primary_completion_date", "completion_date")


def _norm(text) -> str:
    """Ignore differences in capital letters, spaces, and punctuation."""
    return re.sub(r"[^a-z0-9]+", " ", str(text or "").lower()).strip()


def parse_date(value) -> date | None:
    """CT.gov dates are '2027-06-15' or just '2027-06' (we treat that as the 1st)."""
    if not value:
        return None
    parts = [int(p) for p in str(value).split("-")]
    return date(parts[0], parts[1] if len(parts) > 1 else 1, parts[2] if len(parts) > 2 else 1)


def months_between(a: date, b: date) -> float:
    return round((b - a).days / 30.44, 1)  # 30.44 = average days in a month


def _change(change_type, field, old, new, paperwork=False, **details):
    return {"change_type": change_type, "field": field, "old_value": old, "new_value": new,
            "is_paperwork": paperwork, "details": details or None}


def _outcome_changes(old: list, new: list) -> list[dict]:
    old_measures = {_norm(o.get("measure")) for o in old or []}
    new_measures = {_norm(o.get("measure")) for o in new or []}
    if old_measures == new_measures:
        old_full = sorted((_norm(o.get("measure")), _norm(o.get("description")), _norm(o.get("timeFrame"))) for o in old or [])
        new_full = sorted((_norm(o.get("measure")), _norm(o.get("description")), _norm(o.get("timeFrame"))) for o in new or [])
        if old_full == new_full:
            return []  # only capitalization/punctuation changed: not worth mentioning
        return [_change("primary_outcome_reworded", "primary_outcomes", old, new)]
    removed = sorted(old_measures - new_measures)
    added = sorted(new_measures - old_measures)
    kind = "primary_outcome_changed" if removed else "primary_outcome_added"
    return [_change(kind, "primary_outcomes", old, new, removed=removed, added=added)]


def _enrollment_changes(old: dict, new: dict) -> list[dict]:
    a, b = old.get("enrollment"), new.get("enrollment")
    if a == b or a is None or b is None:
        return []
    details = {"old_type": old.get("enrollment_type"), "new_type": new.get("enrollment_type")}
    if b > a:
        return [_change("enrollment_increased", "enrollment", a, b, **details)]
    percent = round((a - b) / a * 100, 1) if a else 0
    kind = "enrollment_cut" if percent >= ENROLLMENT_CUT_PERCENT else "enrollment_small_cut"
    return [_change(kind, "enrollment", a, b, percent_cut=percent, **details)]


def _date_changes(old: dict, new: dict) -> list[dict]:
    changes = []
    for field in DATE_FIELDS:
        a, b = parse_date(old.get(field)), parse_date(new.get(field))
        if a == b or a is None or b is None:
            continue
        months = months_between(a, b)
        if months >= DATE_DELAY_MONTHS:
            kind = "date_delayed"
        elif months < 0:
            kind = "date_moved_earlier"
        else:
            kind = "date_small_change"
        changes.append(_change(kind, field, old.get(field), new.get(field), months=months))
    return changes


def compare(old: dict, new: dict, other_sections_changed: list[str] | None = None) -> list[dict]:
    """All meaningful changes between two trial summaries.

    other_sections_changed: names of raw-record sections that changed (e.g. contacts),
    used to report a 'paperwork' change when nothing important changed.
    """
    changes = []
    changes += _outcome_changes(old.get("primary_outcomes"), new.get("primary_outcomes"))
    changes += _enrollment_changes(old, new)
    changes += _date_changes(old, new)

    if old.get("overall_status") != new.get("overall_status"):
        kind = "trial_stopped" if new.get("overall_status") in STOPPED_STATUSES else "status_changed"
        changes.append(_change(kind, "overall_status", old.get("overall_status"), new.get("overall_status")))

    if not old.get("results_first_posted") and new.get("results_first_posted"):
        changes.append(_change("results_posted", "results_first_posted", None, new["results_first_posted"]))

    if sorted(map(_norm, old.get("interventions") or [])) != sorted(map(_norm, new.get("interventions") or [])):
        changes.append(_change("interventions_changed", "interventions", old.get("interventions"), new.get("interventions")))

    if sorted(old.get("phases") or []) != sorted(new.get("phases") or []):
        changes.append(_change("phase_changed", "phases", old.get("phases"), new.get("phases")))

    if not changes and other_sections_changed:
        changes.append(_change("paperwork", "other", None, None, paperwork=True, sections=other_sections_changed))
    return changes
