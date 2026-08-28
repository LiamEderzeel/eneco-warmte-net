"""Parsing logic for Meterstanden.csv.

No network, no Home Assistant dependency - shared between the coordinator
and the standalone test suite.
"""

import csv
from collections import defaultdict

from .const import KNOWN_TYPES


def parse_dutch_number(value: str) -> float:
    """Convert a Dutch-formatted number ("3747,19") to a float."""
    return float(value.replace(".", "").replace(",", "."))


def load_readings(text_stream, known_types=KNOWN_TYPES):
    """
    Return {type: {date_str: [values seen for that date, in file order]}}
    for each type in known_types. Accepts any text stream with
    Meterstanden.csv's semicolon-delimited, Dutch-decimal format.
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
    Take {date_str: [values]} and return a sorted list of
    (date_str, resolved_value) where resolved_value is monotonically
    non-decreasing - safe to feed straight into HA's "sum" statistics.

    Same-date duplicates: takes the maximum value. Any apparent decrease
    across dates is clamped upward rather than guessed at, to avoid ever
    reporting negative usage for a period. This means sparse historical
    annual readings (from before smart-meter permission was granted) may
    show a single lump-sum spike on any date where a reset/correction
    was recorded.
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
