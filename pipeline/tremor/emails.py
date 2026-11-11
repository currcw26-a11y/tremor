"""Writing alert emails (plain English, phone-friendly) and sending them.

Every email has: what changed, the score before/after, why it might matter, money left,
when we'll find out, links to check, "Not investment advice", and a one-click unsubscribe.
"""
import html
import os
from datetime import date

import requests

from .words import money_left, nice_date

SITE_URL = (os.getenv("SITE_URL") or "https://www.tremoralerts.com").rstrip("/")
EMAIL_FROM = os.getenv("EMAIL_FROM") or "Tremor <alerts@tremoralerts.com>"  # domain verified in Resend on Nov 9, 2026

# Same palette and type as the website. The gold here is the darker text version, so it reads on white.
COLORS = {"calm": "#18794e", "shaky": "#8a5a00", "tremor": "#b4232c"}
INK, MUTED, LINE, LINK = "#0b1626", "#667085", "#e2e6eb", "#1b3a63"
SANS = "'IBM Plex Sans',-apple-system,'Segoe UI',Helvetica,Arial,sans-serif"
SERIF = "Newsreader,Georgia,'Times New Roman',serif"
LOGO = "".join(
    f'<span style="display:inline-block;width:5px;height:{h}px;border-radius:3px;background:{c};margin-right:{m}px"></span>'
    for h, c, m in ((14, "#18794e", 3), (18, "#d4900a", 3), (22, "#b4232c", 10)))


def _block_html(title: str, rows: list[tuple[str, str]], links: list[tuple[str, str]]) -> str:
    """One tremor in an email: a rule on top, a serif title, label/value lines, then links to check."""
    h = [f'<div style="border-top:2px solid {INK};padding:14px 0 4px;margin:0 0 26px">',
         f'<p style="margin:0 0 10px;font-family:{SERIF};font-weight:500;font-size:21px;color:{INK}">{_e(title)}</p>']
    h += [f'<p style="margin:0 0 10px"><strong>{_e(k)}:</strong> {_e(v)}</p>' for k, v in rows]
    h.append(f'<p style="margin:14px 0 4px;color:{MUTED};font-size:13px;text-transform:uppercase;letter-spacing:1px">'
             f'What to check next</p><ul style="margin:0;padding-left:20px">')
    h += [f'<li style="margin:2px 0"><a href="{_e(u)}" style="color:{LINK}">{_e(t)}</a></li>' for t, u in links]
    h.append("</ul></div>")
    return "".join(h)
LABELS = {"calm": "● Calm", "shaky": "▲ Shaky", "tremor": "◆ Tremor"}
KIND_ICON = {"critical": "🔴", "big_jump": "🔴", "head_start": "🟡", "coming_up": "📅"}


def _e(s) -> str:
    return html.escape(str(s or ""))


def pick_past_cases(outlook: dict, signal_type: str | None) -> dict | None:
    """The past-cases entry for this alert's signal (a score jump uses the trial's best-documented signal)."""
    signals = (outlook or {}).get("signals") or []
    match = [s for s in signals if s["type"] == signal_type]
    return (match or signals or [None])[0]


def sure_words(past: dict) -> str:
    n = past.get("cases") or 0
    if not past.get("has_history"):
        return "Low. There aren't enough past cases yet."
    if n < 10:
        return f"Low. Only {n} past cases."
    if n < 30:
        return f"Medium. {n} past cases is a decent number, but not a lot."
    return f"High. Based on {n} past cases."


