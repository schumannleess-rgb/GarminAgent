"""Garmin Connect login module with auto token persistence.

Usage:
    from login.garmin_login import garmin_login

    garmin = garmin_login(email="xxx@qq.com", password="xxx")
    # Token auto-persisted to project_root/tokens/garmin_tokens.json
    # Next call restores from token, no password needed

Token lifecycle:
    - access_token: ~30 hours, auto-refreshed by library before expiry
    - refresh_token: ~30 days, used to renew access_token
    - As long as the app runs at least once within 30 days, tokens stay valid
"""

import os
import sys
from pathlib import Path

# Add vendor path for garminconnect library
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if _PROJECT_ROOT.is_dir():
    sys.path.insert(0, str(_PROJECT_ROOT))

from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)

DEFAULT_TOKEN_DIR = str(Path(__file__).resolve().parent.parent / "tokens")
TOKEN_FILE = str(Path(__file__).resolve().parent.parent / "tokens" / "garmin_tokens.json")


def garmin_login(
    email: str | None = None,
    password: str | None = None,
    tokenstore: str = DEFAULT_TOKEN_DIR,
    is_cn: bool = False,
) -> Garmin:
    """Login to Garmin Connect with auto token persistence.

    Flow:
        1. Try restore from saved tokens (no password needed)
        2. If tokens invalid/expired, fallback to credential login
        3. Tokens are always saved after successful login

    Args:
        email: Garmin account email. Required for first login.
        password: Garmin account password. Required for first login.
        tokenstore: Directory to store tokens. Defaults to project_root/tokens.
        is_cn: Use China region (garmin.cn). Defaults to False.

    Returns:
        Authenticated Garmin client instance.
    """
    # Ensure token directory exists
    Path(tokenstore).mkdir(parents=True, exist_ok=True)

    # Single login attempt: library handles token restore + credential fallback internally
    if not email or not password:
        # Token-only login (no credentials provided)
        garmin = Garmin(is_cn=is_cn)
        try:
            garmin.login(TOKEN_FILE)
            print(f"[garmin_login] Token restored from {TOKEN_FILE}")
            return garmin
        except GarminConnectAuthenticationError as e:
            raise GarminConnectAuthenticationError(
                "No valid tokens found and no credentials provided. "
                "Please provide email and password for first login."
            ) from e
        except Exception as e:
            raise GarminConnectAuthenticationError(
                f"Token login failed: {e}"
            ) from e

    # Credential login (library also tries token restore first if token file exists)
    try:
        garmin = Garmin(email=email, password=password, is_cn=is_cn)
        # Use login() without tokenstore (avoids library token format issues)
        garmin.login()
        # Also try login with tokenstore (if it fails, that's OK - we already logged in)
        try:
            garmin.login(TOKEN_FILE)
        except Exception:
            pass  # Token file login might fail, but we are already authenticated
        print(f"[garmin_login] Login success for {email}")
        return garmin
    except GarminConnectAuthenticationError:
        print(f"[garmin_login] Auth failed for {email}")
        raise
    except Exception as e:
        print(f"[garmin_login] Login error: {type(e).__name__}: {e}")
        raise


def garmin_login_interactive(
    tokenstore: str = DEFAULT_TOKEN_DIR,
    is_cn: bool = False,
) -> Garmin:
    """Interactive login — prompts for credentials if needed."""
    email = os.getenv("GARMIN_EMAIL") or os.getenv("EMAIL")
    password = os.getenv("GARMIN_PASSWORD") or os.getenv("PASSWORD")

    try:
        return garmin_login(
            email=email, password=password, tokenstore=tokenstore, is_cn=is_cn
        )
    except GarminConnectAuthenticationError:
        if not email:
            email = input("Garmin email: ").strip()
        if not password:
            from getpass import getpass
            password = getpass("Garmin password: ")

        return garmin_login(
            email=email, password=password, tokenstore=tokenstore, is_cn=is_cn
        )
