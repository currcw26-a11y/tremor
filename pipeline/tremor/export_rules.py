"""Copy the score rules from config/tremor.yaml into web/lib/score-rules.json for the website's
"How the score works" page, and the welcome email into web/lib/welcome-email.json. Run after changing a weight
or the welcome email's words:

    python -m tremor.export_rules

A test (tests/test_export_rules.py) fails if the two files ever disagree.
"""
import json
from pathlib import Path

from . import config, emails

OUT = Path(__file__).resolve().parents[2] / "web" / "lib" / "score-rules.json"
WELCOME_OUT = OUT.with_name("welcome-email.json")   # the welcome email the website sends at sign-up


def welcome(cfg: dict | None = None) -> dict:
    cfg = cfg or config.load()
    return {**emails.welcome_template(), "daily_limit": cfg["email"]["daily_limit"],
            "monthly_limit": cfg["email"]["monthly_limit"]}


def rules(cfg: dict | None = None) -> dict:
    cfg = cfg or config.load()
    s, d = cfg["score"], cfg["detection"]
    return {
        "labels": {k: v["min"] for k, v in s["labels"].items()},
        "half_life_days": s["half_life_days"], "max_age_days": s["max_age_days"], "stopped_floor": s["stopped_floor"],
        "big_company_trial_count": s["big_company_trial_count"], "big_company_factor": s["big_company_factor"],
        "enrollment_final_count_factor": s["enrollment_final_count_factor"],
        "weights": dict(s["weights"]),
        "detection": dict(d),
        "repeat_exec_window_days": cfg["signals"].get("repeat_exec_window_days", 182),
        "big_jump_points": cfg["alerts"]["big_jump_points"],
    }


if __name__ == "__main__":
    OUT.write_text(json.dumps(rules(), indent=2) + "\n")
    WELCOME_OUT.write_text(json.dumps(welcome(), indent=2) + "\n")
    print(f"wrote {OUT} and {WELCOME_OUT.name}")
