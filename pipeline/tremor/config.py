"""Loads config/tremor.yaml: all score weights and cutoffs in one place."""
from functools import lru_cache
from pathlib import Path

import yaml

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "tremor.yaml"


@lru_cache
def load() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text())
