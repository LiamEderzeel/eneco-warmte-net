"""Constants for the Eneco Data integration."""

from datetime import timedelta

from homeassistant.const import UnitOfEnergy, UnitOfVolume

DOMAIN = "eneco_data"

CONF_CUSTOMER_ID = "customer_id"
CONF_API_KEY = "api_key"
CONF_SESSION_TOKEN = "session_token"

UPDATE_INTERVAL = timedelta(hours=12)

SESSION_URL = "https://www.eneco.nl/mijn-eneco/api/auth/session"
DOWNLOAD_URL_TEMPLATE = (
    "https://api-digital.enecogroup.com/dxpweb/nl/eneco/customers/"
    "{customer_id}/gdprdata/download"
)
SESSION_COOKIE_NAME = "__Secure-next-auth.session-token"

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:152.0) Gecko/20100101 Firefox/152.0",
    "Accept": "application/json",
    "Accept-Language": "nl-NL",
    "Origin": "https://www.eneco.nl",
    "Referer": "https://www.eneco.nl/",
}

# The two district-heating registers we care about. Both come from the same
# physical meter - GJ is the energy register, m3 is the volume register -
# not a separate gas meter.
KNOWN_TYPES = ("WarmthGJ", "WarmthM3")

# row type -> (statistic slug, unit, unit_class)
TYPE_TO_STAT = {
    "WarmthGJ": ("heat_gj", UnitOfEnergy.GIGA_JOULE, "energy"),
    "WarmthM3": ("heat_m3", UnitOfVolume.CUBIC_METERS, "volume"),
}
