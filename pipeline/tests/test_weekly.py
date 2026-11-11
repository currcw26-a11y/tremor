from datetime import date

from tremor import ai, weekly

F = {"start": date(2026, 11, 2), "end": date(2026, 11, 8), "trials_tracked": 1571, "important_changes": 2,
     "routine_changes": 40,
     "changes": [{"ticker": "CLLS", "company": "Cellectis", "trial": "UCART22 in Leukemia",
                  "what": "cut the planned number of patients from 52 to 45"}],
     "alerts": ["Ocugen: A key executive is leaving"],
     "score_rises": [{"ticker": "CLLS", "company": "Cellectis", "trial": "UCART22 in Leukemia", "old": 10, "new": 35}],
     "coming": ["FDA decision expected for Summit Therapeutics (SMMT) by Nov 14"]}


def test_week_is_the_last_full_monday_to_sunday():
    assert weekly.week_bounds(date(2026, 11, 9)) == (date(2026, 11, 2), date(2026, 11, 8))    # a Monday
    assert weekly.week_bounds(date(2026, 11, 11)) == (date(2026, 11, 2), date(2026, 11, 8))   # mid-week, same issue
    assert weekly.title_for(date(2026, 11, 2), date(2026, 11, 8)) == "Tremor Weekly: Nov 2 to Nov 8, 2026"


def test_facts_hold_every_number_the_writer_may_use():
    text = weekly.facts_text(F)
    for needed in ("52 to 45", "10 to 35", "1571", "Nov 14", "40"):
        assert needed in text
    ok = "## The week in brief\nCellectis cut patients from 52 to 45, and its score rose from 10 to 35."
    assert not ai.invented_numbers(ok, text)
    assert ai.invented_numbers("## The week in brief\nShares could fall 60%.", text) == {"60"}


def test_drafts_with_advice_or_without_sections_are_rejected():
    assert weekly.acceptable("## The week in brief\nA quiet week.")
    assert not weekly.acceptable("## The week in brief\nNow may be a good time to buy.")
    assert not weekly.acceptable("## Coming up\nInvestors might want to sell before the decision.")
    assert not weekly.acceptable("No sections at all.")
    assert not weekly.acceptable(None)


def test_fallback_is_plain_and_honest():
    body = weekly.fallback_body(F)
    assert body.startswith("## The week in brief")
    assert "2 important changes" in body and "40 routine edits" in body and "harmless paperwork" in body
    assert "- Cellectis (CLLS): cut the planned number of patients from 52 to 45" in body
    assert "not a prediction" in body
    assert weekly.acceptable(body)
    quiet = weekly.fallback_body({**F, "important_changes": 1, "routine_changes": 1, "changes": [], "alerts": [], "coming": []})
    assert "1 important change to" in quiet and "1 routine edit," in quiet and "## What changed" not in quiet
