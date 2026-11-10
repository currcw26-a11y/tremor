"""The upside/downside breakdown ("When this happened before") for one trial.

Code computes every number here from the backtest and SEC data; the sentences are fixed
templates, not AI, so nothing can be invented. The result is saved on the trial (trials.outlook)
so the website and the emails show exactly the same thing.
"""
from datetime import date

RECORDING_SINCE = "Nov 6, 2026"     # when Tremor started saving its own copies of trial records
MIN_MOVES = 10                      # fewer measured stock moves than this -> "not enough to say"

# Score signals that have past cases in the backtest (backtest_summary.signal_type)
BACKTESTED = {"layoffs": "layoffs", "key_exec_departure": "key_exec_departure", "trial_stopped": "trial_stopped"}

WHAT = {
    "layoffs": "smaller cancer-drug companies announced layoffs",
    "key_exec_departure": "a key executive, like the head of research, left a smaller cancer-drug company",
}

# Signals Tremor can only learn about from its own recordings (no past history available for free)
NO_HISTORY = {
    "primary_outcome_changed": "the main goal of a trial was changed",
    "enrollment_cut": "a trial cut the number of patients",
    "date_delayed": "a trial pushed back its dates",
    "results_overdue": "a trial's results were overdue",
    "insider_selling_cluster": "several insiders sold shares",
    "fda_advisory_meeting": "the FDA scheduled an advisory meeting",
    "job_postings_drop": "clinical job postings dropped",
    "rival_trial_failed": "a rival drug's trial failed",
}

RANDOM_DAY_NOTE = "Starting from a random day instead, a trial was stopped within the next year about 1 in {n} times."


def one_in(share: float | None) -> int | None:
    """0.08 -> 12 ('about 1 in 12')."""
    return round(1 / share) if share and share > 0 else None


def confidence(n: int) -> str:
    return "low" if n < 10 else "medium" if n < 30 else "high"


def move_words(pct: float) -> str:
    """-12.2 -> 'fell about 12%', 48 -> 'rose about 48%', 0.4 -> 'barely moved'."""
    if abs(pct) < 3:
        return "barely moved"
    if pct <= -45:
        return "lost about half its value" if pct > -60 else f"fell about {round(-pct)}%"
    return f"{'rose' if pct > 0 else 'fell'} about {round(abs(pct))}%"


def compare_words(share: float, baseline: float | None) -> str:
    if not baseline:
        return ""
    ratio = share / baseline
    if ratio >= 1.8:
        return "about twice as often as a random day, or more"
    if ratio >= 1.25:
        return "a bit more often than a random day"
    if ratio > 0.8:
        return "about as often as a random day"
    return "less often than a random day"


