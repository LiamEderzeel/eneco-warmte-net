"""Tests for the pure parsing logic - no HA runtime needed beyond imports."""

from pathlib import Path

import pytest

from custom_components.eneco_data.parser import (
    load_readings,
    parse_dutch_number,
    resolve_series,
)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "meterstanden.csv"


def test_parse_dutch_number():
    assert parse_dutch_number("3747,19") == 3747.19
    assert parse_dutch_number("0,0") == 0.0
    assert parse_dutch_number("1.234,56") == 1234.56


def test_load_readings_groups_by_date_and_type():
    with open(FIXTURE_PATH, encoding="utf-8-sig", newline="") as f:
        readings = load_readings(f)

    assert "WarmthGJ" in readings
    assert "WarmthM3" in readings
    # 2024-01-08 has two WarmthM3 rows (a duplicate-value date)
    assert readings["WarmthM3"]["2024-01-08"] == [1.0, 0.0]


def test_resolve_series_is_monotonic_non_decreasing():
    with open(FIXTURE_PATH, encoding="utf-8-sig", newline="") as f:
        readings = load_readings(f)

    series = resolve_series(readings["WarmthGJ"])
    values = [value for _, value in series]
    assert values == sorted(values)


def test_resolve_series_clamps_real_decrease():
    # 2024-05-01 (198.584) is a real decrease from 2024-01-08 (199.429) -
    # must be clamped up to the running max, not reported as-is.
    with open(FIXTURE_PATH, encoding="utf-8-sig", newline="") as f:
        readings = load_readings(f)

    series = dict(resolve_series(readings["WarmthGJ"]))
    assert series["2024-01-08"] == 199.429
    assert series["2024-05-01"] == 199.429


def test_resolve_series_takes_max_of_same_date_duplicates():
    # 2025-05-01 WarmthM3 has both 0,0 and 3482,0 recorded the same day.
    with open(FIXTURE_PATH, encoding="utf-8-sig", newline="") as f:
        readings = load_readings(f)

    series = dict(resolve_series(readings["WarmthM3"]))
    assert series["2025-05-01"] == 3482.0


def test_resolve_series_empty_input():
    assert resolve_series({}) == []
