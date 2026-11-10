from datetime import date

from tremor.sources.fda_dates import extract_dates

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