def past_cases(signal_type: str, summary: dict | None) -> dict:
    """Facts + plain sentences for one kind of signal."""
    if signal_type not in BACKTESTED:
        what = NO_HISTORY.get(signal_type, "this happened")
        return {"type": signal_type, "cases": 0, "has_history": False,
                "sentences": [f"We don't have enough past cases yet to say how often bad news followed when {what}. "
                              f"Tremor started recording trial records on {RECORDING_SINCE} and builds this history "
                              "as it goes."]
                + (["Many edits like this turn out to be harmless paperwork."]
                   if signal_type in ("primary_outcome_changed", "enrollment_cut", "date_delayed") else [])}
    s = summary or {}
    n, bad, fine = s.get("cases") or 0, s.get("bad") or 0, s.get("fine") or 0
    out = {"type": signal_type, "cases": n, "bad": bad, "fine": fine, "has_history": n > 0,
           "confidence": confidence(n), "baseline_one_in": one_in(s.get("baseline_bad_share")),
           "bad_move": s.get("typical_bad_move"), "bad_moves": s.get("bad_moves") or 0,
           "fine_move": s.get("typical_fine_move"), "fine_moves": s.get("fine_moves") or 0,
           "sentences": []}
    if not n:
        out["sentences"] = ["We don't have past cases for this yet."]
        return out
    sent = out["sentences"]
    if signal_type == "trial_stopped":
        reasons = (s.get("extra") or {}).get("reasons") or {}
        biz = reasons.get("business", 0)
        sent.append(f"Since 2016, smaller cancer-drug companies stopped {n} trials early. "
                    + (f"{biz} out of {n} said it was a business decision, like saving money or focusing on other drugs, "
                       f"and {reasons.get('safety_or_efficacy', 0)} out of {n} said the drug wasn't working well "
                       "enough or had safety problems." if reasons else ""))
        if out["bad_moves"] >= MIN_MOVES:
            sent.append(f"In the {out['bad_moves']} cases where we could find the company's announcement, the stock "
                        f"typically {move_words(out['bad_move'])} from the day before to the day after.")
        else:
            sent.append("We couldn't find a clear announcement day in enough cases to say how the stock usually moved.")
        safety = (s.get("extra") or {}).get("safety") or {}
        if safety.get("moves", 0) >= MIN_MOVES:
            sent.append(f"When the reason was that the drug wasn't working or wasn't safe, the stock typically "
                        f"{move_words(safety['typical_move'])} ({safety['moves']} cases).")
        elif safety.get("worst_move") is not None:
            sent.append(f"When the drug itself wasn't working, the drop can be big (one fell {round(-safety['worst_move'])}%), "
                        f"but we only have {safety.get('moves', 0)} such cases with a clear announcement day, too few to say "
                        "what's typical.")
        return out

    sent.append(f"Since 2016, {WHAT[signal_type]} {n} times. In {bad} out of {n}, one of that company's trials "
                f"was stopped within the next year. In the other {fine}, none was.")
    if out["baseline_one_in"]:
        cmp = compare_words(bad / n, s.get("baseline_bad_share"))
        sent.append(RANDOM_DAY_NOTE.format(n=out["baseline_one_in"]) + (f" So this sign came before bad news {cmp}."
                                                                         if cmp else ""))
    moves = []
    if out["bad_moves"] >= MIN_MOVES:
        moves.append(f"when a trial was stopped, the stock typically {move_words(out['bad_move'])} on the news "
                     f"({out['bad_moves']} cases)")
    if out["fine_moves"] >= MIN_MOVES:
        moves.append(f"when results came out instead, it typically {move_words(out['fine_move'])} "
                     f"({out['fine_moves']} cases)")
    if moves:
        sent.append(("; ".join(moves)).capitalize() + ".")
    else:
        sent.append(f"We could only measure the stock's move on the news in {out['bad_moves'] + out['fine_moves']} "
                    "of these cases, which isn't enough to say what's typical.")
    return out


def stakes(trial_count: int) -> dict:
    """How much rides on this trial, from how many late-stage cancer trials we track for the company."""
    if trial_count <= 2:
        level, text = "high", (f"High. This is one of only {trial_count} late-stage cancer trials we track for this "
                               "company, so a lot rides on it." if trial_count == 2 else
                               "High. This is the only late-stage cancer trial we track for this company, so a lot rides on it.")
    elif trial_count < 15:
        level, text = "medium", (f"Medium. It's one of {trial_count} late-stage cancer trials we track for this company.")
    else:
        level, text = "low", (f"Lower. It's one of {trial_count} late-stage cancer trials we track for this big company, "
                              "so one trial usually matters less to its stock.")
    return {"level": level, "trial_count": trial_count, "text": text}


def next_event(trial: dict, today: date) -> dict | None:
    due = trial.get("primary_completion_date")
    if not due or trial.get("results_first_posted"):
        return None
    due = str(due)[:10]
    return {"date": due, "passed": due < today.isoformat()[:len(due)]}


def build(trial: dict, signal_types: list[str], summaries: dict[str, dict], trial_count: int, today: date) -> dict:
    """Everything the breakdown shows for one trial. Only signals the trial actually has right now."""
    seen, signals = set(), []
    for t in signal_types:
        if t not in seen:
            seen.add(t)
            signals.append(past_cases(t, summaries.get(BACKTESTED.get(t, ""))))
    signals.sort(key=lambda s: -s["cases"])   # the ones with real history first
    big = trial_count >= 15
    notes = ["Past cases come from public records since 2016 for companies still listed today. Companies that went "
             "out of business aren't included, which may make past outcomes look a little better than they were."]
    if big and any(s["has_history"] and s["type"] != "trial_stopped" for s in signals):
        notes.append("These past cases are from smaller companies. At a big company, one signal like this usually "
                     "matters less.")
    return {"signals": signals, "stakes": stakes(trial_count), "next_event": next_event(trial, today),
            "notes": notes}
