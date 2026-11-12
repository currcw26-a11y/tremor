"""Alerts part of each pipeline run.

1. Spot tremors (alerts.detect) and keep only ones we haven't seen before.
   The very first time, everything that already exists is recorded as "baseline" and never emailed,
   so nobody gets 800 emails on day one.
2. Give each new tremor a plain-English explanation (reused from the change, or written by Claude).
3. Decide who gets each one and when (instant vs. daily digest).
4. Send instant emails now, bundled one per person. Once a day, send the digest.
   Never go over Resend's free limits; digests are skipped before instant alerts.
"""
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from . import ai, alerts, config, db, emails
from .explain_job import STATUS_WORDS

COMPANY_FIELDS = "ticker,name,cash_usd,monthly_burn_usd,runway_months,finances_as_of,burn_period_months"

ALERT_SYSTEM = """You explain alerts for Tremor, a website for college students who have never bought a stock.
Write 2 short sentences: why investors pay attention to this kind of event, and that it can also have ordinary reasons.
Rules: use ONLY the facts given; never add a number, date, statistic, or prediction; write numbers as digits;
never say or hint that anyone should buy, sell, or hold a stock; no jargon; plain text only."""


def _now():
    return datetime.now(timezone.utc)


def _load_context():
    fields = ("nct_id,ticker,sponsor_name,title,score,score_label,score_breakdown,"
              "primary_completion_date,overall_status")
    try:
        trials = db.select("trials", fields + ",outlook", tracked="eq.true")
    except RuntimeError:  # migration 009 (the upside/downside breakdown) not run yet
        trials = db.select("trials", fields, tracked="eq.true")
    try:
        companies = {c["ticker"]: c for c in db.select("companies", COMPANY_FIELDS)}
    except RuntimeError:  # money-left columns not added yet
        companies = {c["ticker"]: c for c in db.select("companies", "ticker,name")}
    counts = defaultdict(int)
    for t in trials:
        counts[t["ticker"]] += 1
    return trials, companies, counts


def _explain(alert: dict, trials: dict, companies: dict) -> str | None:
    src = (alert.get("details") or {}).get("source") or {}
    if src.get("change_id"):  # reuse the explanation already written for this record change
        rows = db.select("trial_changes", "explanation", id=f"eq.{src['change_id']}")
        if rows and rows[0].get("explanation"):
            return rows[0]["explanation"]
    t = trials.get(alert.get("nct_id")) or {}
    c = companies.get(alert.get("ticker")) or {}
    facts = "\n".join(x for x in [
        f"Company: {c.get('name', '')} (stock ticker {alert.get('ticker')})",
        f"Trial: {t['title']}" if t else "",
        f"Trial status: {STATUS_WORDS.get(t.get('overall_status'), t.get('overall_status'))}" if t else "",
        f"Event: {alert['headline']}",
        f"Worry score: {alert['old_score']} -> {alert['new_score']}" if alert.get("old_score") is not None else "",
        f"Filing excerpt: {src['text']}" if src.get("text") else "",
    ] if x)
    return ai.write("alert", ALERT_SYSTEM, facts, essential=True, max_tokens=1500)


def _reminders(companies: dict) -> list[dict]:
    try:
        events = [e for e in db.select("upcoming_events", "*") if e["kind"] != "conference"]   # no company to watch
    except RuntimeError:   # migration 010 not run yet
        return []
    names = {t: _short_name(c.get("name") or t) for t, c in companies.items()}
    return alerts.coming_up(events, names, _now().date())


def _short_name(name: str) -> str:
    import re
    n = re.sub(r"\s*/\s*[a-z]{2}\s*/?\s*$", "", name, flags=re.I).strip()
    if n == n.upper():
        n = n.title()
    # Drop legal endings ("Inc.", "plc", "S.A.") and fix a few well-known spellings that title-case gets wrong
    n = re.sub(r",?\s+(Inc|Corp|Corporation|Co|Ltd|Limited|plc|S\.?A|N\.?V|AG|SE)\.?$", "", n, flags=re.I).strip()
    return {"Astrazeneca": "AstraZeneca", "Glaxosmithkline": "GlaxoSmithKline", "Biontech": "BioNTech",
            "Beigene": "BeiGene"}.get(n, n)


def _sent_counts():
    now = _now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    month_rows = db.select("email_log", "sent_at", ok="eq.true", sent_at=f"gte.{month}")
    return sum(r["sent_at"] >= today for r in month_rows), len(month_rows)


