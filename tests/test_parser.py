"""Tests for the pure parsing logic - no HA runtime needed beyond imports."""

from custom_components.eneco_data.parser import cumulative, parse_daily_usage


def _entry(date, value, status="MEASURED"):
    warmth = (
        None
        if value is None
        else {"status": status, "high": {"scale": 5, "value": value}}
    )
    return {"actual": {"date": f"{date}T00:00:00Z", "warmth": warmth}}


PAYLOAD = {
    "data": {
        "usages": [
            {
                "entries": [
                    _entry("2026-11-01", 5202),
                    _entry("2026-11-02", 10000),
                    _entry("2026-11-03", None),
                    _entry("2026-11-04", 0, "NOT_MEASURED"),
                ]
            }
        ]
    }
}


def test_parse_daily_usage_scales_values_and_skips_unmeasured():
    assert parse_daily_usage(PAYLOAD) == {"2026-11-01": 0.05202, "2026-11-02": 0.1}


def test_cumulative_is_sorted_running_total():
    series = cumulative({"2026-11-02": 0.1, "2026-11-01": 0.05})
    assert [d for d, _ in series] == ["2026-11-01", "2026-11-02"]
    assert [round(v, 2) for _, v in series] == [0.05, 0.15]


def test_cumulative_empty():
    assert cumulative({}) == []
