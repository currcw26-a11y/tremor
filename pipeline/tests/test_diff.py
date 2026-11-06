"""Tests for the change detector: feed in fake before/after trials, check what gets caught."""
import copy

from tremor.diff import compare, months_between, parse_date
from tremor.snapshot import changed_sections, content_hash

BEFORE = {
    "nct_id": "NCT00000001",
    "overall_status": "RECRUITING",
    "phases": ["PHASE3"],
    "enrollment": 300,
    "enrollment_type": "ESTIMATED",
    "primary_completion_date": "2027-06",
    "completion_date": "2028-01-15",
    "results_first_posted": None,
    "interventions": ["EXB-101", "Placebo"],
    "primary_outcomes": [{"measure": "Overall Survival", "description": "Time to death", "timeFrame": "3 years"}],
}


def after(**edits):
    new = copy.deepcopy(BEFORE)
    new.update(edits)
    return new


def types(changes):
    return [c["change_type"] for c in changes]


def test_no_change_means_no_changes():
    assert compare(BEFORE, copy.deepcopy(BEFORE)) == []


def test_main_goal_replaced_is_caught():
    new = after(primary_outcomes=[{"measure": "Progression-Free Survival", "timeFrame": "2 years"}])
    [c] = compare(BEFORE, new)
    assert c["change_type"] == "primary_outcome_changed"
    assert c["details"]["removed"] == ["overall survival"]


def test_main_goal_with_only_capitalization_change_is_ignored():
    new = after(primary_outcomes=[{"measure": "overall survival.", "description": "time to death", "timeFrame": "3 Years"}])
    assert compare(BEFORE, new) == []


def test_main_goal_new_time_frame_is_a_rewording():
    new = after(primary_outcomes=[{"measure": "Overall Survival", "description": "Time to death", "timeFrame": "4 years"}])
    assert types(compare(BEFORE, new)) == ["primary_outcome_reworded"]


def test_extra_main_goal_added():
    new = after(primary_outcomes=BEFORE["primary_outcomes"] + [{"measure": "Response Rate"}])
    assert types(compare(BEFORE, new)) == ["primary_outcome_added"]


def test_enrollment_cut_20_percent_is_big():
    [c] = compare(BEFORE, after(enrollment=240))
    assert c["change_type"] == "enrollment_cut"
    assert c["details"]["percent_cut"] == 20.0


def test_enrollment_cut_10_percent_is_small():
    assert types(compare(BEFORE, after(enrollment=270))) == ["enrollment_small_cut"]


def test_enrollment_cut_exactly_15_percent_counts_as_big():
    assert types(compare(BEFORE, after(enrollment=255))) == ["enrollment_cut"]


def test_enrollment_increase():
    assert types(compare(BEFORE, after(enrollment=400))) == ["enrollment_increased"]


def test_date_pushed_back_6_months():
    [c] = compare(BEFORE, after(primary_completion_date="2027-12"))
    assert c["change_type"] == "date_delayed"
    assert c["field"] == "primary_completion_date"
    assert c["details"]["months"] >= 5.9


def test_date_pushed_back_1_month_is_small():
    assert types(compare(BEFORE, after(primary_completion_date="2027-07"))) == ["date_small_change"]


def test_date_moved_earlier():
    assert types(compare(BEFORE, after(completion_date="2027-09-01"))) == ["date_moved_earlier"]


def test_trial_terminated_is_stopped():
    [c] = compare(BEFORE, after(overall_status="TERMINATED"))
    assert c["change_type"] == "trial_stopped"


def test_normal_status_progress_is_not_stopped():
    assert types(compare(BEFORE, after(overall_status="ACTIVE_NOT_RECRUITING"))) == ["status_changed"]


def test_results_posted():
    assert types(compare(BEFORE, after(results_first_posted="2026-11-01"))) == ["results_posted"]


def test_several_changes_at_once():
    new = after(enrollment=200, primary_completion_date="2028-06", overall_status="ACTIVE_NOT_RECRUITING")
    assert sorted(types(compare(BEFORE, new))) == ["date_delayed", "enrollment_cut", "status_changed"]


def test_only_contact_info_changed_is_paperwork():
    [c] = compare(BEFORE, copy.deepcopy(BEFORE), other_sections_changed=["contactsLocationsModule"])
    assert c["change_type"] == "paperwork"
    assert c["is_paperwork"] is True


def test_dates_without_day_are_understood():
    assert parse_date("2027-06") == parse_date("2027-06-01")
    assert months_between(parse_date("2027-01"), parse_date("2027-04")) == 3.0


def test_fingerprint_changes_only_when_record_changes():
    rec = {"protocolSection": {"statusModule": {"overallStatus": "RECRUITING"}}, "hasResults": False}
    same = copy.deepcopy(rec)
    edited = copy.deepcopy(rec)
    edited["protocolSection"]["statusModule"]["overallStatus"] = "TERMINATED"
    assert content_hash(rec) == content_hash(same)
    assert content_hash(rec) != content_hash(edited)
    assert changed_sections(rec, edited) == ["statusModule"]
