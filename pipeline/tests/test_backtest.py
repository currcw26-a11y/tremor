from datetime import date, timedelta

from tremor import backtest as bt

TODAY = date(2026, 11, 10)


def test_stop_reasons_are_sorted_into_plain_buckets():
    assert bt.stop_reason("Phase 3 study was stopped due to futility of efficacy at interim analysis") == "safety_or_efficacy"
    assert bt.stop_reason("Change in clinical strategy.") == "business"
    assert bt.stop_reason("Strategic Business Decision") == "business"
    assert bt.stop_reason("Slow accrual") == "enrollment"
    assert bt.stop_reason(None) == "other"


def test_outcome_within_12_months():
    d = date(2024, 1, 1)
    assert bt.outcome_after(d, [date(2024, 6, 1)], [], TODAY) == ("bad", date(2024, 6, 1))
    assert bt.outcome_after(d, [date(2025, 6, 1)], [], TODAY)[0] == "fine"      # stop came too late to count
    assert bt.outcome_after(date(2026, 6, 1), [], [], TODAY)[0] == "unknown"   # less than 12 months ago
    assert bt.outcome_after(d, [date(2023, 6, 1)], [], TODAY)[0] == "fine"      # stop BEFORE the sign doesn't count


def prices(start, closes):
    return bt.Prices([{"day": (start + timedelta(days=i)).isoformat(), "close": c} for i, c in enumerate(closes)])


def test_news_day_is_the_biggest_move_and_move_is_day_before_to_day_after():
    p = prices(date(2024, 3, 1), [10, 10, 10, 5, 5.5, 5.5, 5.5])   # crash on day 3 (Mar 4)
    day, move = p.biggest_move_near(date(2024, 3, 2))
    assert day == date(2024, 3, 4)
    assert move == -45.0   # 10 (day before) -> 5.5 (day after)


def test_cases_and_summary():
    signals = {"EXMP": [date(2024, 1, 10), date(2025, 2, 1), date(2026, 8, 1)]}
    stops = {"EXMP": [date(2024, 3, 1)]}
    cases = bt.build_cases("layoffs", signals, stops, {}, {}, TODAY)
    assert [c["outcome"] for c in cases] == ["bad", "fine", "unknown"]
    s = bt.summarize("layoffs", cases, baseline=0.25)
    assert (s["cases"], s["bad"], s["fine"], s["confidence"]) == (2, 1, 1, "low")


def test_baseline_counts_random_months():
    share = bt.baseline_bad_share(["EXMP"], {"EXMP": [date(2024, 6, 15)]}, date(2024, 1, 1), date(2025, 12, 31))
    assert 0 < share < 1


def test_confidence_levels():
    assert [bt.confidence(n) for n in (9, 10, 29, 30)] == ["low", "medium", "medium", "high"]