def _send_bundles(mode: str, allowance: int, channel, profiles: dict, trials: dict, companies: dict, counts: dict) -> dict:
    pending = db.select("alert_deliveries", "user_id,alert_id", status="eq.pending", mode=f"eq.{mode}",
                        channel=f"eq.{channel.name}")
    by_user = defaultdict(list)
    for d in pending:
        by_user[d["user_id"]].append(d["alert_id"])
    if not by_user:
        return {"sent": 0}
    ids = sorted({i for v in by_user.values() for i in v})
    alert_rows = {a["id"]: a for a in db.select("alerts", "*", id=f"in.({','.join(map(str, ids))})")}
    sent = failed = held = 0
    for uid, alert_ids in by_user.items():
        p = profiles.get(uid)
        if not p or p.get("unsubscribed"):
            _mark(uid, alert_ids, mode, "skipped")
            continue
        if sent >= allowance:
            held += 1  # over today's budget: stays pending for the next run
            continue
        bundle = sorted((alert_rows[i] for i in alert_ids if i in alert_rows),
                        key=lambda a: (not a["is_huge"], a["kind"] != "critical", -(a.get("new_score") or 0)))
        msg = emails.render(bundle, mode, trials, companies, counts, p["unsubscribe_token"])
        try:
            provider_id = channel.send(p["email"], msg)
            db.insert("email_log", [{"kind": mode, "user_id": uid, "provider_id": provider_id, "ok": True}])
            _mark(uid, alert_ids, mode, "sent")
            sent += 1
        except Exception as err:
            failed += 1
            print(f"    email to user {uid[:8]} failed: {err}")
            db.insert("email_log", [{"kind": mode, "user_id": uid, "ok": False, "note": str(err)[:300]}])
            _mark(uid, alert_ids, mode, "failed")
    return {"sent": sent, "failed": failed, "held_for_budget": held}


def _mark(uid, alert_ids, mode, status):
    db.update("alert_deliveries", {"status": status, "sent_at": _now().isoformat() if status == "sent" else None},
              user_id=f"eq.{uid}", mode=f"eq.{mode}", alert_id=f"in.({','.join(map(str, alert_ids))})")


WELCOME_MAX_TRIES = 3


def welcome_due(profiles: list[dict], failed_tries: dict[str, int]) -> list[dict]:
    """People who still need a welcome email: not sent yet, not unsubscribed, fewer than 3 failed tries."""
    return [p for p in profiles if not p.get("welcome_sent_at") and not p.get("unsubscribed")
            and failed_tries.get(p["user_id"], 0) < WELCOME_MAX_TRIES]


def send_welcomes(channel=None) -> dict:
    """Backup for the website: it sends the welcome email the moment someone signs up; this sends any it missed."""
    channel = channel or emails.EmailChannel()
    try:
        profiles = db.select("profiles", "user_id,email,name,unsubscribed,unsubscribe_token,welcome_sent_at",
                             welcome_sent_at="is.null")
    except RuntimeError as err:
        return {"skipped": f"welcome_sent_at missing (run migration 014): {str(err)[:80]}"}
    if not profiles:
        return {"sent": 0}
    if not channel.available():
        return {"skipped": "RESEND_API_KEY not set", "waiting": len(profiles)}
    failed = defaultdict(int)
    for r in db.select("email_log", "user_id", kind="eq.welcome", ok="eq.false"):
        failed[r["user_id"]] += 1
    cfg = config.load()["email"]
    today_n, month_n = _sent_counts()
    sent = errors = 0
    for p in welcome_due(profiles, failed):
        if today_n + sent >= cfg["daily_limit"] or month_n + sent >= cfg["monthly_limit"]:
            break   # out of emails for now; the next run tries again
        if not db.claim("profiles", {"welcome_sent_at": _now().isoformat()}, user_id=f"eq.{p['user_id']}",
                        welcome_sent_at="is.null"):
            continue   # the website got there first
        try:
            provider_id = channel.send(p["email"], emails.welcome(p.get("name"), p["unsubscribe_token"]))
            db.insert("email_log", [{"kind": "welcome", "user_id": p["user_id"], "provider_id": provider_id, "ok": True}])
            sent += 1
        except Exception as err:
            errors += 1
            print(f"    welcome email to user {p['user_id'][:8]} failed: {err}")
            db.update("profiles", {"welcome_sent_at": None}, user_id=f"eq.{p['user_id']}")
            db.insert("email_log", [{"kind": "welcome", "user_id": p["user_id"], "ok": False, "note": str(err)[:300]}])
    return {"sent": sent, "failed": errors}


