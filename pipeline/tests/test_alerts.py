"""Tests for alert rules: what counts as a tremor, who gets it, and staying under email limits."""
import re

from tremor import alerts, emails

T1 = {"nct_id": "NCT1", "ticker": "EXMP", "sponsor_name": "Example Bio", "title": "Drug X in Lung Cancer",
      "score": 85, "score_label": "tremor",
      "score_breakdown": [
          {"type": "trial_stopped", "label": "The trial was stopped early", "occurred": "2026-11-09", "points": 85},
          {"type": "insider_selling_cluster", "label": "2 insiders sold shares within a month", "occurred": "2026-11-01", "points": 9},
      ]}
T2 = {**T1, "nct_id": "NCT2", "title": "Drug X in Breast Cancer", "score": 19, "score_label": "calm",
      "score_breakdown": [
          {"type": "insider_selling_cluster", "label": "2 insiders sold shares within a month", "occurred": "2026-11-01", "points": 9},
          {"type": "date_delayed", "label": "Pushed back a key date by about 6 months", "occurred": "2026-11-08", "points": 10},
      ]}


def test_classification():
    assert alerts.classify("trial_stopped") == ("critical", True, True)
    assert alerts.classify("key_exec_departure") == ("critical", True, True)
    assert alerts.classify("date_delayed") == ("head_start", False, False)
    assert alerts.classify("enrollment_cut", "Cut patients by 20% (final count when sign-up ended)")[0] == "head_start"
    assert alerts.classify("status_changed") is None


def test_company_wide_signal_becomes_one_alert_not_one_per_trial():
    found = alerts.detect([T1, T2], [])
    insider = [a for a in found.values() if a["signal_type"] == "insider_selling_cluster"]
    assert len(insider) == 1 and insider[0]["nct_id"] is None and insider[0]["ticker"] == "EXMP"
    assert len(found) == 3  # stopped + insider (once) + date delay


def test_stopped_trial_key_is_stable_across_days():
    assert alerts.dedupe_key("trial_stopped", "NCT1", "EXMP", "2026-11-09") == alerts.dedupe_key("trial_stopped", "NCT1", "EXMP", "2026-11-10")


def test_big_jump_and_turning_red():
    hist = [{"id": 7, "nct_id": "NCT2", "old_score": 20, "new_score": 38, "old_label": "calm", "new_label": "calm"},
            {"id": 8, "nct_id": "NCT2", "old_score": 60, "new_score": 72, "old_label": "shaky", "new_label": "tremor"},
            {"id": 9, "nct_id": "NCT2", "old_score": 20, "new_score": 30, "old_label": "calm", "new_label": "calm"}]
    found = alerts.detect([T2], hist)
    assert found["jump:7"]["is_huge"] is False and found["jump:7"]["instant"] is True
    assert found["jump:8"]["is_huge"] is True          # turned red, even though it only rose 12 points
    assert "jump:9" not in found                        # 10 points is not a big jump


PROFILES = [
    {"user_id": "watcher", "instant_alerts": True, "daily_digest": True},
    {"user_id": "stranger", "instant_alerts": True, "daily_digest": True},
    {"user_id": "digest_only", "instant_alerts": False, "daily_digest": True},
    {"user_id": "gone", "unsubscribed": True},
]
WATCH = {"watcher": {"NCT2"}, "digest_only": {"NCT2"}, "gone": {"NCT2"}}


def who(alert):
    return dict(alerts.interested_users(alert, PROFILES, WATCH, {}, {"NCT1": "EXMP", "NCT2": "EXMP"}))


def test_huge_alerts_go_to_everyone_except_unsubscribed():
    huge = {"nct_id": "NCT1", "ticker": "EXMP", "instant": True, "is_huge": True}
    assert who(huge) == {"watcher": "instant", "stranger": "instant", "digest_only": "digest"}


def test_normal_alerts_go_to_watchers_only():
    small = {"nct_id": "NCT2", "ticker": "EXMP", "instant": False, "is_huge": False}
    assert who(small) == {"watcher": "digest", "digest_only": "digest"}


def test_company_alert_reaches_people_watching_one_of_its_trials():
    company = {"nct_id": None, "ticker": "EXMP", "instant": False, "is_huge": False}
    assert set(who(company)) == {"watcher", "digest_only"}


def test_email_limits_reserve_room_for_instant_alerts():
    assert alerts.email_allowance(0, 0) == {"instant": 100, "digest": 75}
    assert alerts.email_allowance(90, 500) == {"instant": 10, "digest": 0}      # digests stop first
    assert alerts.email_allowance(10, 2995) == {"instant": 5, "digest": 0}      # monthly limit
    assert alerts.email_allowance(120, 3100) == {"instant": 0, "digest": 0}     # never negative


