"""Fingerprinting trial records so we only save a new copy when something changed."""
import hashlib
import json


def record_for_snapshot(study: dict) -> dict:
    """The part of a raw study we keep: the trial record itself plus whether results exist.
    (We skip 'derivedSection', which ClinicalTrials.gov recomputes itself and isn't an edit.)"""
    return {"protocolSection": study.get("protocolSection", {}), "hasResults": study.get("hasResults", False)}


def content_hash(record: dict) -> str:
    """A short fingerprint. Same record -> same fingerprint; any edit -> different fingerprint."""
    return hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest()[:32]


def changed_sections(old_record: dict, new_record: dict) -> list[str]:
    """Names of record sections that differ, e.g. ['contactsLocationsModule']."""
    old_p, new_p = old_record.get("protocolSection", {}), new_record.get("protocolSection", {})
    names = sorted(k for k in set(old_p) | set(new_p) if old_p.get(k) != new_p.get(k))
    if old_record.get("hasResults") != new_record.get("hasResults"):
        names.append("hasResults")
    return names