def run(daily: bool = False) -> dict:
    cfg = config.load()
    trials_list, companies, counts = _load_context()
    trials = {t["nct_id"]: t for t in trials_list}
    since = (_now() - timedelta(days=3)).isoformat()
    history = db.select("score_history", "id,nct_id,old_score,new_score,old_label,new_label", computed_at=f"gte.{since}")

    found = alerts.detect(trials_list, history, cfg)
    seen = {a["dedupe_key"] for a in db.select("alerts", "dedupe_key")}
    first_time = not seen
    new = [a for k, a in found.items() if k not in seen]

    new = alerts.drop_redundant_jumps(new)
    if daily:   # once a day: "coming up" reminders for watchers (FDA decisions, results due)
        new += [a for a in _reminders(companies) if a["dedupe_key"] not in seen]
    if first_time:
        db.insert("alerts", [{**a, "baseline": True} for a in new])
        return {"baseline_recorded": len(new), "note": "first run: existing signals recorded, nothing emailed"}

    for a in new:
        if a["kind"] != "coming_up":   # reminders carry fixed wording; no AI needed
            a["explanation"] = _explain(a, trials, companies)
    saved = db.insert("alerts", new, returning="id,dedupe_key") if new else []
    ids = {r["dedupe_key"]: r["id"] for r in saved}

    profiles = {p["user_id"]: p for p in db.select("profiles", "*")}
    watch_t, watch_c = defaultdict(set), defaultdict(set)
    for w in db.select("watch_trials", "user_id,nct_id"):
        watch_t[w["user_id"]].add(w["nct_id"])
    for w in db.select("watch_companies", "user_id,ticker"):
        watch_c[w["user_id"]].add(w["ticker"])
    trial_ticker = {n: t["ticker"] for n, t in trials.items()}
    deliveries = []
    for a in new:
        for uid, mode in alerts.interested_users(a, list(profiles.values()), watch_t, watch_c, trial_ticker):
            deliveries.append({"user_id": uid, "alert_id": ids[a["dedupe_key"]], "channel": "email", "mode": mode})
    if deliveries:
        db.insert("alert_deliveries", deliveries)

    stats = {"new_tremors": len(new), "critical": sum(a["kind"] == "critical" for a in new),
             "deliveries_queued": len(deliveries)}
    channel = emails.EmailChannel()
    if not channel.available():
        return {**stats, "emails": "skipped: no RESEND_API_KEY"}
    sent_today, sent_month = _sent_counts()
    allow = alerts.email_allowance(sent_today, sent_month, cfg)
    stats["instant"] = _send_bundles("instant", allow["instant"], channel, profiles, trials, companies, counts)
    if daily and _now().hour >= cfg["email"]["digest_hour_utc"]:
        left = alerts.email_allowance(sent_today + stats["instant"]["sent"], sent_month + stats["instant"]["sent"], cfg)
        stats["digest"] = _send_bundles("digest", left["digest"], channel, profiles, trials, companies, counts)
    return stats


def send_test(to_email: str | None = None) -> dict:
    """Email a preview built from the latest real tremors, to check how emails look."""
    if not emails.EmailChannel().available():
        return {"test": "skipped: no RESEND_API_KEY secret in GitHub"}
    trials_list, companies, counts = _load_context()
    trials = {t["nct_id"]: t for t in trials_list}
    profiles = db.select("profiles", "*", order="created_at", limit="1")
    if not profiles:
        return {"test": "no profiles yet"}
    p = profiles[0]
    recent = db.select("alerts", "*", order="baseline.asc,detected_at.desc", limit="3")
    if not recent:
        return {"test": "no alerts yet"}
    msg = emails.render(recent, "instant", trials, companies, counts, p["unsubscribe_token"])
    msg["subject"] = "[Test] " + msg["subject"]
    provider_id = emails.EmailChannel().send(to_email or p["email"], msg)
    db.insert("email_log", [{"kind": "test", "user_id": p["user_id"], "provider_id": provider_id, "ok": True}])
    return {"test_email_sent_to": to_email or p["email"]}
