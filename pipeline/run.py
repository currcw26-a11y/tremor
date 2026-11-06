"""One full Tremor pipeline run. GitHub Actions runs this every 4 hours.

    python run.py

Each part is wrapped so one broken data source doesn't stop the others.
"""
import sys
import traceback
from datetime import datetime, timezone

from tremor import db, trials_job


def main() -> int:
    run_id = db.insert("pipeline_runs", [{"status": "running"}], returning="id")[0]["id"]
    stats, errors = {}, []
    for name, job in [("trials", trials_job.run)]:  # SEC + FDA jobs get added in Step 6
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
