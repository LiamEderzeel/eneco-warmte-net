"""Eneco usages client.

Flow:
  1. A NextAuth session cookie (__Secure-next-auth.session-token) is
     obtained once by logging in by hand (password + emailed code).
  2. GET .../api/auth/session, sent with just that cookie, returns a
     fresh idToken (1hr lifetime) AND reissues the session cookie with
     a new ~30-day expiry. Calling this regularly is what keeps the
     session alive indefinitely.
  3. That idToken + a static apikey header authorize GETs to the usages
     endpoint, which returns one month of daily usage per request.

Deliberately synchronous (requests) - callers must invoke via
hass.async_add_executor_job.
"""

from datetime import date

import requests

from .const import (
    DEFAULT_HEADERS,
    SESSION_COOKIE_NAME,
    SESSION_URL,
    USAGES_URL_TEMPLATE,
)
from .parser import parse_daily_usage


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

    def fetch_daily_usage(self, first_month: date) -> tuple[dict[str, float], str]:
        """Return ({date: GJ used that day}, renewed_session_token).

        Fetches every month from first_month up to the current one.
        Raises EnecoAuthError if the session cookie is expired/invalid,
        EnecoApiError for any other failure.
        """
        headers = {**DEFAULT_HEADERS, "apikey": self._api_key}

        session = requests.Session()
        session.headers.update(headers)
        session.cookies.set(
            SESSION_COOKIE_NAME, self._session_token, domain="www.eneco.nl"
        )

        sess_resp = session.get(SESSION_URL, timeout=30)
        if sess_resp.status_code != 200:
            raise EnecoAuthError(
                f"session refresh failed ({sess_resp.status_code}) - "
                "cookie is likely expired, log in by hand again"
            )

        id_token = sess_resp.json().get("idToken")
        if not id_token:
            raise EnecoAuthError("no idToken in session response - cookie may be invalid")

        renewed_token = session.cookies.get(SESSION_COOKIE_NAME) or self._session_token

        url = USAGES_URL_TEMPLATE.format(customer_id=self._customer_id)
        auth = {"Authorization": f"Bearer {id_token}"}
        today = date.today()
        month = first_month
        daily: dict[str, float] = {}
        while month <= today:
            resp = requests.get(
                url,
                headers={**headers, **auth},
                params={
                    "interval": "Day",
                    "aggregation": "Month",
                    "start": month.isoformat(),
                    "extrapolate": "false",
                    "addWeather": "false",
                    "addPreviousYear": "false",
                    "addBudget": "false",
                },
                timeout=30,
            )
            if resp.status_code != 200:
                raise EnecoApiError(f"usages request failed ({resp.status_code})")
            daily |= parse_daily_usage(resp.json())
            month = (
                date(month.year + 1, 1, 1)
                if month.month == 12
                else month.replace(month=month.month + 1)
            )

        return daily, renewed_token
