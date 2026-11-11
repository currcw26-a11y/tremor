"""Tremor Weekly: pure helpers (no database), so they're easy to test.

Code gathers the week's facts; Claude only turns them into plain English. If Claude is over budget,
adds a number that isn't in the facts, or uses buy/sell language, we publish a short list written by
code instead, so there is always an issue.
"""
import re
from datetime import date, timedelta

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
ADVICE = re.compile(r"\b(buy|buying|sell|selling|hold|holding|invest in|should invest|price target|guaranteed?)\b", re.I)

SYSTEM = """You write "Tremor Weekly", a short weekly roundup for college students who have never bought a stock.
Use ONLY the facts given. Never add a number, date, statistic, prediction, or company that isn't in the facts.
Write numbers exactly as they appear in the facts. Never say or hint that anyone should buy, sell, or hold a stock.
Plain English, no jargon; explain any unavoidable term in a few words. Say plainly that many trial edits are harmless paperwork.
Format: plain text. Section titles on their own line starting with "## ". Bullets start with "- ".
Sections, in order: "## The week in brief" (2-3 sentences), "## What changed" (up to 6 bullets),
"## Coming up" (up to 5 bullets), "## Keep in mind" (1-2 sentences). If it was a quiet week, say so honestly.
Keep it under 300 words."""


def week_bounds(today: date) -> tuple[date, date]:
    """(Monday, Sunday) of the most recent FULL week before `today`."""
    this_monday = today - timedelta(days=today.weekday())
    start = this_monday - timedelta(days=7)
    return start, start + timedelta(days=6)


def nice(d: date) -> str:
    return f"{MONTHS[d.month - 1]} {d.day}"


def title_for(start: date, end: date) -> str:
    return f"Tremor Weekly: {nice(start)} to {nice(end)}, {end.year}"


def facts_text(f: dict) -> str:
    """The facts as plain lines. This is ALL Claude sees, and what the number check compares against."""
    lines = [f"Week: {nice(f['start'])} to {nice(f['end'])}, {f['end'].year}",
             f"Cancer trials Tremor watches: {f['trials_tracked']}",
             f"Important changes to trial records this week: {f['important_changes']}",
             f"Routine edits this week (usually harmless paperwork): {f['routine_changes']}"]
    if f["changes"]:
        lines.append("Important changes:")
        lines += [f"- {c['company']} ({c['ticker']}): {c['what']} in the trial \"{c['trial']}\"" for c in f["changes"]]
    if f["alerts"]:
        lines.append("Serious alerts this week:")
        lines += [f"- {a}" for a in f["alerts"]]
    if f["score_rises"]:
        lines.append("Biggest worry-score rises (out of 100):")
        lines += [f"- {r['company']} ({r['ticker']}), \"{r['trial']}\": {r['old']} to {r['new']}" for r in f["score_rises"]]
    if f["coming"]:
        lines.append("Coming up in the next 2 weeks:")
        lines += [f"- {c}" for c in f["coming"]]
    return "\n".join(lines)


def acceptable(text: str | None) -> bool:
    """Claude's draft must exist, use our section format, and contain no buy/sell language."""
    return bool(text) and "## " in text and not ADVICE.search(text)


def fallback_body(f: dict) -> str:
    """A plain list written by code, used when Claude can't (or shouldn't) write this week."""
    out = ["## The week in brief",
           f"Tremor spotted {f['important_changes']} important change{'s' if f['important_changes'] != 1 else ''} "
           f"to trial records this week, plus {f['routine_changes']} routine edit{'s' if f['routine_changes'] != 1 else ''}, "
           "which are usually harmless paperwork."]
    if f["changes"] or f["alerts"]:
        out.append("## What changed")
        out += [f"- {c['company']} ({c['ticker']}): {c['what']}" for c in f["changes"][:6]]
        out += [f"- {a}" for a in f["alerts"][: max(0, 6 - len(f['changes']))]]
    if f["coming"]:
        out.append("## Coming up")
        out += [f"- {c}" for c in f["coming"][:5]]
    out += ["## Keep in mind", "A warning sign is not a prediction. Many changes turn out to be ordinary."]
    return "\n".join(out)
