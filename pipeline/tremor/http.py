"""A polite way to download data.

- Sends our User-Agent label on every request.
- Waits between requests to the same website (so we never hammer anyone).
- If a site is busy or errors, waits longer and tries again ("backing off").
"""
import hashlib
import json
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

from . import settings

# Minimum seconds between two requests to the same website.
MIN_GAP_SECONDS = {
    "clinicaltrials.gov": 0.5,
    "www.sec.gov": 0.15,   # SEC allows 10/second; we stay well under
    "data.sec.gov": 0.15,
    "efts.sec.gov": 0.15,
}
DEFAULT_GAP = 0.5
RETRY_STATUS = {429, 500, 502, 503, 504}

CACHE_DIR = Path(__file__).resolve().parents[1] / ".cache"  # gitignored

_session = requests.Session()
_last_request_at: dict[str, float] = {}


def get_text(url: str, params: dict | None = None, retries: int = 5, timeout: int = 60) -> str:
    return _get(url, params, retries, timeout).text


def get_json(url: str, params: dict | None = None, retries: int = 5, timeout: int = 60,
             cache_hours: float = 0):
    """Download JSON. With cache_hours > 0, reuse a saved copy younger than that."""
    if cache_hours:
        key = hashlib.sha1(json.dumps([url, params], sort_keys=True).encode()).hexdigest()
        path = CACHE_DIR / f"{key}.json"
        if path.exists() and time.time() - path.stat().st_mtime < cache_hours * 3600:
            return json.loads(path.read_text())
        data = get_json(url, params, retries, timeout)
        CACHE_DIR.mkdir(exist_ok=True)
        path.write_text(json.dumps(data))
        return data
    return _get(url, params, retries, timeout).json()


def _get(url: str, params: dict | None, retries: int, timeout: int) -> requests.Response:
    host = urlparse(url).netloc
    for attempt in range(retries):
        # Wait if we asked this site something very recently
        gap = MIN_GAP_SECONDS.get(host, DEFAULT_GAP)
        wait = _last_request_at.get(host, 0) + gap - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        _last_request_at[host] = time.monotonic()

        try:
            resp = _session.get(
                url, params=params, timeout=timeout,
                headers={"User-Agent": settings.user_agent()},
            )
        except requests.RequestException as err:
            error = err
        else:
            if resp.status_code == 200:
                return resp
            if resp.status_code not in RETRY_STATUS:
                resp.raise_for_status()
            error = RuntimeError(f"{host} answered {resp.status_code}")

        delay = 2 ** attempt  # 1, 2, 4, 8, 16 seconds
        print(f"  ...{error}; retrying in {delay}s")
        time.sleep(delay)
    raise RuntimeError(f"Gave up on {url} after {retries} tries: {error}")
