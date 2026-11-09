"""Spotting "tremors" (alert-worthy events) and deciding who gets each one.

Pure logic only (no database or email), so it's easy to test.

A tremor comes from either:
  - a signal behind a trial's score (see scoring.py), like "trial stopped" or "insider selling", or
  - a big score jump (15+ points in one update) or a score turning red.

Kinds (rules live in config/tremor.yaml under `alerts`):
  critical   -> emailed right away, to watchers AND everyone else ("huge")
  big_jump   -> emailed right away to watchers; to everyone if the score just turned red
  head_start -> goes into the daily digest for watchers
"""
from . import config

COMPANY_WIDE = {"insider_selling_cluster", "key_exec_departure", "layoffs"}


def classify(signal_type: str, reason_label: str = "", cfg: dict | None = None):
    """(kind, instant, huge) for a score signal, or None if it isn't alert-worthy."""
    a = (cfg or config.load())["alerts"]
    if signal_type == "enrollment_cut" and "final count" in reason_label:
        return ("head_start", False, False)  # trimmed to the final real count: less alarming
    if signal_type in a["critical"]:
        return ("critical", True, True)
    if signal_type in a["head_start"]:
        return ("head_start", False, False)
    return None


def dedupe_key(signal_type: str, nct_id: str | None, ticker: str | None, occurred: str) -> str:
    if signal_type == "trial_stopped":  # its "date" is just today's, so leave it out
        return f"trial_stopped:{nct_id}"
    if signal_type in COMPANY_WIDE:
        return f"{signal_type}:{ticker}:{occurred}"
    return f"{signal_type}:{nct_id}:{occurred}"


def detect(trials: list[dict], history: list[dict], cfg: dict | None = None) -> dict[str, dict]:
    """All current tremors, keyed by dedupe_key. The caller drops keys it has already seen.

    trials: tracked trials with nct_id, ticker, sponsor_name, title, score, score_label, score_breakdown
    history: recent score_history rows with id, nct_id, old_score, new_score, old_label, new_label
    """
    cfg = cfg or config.load()
    by_nct = {t["nct_id"]: t for t in trials}
    found: dict[str, dict] = {}
    for t in trials:
        for r in t.get("score_breakdown") or []:
            c = classify(r["type"], r.get("label", ""), cfg)
            if not c:
                continue
            kind, instant, huge = c
            company_wide = r["type"] in COMPANY_WIDE
            key = dedupe_key(r["type"], t["nct_id"], t["ticker"], r["occurred"])
            if key in found:
                continue
            found[key] = {
                "nct_id": None if company_wide else t["nct_id"],
                "ticker": t["ticker"],
                "kind": kind, "signal_type": r["type"], "instant": instant, "is_huge": huge,
                "headline": f"{t['sponsor_name']}: {r['label']}" if company_wide
                            else f"{r['label']} in “{t['title']}”",
                "old_score": None, "new_score": None if company_wide else t["score"],
                "details": {"source": r.get("source") or {}, "occurred": r["occurred"]},
                "dedupe_key": key,
            }
    jump = cfg["alerts"]["big_jump_points"]
    for h in history:
        t = by_nct.get(h["nct_id"])
        if not t or h.get("old_score") is None:
            continue
        turned_red = h["new_label"] == "tremor" and h.get("old_label") != "tremor"
        if h["new_score"] - h["old_score"] < jump and not turned_red:
            continue
        key = f"jump:{h['id']}"
        found[key] = {
            "nct_id": t["nct_id"], "ticker": t["ticker"], "kind": "big_jump", "signal_type": "score_jump",
            "instant": True, "is_huge": turned_red,
            "headline": f"Worry score jumped from {h['old_score']} to {h['new_score']} for “{t['title']}”",
            "old_score": h["old_score"], "new_score": h["new_score"],
            "details": {"history_id": h["id"]}, "dedupe_key": key,
        }
    return found


def interested_users(alert: dict, profiles: list[dict], watch_trials: dict[str, set], watch_companies: dict[str, set],
                     trial_ticker: dict[str, str]) -> list[tuple[str, str]]:
    """[(user_id, 'instant' | 'digest')] for one alert.

    Watchers of the trial or its company get it; "huge" alerts go to everyone.
    Instant alerts fall back to the digest for people who turned instant alerts off.
    """
    out = []
    for p in profiles:
        if p.get("unsubscribed"):
            continue
        uid = p["user_id"]
        my_trials, my_companies = watch_trials.get(uid, set()), watch_companies.get(uid, set())
        watching = (alert.get("nct_id") in my_trials or alert.get("ticker") in my_companies
                    or (alert.get("nct_id") is None and any(trial_ticker.get(n) == alert.get("ticker") for n in my_trials)))
        if not (watching or alert.get("is_huge")):
            continue
        if alert.get("instant") and p.get("instant_alerts", True):
            out.append((uid, "instant"))
        elif p.get("daily_digest", True):
            out.append((uid, "digest"))
    return out


def email_allowance(sent_today: int, sent_this_month: int, cfg: dict | None = None) -> dict[str, int]:
    """How many more instant and digest emails we may send right now without passing the free limits."""
    e = (cfg or config.load())["email"]
    left = max(0, min(e["daily_limit"] - sent_today, e["monthly_limit"] - sent_this_month))
    return {"instant": left, "digest": max(0, left - e["reserve_for_instant"])}
