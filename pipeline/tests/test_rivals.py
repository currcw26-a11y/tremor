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
