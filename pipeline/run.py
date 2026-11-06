"""One full Tremor pipeline run. GitHub Actions runs this every 4 hours.

    python run.py

Each part is wrapped so one broken data source doesn't stop the others.
"""
import sys
import traceback
from datetime import datetime, timezone

from tremor import db, score_job, sec_job, trials_job


def main() -> int:
    run_id = db.insert("pipeline_runs", [{"status": "running"}], returning="id")[0]["id"]
    stats, errors = {}, []
    jobs = [("trials", trials_job.run), ("sec", sec_job.run_sec), ("fda", sec_job.run_fda),
            ("scores", score_job.run)]  # scores last: they use everything above
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
