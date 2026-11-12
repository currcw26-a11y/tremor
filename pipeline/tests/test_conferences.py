from datetime import date

from tremor.upcoming_job import conferences

CSV = """name,starts,ends,city,about,url,confirmed,checked_from
Past Meeting,2026-06-01,2026-06-05,Chicago,All cancers,https://a,yes,x
Big Meeting,2026-12-12,2026-12-15,New Orleans,Blood cancers,https://b,yes,x
Not Checked,2027-01-10,2027-01-12,Somewhere,All,https://c,no,x
Far Away,2028-06-01,2028-06-05,Chicago,All,https://d,yes,x
Typo Meeting,2026-13-01,2026-13-02,X,All,https://e,yes,x
"""


def test_only_confirmed_upcoming_conferences(tmp_path):
    p = tmp_path / "c.csv"
    p.write_text(CSV)
    rows = conferences(date(2026, 11, 12), p)
    assert [r["title"] for r in rows] == ["Big Meeting"]
    r = rows[0]
    assert (r["kind"], r["ticker"], r["event_date"], r["end_date"], r["source_form"]) == (
        "conference", None, "2026-12-12", "2026-12-15", "New Orleans")
