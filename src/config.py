"""Central configuration for the personal research intelligence agent."""

from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - GitHub Actions installs dependencies.
    load_dotenv = None


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
SENT_PAPERS_FILE = DATA_DIR / "sent_papers.json"

if load_dotenv:
    load_dotenv(ROOT_DIR / ".env")


def _env(name: str, default: str = "") -> str:
    value = os.getenv(name)
    return value if value not in (None, "") else default


def _env_int(name: str, default: int) -> int:
    value = _env(name, str(default))
    try:
        return int(value)
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    value = _env(name, "true" if default else "false")
    return value.lower() in {"1", "true", "yes", "y", "on"}


KEYWORDS = [
    "artificial intelligence",
    "deep learning",
    "machine learning",
    "data science",
    "large language model",
    "graph neural network",
    "remote sensing",
]

MAX_PAPERS = _env_int("MAX_PAPERS", 20)
try:
    MIN_SCORE = float(_env("MIN_SCORE", "25"))
except ValueError:
    MIN_SCORE = 25.0

ENABLE_OPENALEX = _env_bool("ENABLE_OPENALEX", True)
ENABLE_ARXIV = _env_bool("ENABLE_ARXIV", True)

OPENALEX_MAILTO = _env("OPENALEX_MAILTO")
OPENALEX_BASE_URL = "https://api.openalex.org/works"
OPENALEX_SOURCES_BASE_URL = "https://api.openalex.org/sources"

ARXIV_BASE_URL = "https://export.arxiv.org/api/query"

DEEPSEEK_API_KEY = _env("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = _env("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = _env("DEEPSEEK_MODEL", "deepseek-v4-flash")
DEEPSEEK_THINKING = _env("DEEPSEEK_THINKING", "enabled").lower()
DEEPSEEK_REASONING_EFFORT = _env("DEEPSEEK_REASONING_EFFORT", "high").lower()
DEEPSEEK_TIMEOUT_SECONDS = _env_int("DEEPSEEK_TIMEOUT_SECONDS", 45)

EMAIL_HOST = _env("EMAIL_HOST")
EMAIL_PORT = _env_int("EMAIL_PORT", 587)
EMAIL_USER = _env("EMAIL_USER")
EMAIL_PASSWORD = _env("EMAIL_PASSWORD")
EMAIL_TO = _env("EMAIL_TO")
EMAIL_USE_TLS = _env_bool("EMAIL_USE_TLS", True)

TELEGRAM_BOT_TOKEN = _env("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = _env("TELEGRAM_CHAT_ID")
