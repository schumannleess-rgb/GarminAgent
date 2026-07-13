"""Garmin Connect China region login module with CN-aware authentication.

Monkey-patches garminconnect library (0.3.x) to make is_cn=True work:
- Skips DI token exchange (diauth.garmin.com rejects CN client IDs)
- Uses JWT_WEB cookie via connect.garmin.cn/modern
- Injects SSO cookies into fresh API sessions
- Adds native app headers for CN JWT_WEB API calls
"""

import os
import sys
from pathlib import Path
from typing import Any

# Add vendor path for garminconnect library
_VENDOR_DIR = Path(__file__).resolve().parent.parent / "python-garminconnect-master"
if _VENDOR_DIR.is_dir():
    sys.path.insert(0, str(_VENDOR_DIR))

from garminconnect import (  # noqa: E402
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)

DEFAULT_TOKENSTORE = str(Path("~/.garminconnect").expanduser())


def _patch_client_for_cn():
    """Minimal CN monkey-patch for garminconnect library (0.3.6).

    The library sets domain-aware URLs for is_cn=True but the auth flow
    still tries DI token exchange at diauth.garmin.com which rejects CN
    client IDs. This patch:
    1. Skips DI exchange for CN, gets JWT_WEB via connect.garmin.cn/modern
    2. Extracts JWT_WEB from cffi session (uses get_dict(), not .jar)
    3. Fixes JWT_WEB cookie domain to .garmin.cn for cross-subdomain access
    4. Injects SSO cookies into fresh API sessions
    5. Adds native app headers for CN JWT_WEB API calls
    6. Uses self.cs (SSO session) for CN API requests to preserve cookies
    7. Skips social profile/settings checks that don't exist on CN
    """
    from garminconnect import client as _c

    # -- Patch 0: Client.login: skip DI-based strategies for CN --
    # mobile+cffi and mobile+requests both try DI token exchange at
    # diauth.garmin.com / mobile.integration.garmin.com, which reject CN
    # client IDs and may be unreachable from Chinese networks. Skip them.
    _orig_client_login = _c.Client.login

    def _patched_client_login(self, email, password, prompt_mfa=None, return_on_mfa=False):
        if self.is_cn:
            strategies: list[tuple[str, Any]] = [
                ("widget+cffi", lambda: self._widget_web_login(email, password)),
                ("portal+cffi", lambda: self._portal_web_login_cffi(email, password)),
                ("portal+requests", lambda: self._portal_web_login_requests(email, password)),
            ]
            last_err: Exception | None = None
            rate_limited_count = 0
            for name, run in strategies:
                try:
                    _c._LOGGER.debug("Trying login strategy: %s", name)
                    run()
                    return None, None
                except _c.GarminConnectAuthenticationError:
                    raise
                except _c._MFARequired:
                    if return_on_mfa:
                        return "needs_mfa", None
                    if prompt_mfa:
                        mfa_code = prompt_mfa()
                        self._complete_mfa(mfa_code)
                        return None, None
                    raise _c.GarminConnectAuthenticationError(
                        "MFA Required but no prompt_mfa mechanism supplied"
                    )
                except _c.GarminConnectTooManyRequestsError as e:
                    _c._LOGGER.warning("%s returned 429: %s", name, e)
                    rate_limited_count += 1
                    last_err = e
                    continue
                except Exception as e:
                    _c._LOGGER.warning("%s failed: %s", name, e)
                    last_err = e
                    continue
            if rate_limited_count == len(strategies):
                raise _c.GarminConnectTooManyRequestsError(
                    "All login strategies rate limited (429). "
                    "Try again later or check your IP/network."
                )
            raise _c.GarminConnectConnectionError(
                f"All login strategies exhausted: {last_err}"
            )
        return _orig_client_login(self, email, password, prompt_mfa, return_on_mfa)

    _c.Client.login = _patched_client_login

    def _fix_jwt_web_domain(sess):
        """Force JWT_WEB cookie domain to .garmin.cn.

        The SSO server sets the cookie with domain matching the host that
        served it (connect.garmin.cn), but API calls go to connectapi.garmin.cn.
        RFC 6265 requires an exact host match for host-only cookies, so we
        rewrite the domain to the parent .garmin.cn to cover all subdomains.
        """
        jwt_value = None
        try:
            jwt_value = sess.cookies.get_dict().get("JWT_WEB")
        except Exception:
            pass

        if not jwt_value:
            try:
                for c in sess.cookies.jar:
                    if c.name == "JWT_WEB":
                        jwt_value = c.value
                        break
            except Exception:
                pass

        if not jwt_value:
            return

        # cffi-requests Cookies.set() doesn't overwrite — it appends, so we
        # end up with two JWT_WEB entries. The cookie jar picks the more
        # specific domain (.connect.garmin.cn over .garmin.cn), but that
        # cookie doesn't reach connectapi.garmin.cn.  Clear the old domain
        # and re-set with the parent domain.
        try:
            sess.cookies.clear(domain=".connect.garmin.cn")
        except Exception:
            pass
        try:
            sess.cookies.set("JWT_WEB", jwt_value, domain=".garmin.cn")
            _c._LOGGER.info("CN: JWT_WEB cookie domain fixed to .garmin.cn")
        except Exception as e:
            _c._LOGGER.warning(f"CN: failed to fix JWT_WEB cookie domain: {e}")

    # -- Patch 1: _establish_session: skip DI for CN, fix cookie domain --
    _orig_establish = _c.Client._establish_session

    def _patched_establish(self, ticket, sess=None, service_url=None):
        if self.is_cn:
            # CN: skip DI exchange, go straight to JWT_WEB
            if sess is not None:
                self.cs = sess
            svc = self._connect + "/modern"
            self.cs.get(
                svc,
                params={"ticket": ticket},
                allow_redirects=True,
                timeout=30,
            )
            # cffi session: use get_dict() instead of .jar iteration
            jwt_web = None
            try:
                jwt_web = self.cs.cookies.get_dict().get("JWT_WEB")
            except Exception:
                pass
            if not jwt_web:
                # Fallback: try .jar for non-cffi sessions
                try:
                    for c in self.cs.cookies.jar:
                        if c.name == "JWT_WEB":
                            jwt_web = c.value
                            break
                except Exception:
                    pass
            if not jwt_web:
                raise GarminConnectAuthenticationError(
                    "JWT_WEB cookie not set after ticket consumption (CN)"
                )
            self.jwt_web = jwt_web
            _c._LOGGER.info("CN: JWT_WEB obtained successfully")
            # Fix cookie domain: server sets JWT_WEB with domain=connect.garmin.cn
            # but the API lives at connectapi.garmin.cn. Force domain to .garmin.cn
            # so the cookie is sent to all garmin.cn subdomains.
            _fix_jwt_web_domain(self.cs)
            return

        # Non-CN: original logic
        try:
            self._exchange_service_ticket(ticket, service_url=service_url)
            return
        except Exception as e:
            _c._LOGGER.warning(
                "DI token exchange failed (%s), falling back to JWT_WEB", e
            )

        if sess is not None:
            self.cs = sess

        svc = service_url or _c.IOS_SERVICE_URL
        self.cs.get(
            svc,
            params={"ticket": ticket},
            allow_redirects=True,
            timeout=30,
        )

        jwt_web = None
        for c in self.cs.cookies.jar:
            if c.name == "JWT_WEB":
                jwt_web = c.value
                break

        if not jwt_web:
            raise GarminConnectAuthenticationError(
                "JWT_WEB cookie not set after ticket consumption"
            )
        self.jwt_web = jwt_web

    _c.Client._establish_session = _patched_establish

    # -- Patch 2: _fresh_api_session: inject SSO cookies for CN --
    _orig_fresh = _c.Client._fresh_api_session

    def _patched_fresh_api_session(self):
        sess = _orig_fresh(self)
        if self.is_cn and self.jwt_web:
            try:
                from http.cookiejar import Cookie
            except ImportError:
                from cookielib import Cookie  # type: ignore

            # Extract cookies from SSO session (handles cffi Cookies)
            cookie_dict = {}
            try:
                cookie_dict = self.cs.cookies.get_dict()
            except Exception:
                pass

            for name, value in cookie_dict.items():
                try:
                    fixed = Cookie(
                        0,
                        name,
                        value,
                        None,
                        False,
                        ".garmin.cn",
                        True,
                        True,
                        "/",
                        True,
                        False,
                        0,
                        False,
                        False,
                        None,
                        {},
                    )
                    sess.cookies.set_cookie(fixed)
                except Exception:
                    pass
            _c._LOGGER.info(
                "CN: injected cookies into API session with .garmin.cn domain"
            )
        return sess

    _c.Client._fresh_api_session = _patched_fresh_api_session

    # -- Patch 3: get_api_headers: add native headers for CN JWT_WEB path --
    _orig_get_headers = _c.Client.get_api_headers

    def _patched_get_headers(self):
        if not self.is_authenticated:
            raise GarminConnectAuthenticationError("Not authenticated")
        if self.di_token:
            return _orig_get_headers(self)
        # JWT_WEB fallback with native app headers for CN
        headers = {
            "Accept": "application/json",
            "NK": "NT",
            "Origin": self._connect,
            "Referer": f"{self._connect}/modern/",
            "DI-Backend": f"connectapi.{self.domain}",
            # Explicitly set JWT_WEB cookie — the session's cookie jar
            # may not route it to connectapi.garmin.cn due to domain pinning.
            # Other cookies (CASTGC, GARMIN-SSO) are for sso.garmin.cn and
            # are not needed for API calls.
            "Cookie": f"JWT_WEB={self.jwt_web}",
        }
        if self.is_cn:
            headers.update({
                "User-Agent": _c.NATIVE_API_USER_AGENT,
                "X-Garmin-User-Agent": _c.NATIVE_X_GARMIN_USER_AGENT,
                "X-Garmin-Paired-App-Version": "10861",
                "X-Garmin-Client-Platform": "Android",
                "X-App-Ver": "10861",
                "X-Lang": "en",
                "X-GCExperience": "GC5",
                "Accept-Language": "en-US,en;q=0.9",
            })
        if self.csrf_token:
            headers["connect-csrf-token"] = str(self.csrf_token)
        return headers

    _c.Client.get_api_headers = _patched_get_headers

    # -- Patch 4: _run_request: use self.cs for CN API calls --
    # The library uses _fresh_api_session() which creates empty sessions,
    # losing all cookies. For CN, use self.cs which carries full auth context.
    _orig_run_request = _c.Client._run_request

    def _patched_run_request(self, method, path, **kwargs):
        if self.is_cn and self.jwt_web:
            url = f"{self._connectapi}/{path.lstrip('/')}"
            if "timeout" not in kwargs:
                kwargs["timeout"] = 15
            headers = self.get_api_headers()
            custom_headers = kwargs.pop("headers", {})
            headers.update(custom_headers)
            # Use self.cs (SSO session with cookies) instead of fresh session
            resp = self.cs.request(method, url, headers=headers, **kwargs)
            if resp.status_code == 401:
                self._refresh_session()
                resp = self.cs.request(method, url, headers=self.get_api_headers(), **kwargs)
            if resp.status_code == 204:
                class EmptyJSONResp:
                    status_code = 204
                    content = b""
                    def json(self):
                        return {}
                return EmptyJSONResp()
            if resp.status_code >= 400:
                error_msg = f"API Error {resp.status_code}"
                try:
                    error_data = resp.json()
                    if isinstance(error_data, dict):
                        msg = (error_data.get("message") or error_data.get("content") or
                               error_data.get("detailedImportResult", {}).get("failures", [{}])[0].get("messages", [""])[0])
                        if msg:
                            error_msg += f" - {msg}"
                        else:
                            error_msg += f" - {error_data}"
                except Exception:
                    if len(resp.text) < 500:
                        error_msg += f" - {resp.text}"
                raise _c.GarminConnectConnectionError(error_msg)
            return resp
        return _orig_run_request(self, method, path, **kwargs)

    _c.Client._run_request = _patched_run_request

    # -- Patch 5: Garmin.login() skip social profile for CN --
    _garmin_module = __import__("garminconnect", fromlist=["Garmin"])
    _orig_garmin_login = _garmin_module.Garmin.login

    def _patched_garmin_login(self, tokenstore=None):
        from garminconnect import GarminConnectAuthenticationError
        import time as _time
        tokenstore = tokenstore or __import__("os").getenv("GARMINTOKENS")

        mfa_status = None
        _legacy_token = None

        tokens_loaded = False
        tokenstore_path = None
        if tokenstore:
            try:
                if len(tokenstore) > 512:
                    self.client.loads(tokenstore)
                else:
                    tokenstore_path = str(Path(tokenstore).expanduser().resolve())
                    self.client.load(tokenstore_path)
                tokens_loaded = True
                if (
                    self.client.di_refresh_token
                    and self.client._token_expires_soon()
                ):
                    self.client._refresh_session()
            except Exception:
                tokens_loaded = False

        if not tokens_loaded:
            if not self.username or not self.password:
                raise GarminConnectAuthenticationError(
                    "Username and password are required"
                )
            if self.return_on_mfa:
                mfa_status, _legacy_token = self.client.login(
                    self.username, self.password, return_on_mfa=self.return_on_mfa
                )
                return mfa_status, _legacy_token
            if tokenstore_path is not None:
                self.client._tokenstore_path = tokenstore_path
            mfa_status, _legacy_token = self.client.login(
                self.username, self.password, prompt_mfa=self.prompt_mfa
            )
            # Only persist tokens if DI exchange succeeded (CN-compatible).
            # JWT_WEB-only fallback dumps an unusable token file that would
            # overwrite a working DI token from a previous session.
            if tokenstore_path is not None and self.client.di_token:
                import contextlib
                with contextlib.suppress(Exception):
                    self.client.dump(tokenstore_path)

        if self.is_cn:
            import logging as _logging
            _logging.getLogger("garminconnect").info(
                "CN account: skipping social profile/settings checks"
            )
            self.display_name = self.username
            self.full_name = ""
            return None, None

        # Non-CN: original profile/settings loading
        prof = None
        for _attempt in range(3):
            try:
                prof = self.client.connectapi("/userprofile-service/socialProfile")
                if isinstance(prof, dict):
                    break
            except Exception as e:
                if _attempt == 2:
                    raise GarminConnectAuthenticationError(
                        "Failed to retrieve social profile"
                    ) from e
                _time.sleep(1)

        if not isinstance(prof, dict):
            raise GarminConnectAuthenticationError(
                "Invalid profile data found"
            )

        self.display_name = prof.get("displayName", self.username)
        self.full_name = prof.get("fullName", "")

        settings = None
        for _attempt in range(3):
            try:
                settings = self.client.connectapi(
                    self.garmin_connect_user_settings_url
                )
                if (
                    settings
                    and isinstance(settings, dict)
                    and "userData" in settings
                ):
                    break
            except Exception as e:
                if _attempt == 2:
                    raise GarminConnectAuthenticationError(
                        "Failed to retrieve user settings"
                    ) from e
                _time.sleep(1)

        return None, None

    _garmin_module.Garmin.login = _patched_garmin_login


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
    _patch_client_for_cn()

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
