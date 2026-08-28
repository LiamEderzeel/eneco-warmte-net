"""
pyscript app: eneco_main
Responsibility: runs the full daily pipeline - fetch, then import - as
a single sequential trigger, replacing the previously separate
eneco_fetch and eneco_import cron schedules with one here.

eneco_fetch.py and eneco_import.py keep their own @service entry
points (pyscript.eneco_fetch_run / pyscript.eneco_import_run) so each
step can still be run and tested individually - this file only chains
them together for the real daily run, and is the only one with a
schedule attached.

SETUP
-----
1. Put this file at: config/pyscript/eneco_main.py
   (eneco_fetch.py and eneco_import.py stay where they already are -
   see their own SETUP sections. Their @time_trigger crons have been
   removed; only this file's trigger fires the daily run now.)
2. Reload pyscript, then test manually with pyscript.eneco_run_all
   before trusting the daily cron trigger.
"""


@time_trigger("cron(0 5 * * *)")
def eneco_run_all_scheduled():
    """Runs automatically every day at 05:00."""
    run_all()


@service
def eneco_run_all():
    """Callable manually as pyscript.eneco_run_all for testing."""
    run_all()


def run_all():
    log.info("Eneco pipeline: fetching export")
    pyscript.eneco_fetch_run()

    log.info("Eneco pipeline: importing into HA statistics")
    pyscript.eneco_import_run()

    log.info("Eneco pipeline: done")
