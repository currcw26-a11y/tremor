from datetime import date, datetime, timezone

from tremor.prices_job import new_york_today


def test_new_york_date_lags_utc_in_the_evening():
    # 01:05 UTC on Nov 13 is 8:05 pm on Nov 12 in New York: Nov 12 isn't over yet there
    assert new_york_today(datetime(2026, 11, 13, 1, 5, tzinfo=timezone.utc)) == date(2026, 11, 12)
    assert new_york_today(datetime(2026, 11, 13, 16, 0, tzinfo=timezone.utc)) == date(2026, 11, 13)
