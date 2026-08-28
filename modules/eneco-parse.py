"""
eneco_parse.py - parsing logic for Meterstanden.csv, shared between:
  - standalone local testing: python eneco_parse.py <path>
  - the pyscript automation (eneco_import.py), which imports this module

To use from pyscript: copy this file to
config/pyscript/modules/eneco_parse.py (pyscript's convention for
shared modules), then `import eneco_parse` from eneco_import.py, which
lives directly in config/pyscript/.
"""

import csv
import sys
from collections import defaultdict

# The two district-heating registers we care about. Both come from the
# same physical meter - GJ is the energy register, m3 is the volume
# register - not a separate gas meter.
KNOWN_TYPES = ("WarmthGJ", "WarmthM3")


def parse_dutch_number(value):
    """Converts a Dutch-formatted number ("3747,19") to a float."""
    return float(value.replace(".", "").replace(",", "."))


def load_readings(text_stream, known_types=KNOWN_TYPES):
    """
    Returns {type: {date_str: [values seen for that date, in file order]}}
    for each type in known_types. Accepts any text stream (an open file,
    or a TextIOWrapper around a ZipExtFile) with Meterstanden.csv's
    semicolon-delimited, Dutch-decimal format.
    """
    readings = defaultdict(lambda: defaultdict(list))
    reader = csv.DictReader(text_stream, delimiter=";")
    for row in reader:
        row_type = row["Type"]
        if row_type not in known_types:
            continue
        date = row["Datum stand"]
        value = parse_dutch_number(row["Waarde"])
        readings[row_type][date].append(value)
    return readings


def resolve_series(readings_for_type):
    """
    Takes {date_str: [values]} and returns a sorted list of
    (date_str, resolved_value) where resolved_value is monotonically
    non-decreasing - safe to feed straight into HA's "sum" statistics.

    Same-date duplicates: takes the maximum value. Any apparent decrease
    across dates is clamped upward rather than guessed at, to avoid ever
    reporting negative usage for a period.
    """
    dates = sorted(readings_for_type.keys())
    resolved = []
    running_max = None

    for date in dates:
        value = max(readings_for_type[date])
        if running_max is None or value > running_max:
            running_max = value
        resolved.append((date, running_max))

    return resolved


# --- CLI, only used when running this file directly (not on import) ------

def _main():
    if len(sys.argv) != 2:
        print("Usage: python eneco_parse.py <path-to-Meterstanden.csv>")
        sys.exit(1)

    with open(sys.argv[1], encoding="utf-8-sig", newline="") as f:
        readings = load_readings(f)

    for row_type in KNOWN_TYPES:
        print(f"\n=== {row_type} ===")
        dates = sorted(readings[row_type].keys())
        print(f"{len(dates)} distinct date(s)")

        for date in dates:
            values = readings[row_type][date]
            if len(set(values)) > 1:
                print(
                    f"  {date}: MULTIPLE DIFFERENT VALUES {values} "
                    f"- needs manual review (meter swap? correction?)"
                )
            else:
                print(f"  {date}: {values[0]}")

        print(f"\n  --- Resolved series (safe for HA statistics 'sum') ---")
        for date, value in resolve_series(readings[row_type]):
            print(f"  {date}: {value}")


if __name__ == "__main__":
    _main()
