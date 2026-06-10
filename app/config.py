"""Configuration loaded from environment / .env. No secrets are hardcoded here."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env if present (gitignored). Real secrets live there, never in code.
load_dotenv()

ROOT = Path(__file__).resolve().parent.parent

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
COACH_MODEL = os.environ.get("COACH_MODEL", "claude-sonnet-4-6").strip()

HOST = os.environ.get("HOST", "0.0.0.0").strip()
PORT = int(os.environ.get("PORT", "8042"))

DATA_DIR = (ROOT / os.environ.get("DATA_DIR", "data")).resolve()
AUDIO_DIR = DATA_DIR / "audio"
REPORTS_DIR = DATA_DIR / "reports"
DB_PATH = DATA_DIR / "learning_coach.db"


def ensure_dirs() -> None:
    for d in (DATA_DIR, AUDIO_DIR, REPORTS_DIR):
        d.mkdir(parents=True, exist_ok=True)


def has_api_key() -> bool:
    return bool(ANTHROPIC_API_KEY)
