"""Eneco GDPR-export client.

Confirmed flow:
  1. A NextAuth session cookie (__Secure-next-auth.session-token) is
     obtained once by logging in by hand (password + emailed code).
  2. GET .../api/auth/session, sent with just that cookie, returns a
     fresh idToken (1hr lifetime) AND reissues the session cookie with
     a new ~30-day expiry. Calling this regularly is what keeps the
     session alive indefinitely.
  3. That idToken + a static apikey header authorize a GET to the GDPR
     export endpoint, which returns a ZIP containing Meterstanden.csv.

Deliberately synchronous (requests) - callers must invoke via
hass.async_add_executor_job.
"""

import io
import zipfile

import requests

from .const import (
    DEFAULT_HEADERS,
    DOWNLOAD_URL_TEMPLATE,
    SESSION_COOKIE_NAME,
    SESSION_URL,
)


class EnecoAuthError(Exception):
    """Raised when the session cookie is expired or invalid."""


class EnecoApiError(Exception):
    """Raised for any other API failure (download, unexpected response)."""


class EnecoClient:
    """Thin client around the Eneco GDPR export endpoints."""

    def __init__(self, customer_id: str, api_key: str, session_token: str) -> None:
        self._customer_id = customer_id
        self._api_key = api_key
        self._session_token = session_token

    def fetch_meterstanden_csv(self) -> tuple[bytes, str]:
        """Log in, download the GDPR export, and return (csv_bytes, renewed_session_token).

        Raises EnecoAuthError if the session cookie is expired/invalid,
        EnecoApiError for any other failure.
        """
        headers = {**DEFAULT_HEADERS, "apikey": self._api_key}

        session = requests.Session()
        session.headers.update(headers)
        session.cookies.set(
            SESSION_COOKIE_NAME, self._session_token, domain="www.eneco.nl"
        )

        # --- Step 1: refresh the idToken, let the session cookie renew ---
        sess_resp = session.get(SESSION_URL, timeout=30)
        if sess_resp.status_code != 200:
            raise EnecoAuthError(
                f"session refresh failed ({sess_resp.status_code}) - "
                "cookie is likely expired, log in by hand again"
            )

        data = sess_resp.json()
        id_token = data.get("idToken")
        if not id_token:
            raise EnecoAuthError("no idToken in session response - cookie may be invalid")

        renewed_token = session.cookies.get(SESSION_COOKIE_NAME) or self._session_token

        # --- Step 2: download the GDPR export ---
        download_url = DOWNLOAD_URL_TEMPLATE.format(customer_id=self._customer_id)
        data_resp = requests.get(
            download_url,
            headers={**headers, "Authorization": f"Bearer {id_token}"},
            timeout=30,
        )
        if data_resp.status_code != 200:
            raise EnecoApiError(f"data download failed ({data_resp.status_code})")

        # --- Step 3: extract Meterstanden.csv ---
        with zipfile.ZipFile(io.BytesIO(data_resp.content)) as zf:
            if "Meterstanden.csv" not in zf.namelist():
                raise EnecoApiError(
                    f"Meterstanden.csv not found in export ({zf.namelist()})"
                )
            csv_bytes = zf.read("Meterstanden.csv")

        return csv_bytes, renewed_token
