from datetime import date, timedelta

from tremor import backtest as bt

TODAY = date(2026, 11, 10)


def test_stop_reasons_are_sorted_into_plain_buckets():
    assert bt.stop_reason("Phase 3 study was stopped due to futility of efficacy at interim analysis") == "safety_or_efficacy"
    assert bt.stop_reason("Change in clinical strategy.") == "business"
    assert bt.stop_reason("Strategic Business Decision") == "business"
    assert bt.stop_reason("Slow accrual") == "enrollment"
    assert bt.stop_reason(None) == "other"


def test_not_a_safety_problem_is_not_counted_as_one():
    assert bt.stop_reason("Sponsor decision to cancel trial, not related to safety concern.") == "business"
    assert bt.stop_reason("Early discontinuation based on strategic sponsor decision not driven by any safety concerns") == "business"
    assert bt.stop_reason("Discontinued based on financial constraints and is not related to the safety of study participants") == "business"
    assert bt.stop_reason("The Data Monitoring Committee recommended that the study be halted for futility") == "safety_or_efficacy"


def test_outcome_within_12_months():
    d = date(2024, 1, 1)
    assert bt.outcome_after(d, [date(2024, 6, 1)], [], TODAY) == ("bad", date(2024, 6, 1))
    assert bt.outcome_after(d, [date(2025, 6, 1)], [], TODAY)[0] == "fine"      # stop came too late to count
    assert bt.outcome_after(date(2026, 6, 1), [], [], TODAY)[0] == "unknown"   # less than 12 months ago
    assert bt.outcome_after(d, [date(2023, 6, 1)], [], TODAY)[0] == "fine"      # stop BEFORE the sign doesn't count


def prices(start, closes):
    return bt.Prices([{"day": (start + timedelta(days=i)).isoformat(), "close": c} for i, c in enumerate(closes)])


def test_move_is_day_before_to_day_after_the_announcement():
    p = prices(date(2024, 3, 1), [10, 10, 10, 5, 5.5, 5.5, 5.5])   # crash on Mar 4
    # 8-K filed Mar 6, press release came out Mar 4: still found (8-Ks can lag up to 4 days)
    assert p.move_on_filing(date(2024, 3, 6)) == (date(2024, 3, 4), -45.0)   # 10 (day before) -> 5.5 (day after)


def test_news_is_the_filing_the_stock_reacted_to_and_unrelated_jumps_are_ignored():
    closes = [10] * 40
    closes[5:] = [20] * 35      # big unrelated jump on day 5 (no filing about the drug then)
    closes[30:] = [12] * 10     # drop on day 30, the day of the drug announcement
    p = prices(date(2024, 1, 1), closes)
    day, move = bt.news_move([date(2024, 1, 20), date(2024, 1, 31)], p)
    assert day == date(2024, 1, 31) and move == -40.0
    assert bt.news_move([], p) == (None, None)            # no filing found -> unknown, never a guess
    assert bt.news_move([date(2024, 1, 31)], None) == (None, None)


def test_cases_and_summary():
    signals = {"EXMP": [date(2024, 1, 10), date(2025, 2, 1), date(2026, 8, 1)]}
    stops = {"EXMP": [date(2024, 3, 1)]}
    news = {("EXMP", date(2024, 3, 1)): (date(2024, 2, 20), -50.0)}
    cases = bt.build_cases("layoffs", signals, stops, {}, news, TODAY)
    assert [c["outcome"] for c in cases] == ["bad", "fine", "unknown"]
    assert (cases[0]["news_day"], cases[0]["move_pct"]) == ("2024-02-20", -50.0)
    s = bt.summarize("layoffs", cases, baseline=0.25)
    assert (s["cases"], s["bad"], s["fine"], s["confidence"]) == (2, 1, 1, "low")


def test_baseline_counts_random_months():
    share = bt.baseline_bad_share(["EXMP"], {"EXMP": [date(2024, 6, 15)]}, {"EXMP": date(2024, 1, 1)}, date(2025, 12, 31))
    assert 0 < share < 1


def test_baseline_only_counts_months_when_the_company_was_trading():
    stops = {"OLD": [date(2017, 6, 1)], "NEW": [date(2024, 6, 1)]}
    today = date(2025, 12, 31)
    # NEW started trading in 2024: its quiet 2016-2023 years must not dilute the comparison
    fair = bt.baseline_bad_share(["NEW"], stops, {"NEW": date(2024, 1, 1)}, today)
    diluted = bt.baseline_bad_share(["NEW"], stops, {"NEW": date(2016, 1, 1)}, today)
    assert fair > diluted
    assert bt.baseline_bad_share(["NEW"], stops, {}, today) is None    # no start known -> left out


def test_confidence_levels():
    assert [bt.confidence(n) for n in (9, 10, 29, 30)] == ["low", "medium", "medium", "high"]
