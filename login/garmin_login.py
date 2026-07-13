"""Garmin Connect China region login module with auto token persistence.

Usage:
    from login.garmin_login import garmin_login

    garmin = garmin_login(email="xxx@qq.com", password="xxx")
    # Token auto-persisted to ~/.garminconnect/garmin_tokens.json
    # Next call restores from token, no password needed

Token lifecycle:
    - access_token: ~30 hours, auto-refreshed by library before expiry
    - refresh_token: ~30 days, used to renew access_token
    - As long as the app runs at least once within 30 days, tokens stay valid
"""

import os
import sys
from pathlib import Path

from garminconnect import (  # noqa: E402
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)

DEFAULT_TOKENSTORE = str(Path("~/.garminconnect").expanduser())


def garmin_login(
    email: str | None = None,
    password: str | None = None,
    tokenstore: str = DEFAULT_TOKENSTORE,
    is_cn: bool = True,
) -> Garmin:
    """Login to Garmin Connect with auto token persistence.

    Flow:
        1. Try restore from saved tokens (no password needed)
        2. If tokens invalid/expired, fallback to credential login
        3. Tokens are always saved after successful login

    Args:
        email: Garmin account email. Required for first login.
        password: Garmin account password. Required for first login.
        tokenstore: Directory to store tokens. Defaults to ~/.garminconnect.
        is_cn: Use China region (garmin.cn). Defaults to True.

    Returns:
        Authenticated Garmin client instance.

    Raises:
        GarminConnectAuthenticationError: Invalid credentials or tokens.
        GarminConnectConnectionError: Network issues.
        GarminConnectTooManyRequestsError: Rate limited.
    """
    # Step 1: Try token restore
    try:
        garmin = Garmin(is_cn=is_cn)
        garmin.login(tokenstore)
        return garmin
    except (GarminConnectAuthenticationError, GarminConnectConnectionError):
        pass  # Tokens invalid, fall through to credential login

    # Step 2: Credential login
    if not email or not password:
        raise GarminConnectAuthenticationError(
            "No valid tokens found and no credentials provided. "
            "Please provide email and password for first login."
        )

    garmin = Garmin(email=email, password=password, is_cn=is_cn)
    garmin.login(tokenstore)
    return garmin


def garmin_login_interactive(
    tokenstore: str = DEFAULT_TOKENSTORE,
    is_cn: bool = True,
) -> Garmin:
    """Interactive login — prompts for credentials if needed.

    Same as garmin_login() but reads email/password from
    environment variables or stdin when tokens are invalid.
    """
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
