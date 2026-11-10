import re
from datetime import date

from tremor import emails, outlook

TODAY = date(2026, 11, 10)
SUMMARIES = {
    "key_exec_departure": {"cases": 177, "bad": 20, "fine": 157, "baseline_bad_share": 0.08,
                           "typical_bad_move": -12.2, "bad_moves": 6, "typical_fine_move": 12.4, "fine_moves": 5},
    "layoffs": {"cases": 90, "bad": 11, "fine": 79, "baseline_bad_share": 0.08,
                "typical_bad_move": -30.0, "bad_moves": 12, "typical_fine_move": 4.0, "fine_moves": 15},
    "trial_stopped": {"cases": 215, "bad": 215, "fine": 0, "typical_bad_move": 1.6, "bad_moves": 34,
                      "extra": {"reasons": {"business": 70, "safety_or_efficacy": 26, "other": 90, "enrollment": 29},
                                "safety": {"moves": 4, "typical_move": -19.0, "worst_move": -76.1}}},
}


def text(o):
    return " ".join(" ".join(s["sentences"]) for s in o["signals"]) + " " + o["stakes"]["text"] + " ".join(o["notes"])


def test_counts_are_written_as_x_out_of_n_and_compared_with_random_days():
    s = outlook.past_cases("key_exec_departure", SUMMARIES["key_exec_departure"])
    words = " ".join(s["sentences"])
    assert "20 out of 177" in words and "1 in 13" in words   # 1 / 0.08 = 12.5, rounded up like the website
    assert "a bit more often than a random day" in words
    assert s["confidence"] == "high"


def test_stock_moves_only_shown_with_enough_measured_cases():
    few = " ".join(outlook.past_cases("key_exec_departure", SUMMARIES["key_exec_departure"])["sentences"])
    assert "12%" not in few and "isn't enough to say" in few          # only 6 + 5 measured
    many = " ".join(outlook.past_cases("layoffs", SUMMARIES["layoffs"])["sentences"])
    assert "fell about 30%" in many and "(12 cases)" in many and "rose about 4%" in many


def test_signals_without_history_say_so_and_mention_harmless_paperwork():
    s = outlook.past_cases("primary_outcome_changed", None)
    words = " ".join(s["sentences"])
    assert not s["has_history"] and "Nov 6, 2026" in words and "harmless paperwork" in words


def test_stopped_trial_explains_reasons_and_does_not_overclaim():
    words = " ".join(outlook.past_cases("trial_stopped", SUMMARIES["trial_stopped"])["sentences"])
    assert "70 out of 215" in words and "26 out of 215" in words
    assert "barely moved" in words and "76%" in words and "too few to say" in words


def test_whole_breakdown_follows_the_hard_rules():
    trial = {"primary_completion_date": "2027-03", "results_first_posted": None}
    types = ["primary_outcome_changed", "key_exec_departure", "layoffs", "trial_stopped", "key_exec_departure"]
    o = outlook.build(trial, types, SUMMARIES, trial_count=1, today=TODAY)
    assert [s["type"] for s in o["signals"]][0] == "trial_stopped"         # most past cases first
    assert len(o["signals"]) == 4                                            # duplicates merged
    assert o["next_event"] == {"date": "2027-03", "passed": False}
    t = text(o).lower()
    assert not re.search(r"\b(buy|sell|selling|hold|median|average)\b", t)
    assert "only late-stage cancer trial" in t
    assert "went out of business" in t                                       # survivor-bias warning


def test_big_companies_get_a_caution():
    o = outlook.build({}, ["layoffs"], SUMMARIES, trial_count=40, today=TODAY)
    assert o["stakes"]["level"] == "low" and any("smaller companies" in n for n in o["notes"])


def test_email_shows_past_cases_for_the_alerts_own_signal():
    o = outlook.build({}, ["layoffs", "key_exec_departure"], SUMMARIES, trial_count=2, today=TODAY)
    a = {"kind": "critical", "headline": "A key executive left", "signal_type": "key_exec_departure",
         "ticker": "EXMP", "nct_id": "NCT00000001"}
    html, plain = emails.alert_block(a, {"outlook": o}, {"name": "Example Bio"}, 2, today=TODAY)
    assert "When this happened before: Since 2016, a key executive" in plain
    assert "How sure are we: High. Based on 177 past cases." in plain
    assert "one of only 2 late-stage cancer trials" in plain
    assert not re.search(r"\b(buy|sell)\b", plain.lower())
