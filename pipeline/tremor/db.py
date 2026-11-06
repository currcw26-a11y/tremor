"""Talking to the Supabase database through its web API ("PostgREST").

Needs SUPABASE_URL and SUPABASE_SECRET_KEY (in .env.local or GitHub secrets).
The secret key can write to every table, so it only ever lives in the pipeline.
"""
import json
import os

import requests

from . import settings  # noqa: F401  (loads .env.local)

URL = os.getenv("SUPABASE_URL", "").rstrip("/")
KEY = os.getenv("SUPABASE_SECRET_KEY", "")
BATCH = 200

_session = requests.Session()


def _headers(extra: dict | None = None) -> dict:
    if not URL or not KEY:
        raise RuntimeError("Set SUPABASE_URL and SUPABASE_SECRET_KEY (see .env.example).")
    h = {"apikey": KEY, "Content-Type": "application/json"}
    if KEY.startswith("eyJ"):  # older-style keys also need this header
        h["Authorization"] = f"Bearer {KEY}"
    return {**h, **(extra or {})}


def _check(resp: requests.Response):
    if resp.status_code >= 300:
        raise RuntimeError(f"Supabase error {resp.status_code}: {resp.text[:500]}")
    return resp


def select(table: str, columns: str = "*", **filters) -> list[dict]:
    """Read every matching row, 1,000 at a time. Filters look like  tracked="eq.true"."""
    rows, start = [], 0
    while True:
        resp = _check(_session.get(f"{URL}/rest/v1/{table}", params={"select": columns, **filters},
                                   headers=_headers({"Range": f"{start}-{start + 999}"}), timeout=60))
        page = resp.json()
        rows += page
        if len(page) < 1000:
            return rows
        start += 1000


def insert(table: str, rows: list[dict], returning: str | None = None) -> list[dict]:
    """Add new rows. With returning="id,nct_id", gives back those columns of the new rows."""
    out = []
    for i in range(0, len(rows), BATCH):
        prefer = "return=representation" if returning else "return=minimal"
        params = {"select": returning} if returning else {}
        resp = _check(_session.post(f"{URL}/rest/v1/{table}", params=params, data=json.dumps(rows[i:i + BATCH]),
                                    headers=_headers({"Prefer": prefer}), timeout=120))
        if returning:
            out += resp.json()
    return out


def upsert(table: str, rows: list[dict], on_conflict: str):
    """Add rows, or update them if a row with the same key already exists."""
    for i in range(0, len(rows), BATCH):
        _check(_session.post(f"{URL}/rest/v1/{table}", params={"on_conflict": on_conflict},
                             data=json.dumps(rows[i:i + BATCH]),
                             headers=_headers({"Prefer": "resolution=merge-duplicates,return=minimal"}), timeout=120))


def update(table: str, values: dict, **filters):
    _check(_session.patch(f"{URL}/rest/v1/{table}", params=filters, data=json.dumps(values),
                          headers=_headers({"Prefer": "return=minimal"}), timeout=60))