def test_email_has_required_parts_and_never_says_buy_or_sell():
    a = {"nct_id": "NCT1", "ticker": "EXMP", "kind": "critical", "is_huge": True, "headline": "The trial was stopped early in “Drug X”",
         "old_score": 30, "new_score": 85, "explanation": "An early stop can signal trouble, but it can also be routine.",
         "details": {"source": {"url": "https://www.sec.gov/x"}}}
    company = {"name": "Example Bio", "runway_months": 8.2, "monthly_burn_usd": 10_000_000,
               "finances_as_of": "2026-09-30", "burn_period_months": 9}
    msg = emails.render([a], "instant", {"NCT1": {"primary_completion_date": "2027-03"}}, {"EXMP": company},
                        {"EXMP": 1}, "tok-123")
    for must in ["Not investment advice", "unsubscribe?token=tok-123", "30 → 85", "About 8 months", "Mar 2027",
                 "clinicaltrials.gov/study/NCT1", "https://www.sec.gov/x"]:
        assert must in msg["text"], must
    assert "Not investment advice" in msg["html"] and "tok-123" in msg["html"]
    assert not re.search(r"\b(buy|sell)\b", msg["text"].replace("never tells anyone to buy or sell", ""), re.I)
    assert msg["subject"] == "🔴 Example Bio (EXMP): the trial was stopped early"   # short, no trial title


def test_digest_bundles_several_alerts_in_one_email():
    a = {"nct_id": "NCT1", "ticker": "EXMP", "kind": "head_start", "is_huge": False, "headline": "x", "new_score": 10}
    b = {**a, "nct_id": "NCT2", "ticker": "OTHR"}
    msg = emails.render([a, b], "digest", {}, {}, {}, "t")
    assert msg["subject"] == "Tremor daily digest: 2 updates (EXMP, OTHR)"
    assert msg["text"].count("What happened:") == 2


def test_score_jump_explained_by_another_alert_is_dropped():
    exec_leaves = {"nct_id": None, "ticker": "GOVX", "kind": "critical", "is_huge": True}
    jump_same_company = {"nct_id": "NCT9", "ticker": "GOVX", "kind": "big_jump", "is_huge": False}
    jump_turned_red = {"nct_id": "NCT8", "ticker": "GOVX", "kind": "big_jump", "is_huge": True}
    jump_other = {"nct_id": "NCT7", "ticker": "OTHR", "kind": "big_jump", "is_huge": False}
    kept = alerts.drop_redundant_jumps([exec_leaves, jump_same_company, jump_turned_red, jump_other])
    assert kept == [exec_leaves, jump_turned_red, jump_other]   # turning red is always worth its own line


def test_past_results_date_is_described_as_passed():
    from datetime import date
    a = {"nct_id": "NCT1", "ticker": "EXMP", "kind": "critical", "headline": "x", "new_score": 40}
    past = emails.alert_block(a, {"primary_completion_date": "2026-09-16"}, None, 1, today=date(2026, 11, 9))[1]
    future = emails.alert_block(a, {"primary_completion_date": "2027-03"}, None, 1, today=date(2026, 11, 9))[1]
    assert "were due around Sep 16, 2026. That date has passed" in past
    assert "are expected around Mar 2027" in future


def test_subject_for_company_names_with_suffixes():
    a = {"ticker": "CLLS", "kind": "critical", "headline": "Changed the trial's main goal in “Long title”", "details": {}}
    assert emails.short_subject(a, {"CLLS": {"name": "Cellectis S.A."}}) == "Cellectis (CLLS): changed the trial's main goal"


def test_falls_back_to_test_sender_when_domain_not_verified(monkeypatch):
    from types import SimpleNamespace
    senders = []

    def fake_post(url, headers, json, timeout):
        senders.append(json["from"])
        if "tremoralerts.com" in json["from"]:
            return SimpleNamespace(status_code=403, text='{"message":"The tremoralerts.com domain is not verified."}')
        return SimpleNamespace(status_code=200, text="", json=lambda: {"id": "abc"})

    monkeypatch.setattr(emails.requests, "post", fake_post)
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    msg = {"subject": "s", "html": "h", "text": "t", "unsubscribe_url": "u"}
    assert emails.EmailChannel().send("me@example.com", msg) == "abc"
    assert senders == ["Tremor <alerts@tremoralerts.com>", "Tremor <onboarding@resend.dev>"]
