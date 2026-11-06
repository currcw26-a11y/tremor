"""Reads settings (like CONTACT_EMAIL) from environment variables or .env.local.

Secrets live in .env.local on your computer (gitignored) or in GitHub Actions secrets,
never in the code itself.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env.local")  # does nothing if the file doesn't exist

CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "").strip()


def user_agent() -> str:
    """The polite 'who is asking' label we send to every website.

    The SEC requires a contact email in it, so we include CONTACT_EMAIL when it's set.
    """
    return f"Tremor research project ({CONTACT_EMAIL})" if CONTACT_EMAIL else "Tremor research project"