def alert_block(a: dict, trial: dict | None, company: dict | None, trial_count: int,
                today: date | None = None) -> tuple[str, str]:
    """(html, text) for one tremor."""
    if a["kind"] == "coming_up":
        return _coming_up_block(a, company)
    rows: list[tuple[str, str]] = [("What happened", a["headline"])]
    if a.get("old_score") is not None:
        rows.append(("Worry score", f"{a['old_score']} → {a['new_score']} (out of 100)"))
    elif a.get("new_score") is not None:
        rows.append(("Worry score now", f"{a['new_score']} out of 100"))
    if a.get("explanation"):
        rows.append(("Why it might matter", a["explanation"]))
    ol = (trial or {}).get("outlook") or {}
    if ol.get("stakes"):
        rows.append(("How big a deal for them", ol["stakes"]["text"]))
    elif company:
        rows.append(("How big a deal for them", f"Tremor tracks {trial_count} of {company['name']}'s cancer trials."
                     + (" This is one of only a few, so each one matters more." if trial_count <= 3 else "")))
        ml = money_left(company)
        if ml:
            rows.append(("Money left", ml))
    if trial and trial.get("primary_completion_date"):
        due = trial["primary_completion_date"]
        if str(due)[:10] < (today or date.today()).isoformat()[: len(str(due)[:10])]:
            rows.append(("When we'll find out", f"Main results were due around {nice_date(due)}. That date has passed "
                         "and no results are posted yet."))
        else:
            rows.append(("When we'll find out", f"Main results are expected around {nice_date(due)}."))
    past = pick_past_cases(ol, a.get("signal_type"))
    if past:
        rows.append(("When this happened before", " ".join(past["sentences"])))
        rows.append(("How sure are we", sure_words(past)))
    else:
        rows.append(("When this happened before", "We don't have enough similar past cases yet to say how often this "
                     "led to bad news."))

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
    t = [title] + [f"{label}: {value}" for label, value in rows] + ["What to check next:"] + [f"- {t}: {u}" for t, u in links]
    return _block_html(title, rows, links), "\n".join(t)


def _coming_up_block(a: dict, company: dict | None) -> tuple[str, str]:
    """A reminder: what's coming, why it matters, the company's own words, and money left."""
    d = a.get("details") or {}
    rows = [("Coming up", a["headline"]), ("Why it matters", a.get("explanation") or "")]
    if d.get("quote"):
        rows.append(("In the company's words", f"“{d['quote']}”"))
    ml = money_left(company) if company else None
    if ml:
        rows.append(("Money left", ml))
    links = [("Everything coming up on Tremor", f"{SITE_URL}/upcoming")]
    if a.get("nct_id"):
        links.insert(0, ("This trial on Tremor", f"{SITE_URL}/trials/{a['nct_id']}"))
    if a.get("ticker"):
        links.append(("The company on Tremor", f"{SITE_URL}/companies/{a['ticker']}"))
    src = (d.get("source") or {}).get("url")
    if isinstance(src, str) and src:
        links.append(("Where this date comes from", src))
    title = f"📅 {a.get('ticker') or ''}".strip()
    t = [title] + [f"{k}: {v}" for k, v in rows] + ["What to check next:"] + [f"- {k}: {u}" for k, u in links]
    return _block_html(title, rows, links), "\n".join(t)


def short_subject(a: dict, companies: dict) -> str:
    """'Cellectis (CLLS): changed the trial's main goal' — short enough for a phone's inbox."""
    name = (companies.get(a.get("ticker")) or {}).get("name") or a.get("ticker") or "Tremor"
    name = name.split(",")[0].replace(" S.A.", "").replace(" Inc.", "").replace(" Inc", "").strip()
    event = (a.get("details") or {}).get("short") or a["headline"].split(" in “")[0]
    event = event[0].lower() + event[1:] if event[:2] != event[:2].upper() else event
    return f"{name} ({a.get('ticker')}): {event}"[:90] if a.get("ticker") else event[:90]


