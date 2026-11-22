# Eneco Data

A [Home Assistant](https://www.home-assistant.io/) custom integration that
pulls your own Eneco daily district-heating usage and imports it into HA's long-term statistics, so it's selectable as a gas/heat
source on the Energy Dashboard.

Installable via [HACS](https://hacs.xyz/) as a custom repository.

## How it works

- **`custom_components/eneco_data/api.py`** — logs in via a saved NextAuth
  session cookie and fetches one month of daily usage per request from the
  usages API, from `FIRST_MONTH` up to the current month.
- **`custom_components/eneco_data/parser.py`** — pure parsing logic
  (usages JSON → daily GJ → running total). No network, no HA dependency.
- **`custom_components/eneco_data/coordinator.py`** — runs the fetch +
  parse steps once every 12 hours and pushes the running total of daily
  heat usage (GJ) into HA's recorder as an *external statistic*
  (`eneco_data:heat_gj_daily`). There's no separate entity to create by
  hand — the Energy Dashboard's gas/heat source picker lists external
  statistics directly.
- **`custom_components/eneco_data/config_flow.py`** — the UI setup flow
  (Settings → Devices & Services → Add Integration) and the reauth flow
  that fires automatically when your session cookie expires.

The one entity the integration owns is a diagnostic "Last successful
import" timestamp sensor, so you can see at a glance whether the daily
run is actually working.

## Installing via HACS

1. In HACS, add this repository as a **custom repository** (category:
   Integration).
2. Install "Eneco Data" and restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration**, search for
   "Eneco Data", and fill in the setup form (see below for where each
   value comes from).

## Getting the setup values

There's no programmatic login — Eneco's login is password + emailed
2FA-code gated, so the session token has to be obtained once by hand and
pasted in. It renews itself automatically after that (every successful
run reissues it with a fresh ~30-day expiry), so this is a one-time
bootstrap step, not something you'll repeat regularly — until it does
expire (e.g. after an extended period without HA running), at which point
Home Assistant will prompt you to re-authenticate with a fresh token via
the same flow.

- **Customer ID** — your Mijn Eneco customer number.
- **Account number** — usually `1`. It's the number after `/accounts/` in
  the usages request Mijn Eneco makes
  (`…/customers/<customer ID>/accounts/<account number>/usages`); Eneco can
  move you to a new account after a contract change. If it changes later,
  update it under the integration's **Configure** options.
- **API key** — the static `apikey` header value used by mijn-eneco.
- **Session token** — log in to eneco.nl by hand, open DevTools →
  Application/Storage → Cookies, and copy the value of
  `__Secure-next-auth.session-token`.

## Adding it to the Energy Dashboard

Settings → Energy → **Add gas source** (or heating, depending on your HA
version's wording) → pick "Eneco heat_gj_daily" from the
statistic picker.

### Costs

External statistics can't use the Energy Dashboard's fixed-price or
price-entity options, so the integration can import a cost statistic
itself: set **Price per GJ** (your variable heat tariff incl. VAT) under
the integration's **Configure** options. It then imports
`eneco_data:heat_cost` (running total of GJ × price), which you pick as
"Use an entity tracking the total costs" on the gas/heat source. The whole
series is rewritten on every run, so a new price applies to all history.
Leave it at 0 to skip costs.

If Eneco rejects the stored session token or apikey, Home Assistant asks
you to re-authenticate; the reauth form takes a fresh token and, if it
changed, the new apikey.

## Testing

```sh
nix develop
pytest
```

`tests/test_parser.py` covers the usages parsing and running total with
synthetic payloads. `tests/test_config_flow.py` and `tests/test_coordinator.py` use
`pytest-homeassistant-custom-component` with a mocked API client.
