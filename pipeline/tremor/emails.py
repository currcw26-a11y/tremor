"""Writing alert emails (plain English, phone-friendly) and sending them.

Every email has: what changed, the score before/after, why it might matter, money left,
when we'll find out, links to check, "Not investment advice", and a one-click unsubscribe.
"""
import html
import os

import requests

from .words import money_left, nice_date

SITE_URL = (os.getenv("SITE_URL") or "https://www.tremoralerts.com").rstrip("/")
EMAIL_FROM = os.getenv("EMAIL_FROM") or "Tremor <onboarding@resend.dev>"  # switch to your domain once verified

COLORS = {"calm": "#166534", "shaky": "#d97706", "tremor": "#b91c1c"}
LABELS = {"calm": "● Calm", "shaky": "▲ Shaky", "tremor": "◆ Tremor"}
KIND_ICON = {"critical": "🔴", "big_jump": "🔴", "head_start": "🟡"}


def _e(s) -> str:
    return html.escape(str(s or ""))


def alert_block(a: dict, trial: dict | None, company: dict | None, trial_count: int) -> tuple[str, str]:
    """(html, text) for one tremor."""
    rows: list[tuple[str, str]] = [("What happened", a["headline"])]
    if a.get("old_score") is not None:
        rows.append(("Worry score", f"{a['old_score']} → {a['new_score']} (out of 100)"))
    elif a.get("new_score") is not None:
        rows.append(("Worry score now", f"{a['new_score']} out of 100"))
    if a.get("explanation"):
        rows.append(("Why it might matter", a["explanation"]))
    if company:
        rows.append(("How big a deal for them", f"Tremor tracks {trial_count} of {company['name']}'s cancer trials."
                     + (" This is one of only a few, so each one matters more." if trial_count <= 3 else "")))
        ml = money_left(company)
        if ml:
            rows.append(("Money left", ml))
    if trial and trial.get("primary_completion_date"):
        rows.append(("When we'll find out", f"Main results are expected around {nice_date(trial['primary_completion_date'])}."))
    rows.append(("Past cases", "We're still collecting what happened in similar past cases, so we can't say yet how often this led to bad news."))

    links = []
    if a.get("nct_id"):
        links += [("This trial on Tremor", f"{SITE_URL}/trials/{a['nct_id']}"),
                  ("Every edit to the official record", f"https://clinicaltrials.gov/study/{a['nct_id']}?tab=history")]
    if a.get("ticker"):
        links.append(("The company on Tremor", f"{SITE_URL}/companies/{a['ticker']}"))
    src = (a.get("details") or {}).get("source") or {}
    if isinstance(src.get("url"), str):
        links.append(("The original filing", src["url"]))

    icon = KIND_ICON.get(a["kind"], "🟡")
    title = f"{icon} {a.get('ticker') or ''}".strip()
    h = [f'<div style="border:1px solid #e7e5e4;border-radius:12px;padding:16px;margin:0 0 16px">',
         f'<p style="margin:0 0 8px;font-weight:800;font-size:18px">{_e(title)}</p>']
    for label, value in rows:
        h.append(f'<p style="margin:0 0 10px"><strong>{_e(label)}:</strong> {_e(value)}</p>')
    h.append('<p style="margin:12px 0 4px"><strong>What to check next:</strong></p><ul style="margin:0;padding-left:20px">')
    h += [f'<li><a href="{_e(u)}" style="color:#0c0a09">{_e(t)}</a></li>' for t, u in links]
    h.append("</ul></div>")
    t = [title] + [f"{label}: {value}" for label, value in rows] + ["What to check next:"] + [f"- {t}: {u}" for t, u in links]
    return "".join(h), "\n".join(t)


def render(alerts: list[dict], mode: str, trials: dict, companies: dict, trial_counts: dict,
           unsubscribe_token: str) -> dict:
    """Subject, HTML and plain text for one person's bundle."""
    n = len(alerts)
    tickers = ", ".join(dict.fromkeys(a.get("ticker") or "" for a in alerts if a.get("ticker")))
    if mode == "digest":
        subject = f"Tremor daily digest: {n} update{'s' if n != 1 else ''} ({tickers})"
        intro = "Here's what changed on the trials and companies you follow."
    elif n == 1:
        subject = f"{KIND_ICON.get(alerts[0]['kind'], '🔴')} Tremor: {alerts[0]['headline']}"[:120]
        intro = "Tremor just spotted this."
    else:
        subject = f"🔴 {n} new tremors: {tickers}"
        intro = f"Tremor just spotted {n} things."
    blocks = [alert_block(a, trials.get(a.get("nct_id")), companies.get(a.get("ticker")),
                          trial_counts.get(a.get("ticker"), 0)) for a in alerts]
    unsub = f"{SITE_URL}/unsubscribe?token={unsubscribe_token}"           # page with one button
    one_click = f"{SITE_URL}/api/unsubscribe?token={unsubscribe_token}"   # for Gmail/Apple Mail's own button
    settings = f"{SITE_URL}/settings"
    footer_text = ("Not investment advice. Tremor shows what changed in public records and never tells anyone to buy or sell. "
                   "Many trial edits turn out to be harmless.")
    body_html = (
        '<div style="font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;max-width:600px;margin:0 auto;'
        'padding:16px;color:#0c0a09;line-height:1.5">'
        '<p style="font-size:22px;font-weight:900;margin:0 0 4px">Tremor</p>'
        f'<p style="margin:0 0 16px;color:#57534e">{_e(intro)}</p>'
        + "".join(b[0] for b in blocks)
        + f'<p style="font-size:13px;color:#57534e;margin-top:24px"><strong>{_e(footer_text)}</strong></p>'
        f'<p style="font-size:13px;color:#57534e"><a href="{_e(unsub)}" style="color:#57534e">Unsubscribe</a>'
        f' · <a href="{_e(settings)}" style="color:#57534e">Alert settings</a></p></div>'
    )
    body_text = (intro + "\n\n" + "\n\n".join(b[1] for b in blocks) + f"\n\n{footer_text}\n"
                 f"Unsubscribe: {unsub}\nAlert settings: {settings}\n")
    return {"subject": subject, "html": body_html, "text": body_text, "unsubscribe_url": one_click}


class EmailChannel:
    """Sends through Resend. Another channel (like text messages) would offer the same send() method."""
    name = "email"

    def __init__(self):
        self.key = os.getenv("RESEND_API_KEY", "")

    def available(self) -> bool:
        return bool(self.key)

    def send(self, to: str, message: dict) -> str:
        resp = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"},
            json={
                "from": EMAIL_FROM, "to": [to], "subject": message["subject"],
                "html": message["html"], "text": message["text"],
                # Lets Gmail/Apple Mail show their own one-click "Unsubscribe" button
                "headers": {"List-Unsubscribe": f"<{message['unsubscribe_url']}>",
                            "List-Unsubscribe-Post": "List-Unsubscribe=One-Click"},
            },
            timeout=30,
        )
        if resp.status_code >= 300:
            raise RuntimeError(f"Resend {resp.status_code}: {resp.text[:300]}")
        return resp.json().get("id", "")
