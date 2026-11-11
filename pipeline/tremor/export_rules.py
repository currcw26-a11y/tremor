"""Copy the score rules from config/tremor.yaml into web/lib/score-rules.json for the website's
"How the score works" page. Run after changing a weight:

    python -m tremor.export_rules

A test (tests/test_export_rules.py) fails if the two files ever disagree.
"""
import json
from pathlib import Path

from . import config

OUT = Path(__file__).resolve().parents[2] / "web" / "lib" / "score-rules.json"


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
    print(f"wrote {OUT}")
