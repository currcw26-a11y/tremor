from datetime import date

from tremor.sources.fda_dates import decided_dates, extract_dates

TODAY = date(2026, 11, 10)


def test_finds_exact_upcoming_dates_with_the_companys_words():
    text = ("Highlights. The FDA accepted our application and assigned a PDUFA target action date of "
            "April 28, 2027. We ended the quarter with cash of $300 million.")
    [d] = extract_dates(text, TODAY)
    assert d["date"] == "2027-04-28" and d["precision"] == "day"
    assert "PDUFA target action date of April 28, 2027" in d["sentence"]
    assert "300 million" not in d["sentence"]          # only the sentence about the date


def test_month_only_dates_and_several_dates_in_one_line():
    ds = extract_dates("PDUFA action date November 30, 2026 and PDUFA target action date December 30, 2026.", TODAY)
    assert [d["date"] for d in ds] == ["2026-11-30", "2026-12-30"]
    [m] = extract_dates("We expect a PDUFA date in March 2027.", TODAY)
    assert (m["date"], m["precision"]) == ("2027-03-01", "month")


def test_ignores_past_dates_past_approvals_and_unrelated_sentences():
    assert extract_dates("The PDUFA date was June 1, 2026.", TODAY) == []                       # already passed
    assert extract_dates("The drug was approved on December 1, 2026 under PDUFA.", TODAY) == []  # not a target date
    assert extract_dates("Our lease ends on March 1, 2027.", TODAY) == []                       # nothing about the FDA
    assert extract_dates("PDUFA target action date of February 30, 2027.", TODAY) == []         # not a real date


def test_quote_is_trimmed_at_word_edges():
    junk = "EX-99.1 2 abc-ex99_1.htm Exhibit 99.1 " + "word " * 60
    [d] = extract_dates(junk + "PDUFA target action date of April 28, 2027.", TODAY)
    assert d["sentence"].startswith("…") and "abc-ex99" not in d["sentence"]


def test_real_mistakes_are_skipped():
    # A date of something else (an FDA letter) that comes BEFORE the words
    letter = ("The Company expects to receive a Day-74 Letter from the FDA on or about November 20, 2026, which will "
              "include the Prescription Drug User Fee Act goal date.")
    assert extract_dates(letter, TODAY) == []
    # Already approved, ahead of the date
    early = "The FDA approved the drug, four months ahead of the January 4, 2027, target action date."
    assert extract_dates(early, TODAY) == []
    early2 = "The FDA approved the drug ahead of its PDUFA target action date of January 4, 2027."
    assert extract_dates(early2, TODAY) == []
    # A month that's about something else, too far from the words
    other = ("Expected to receive decision on BLA acceptance by the end of November 2026 and a Prescription Drug "
             "User Fee Act date allocation and decision in 2027.")
    assert extract_dates(other, TODAY) == []


def test_quote_drops_filing_junk():
    [d] = extract_dates("EX-99.1 2 tm2628936d1_ex99-1.htm EXHIBIT 99.1 Exhibit 99.1 Zenas Reports Results. "
                        "The BLA was accepted with a PDUFA target action date of May 27, 2027.", TODAY)
    assert "htm" not in d["sentence"] and "EX-99" not in d["sentence"]
    assert d["sentence"].endswith("May 27, 2027.") or "May 27, 2027" in d["sentence"]


def test_a_date_the_filing_says_was_already_acted_on_is_dropped():
    text = ("The FDA approved the sNDA, four months ahead of the January 4, 2027, target action date. "
            "In June we submitted the sNDA, with a target action date of January 4, 2027. "
            "Another drug has a PDUFA date of March 22, 2027.")
    assert [d["date"] for d in extract_dates(text, TODAY)] == ["2027-03-22"]


def test_a_newer_filing_can_cancel_a_date_in_an_older_one():
    newer = "The FDA approved IBTROZI, four months ahead of the January 4, 2027, target action date."
    older = "The FDA accepted the sNDA, with a target action date of January 4, 2027."
    assert extract_dates(older, TODAY, also_decided=decided_dates(newer)) == []
    assert len(extract_dates(older, TODAY)) == 1


def test_headlines_with_the_word_approved_do_not_cancel_a_date():
    text = ("PDUFA Target Action Date Set for February 28, 2027 QTORIN Rapamycin Could Become the First "
            "FDA-Approved Therapy. Our focus: obtain FDA approval. Launch if Approved February 28, 2027.")
    assert decided_dates(text) == set()
    assert [d["date"] for d in extract_dates(text, TODAY)] == ["2027-02-28"]