def render(alerts: list[dict], mode: str, trials: dict, companies: dict, trial_counts: dict,
           unsubscribe_token: str) -> dict:
    """Subject, HTML and plain text for one person's bundle."""
    n = len(alerts)
    tickers = ", ".join(dict.fromkeys(a.get("ticker") or "" for a in alerts if a.get("ticker")))
    if mode == "digest":
        subject = f"Tremor daily digest: {n} update{'s' if n != 1 else ''} ({tickers})"
        intro = "Here's what changed on the trials and companies you follow."
    elif n == 1:
        subject = f"{KIND_ICON.get(alerts[0]['kind'], '🔴')} {short_subject(alerts[0], companies)}"
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
        f'<div style="font-family:{SANS};max-width:600px;margin:0 auto;padding:20px 16px;color:{INK};line-height:1.55">'
        f'<p style="margin:0 0 6px;font-family:{SERIF};font-size:26px;font-weight:600;letter-spacing:-0.3px">{LOGO}Tremor</p>'
        f'<p style="margin:0 0 26px;color:{MUTED}">{_e(intro)}</p>'
        + "".join(b[0] for b in blocks)
        + f'<p style="font-size:13px;color:{MUTED};margin-top:28px;border-top:1px solid {LINE};padding-top:14px">'
        f'<strong style="color:{INK}">{_e(footer_text)}</strong></p>'
        f'<p style="font-size:13px;color:{MUTED}"><a href="{_e(unsub)}" style="color:{MUTED}">Unsubscribe</a>'
        f' · <a href="{_e(settings)}" style="color:{MUTED}">Alert settings</a></p></div>'
    )
    body_text = (intro + "\n\n" + "\n\n".join(b[1] for b in blocks) + f"\n\n{footer_text}\n"
                 f"Unsubscribe: {unsub}\nAlert settings: {settings}\n")
    return {"subject": subject, "html": body_html, "text": body_text, "unsubscribe_url": one_click}


WELCOME_SUBJECT = "Welcome to Tremor"


def welcome_template() -> dict:
    """The welcome email, with {{GREETING}} and {{UNSUBSCRIBE_URL}} left to fill in.
    The website sends it the moment someone signs up (web/lib/welcome-email.json, exported by
    `python -m tremor.export_rules`); the pipeline sends any the website missed. Same words either way."""
    settings = f"{SITE_URL}/settings"
    gets = [
        ("Right away", "an email when something big happens to a trial or company you follow, like a trial "
                       "stopping or its main goal changing. You'll also hear about the very biggest events on any "
                       "trial Tremor tracks, like a trial being stopped or a worry score turning red."),
        ("Once a day", "smaller changes to what you follow, plus reminders about a month and a week before "
                       "an FDA decision or expected trial results."),
        ("Quiet days", "you only get an email when something actually happens, so many days there's nothing."),
    ]
    start = [
        ("Find trials to follow", f"{SITE_URL}/trials", "Tap the star on any trial or company."),
        ("See what's coming up", f"{SITE_URL}/upcoming", "FDA decisions and trial results expected soon."),
        ("New to biotech stocks?", f"{SITE_URL}/learn", "A 2-minute guide to how they move."),
        ("How the worry score works", f"{SITE_URL}/how-it-works", "Every rule, written simply."),
    ]
    footer_text = ("Not investment advice. Tremor shows what changed in public records and never tells anyone to "
                   "buy or sell. Many trial edits turn out to be harmless.")
    h = [f'<div style="font-family:{SANS};max-width:600px;margin:0 auto;padding:20px 16px;color:{INK};line-height:1.55">',
         f'<p style="margin:0 0 26px;font-family:{SERIF};font-size:26px;font-weight:600;letter-spacing:-0.3px">{LOGO}Tremor</p>',
         '<p style="margin:0 0 12px">{{GREETING}}</p>',
         '<p style="margin:0 0 26px">Thanks for signing up. Tremor watches public records about cancer drug trials '
         'and the companies running them, and emails you when something changes that could matter before big news '
         'comes out. You\'re all set: there\'s nothing else to do, and you won\'t need to sign in again.</p>',
         f'<div style="border-top:2px solid {INK};padding:14px 0 4px;margin:0 0 26px">',
         f'<p style="margin:0 0 10px;font-family:{SERIF};font-weight:500;font-size:21px">What you\'ll get</p>']
    h += [f'<p style="margin:0 0 10px"><strong>{_e(k)}:</strong> {_e(v)}</p>' for k, v in gets]
    h += ["</div>", f'<div style="border-top:2px solid {INK};padding:14px 0 4px;margin:0 0 26px">',
          f'<p style="margin:0 0 10px;font-family:{SERIF};font-weight:500;font-size:21px">Get started</p>']
    h += [f'<p style="margin:0 0 10px"><a href="{_e(u)}" style="color:{LINK};font-weight:600">{_e(t)}</a><br>'
          f'<span style="color:{MUTED}">{_e(d)}</span></p>' for t, u, d in start]
    h += ["</div>",
          f'<p style="margin:0 0 10px">You can choose which emails you get in your '
          f'<a href="{_e(settings)}" style="color:{LINK}">alert settings</a>.</p>',
          f'<p style="font-size:13px;color:{MUTED};margin-top:28px;border-top:1px solid {LINE};padding-top:14px">'
          f'<strong style="color:{INK}">{_e(footer_text)}</strong></p>',
          f'<p style="font-size:13px;color:{MUTED}"><a href="{{{{UNSUBSCRIBE_URL}}}}" style="color:{MUTED}">Unsubscribe</a>'
          f' · <a href="{_e(settings)}" style="color:{MUTED}">Alert settings</a></p></div>']
    text = ("{{GREETING}}\n\nThanks for signing up. Tremor watches public records about cancer drug trials and the "
            "companies running them, and emails you when something changes that could matter before big news comes "
            "out. You're all set: there's nothing else to do, and you won't need to sign in again.\n\n"
            "WHAT YOU'LL GET\n" + "\n".join(f"- {k}: {v}" for k, v in gets) + "\n\nGET STARTED\n"
            + "\n".join(f"- {t}: {u} ({d})" for t, u, d in start)
            + f"\n\nChoose which emails you get: {settings}\n\n{footer_text}\nUnsubscribe: {{{{UNSUBSCRIBE_URL}}}}\n")
    return {"subject": WELCOME_SUBJECT, "html": "".join(h), "text": text}


