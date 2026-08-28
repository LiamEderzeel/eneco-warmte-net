"""
pyscript app: eneco_import
Responsibility: reads the Meterstanden.csv already written to disk by
eneco_fetch.py, parses it (via the shared eneco_parse module), and
pushes the district heating GJ/m3 readings into Home Assistant's
long-term statistics for the Energy Dashboard.

Deliberately has NO network calls - if this fails, it's a parsing or
HA-side problem, not an auth/network problem. That separation is the
whole point of splitting fetch and import.

SETUP
-----
1. Install "pyscript" via HACS and enable it.
2. Put this file at: config/pyscript/eneco_import.py
3. Put eneco_parse.py at: config/pyscript/modules/eneco_parse.py
   (pyscript's convention for modules shared between apps.)
4. Make sure eneco_fetch.py has run at least once, so
   config/eneco_export/Meterstanden.csv exists.
5. Create two entities for the imported statistics to attach to, e.g.
   template sensors with unit_of_measurement "GJ" and "m³" respectively
   (device_class: energy is fine for both - these are cumulative meter
   registers, not literal natural gas).
6. Reload pyscript, then test manually with pyscript.eneco_import_run
   to confirm it works before trusting the daily run.

Has no schedule of its own - eneco_main.py's daily trigger calls
pyscript.eneco_fetch_run() and then pyscript.eneco_import_run() in
sequence. The @service function below stays for testing this step in
isolation (against whatever Meterstanden.csv is already on disk).

CAVEAT: historical annual readings before your smart-meter permission
was granted are sparse and may include a reset/correction artifact
(see eneco_parse.resolve_series) - this is handled by clamping to a
non-decreasing series, at the cost of showing a single lump-sum spike
on any date where multiple/decreasing values were recorded.
"""

from datetime import datetime

import eneco_parse

EXPORT_CSV_PATH = "/config/eneco_export/Meterstanden.csv"

HEAT_GJ_ENTITY = "sensor.eneco_heat_gj"
HEAT_M3_ENTITY = "sensor.eneco_heat_m3"

TYPE_TO_ENTITY = {
    "WarmthGJ": (HEAT_GJ_ENTITY, "GJ"),
    "WarmthM3": (HEAT_M3_ENTITY, "m³"),
}


# --- Entry points -------------------------------------------------------

@service
def eneco_import_run():
    """Callable manually as pyscript.eneco_import_run for testing."""
    run_import()


# --- Core logic -----------------------------------------------------------

def run_import():
    try:
        with open(EXPORT_CSV_PATH, encoding="utf-8-sig", newline="") as f:
            readings = eneco_parse.load_readings(f)
    except FileNotFoundError:
        log.error(
            f"Eneco import: {EXPORT_CSV_PATH} not found - "
            "has eneco_fetch_run been called yet?"
        )
        return

    imported_counts = {}
    for row_type, (entity_id, unit) in TYPE_TO_ENTITY.items():
        series = eneco_parse.resolve_series(readings.get(row_type, {}))
        if not series:
            log.warning(f"Eneco import: no data found for {row_type}")
            continue

        stats = [
            {"start": datetime.fromisoformat(date), "sum": value}
            for date, value in series
        ]
        _push_statistics(entity_id, unit, stats)
        imported_counts[entity_id] = len(stats)

    log.info(f"Eneco import: done - {imported_counts}")


def _push_statistics(entity_id, unit, stats):
    recorder.import_statistics(
        metadata={
            "has_mean": False,
            "has_sum": True,
            "statistic_id": entity_id,
            "unit_of_measurement": unit,
            "source": "recorder",
        },
        stats=stats,
    )
