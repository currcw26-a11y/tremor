"""Fetch cancer drug trials from ClinicalTrials.gov (API v2, no key needed).

Which trials we pull:
  1. Active Phase 2 / Phase 3 cancer trials run by companies ("INDUSTRY" sponsors).
  2. Recently finished ones (last 3 years) so we can spot "results overdue".
  3. Any specific trials we're already tracking (by ID), so if one gets stopped
     and drops out of searches 1-2, we still see it.

Run this file directly to see a quick summary:
    python -m tremor.sources.clinicaltrials
"""
from collections import Counter
from datetime import date

from ..http import get_json

BASE = "https://clinicaltrials.gov/api/v2"

CANCER_WORDS = (
    "cancer OR neoplasm OR tumor OR carcinoma OR lymphoma OR leukemia OR myeloma OR sarcoma "
    "OR melanoma OR glioma OR glioblastoma OR malignancy OR oncology OR metastatic"
)
ACTIVE_STATUSES = "RECRUITING,NOT_YET_RECRUITING,ACTIVE_NOT_RECRUITING,ENROLLING_BY_INVITATION"
PHASE_AND_SPONSOR = "AREA[Phase](PHASE2 OR PHASE3) AND AREA[LeadSponsorClass]INDUSTRY"
FINISHED_LOOKBACK_YEARS = 3
PAGE_SIZE = 1000  # the API's maximum


def data_timestamp() -> str:
    """When ClinicalTrials.gov last refreshed its data. If unchanged since last run, nothing new."""
    return get_json(f"{BASE}/version")["dataTimestamp"]


def _paged(params: dict):
    """Yield every study from a search, following pageToken from page to page."""
    params = {**params, "pageSize": PAGE_SIZE, "format": "json"}
    while True:
        page = get_json(f"{BASE}/studies", params)
        yield from page.get("studies", [])
        token = page.get("nextPageToken")
        if not token:
            return
        params["pageToken"] = token


def fetch_cancer_trials():
    """Yield raw study records from searches 1 and 2 (no duplicates)."""
    seen = set()
    since = date.today().replace(year=date.today().year - FINISHED_LOOKBACK_YEARS).isoformat()
    searches = [
        {"query.cond": CANCER_WORDS, "filter.overallStatus": ACTIVE_STATUSES,
         "filter.advanced": PHASE_AND_SPONSOR},
        {"query.cond": CANCER_WORDS, "filter.overallStatus": "COMPLETED",
         "filter.advanced": f"{PHASE_AND_SPONSOR} AND AREA[PrimaryCompletionDate]RANGE[{since},MAX]"},
    ]
    for params in searches:
        for study in _paged(params):
            nct = nct_id(study)
            if nct not in seen:
                seen.add(nct)
                yield study


def fetch_by_ids(nct_ids: list[str]):
    """Yield raw study records for specific trial IDs (search 3)."""
    for i in range(0, len(nct_ids), 200):  # 200 IDs per request keeps the URL a sane length
        yield from _paged({"filter.ids": ",".join(nct_ids[i:i + 200])})


# ---------- Turning the big raw record into the handful of fields we care about ----------

def nct_id(study: dict) -> str:
    return study["protocolSection"]["identificationModule"]["nctId"]


def _date(module: dict, key: str):
    return (module.get(key) or {}).get("date")


def summarize(study: dict) -> dict:
    """Pick out the fields we store in the `trials` table."""
    p = study["protocolSection"]
    ident = p.get("identificationModule", {})
    status = p.get("statusModule", {})
    design = p.get("designModule", {})
    enroll = design.get("enrollmentInfo") or {}
    return {
        "nct_id": ident["nctId"],
        "title": ident.get("briefTitle"),
        "sponsor_name": p.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {}).get("name"),
        "phases": design.get("phases") or [],
        "overall_status": status.get("overallStatus"),
        "conditions": p.get("conditionsModule", {}).get("conditions") or [],
        "interventions": [i.get("name") for i in p.get("armsInterventionsModule", {}).get("interventions") or []],
        "primary_outcomes": p.get("outcomesModule", {}).get("primaryOutcomes") or [],
        "enrollment": enroll.get("count"),
        "enrollment_type": enroll.get("type"),
        "start_date": _date(status, "startDateStruct"),
        "primary_completion_date": _date(status, "primaryCompletionDateStruct"),
        "completion_date": _date(status, "completionDateStruct"),
        "results_first_posted": _date(status, "resultsFirstPostDateStruct"),
        "last_update_posted": _date(status, "lastUpdatePostDateStruct"),
    }


if __name__ == "__main__":
    print(f"ClinicalTrials.gov data last refreshed: {data_timestamp()}")
    trials = [summarize(s) for s in fetch_cancer_trials()]
    print(f"\nFound {len(trials):,} company-run Phase 2/3 cancer trials.\n")
    print("Status breakdown:")
    for status, n in Counter(t["overall_status"] for t in trials).most_common():
        print(f"  {status:<26}{n:>6,}")
    print("\nTop 15 sponsors by number of trials:")
    for sponsor, n in Counter(t["sponsor_name"] for t in trials).most_common(15):
        print(f"  {n:>4}  {sponsor}")
    print(f"\nUnique sponsors: {len({t['sponsor_name'] for t in trials}):,}")
    ex = trials[0]
    print(f"\nExample: {ex['nct_id']} — {ex['title']}\n  sponsor: {ex['sponsor_name']}, "
          f"patients: {ex['enrollment']}, status: {ex['overall_status']}")
