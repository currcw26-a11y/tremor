"""Tests for the worry score. Uses the real config/tremor.yaml weights."""
from datetime import date, timedelta

from tremor import config, scoring
from tremor.scoring import Signal, company_signals, insider_clusters, score, trial_signals

TODAY = date(2026, 11, 6)
W = config.load()["score"]["weights"]
HALF = config.load()["score"]["half_life_days"]


def change(kind, days_ago=0, **details):
    return {"id": 1, "change_type": kind, "is_paperwork": False, "details": details,
            "detected_at": (TODAY - timedelta(days=days_ago)).isoformat()}


TRIAL = {"overall_status": "RECRUITING", "primary_completion_date": "2028-01", "results_first_posted": None}


def test_no_signals_means_calm_zero():
    assert score([], "RECRUITING", TODAY)[:2] == (0, "calm")


def test_main_goal_change_today_is_full_points():
    value, label, _ = score(trial_signals(TRIAL, [change("primary_outcome_changed")], TODAY), "RECRUITING", TODAY)
    assert value == W["primary_outcome_changed"] == 25
    assert label == "calm"


def test_points_halve_after_one_half_life():
    sigs = trial_signals(TRIAL, [change("primary_outcome_changed", days_ago=HALF)], TODAY)
    assert score(sigs, "RECRUITING", TODAY)[0] == round(25 / 2)


def test_signals_add_up_to_shaky_and_tremor():
    shaky = [change("primary_outcome_changed"), change("enrollment_cut", percent_cut=20)]
    assert score(trial_signals(TRIAL, shaky, TODAY), "RECRUITING", TODAY)[:2] == (40, "shaky")
    tremor = shaky + [change("date_delayed", months=6)]
    extra = [Signal("key_exec_departure", "x", TODAY, W["key_exec_departure"]),
             Signal("fda_advisory_meeting", "x", TODAY, W["fda_advisory_meeting"])]
    assert score(trial_signals(TRIAL, tremor, TODAY) + extra, "RECRUITING", TODAY)[:2] == (75, "tremor")


def test_score_never_goes_above_100():
    sigs = [Signal("x", "x", TODAY, 60), Signal("y", "y", TODAY, 60)]
    assert score(sigs, "RECRUITING", TODAY)[0] == 100


def test_stopped_trial_jumps_straight_to_red():
    value, label, _ = score([], "TERMINATED", TODAY)
    assert value == config.load()["score"]["stopped_floor"] and label == "tremor"


def test_two_dates_delayed_in_one_edit_count_once():
    sigs = trial_signals(TRIAL, [change("date_delayed", months=18), change("date_delayed", months=33)], TODAY)
    assert len(sigs) == 1


def test_final_enrollment_count_gets_fewer_points():
    c = change("enrollment_cut", percent_cut=20, old_type="ESTIMATED", new_type="ACTUAL")
    [sig] = trial_signals(TRIAL, [c], TODAY)
    assert sig.base_points == W["enrollment_cut"] * 0.5


def test_paperwork_and_minor_changes_score_nothing():
    cs = [change("status_changed"), change("date_small_change", months=1), {**change("paperwork"), "is_paperwork": True}]
    assert trial_signals(TRIAL, cs, TODAY) == []


def test_results_overdue():
    old = {**TRIAL, "primary_completion_date": "2025-06", "overall_status": "COMPLETED"}
    [sig] = trial_signals(old, [], TODAY)
    assert sig.type == "results_overdue" and sig.fades is False
    posted = {**old, "results_first_posted": "2026-01-10"}
    assert trial_signals(posted, [], TODAY) == []


def sale(name, day):
    return {"insider_name": name, "transaction_date": f"2026-10-{day:02d}", "accession_number": f"A{name}{day}"}


def test_insider_cluster_needs_two_different_people_within_30_days():
    assert insider_clusters([sale("Ann", 1), sale("Ann", 5)]) == []            # same person twice
    assert len(insider_clusters([sale("Ann", 1), sale("Bob", 20)])) == 1       # two people, 19 days
    far = [sale("Ann", 1), {**sale("Bob", 1), "transaction_date": "2026-12-15"}]
    assert insider_clusters(far) == []                                          # too far apart


def test_big_companies_get_smaller_company_wide_points():
    filing = {"filed_at": "2026-11-01", "items": ["5.02"], "key_exec_departure": True, "url": "u"}
    small = company_signals([filing], [], trial_count=3)
    big = company_signals([filing], [], trial_count=200)
    assert small[0].base_points == W["key_exec_departure"]
    assert big[0].base_points == W["key_exec_departure"] * config.load()["score"]["big_company_factor"]


def test_layoff_8k_is_a_signal():
    [sig] = company_signals([{"filed_at": "2026-11-01", "items": ["2.05", "9.01"], "url": "u"}], [], 3)
    assert sig.type == "layoffs"


def test_fda_meeting_counts_only_for_matching_drug_and_until_30_days_after():
    m = {"matched_drugs": ["Lifileucel", "Iovance Biotherapeutics"], "publication_date": "2026-10-01",
         "meeting_date": "2026-11-01", "url": "u"}
    assert len(scoring.fda_signals({"lifileucel"}, [m], TODAY)) == 1
    assert scoring.fda_signals({"other drug"}, [m], TODAY) == []              # company-name match only
    assert scoring.fda_signals({"lifileucel"}, [m], date(2026, 12, 15)) == []  # meeting long over
