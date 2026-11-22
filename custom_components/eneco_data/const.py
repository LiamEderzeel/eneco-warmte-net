"""Constants for the Eneco Data integration."""

from datetime import date, timedelta

DOMAIN = "eneco_data"

CONF_CUSTOMER_ID = "customer_id"
CONF_API_KEY = "api_key"
CONF_SESSION_TOKEN = "session_token"
CONF_ACCOUNT_ID = "account_id"
CONF_HEAT_PRICE = "heat_price"

DEFAULT_ACCOUNT_ID = "1"

UPDATE_INTERVAL = timedelta(hours=12)

SESSION_URL = "https://www.eneco.nl/mijn-eneco/api/auth/session"
USAGES_URL_TEMPLATE = (
    "https://api-digital.enecogroup.com/dxpweb/v3/nl/eneco/customers/"
    "{customer_id}/accounts/{account_id}/usages"
)
SESSION_COOKIE_NAME = "__Secure-next-auth.session-token"

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:152.0) Gecko/20100101 Firefox/152.0",
    "Accept": "application/json",
    "Accept-Language": "nl-NL",
    "Origin": "https://www.eneco.nl",
    "Referer": "https://www.eneco.nl/",
}

# First month known to have data; the daily usage is summed from here, so
# the running total stays stable between updates.
FIRST_MONTH = date(2025, 11, 1)

STAT_SLUG = "heat_gj_daily"
COST_STAT_SLUG = "heat_cost"
