"""
pyscript app: eneco_fetch
Responsibility: ONLY authentication + downloading. Logs into Mijn Eneco
(via the confirmed NextAuth session-cookie flow), downloads the GDPR
data export, extracts Meterstanden.csv, and writes it to disk. Does
NOT parse the data or touch HA statistics - that's eneco_import.py's
job, deliberately kept separate so import can be re-run without
hitting the network again.

CONFIRMED FLOW:
  1. A NextAuth session cookie (__Secure-next-auth.session-token) is
     obtained once by logging in by hand (password + emailed code).
  2. GET https://www.eneco.nl/mijn-eneco/api/auth/session, sent with
     just that cookie, returns a fresh idToken (1hr lifetime) AND
     reissues the session cookie with a new ~30-day expiry. Calling
     this regularly is what keeps you logged in indefinitely.
  3. That idToken + a static apikey header authorize a GET to the GDPR
     export endpoint, which returns a ZIP containing Meterstanden.csv.

SETUP
-----
1. Install "pyscript" via HACS and enable it.
2. Put this file at: config/pyscript/eneco_fetch.py
3. Add to secrets.yaml:
       eneco_customer_id: "your-customer-id"
       eneco_api_key: "the-static-apikey-header-value"
4. Create config/eneco_cookie.json (NOT inside pyscript/) with:
       {"session_token": "<value from DevTools, from a fresh login>"}
5. Reload pyscript, then test manually with pyscript.eneco_fetch_run
   to confirm config/eneco_export/Meterstanden.csv appears afterward.

Has no schedule of its own - eneco_main.py's daily trigger calls
pyscript.eneco_fetch_run() before running the import step. The
@service function below stays for testing this step in isolation.
"""

import io
import json
import os
import zipfile

import requests

COOKIE_FILE = "/config/eneco_cookie.json"
EXPORT_DIR = "/config/eneco_export"
EXPORT_CSV_PATH = f"{EXPORT_DIR}/Meterstanden.csv"

SESSION_URL = "https://www.eneco.nl/mijn-eneco/api/auth/session"
CUSTOMER_ID = secrets["eneco_customer_id"]
API_KEY = secrets["eneco_api_key"]
DOWNLOAD_URL = (
    f"https://api-digital.enecogroup.com/dxpweb/nl/eneco/customers/"
    f"{CUSTOMER_ID}/gdprdata/download"
)

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:152.0) Gecko/20100101 Firefox/152.0",
    "Accept": "application/json",
    "Accept-Language": "nl-NL",
    "Origin": "https://www.eneco.nl",
    "Referer": "https://www.eneco.nl/",
    "apikey": API_KEY,
}


# --- Entry points -------------------------------------------------------

@service
def eneco_fetch_run():
    """Callable manually as pyscript.eneco_fetch_run for testing."""
    run_fetch()


# --- Core logic -----------------------------------------------------------

def run_fetch():
    session_token = _load_session_cookie()

    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
    session.cookies.set(
        "__Secure-next-auth.session-token", session_token, domain="www.eneco.nl"
    )

    # --- Step 1: refresh the idToken, let the session cookie renew ---
    sess_resp = session.get(SESSION_URL, timeout=30)
    if sess_resp.status_code != 200:
        log.error(
            f"Eneco fetch: session refresh failed ({sess_resp.status_code}) - "
            "cookie is likely expired, log in by hand again"
        )
        return

    data = sess_resp.json()
    id_token = data.get("idToken")
    if not id_token:
        log.error("Eneco fetch: no idToken in session response - cookie may be invalid")
        return

    new_cookie = session.cookies.get("__Secure-next-auth.session-token")
    _save_session_cookie(new_cookie or session_token)

    # --- Step 2: download the GDPR export ---
    data_resp = requests.get(
        DOWNLOAD_URL,
        headers={**DEFAULT_HEADERS, "Authorization": f"Bearer {id_token}"},
        timeout=30,
    )
    if data_resp.status_code != 200:
        log.error(f"Eneco fetch: data download failed ({data_resp.status_code})")
        return

    # --- Step 3: extract Meterstanden.csv and write it to disk ---
    with zipfile.ZipFile(io.BytesIO(data_resp.content)) as zf:
        if "Meterstanden.csv" not in zf.namelist():
            log.error(f"Eneco fetch: Meterstanden.csv not found in export ({zf.namelist()})")
            return
        csv_bytes = zf.read("Meterstanden.csv")

    os.makedirs(EXPORT_DIR, exist_ok=True)
    with open(EXPORT_CSV_PATH, "wb") as f:
        f.write(csv_bytes)

    log.info(f"Eneco fetch: wrote {len(csv_bytes)} bytes to {EXPORT_CSV_PATH}")


# --- Cookie persistence -----------------------------------------------

def _load_session_cookie():
    if not os.path.exists(COOKIE_FILE):
        raise RuntimeError(
            f"{COOKIE_FILE} not found - create it with a fresh session_token from DevTools"
        )
    with open(COOKIE_FILE) as f:
        return json.load(f)["session_token"]


def _save_session_cookie(value):
    with open(COOKIE_FILE, "w") as f:
        json.dump({"session_token": value}, f)
