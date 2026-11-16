from typing import List

from .result_schema import GeoRegistrationRecord


def select_demo_records(records: List[GeoRegistrationRecord], max_success: int = 10, max_failure: int = 10):
    """Select representative successful and failed samples for system demonstration."""

    success = sorted((r for r in records if r.error_m <= 1), key=lambda r: r.error_m)[:max_success]
    failure = sorted((r for r in records if r.error_m > 5), key=lambda r: r.error_m, reverse=True)[:max_failure]
    boundary = sorted((r for r in records if 1 < r.error_m <= 5), key=lambda r: abs(r.error_m - 3))[:5]
    return {
        "success_within_1m": success,
        "failure_over_5m": failure,
        "boundary_1m_to_5m": boundary,
    }