def greeting(name: str | None) -> str:
    first = (name or "").strip().split(" ")[0]
    return f"Hi {first}," if first and len(first) <= 40 else "Hi,"


def welcome(name: str | None, unsubscribe_token: str) -> dict:
    """The welcome email for one person (the pipeline's copy; the website fills the same template)."""
    t = welcome_template()
    fill = {"{{UNSUBSCRIBE_URL}}": f"{SITE_URL}/unsubscribe?token={unsubscribe_token}"}
    html, text = t["html"], t["text"]
    for k, v in fill.items():
        html, text = html.replace(k, _e(v)), text.replace(k, v)
    g = greeting(name)
    return {"subject": t["subject"], "html": html.replace("{{GREETING}}", _e(g)), "text": text.replace("{{GREETING}}", g),
            "unsubscribe_url": f"{SITE_URL}/api/unsubscribe?token={unsubscribe_token}"}


class DomainNotVerified(Exception):
    pass


class EmailChannel:
    """Sends through Resend. Another channel (like text messages) would offer the same send() method."""
    name = "email"

    def __init__(self):
        self.key = os.getenv("RESEND_API_KEY", "")

    def available(self) -> bool:
        return bool(self.key)

    FALLBACK_FROM = "Tremor <onboarding@resend.dev>"  # Resend's test sender (only reaches the account owner)

    def send(self, to: str, message: dict) -> str:
        try:
            return self._send(to, message, EMAIL_FROM)
        except DomainNotVerified:
            # Our domain isn't verified in Resend (yet): use the test sender so alerts to the owner still arrive
            print("    tremoralerts.com not verified in Resend yet; sending from the test address")
            return self._send(to, message, self.FALLBACK_FROM)

    def _send(self, to: str, message: dict, sender: str) -> str:
        resp = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"},
            json={
                "from": sender, "to": [to], "subject": message["subject"],
                "html": message["html"], "text": message["text"],
                # Lets Gmail/Apple Mail show their own one-click "Unsubscribe" button
                "headers": {"List-Unsubscribe": f"<{message['unsubscribe_url']}>",
                            "List-Unsubscribe-Post": "List-Unsubscribe=One-Click"},
            },
            timeout=30,
        )
        if resp.status_code == 403 and "not verified" in resp.text and sender != self.FALLBACK_FROM:
            raise DomainNotVerified(resp.text[:300])
        if resp.status_code >= 300:
            raise RuntimeError(f"Resend {resp.status_code}: {resp.text[:300]}")
        return resp.json().get("id", "")
