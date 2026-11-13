"""Parsing logic for the Eneco usages API response.

No network, no Home Assistant dependency.
"""


def parse_daily_usage(payload: dict) -> dict[str, float]:
    """Return {"YYYY-MM-DD": GJ used that day} from one usages response.

    Days not measured yet are returned as 0 by the API and are skipped.
    """
    daily = {}
    for usage in payload["data"]["usages"]:
        for entry in usage["entries"]:
            actual = entry["actual"]
            warmth = actual["warmth"]
            if not warmth or warmth["status"] != "MEASURED":
                continue
            amount = warmth["high"]
            daily[actual["date"][:10]] = amount["value"] / 10 ** amount["scale"]
    return daily


def cumulative(daily: dict[str, float]) -> list[tuple[str, float]]:
    """Turn daily usage into a sorted running total, as HA's "sum" needs."""
    total = 0.0
    series = []
    for day in sorted(daily):
        total += daily[day]
        series.append((day, total))
    return series
