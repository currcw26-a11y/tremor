from datetime import date, timedelta

from tremor.scoring import rival_signals
from tremor.sources.chembl import clean
from tremor.sources.targets import cancer_phrase, cancer_types, from_symbols, targets_in

TODAY = date(2026, 11, 11)


def test_targets_are_read_from_trial_words():
    assert targets_in("A Study of AZD2936 Anti-TIGIT/Anti-PD-1 Bispecific Antibody") == {"TIGIT", "PD-1"}
    assert targets_in("KRAS G12C inhibitor in NSCLC") == {"KRAS G12C"}
    assert targets_in("anti-PD-L1 antibody") == {"PD-L1"}          # PD-L1 is not PD-1
    assert targets_in("HER2-positive breast cancer, BCMA x CD3") >= {"HER2", "BCMA"}
    assert targets_in("A study in all participants who return") == set()   # ordinary words don't count
    assert from_symbols(["PDCD1", "ERBB2", "NOTAGENE"]) == {"PD-1", "HER2"}


def test_cancer_types():
    assert cancer_types(["Non-small Cell Lung Cancer"]) == {"lung"}
    assert cancer_types(["Acute Myeloid Leukemia"]) == {"leukemia"}
    assert cancer_types(["Gastric Cancer", "Gastroesophageal Junction Adenocarcinoma"]) == {"stomach and esophagus"}
    assert cancer_types(["Advanced Solid Tumors"]) == set()          # too broad to call anything a rival
    assert cancer_phrase("lung") == "lung cancer" and cancer_phrase("leukemia") == "leukemia"


def test_drug_names_are_cleaned_before_lookup():
    assert clean("Subcutaneous Tislelizumab") == "Tislelizumab"
    assert clean("Acalabrutinib combination") == "Acalabrutinib"


def fail(nct="NCT9", targets=("PD-1",), types=("lung",), drugs=("CHEMBL_RIVAL",), days_ago=30):
    return {"nct_id": nct, "sponsor": "Rival Bio", "title": "x", "why_stopped": "futility",
            "stopped_on": (TODAY - timedelta(days=days_ago)).isoformat(), "targets": list(targets),
            "cancer_types": list(types), "drug_ids": list(drugs)}


ME = {"nct_id": "NCT1", "targets": ["PD-1", "TIGIT"], "cancer_types": ["lung"], "drug_ids": ["CHEMBL_MINE"]}


def test_rival_needs_same_target_same_cancer_and_a_different_drug():
    [s] = rival_signals(ME, [fail()], TODAY)
    assert s.type == "rival_trial_failed" and s.base_points == 10
    assert "targets PD-1" in s.label and "lung cancer trial" in s.label
    assert rival_signals(ME, [fail(types=("breast",))], TODAY) == []          # different cancer
    assert rival_signals(ME, [fail(targets=("HER2",))], TODAY) == []          # different target
    assert rival_signals(ME, [fail(drugs=("CHEMBL_MINE",))], TODAY) == []     # same drug: not a rival
    assert rival_signals(ME, [fail(nct="NCT1")], TODAY) == []                 # the trial itself
    assert rival_signals(ME, [fail(days_ago=400)], TODAY) == []               # too old
    assert rival_signals({**ME, "cancer_types": []}, [fail()], TODAY) == []   # unknown cancer type


def test_only_the_newest_rival_failure_counts():
    sigs = rival_signals(ME, [fail("NCT8", days_ago=200), fail("NCT9", days_ago=20)], TODAY)
    assert len(sigs) == 1 and sigs[0].source["rival_nct"] == "NCT9"


def test_only_the_new_drugs_target_counts_when_a_trial_fails():
    from tremor.rivals_job import failed_drug_targets
    known = {
        "sotorasib": {"chembl_id": "C1", "approved": True, "symbols": ["KRAS"]},
        "pembrolizumab": {"chembl_id": "C2", "approved": True, "symbols": ["PDCD1"]},
        "newmab": {"chembl_id": "C3", "approved": False, "symbols": ["TIGIT"]},
    }
    look = lambda name: known.get(name.lower())
    # A new TIGIT drug given with pembrolizumab: only TIGIT failed
    assert failed_drug_targets("TIGIT and PD-1", ["Newmab", "Pembrolizumab"], look) == ({"TIGIT"}, {"C3"})
    # A drug ChEMBL doesn't know yet: use the record's words, minus the usual partner-drug targets
    t, ids = failed_drug_targets("MK-9999 is a TIGIT antibody given with a PD-1 inhibitor", ["MK-9999", "Pembrolizumab"], look)
    assert t == {"TIGIT"} and ids == {"mk9999"}
    # Only approved drugs: nothing new failed, so no rival target
    assert failed_drug_targets("PD-L1", ["Pembrolizumab"], look)[0] == set()


def test_a_stop_is_dated_by_when_the_trial_ended_not_a_later_record_edit():
    from tremor.rivals_job import stop_day
    assert stop_day({"primary_completion_date": "2024-01", "last_update_posted": "2026-01-13"}) == "2024-01-15"
    assert stop_day({"primary_completion_date": "2027-06-30", "last_update_posted": "2026-03-01"}) == "2026-03-01"  # planned end
    assert stop_day({"primary_completion_date": None, "last_update_posted": "2026-03-01"}) == "2026-03-01"
