"""One full Tremor pipeline run. GitHub Actions runs this every 4 hours.

    python run.py

Each part is wrapped so one broken data source doesn't stop the others.
"""
import os
import sys
import traceback
from datetime import datetime, timezone

from tremor import alert_job, db, explain_job, score_job, sec_job, trials_job


def first_run_of_day() -> bool:
    """True if no successful run has finished yet today (UTC). Daily jobs run only then."""
    today = datetime.now(timezone.utc).date().isoformat()
    return not db.select("pipeline_runs", "id", status="eq.success", finished_at=f"gte.{today}", limit="1")


def digest_due() -> bool:
    """True if today's digest hasn't gone out yet."""
    today = datetime.now(timezone.utc).date().isoformat()
    try:
        return not db.select("email_log", "id", kind="eq.digest", sent_at=f"gte.{today}", limit="1")
    except RuntimeError:
        return False


def main() -> int:
    daily = first_run_of_day() or os.getenv("FORCE_DAILY") == "1"
    run_id = db.insert("pipeline_runs", [{"status": "running"}], returning="id")[0]["id"]
    stats, errors = {}, []
    jobs = [("trials", trials_job.run), ("sec", sec_job.run_sec), ("fda", sec_job.run_fda),
            ("scores", score_job.run),  # scores use everything above
            ("explanations", explain_job.run)]
    if daily:  # once a day: big downloads
        jobs.append(("runway", sec_job.run_runway))
    # Alerts go last: they use the newest scores and explanations
    jobs.append(("alerts", lambda: alert_job.run(daily=digest_due())))
    if os.getenv("SEND_TEST_EMAIL") == "1":
        jobs.append(("test_email", lambda: alert_job.send_test(os.getenv("TEST_EMAIL_TO") or None)))
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
