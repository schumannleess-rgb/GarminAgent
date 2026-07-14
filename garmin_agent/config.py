"""Centralized local-runtime configuration.

Public source code lives in the repository. Private runtime state lives under
GARMIN_AGENT_HOME, which defaults to <repo>/.local and is ignored by Git.
Environment variables can override every path for local or production use.
"""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

try:
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env", override=False)
    load_dotenv(PROJECT_ROOT / ".local" / ".env", override=False)
except ImportError:
    pass


def _path_from_env(name: str, default: Path) -> Path:
    value = os.getenv(name)
    return Path(value).expanduser() if value else default


RUNTIME_DIR = _path_from_env("GARMIN_AGENT_HOME", PROJECT_ROOT / ".local")
TOKEN_DIR = _path_from_env("GARMIN_TOKEN_DIR", RUNTIME_DIR / "tokens")
CACHE_DIR = _path_from_env("GARMIN_CACHE_DIR", RUNTIME_DIR / "cache")
DATA_DIR = _path_from_env("GARMIN_DATA_DIR", RUNTIME_DIR / "data")
LOG_DIR = _path_from_env("GARMIN_LOG_DIR", RUNTIME_DIR / "logs")
MEMORY_DIR = _path_from_env("GARMIN_MEMORY_DIR", RUNTIME_DIR / "memory")
OUTPUT_DIR = _path_from_env("GARMIN_OUTPUT_DIR", RUNTIME_DIR / "output")

# garminconnect calls this argument "tokenstore"; keep the legacy name for
# callers while making the default private and repo-local.
GARMIN_TOKENSTORE = os.getenv("GARMIN_TOKENSTORE") or str(TOKEN_DIR)
