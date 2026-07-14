"""Centralized configuration for external paths and resources.

All file system paths and external resource locations are defined here.
Defaults are empty strings — the application should handle missing values gracefully.

Environment variables take precedence over .env file values.
"""
import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Project root (this file's grandparent directory)
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Garmin Connect Token Store
# ---------------------------------------------------------------------------
# Path to the directory where garminconnect stores auth tokens.
# Default: empty — tokens will be stored in ~/.garminconnect (library default).
# Set to an absolute path to override, e.g. GARMIN_TOKENSTORE=/custom/token/dir
GARMIN_TOKENSTORE = os.getenv("GARMIN_TOKENSTORE", "")

# ---------------------------------------------------------------------------
# Data Directory
# ---------------------------------------------------------------------------
# Directory for synced health/activity data (JSON files).
# Default: <project_root>/data/
DATA_DIR = PROJECT_ROOT / "data"
