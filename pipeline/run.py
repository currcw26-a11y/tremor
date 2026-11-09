"""One full Tremor pipeline run. GitHub Actions runs this every 4 hours.

    python run.py

Each part is wrapped so one broken data source doesn't stop the others.
"""
import os
import sys
import traceback
from datetime import datetime, timezone

from tremor import db, explain_job, score_job, sec_job, trials_job


def first_run_of_day() -> bool:
    """True if no successful run has finished yet today (UTC). Daily jobs run only then."""
    today = datetime.now(timezone.utc).date().isoformat()
    return not db.select("pipeline_runs", "id", status="eq.success", finished_at=f"gte.{today}", limit="1")


def main() -> int:
    daily = first_run_of_day() or os.getenv("FORCE_DAILY") == "1"
    run_id = db.insert("pipeline_runs", [{"status": "running"}], returning="id")[0]["id"]
    stats, errors = {}, []
    jobs = [("trials", trials_job.run), ("sec", sec_job.run_sec), ("fda", sec_job.run_fda),
            ("scores", score_job.run),  # scores use everything above
            ("explanations", explain_job.run)]
    if daily:  # once a day: big downloads and the digest email
        jobs.append(("runway", sec_job.run_runway))
    for name, job in jobs:
        print(f"--- {name} ---")
        try:
            stats[name] = job()
            print(f"    {stats[name]}")
        except Exception:
            errors.append(f"{name}: {traceback.format_exc()}")
            print(errors[-1])
    db.update("pipeline_runs", {"finished_at": datetime.now(timezone.utc).isoformat(),
                                "status": "failed" if errors else "success",
                                "stats": stats, "error": "\n".join(errors) or None}, id=f"eq.{run_id}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
