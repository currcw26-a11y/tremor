"""Calling Claude, with three safety nets:

1. A monthly budget cap (AI_MONTHLY_BUDGET_USD, default $15). Every call's tokens and
   estimated cost are logged in the ai_calls table. Once the month's total reaches the cap,
   non-essential calls stop and essential ones (alert text) switch to short mode.
2. A number check: Claude may only use numbers that appear in the facts we gave it.
   Any other number = the answer is thrown away (hard rule: Claude never invents statistics).
3. If there's no API key (e.g. on your laptop), AI features quietly switch off.
"""
import os
import re
from datetime import datetime, timezone

from . import db, settings  # noqa: F401  (settings loads .env.local)

MODEL = "claude-haiku-5-5"
# US dollars per 1 million tokens for claude-haiku-5-5 (checked Nov 6, 2026)
PRICE_PER_M = {"input": 0.10, "output": 0.50}
BUDGET_USD = float(os.getenv("AI_MONTHLY_BUDGET_USD", "15"))

_client = None
_spent_this_run = 0.0
_spent_before_run: float | None = None


def available() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY"))


def _get_client():
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment
    return _client


def cost(input_tokens: int, output_tokens: int) -> float:
    return (input_tokens * PRICE_PER_M["input"] + output_tokens * PRICE_PER_M["output"]) / 1_000_000


def spent_this_month() -> float:
    global _spent_before_run
    if _spent_before_run is None:
        start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        rows = db.select("ai_calls", "cost_usd", created_at=f"gte.{start.isoformat()}")
        _spent_before_run = sum(float(r["cost_usd"]) for r in rows)
    return _spent_before_run + _spent_this_run


def over_budget() -> bool:
    return spent_this_month() >= BUDGET_USD


def _log(purpose: str, usage, ok: bool, note: str | None = None) -> float:
    global _spent_this_run
    i = getattr(usage, "input_tokens", 0) or 0
    o = getattr(usage, "output_tokens", 0) or 0
    c = cost(i, o)
    _spent_this_run += c
    db.insert("ai_calls", [{"purpose": purpose, "model": MODEL, "input_tokens": i, "output_tokens": o,
                            "cost_usd": round(c, 6), "ok": ok, "note": note}])
    return c


def numbers_in(text: str) -> set[str]:
    """'cut 20% (from 300 to 240) in 2027' -> {'20', '300', '240', '2027'}"""
    return {n.replace(",", "").rstrip("0").rstrip(".") if "." in n else n.replace(",", "")
            for n in re.findall(r"\d[\d,]*(?:\.\d+)?", text)}


def invented_numbers(answer: str, facts: str) -> set[str]:
    """Numbers in Claude's answer that don't appear anywhere in the facts we gave it."""
    return numbers_in(answer) - numbers_in(facts)


def write(purpose: str, system: str, facts: str, essential: bool, max_tokens: int = 2000) -> str | None:
    """Ask Claude to write text from `facts`. Returns None if skipped or if the answer failed a check."""
    if not available():
        return None
    if over_budget() and not essential:
        return None
    import anthropic
    try:
        resp = _get_client().messages.create(
            model=MODEL,
            max_tokens=max_tokens,
            system=system,
            output_config={"effort": "low"},  # short, simple writing: no need to think hard
            messages=[{"role": "user", "content": facts}],
        )
    except anthropic.APIStatusError as err:
        print(f"    Claude error {err.status_code}: {err.message}")
        return None
    except anthropic.APIConnectionError:
        print("    Could not reach Claude")
        return None

    text = "".join(b.text for b in resp.content if b.type == "text").strip()
    if resp.stop_reason != "end_turn" or not text:
        _log(purpose, resp.usage, ok=False, note=f"stop_reason={resp.stop_reason}")
        return None
    bad = invented_numbers(text, facts)
    if bad:
        _log(purpose, resp.usage, ok=False, note=f"number check failed: {sorted(bad)}")
        return None
    _log(purpose, resp.usage, ok=True)
    return text
