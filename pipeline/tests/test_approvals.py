from tremor.approvals_job import suggest
from tremor.sources.openfda import approved_medicines, core, first_word


def test_fda_abbreviations_and_legal_endings_are_ignored():
    assert core("KARYOPHARM THERAPS") == core("Karyopharm Therapeutics Inc.") == "KARYOPHARM"
    assert core("ELI LILLY AND CO") == core("ELI LILLY & Co") == "ELI LILLY"
    assert core("TAKEDA PHARMS USA") == core("TAKEDA PHARMACEUTICAL CO LTD") == "TAKEDA"
    assert core("GENMAB US, INC.") == core("GENMAB A/S") == "GENMAB"
    assert first_word("Nuvation Bio Inc.") == "NUVATION"


def test_only_the_same_name_is_confirmed_automatically():
    found = {r["fda_sponsor"]: r["status"] for r in suggest("Merck & Co., Inc.", {"MERCK": 68, "MERCK KGAA": 1, "MERCKX": 1})}
    assert found == {"MERCK": "confirmed", "MERCK KGAA": "suggested"}   # KGaA is a different company; a person decides
    assert suggest("Immunome Inc.", {"IMMUNOMEDICS INC": 1}) == []     # a similar name is not even suggested


def _app(num, brand, status="AP", kind="ORIG", day="20200115", sold="Prescription"):
    return {"application_number": num, "products": [{"brand_name": brand, "marketing_status": sold,
                                                     "active_ingredients": [{"name": "TESTINIB"}]}],
            "submissions": [{"submission_type": kind, "submission_status": status, "submission_status_date": day}]}


def test_approved_medicines_are_new_drugs_with_an_approved_original_application():
    meds = approved_medicines([
        _app("NDA000001", "TESTRA"),
        _app("ANDA000002", "GENERIC COPY"),                 # a generic copy of someone else's drug
        _app("NDA000003", "NOT YET", status="TA"),          # only tentatively approved
        _app("BLA000004", "OLDMAB", sold="Discontinued"),
    ])
    assert [(m["brand_name"], m["approved_on"], m["still_sold"]) for m in meds] == [
        ("Testra", "2020-01-15", True), ("Oldmab", "2020-01-15", False)]
