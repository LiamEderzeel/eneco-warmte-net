# Eneco Data

A [Home Assistant](https://www.home-assistant.io/) custom integration that
pulls your own Eneco GDPR data export (district heating meter readings) and
imports it into HA's long-term statistics, so it's selectable as a gas/heat
source on the Energy Dashboard.

Installable via [HACS](https://hacs.xyz/) as a custom repository.

## How it works

- **`custom_components/eneco_data/api.py`** — logs in via a saved NextAuth
  session cookie, downloads the GDPR export, and extracts
  `Meterstanden.csv` in memory. No parsing, no HA statistics.
- **`custom_components/eneco_data/parser.py`** — pure parsing logic
  (Dutch-decimal CSV → monotonic per-date series). No network, no HA
  dependency.
- **`custom_components/eneco_data/coordinator.py`** — runs the fetch +
  parse steps once every 12 hours and pushes the two district-heating
  registers (GJ energy, m³ volume — both from the same physical meter,
  not a separate gas meter) into HA's recorder as *external statistics*
  (`eneco_data:heat_gj` / `eneco_data:heat_m3`). There's no separate
  entity to create by hand — the Energy Dashboard's gas/heat source
  picker lists external statistics directly.
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
- **API key** — the static `apikey` header value used by mijn-eneco.
- **Session token** — log in to eneco.nl by hand, open DevTools →
  Application/Storage → Cookies, and copy the value of
  `__Secure-next-auth.session-token`.

## Adding it to the Energy Dashboard

Settings → Energy → **Add gas source** (or heating, depending on your HA
version's wording) → pick "Eneco heat_gj" or "Eneco heat_m3" from the
statistic picker. Pick whichever unit you actually want tracked — GJ is
the energy register, m³ is the volume register of the same meter.

## Testing

```sh
nix develop
pytest
```

`tests/test_parser.py` covers the parsing/clamping logic against
`tests/fixtures/meterstanden.csv` (a synthetic export, not real account
data). `tests/test_config_flow.py` and `tests/test_coordinator.py` use
`pytest-homeassistant-custom-component` with a mocked API client.
