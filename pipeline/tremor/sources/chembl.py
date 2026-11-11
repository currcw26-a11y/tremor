"""Drug mechanisms ("what the drug targets in the body") from ChEMBL, a free public database.

We only accept an EXACT name match (the drug's main name or one of its listed synonyms), so a drug is
never confused with a similar-sounding one. Very new company codes often aren't in ChEMBL yet; those
come back as None and Tremor says "mechanism unknown" rather than guessing.
"""
import re

from ..http import get_json

BASE = "https://www.ebi.ac.uk/chembl/api/data"
# Words that describe how or with what a drug is given, not which drug it is
EXTRA = re.compile(r"\b(combination|combo|therapy|treatment|monotherapy|mono|subcutaneous|sc|iv|intravenous|oral|"
                   r"injection|infusion|tablets?|capsules?|fdc|liposomal|nanoliposomal|pegylated|formulation|"
                   r"regimen|arm|cohort|part|dose|high|low|plus|and|alone|single agent|maintenance)\b", re.I)


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def clean(name: str) -> str:
    """'Subcutaneous Tislelizumab' -> 'Tislelizumab'; 'Acalabrutinib combination' -> 'Acalabrutinib'."""
    return " ".join(EXTRA.sub(" ", name or "").split())


def target_symbols(target_id: str) -> set[str]:
    """Gene symbols for a ChEMBL target, e.g. CHEMBL3307223 -> {'PDCD1'}."""
    data = get_json(f"{BASE}/target/{target_id}.json", cache_hours=24 * 90)
    return {syn["component_synonym"] for comp in data.get("target_components") or []
            for syn in comp.get("target_component_synonyms") or [] if syn.get("syn_type") == "GENE_SYMBOL"}


def _mechanisms(chembl_id: str) -> list[dict]:
    data = get_json(f"{BASE}/mechanism.json", params={"molecule_chembl_id": chembl_id, "limit": 20}, cache_hours=24 * 60)
    return [m for m in data.get("mechanisms", []) if m.get("target_chembl_id")]


def lookup(name: str) -> dict | None:
    """{'chembl_id', 'pref_name', 'targets': [target ids], 'mechanism': 'PD-1 inhibitor; ...'} or None."""
    q = clean(name)
    if len(norm(q)) < 4:
        return None
    data = get_json(f"{BASE}/molecule/search.json", params={"q": q, "limit": 5}, cache_hours=24 * 60)
    for m in data.get("molecules", []):
        names = {norm(m.get("pref_name"))} | {norm(s.get("molecule_synonym")) for s in m.get("molecule_synonyms") or []}
        if norm(q) not in names:
            continue
        mechs = _mechanisms(m["molecule_chembl_id"])
        parent = (m.get("molecule_hierarchy") or {}).get("parent_chembl_id")
        if not mechs and parent and parent != m["molecule_chembl_id"]:   # a salt: the mechanism sits on the parent drug
            mechs = _mechanisms(parent)
        target_ids = sorted({x["target_chembl_id"] for x in mechs})
        return {"chembl_id": m["molecule_chembl_id"], "pref_name": m.get("pref_name"),
                "targets": target_ids,
                "symbols": sorted({sym for t in target_ids for sym in target_symbols(t)}),
                "mechanism": "; ".join(sorted({x["mechanism_of_action"] for x in mechs if x.get("mechanism_of_action")}))}
    return None
