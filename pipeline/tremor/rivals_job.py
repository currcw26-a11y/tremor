"""Daily: what each tracked trial's drugs target, and which rival trials recently failed.

1. For every drug name in our tracked trials, look up its mechanism in ChEMBL (once; re-checked monthly
   if it wasn't found). Saved in drug_mechanisms.
2. Each tracked trial gets a profile: its targets (from ChEMBL, plus target names written in its own
   record), its drugs, and its kind of cancer. Saved in trial_profiles.
3. Industry cancer trials (any company, public or private) stopped in the last year BECAUSE the drug
   didn't work well enough or wasn't safe are "rival failures". Saved in rival_failures.
Scoring (scoring.rival_signals) then matches them: same target + same kind of cancer + a different drug.

    python -m tremor.rivals_job
"""
from datetime import date, datetime, timedelta, timezone

from . import backtest, db
from .sources import chembl
from .sources import clinicaltrials as ct
from .sources.federal_register import useful_names
from .sources.targets import cancer_types, from_symbols, targets_in

RECHECK_DAYS = 30        # drugs ChEMBL didn't know are looked up again after this long
FAILURE_WINDOW_DAYS = 365


def _text(study_or_record: dict) -> tuple[str, list[str]]:
    """(all the descriptive text of a trial, its drug names)."""
    p = study_or_record.get("protocolSection", {})
    ident, desc = p.get("identificationModule", {}), p.get("descriptionModule", {})
    ivs = (p.get("armsInterventionsModule") or {}).get("interventions") or []
    parts = [ident.get("briefTitle", ""), ident.get("officialTitle", ""), desc.get("briefSummary", "")]
    parts += [f"{i.get('name', '')} {i.get('description', '')} {' '.join(i.get('otherNames') or [])}" for i in ivs]
    return " \n".join(parts), [i.get("name", "") for i in ivs]


class Mechanisms:
    """Drug name -> ChEMBL result, remembered in the database so each name is looked up once."""

    def __init__(self):
        self.known = {r["name_norm"]: r for r in db.select("drug_mechanisms", "*")}
        self.new: dict[str, dict] = {}

    def get(self, name: str) -> dict:
        key = chembl.norm(chembl.clean(name))
        row = self.new.get(key) or self.known.get(key)
        fresh = row and (row.get("chembl_id") or str(row.get("checked_at", "")) >= (date.today() - timedelta(days=RECHECK_DAYS)).isoformat())
        if fresh:
            return row
        try:
            r = chembl.lookup(name)
        except Exception as err:
            print(f"    ChEMBL {name}: {err}", flush=True)
            return row or {"targets": [], "chembl_id": None}
        row = {"name_norm": key, "name": name[:200], "chembl_id": r and r["chembl_id"], "pref_name": r and r["pref_name"],
               "targets": sorted(from_symbols(r["symbols"])) if r else [], "mechanism": r and (r["mechanism"] or None),
               "checked_at": datetime.now(timezone.utc).isoformat()}
        self.new[key] = row
        return row

    def save(self):
        if self.new:
            db.upsert("drug_mechanisms", list(self.new.values()), on_conflict="name_norm")


def profile(nct_id: str, text: str, drug_names: list[str], conditions: list[str], title: str, mech: Mechanisms) -> dict:
    sources, drug_ids = {}, set()
    for name in useful_names(drug_names):
        row = mech.get(name)
        drug_ids.add(row.get("chembl_id") or chembl.norm(chembl.clean(name)))
        for t in row.get("targets") or []:
            sources[t] = "chembl"
    for t in targets_in(text):
        sources.setdefault(t, "record")
    return {"nct_id": nct_id, "targets": sorted(sources), "target_source": sources, "drug_ids": sorted(drug_ids),
            "cancer_types": sorted(cancer_types(conditions, title)), "updated_at": datetime.now(timezone.utc).isoformat()}


def recent_failures(mech: Mechanisms, today: date) -> list[dict]:
    since = (today - timedelta(days=FAILURE_WINDOW_DAYS)).isoformat()
    params = {"query.cond": ct.CANCER_WORDS, "filter.overallStatus": "TERMINATED,SUSPENDED",
              "filter.advanced": f"{ct.PHASE_AND_SPONSOR} AND AREA[LastUpdatePostDate]RANGE[{since},MAX]"}
    out = []
    for s in ct._paged(params):
        sm = ct.summarize(s)
        why = s["protocolSection"]["statusModule"].get("whyStopped")
        if backtest.stop_reason(why) != "safety_or_efficacy" or not ct.is_cancer_trial(sm):
            continue
        text, names = _text(s)
        prof = profile(sm["nct_id"], text, names, sm["conditions"], sm["title"], mech)
        if not prof["targets"] or not prof["cancer_types"]:
            continue   # can't match a rival without knowing both
        out.append({"nct_id": sm["nct_id"], "sponsor": sm["sponsor_name"], "title": (sm["title"] or "")[:300],
                    "why_stopped": (why or "")[:400], "stopped_on": str(sm["last_update_posted"])[:10],
                    "targets": prof["targets"], "cancer_types": prof["cancer_types"], "drug_ids": prof["drug_ids"],
                    "updated_at": prof["updated_at"]})
    return out


def run(today: date | None = None) -> dict:
    today = today or date.today()
    try:
        mech = Mechanisms()
    except RuntimeError as err:
        return {"skipped": f"drug_mechanisms table missing (run migration 012): {str(err)[:80]}"}
    trials = db.select("trials", "nct_id,title,conditions,interventions,latest_snapshot_id", tracked="eq.true")
    snaps = {}
    ids = [str(t["latest_snapshot_id"]) for t in trials if t.get("latest_snapshot_id")]
    for i in range(0, len(ids), 100):
        for r in db.select("trial_snapshots", "nct_id,data", id=f"in.({','.join(ids[i:i + 100])})"):
            snaps[r["nct_id"]] = r["data"]

    profiles = []
    for n, t in enumerate(trials, 1):
        text, names = _text(snaps.get(t["nct_id"]) or {})
        names = names or (t.get("interventions") or [])
        profiles.append(profile(t["nct_id"], text or t["title"], names, t.get("conditions") or [], t["title"], mech))
        if n % 200 == 0:
            print(f"    profiled {n}/{len(trials)} trials", flush=True)
            mech.save()   # keep progress if the run is cut short
    db.upsert("trial_profiles", profiles, on_conflict="nct_id")

    failures = recent_failures(mech, today)
    mech.save()
    db.delete("rival_failures", stopped_on="lt.2100-01-01")   # small table: rebuilt each day
    if failures:
        db.upsert("rival_failures", failures, on_conflict="nct_id")
    return {"profiles": len(profiles), "with_targets": sum(bool(p["targets"]) for p in profiles),
            "from_chembl": sum("chembl" in (p["target_source"] or {}).values() for p in profiles),
            "rival_failures": len(failures), "new_lookups": len(mech.new)}


if __name__ == "__main__":
    print(run())
