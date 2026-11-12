from datetime import date

from tremor.crl import reasons, summarize


def letter(text, status="Approved", year="2024"):
    return {"text": text, "approval_status": status, "letter_year": year}


def test_letters_are_sorted_by_the_fdas_own_sections():
    routine = "\nSAFETY UPDATE\nWhen you resubmit, include all new safety information.\nPRESCRIBING INFORMATION\nWe reserve comment.\n"
    assert reasons(letter(routine)) == set()                       # routine instructions in nearly every letter
    assert reasons(letter(routine + "\nFACILITY INSPECTIONS\nDuring a recent inspection...\n")) == {"making"}
    assert reasons(letter("\nCLINICAL\nThe safety database is insufficient.\n")) == {"evidence"}
    assert reasons(letter("Your trial failed to demonstrate a benefit. Objectionable conditions at the plant.")) == {"making", "evidence"}


def test_summary_counts():
    s = summarize([letter("\nPRODUCT QUALITY\nx\n"), letter("\nCLINICAL\nx\n", status="Unapproved", year="2025"),
                   letter("nothing", status="Unapproved", year="2019")], today=date(2026, 11, 12))
    assert (s["total"], s["making"], s["evidence"], s["neither"]) == (3, 1, 1, 1)
    assert (s["approved_later"], s["not_yet_approved"], s["not_yet_recent"]) == (1, 2, 1)
    assert (s["first_year"], s["last_year"]) == (2019, 2025)
