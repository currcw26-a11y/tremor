import re
from datetime import date

from tremor import alerts, emails

TODAY = date(2026, 11, 10)


def ev(kind="fda_decision", day="2026-12-01", precision="day", **kw):
    return {"kind": kind, "ticker": "EXMP", "nct_id": kw.get("nct_id"), "event_date": day, "date_precision": precision,
            "title": kw.get("title", "A Study of EXB-101 in Lung Cancer"), "quote": kw.get("quote"),
            "source_url": "https://www.sec.gov/x", "dedupe_key": f"{kind}:EXMP:{day}"}


def test_reminders_come_about_30_and_7_days_before():
    assert alerts.reminder_stage(ev(day="2027-01-10"), TODAY) is None          # 61 days away: too early
    assert alerts.reminder_stage(ev(day="2026-12-10"), TODAY) == "30d"
    assert alerts.reminder_stage(ev(day="2026-11-17"), TODAY) == "7d"
    assert alerts.reminder_stage(ev(day="2026-11-10"), TODAY) == "7d"          # today still counts
    assert alerts.reminder_stage(ev(day="2026-11-09"), TODAY) is None          # already passed
    assert alerts.reminder_stage(ev(day="2026-11-01", precision="month"), TODAY) == "month"
    assert alerts.reminder_stage(ev(day="2026-12-01", precision="month"), TODAY) is None


def test_each_stage_has_its_own_key_so_nobody_gets_the_same_reminder_twice():
    a30 = alerts.coming_up([ev(day="2026-12-10")], {"EXMP": "Example Bio"}, TODAY)[0]
    a7 = alerts.coming_up([ev(day="2026-12-10")], {"EXMP": "Example Bio"}, date(2026, 12, 4))[0]
    assert a30["dedupe_key"] != a7["dedupe_key"]
    again = alerts.coming_up([ev(day="2026-12-10")], {"EXMP": "Example Bio"}, date(2026, 11, 20))[0]
    assert again["dedupe_key"] == a30["dedupe_key"]            # same stage, same key: not sent again


def test_reminders_only_reach_watchers_and_go_in_the_digest():
    [a] = alerts.coming_up([ev(day="2026-11-15")], {"EXMP": "Example Bio"}, TODAY)
    assert not a["is_huge"] and not a["instant"]
    profiles = [{"user_id": "u1"}, {"user_id": "u2"}, {"user_id": "u3"}]
    got = alerts.interested_users(a, profiles, {"u2": {"NCT1"}}, {"u1": {"EXMP"}}, {"NCT1": "EXMP"})
    assert got == [("u1", "digest"), ("u2", "digest")]          # company watcher + trial watcher; not u3


def test_wording_is_plain_and_never_advice():
    a = alerts.coming_up([ev(day="2026-11-15"), ev("results_due", "2026-11-01", "month", nct_id="NCT1")],
                         {"EXMP": "Example Bio"}, TODAY)
    words = " ".join(x["headline"] + " " + x["explanation"] for x in a)
    assert "FDA decision for Example Bio expected by Nov 15, 2026 (in 5 days)" in words
    assert "expected this month, by the company's own estimate" in words
    assert not re.search(r"\b(buy|sell|hold)\b", words.lower())


def test_a_reminder_does_not_hide_a_real_score_jump():
    reminder = alerts.coming_up([ev("results_due", "2026-11-15", nct_id="NCT1")], {}, TODAY)[0]
    jump = {"kind": "big_jump", "nct_id": "NCT1", "ticker": "EXMP", "is_huge": False}
    assert jump in alerts.drop_redundant_jumps([reminder, jump])


def test_reminder_email_has_the_companys_words_and_links():
    [a] = alerts.coming_up([ev(day="2026-11-15", quote="PDUFA target action date of November 15, 2026.")],
                           {"EXMP": "Example Bio"}, TODAY)
    html, text = emails.alert_block(a, None, {"name": "Example Bio"}, 1, today=TODAY)
    assert "Coming up: FDA decision for Example Bio" in text
    assert "In the company's words: “PDUFA target action date" in text
    assert "/upcoming" in text and "https://www.sec.gov/x" in text
    assert "📅" in html


def test_long_trial_names_are_cut_at_a_whole_word():
    long = "Study to Evaluate Adverse Events, and Change in Disease Activity, When Intravenously (IV) Infused With Livmoniplimab in Adults"
    [a] = alerts.coming_up([ev("results_due", "2026-11-15", nct_id="NCT1", title=long)], {}, TODAY)
    assert "Infused…”" in a["headline"] and "in ”" not in a["headline"]
