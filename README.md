# eneco-data

[pyscript](https://hacs-pyscript.readthedocs.io/) apps for Home Assistant
that pull your own GDPR data export from Eneco (district heating meter
readings) and import it into HA's long-term statistics for the Energy
Dashboard.

## Pipeline

Three apps, each independently testable, chained by a fourth:

- **`eneco-fetch.py`** — logs in via a saved NextAuth session cookie,
  downloads the GDPR export, and writes `Meterstanden.csv` to disk.
  No parsing, no HA statistics.
- **`eneco-parse.py`** — pure parsing logic (Dutch-decimal CSV →
  monotonic per-date series). No network, no HA. Shared as a pyscript
  *module* by the other apps, and also runnable standalone.
- **`eneco-import.py`** — reads the CSV already on disk, parses it via
  `eneco-parse.py`, and pushes readings into HA's recorder statistics.
  No network calls.
- **`eneco-main.py`** — the only one with a schedule. Runs once a day
  and calls the fetch and import services in sequence, so there's a
  single cron instead of one per step.

## Deploying to Home Assistant

1. Install and enable the **pyscript** integration via HACS.
2. Copy the apps into place:
   - `eneco-fetch.py` → `config/pyscript/eneco_fetch.py`
   - `eneco-import.py` → `config/pyscript/eneco_import.py`
   - `eneco-main.py` → `config/pyscript/eneco_main.py`
   - `eneco-parse.py` → `config/pyscript/modules/eneco_parse.py`
     (pyscript's convention for modules shared between apps)
3. Add to `secrets.yaml`:
   ```yaml
   eneco_customer_id: "your-customer-id"
   eneco_api_key: "the-static-apikey-header-value"
   ```
4. Create `config/eneco_cookie.json` (not inside `pyscript/`) with a
   fresh session token obtained by logging in to eneco.nl by hand
   (DevTools → cookie `__Secure-next-auth.session-token`):
   ```json
   {"session_token": "<value from DevTools>"}
   ```
5. Create two entities for the imported statistics to attach to
   (e.g. template sensors with `unit_of_measurement` `"GJ"` and
   `"m³"`) — see the header of `eneco-import.py` for details.
6. Reload pyscript.

## Testing each step

Each app exposes a `@service` you can call by hand from
Developer Tools → Actions before trusting the daily run:

- `pyscript.eneco_fetch_run` — fetch only, writes the CSV.
- `pyscript.eneco_import_run` — parse + import only, using whatever
  CSV is already on disk.
- `pyscript.eneco_run_all` — runs both in sequence, same as the daily
  05:00 trigger.

`eneco-parse.py` has no HA dependency and can also be tested locally
with plain Python — see below.

## Local dev shell

The Nix flake provides a `python3` with `requests` for local editing
of `eneco-fetch.py` (whose logic only actually runs inside pyscript on
HA — `secrets`, `log`, `@service` etc. are pyscript-injected globals).

```sh
nix develop
```

`eneco-parse.py` has no such dependency and runs standalone against a
sample file:

```sh
python eneco-parse.py mock.csv
```
