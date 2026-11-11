"""Talking to the Supabase database through its web API ("PostgREST").

Needs SUPABASE_URL and SUPABASE_SECRET_KEY (in .env.local or GitHub secrets).
The secret key can write to every table, so it only ever lives in the pipeline.
"""
import json
import os
import time

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


def _send(method: str, url: str, **kw) -> requests.Response:
    """One web request, tried again if the connection drops. After a long quiet stretch (like a slow ChEMBL
    lookup), Supabase closes the idle connection and the next request fails before it reaches the database."""
    for attempt in range(3):
        try:
            return _session.request(method, url, **kw)
        except requests.ConnectionError:
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))


def _check(resp: requests.Response):
    if resp.status_code >= 300:
        raise RuntimeError(f"Supabase error {resp.status_code}: {resp.text[:500]}")
    return resp


def select(table: str, columns: str = "*", **filters) -> list[dict]:
    """Read every matching row, 1,000 at a time. Filters look like  tracked="eq.true"."""
    rows, start = [], 0
    while True:
        resp = _check(_send("GET", f"{URL}/rest/v1/{table}", params={"select": columns, **filters},
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
        resp = _check(_send("POST", f"{URL}/rest/v1/{table}", params=params, data=json.dumps(rows[i:i + BATCH]),
                                    headers=_headers({"Prefer": prefer}), timeout=120))
        if returning:
            out += resp.json()
    return out


def upsert(table: str, rows: list[dict], on_conflict: str):
    """Add rows, or update them if a row with the same key already exists."""
    for i in range(0, len(rows), BATCH):
        _check(_send("POST", f"{URL}/rest/v1/{table}", params={"on_conflict": on_conflict},
                             data=json.dumps(rows[i:i + BATCH]),
                             headers=_headers({"Prefer": "resolution=merge-duplicates,return=minimal"}), timeout=120))


def update(table: str, values: dict, **filters):
    _check(_send("PATCH", f"{URL}/rest/v1/{table}", params=filters, data=json.dumps(values),
                          headers=_headers({"Prefer": "return=minimal"}), timeout=60))


def claim(table: str, values: dict, **filters) -> list[dict]:
    """Update matching rows and return the ones that changed. With a filter like welcome_sent_at="is.null",
    two programs can't both claim the same row: the second finds nothing left to change."""
    resp = _check(_send("PATCH", f"{URL}/rest/v1/{table}", params=filters, data=json.dumps(values),
                        headers=_headers({"Prefer": "return=representation"}), timeout=60))
    return resp.json()


def delete(table: str, **filters):
    """Remove rows matching the filters. Refuses to run with no filters (that would empty the table)."""
    if not filters:
        raise ValueError("delete() needs at least one filter")
    _check(_send("DELETE", f"{URL}/rest/v1/{table}", params=filters, headers=_headers({"Prefer": "return=minimal"}),
                           timeout=60))
