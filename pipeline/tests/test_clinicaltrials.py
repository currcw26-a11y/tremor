"""Checks that we pull the right fields out of a trial record (no internet needed)."""
from tremor.sources.clinicaltrials import summarize

FAKE_STUDY = {
    "protocolSection": {
        "identificationModule": {"nctId": "NCT00000001", "briefTitle": "Drug X in Lung Cancer"},
        "statusModule": {
            "overallStatus": "RECRUITING",
            "primaryCompletionDateStruct": {"date": "2027-06", "type": "ESTIMATED"},
            "lastUpdatePostDateStruct": {"date": "2026-10-01", "type": "ACTUAL"},
        },
        "sponsorCollaboratorsModule": {"leadSponsor": {"name": "Example Bio, Inc.", "class": "INDUSTRY"}},
        "designModule": {"phases": ["PHASE3"], "enrollmentInfo": {"count": 300, "type": "ESTIMATED"}},
        "conditionsModule": {"conditions": ["Non-small Cell Lung Cancer"]},
        "armsInterventionsModule": {"interventions": [{"type": "DRUG", "name": "EXB-101"}]},
        "outcomesModule": {"primaryOutcomes": [{"measure": "Overall Survival", "timeFrame": "3 years"}]},
    }
}


def test_summarize_picks_out_key_fields():
    t = summarize(FAKE_STUDY)
    assert t["nct_id"] == "NCT00000001"
    assert t["sponsor_name"] == "Example Bio, Inc."
    assert t["enrollment"] == 300
    assert t["phases"] == ["PHASE3"]
    assert t["interventions"] == ["EXB-101"]
    assert t["primary_completion_date"] == "2027-06"
    assert t["results_first_posted"] is None  # no results yet


def test_summarize_handles_missing_sections():
    bare = {"protocolSection": {"identificationModule": {"nctId": "NCT00000002"}}}
    t = summarize(bare)
    assert t["nct_id"] == "NCT00000002"
    assert t["enrollment"] is None
    assert t["primary_outcomes"] == []
