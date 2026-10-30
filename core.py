"""Shared sensor schema and simple physical calculations."""

from __future__ import annotations

import math

FEATURES = [
    "current_a",
    "flow_l_min",
    "pressure_bar",
    "raw_tds_ppm",
    "output_tds_ppm",
    "salt_rejection_pct",
    "cumulative_litres",
    "filter_age_days",
    "runtime_hours",
    "flow_trend_pct_week",
    "current_trend_pct_week",
    "pressure_trend_pct_week",
]

LABELS = ["normal", "warning", "critical"]


def salt_rejection(raw_tds_ppm: float, output_tds_ppm: float) -> float:
    """Return percent salt rejection, with invalid inputs rejected explicitly."""
    if not all(math.isfinite(value) for value in (raw_tds_ppm, output_tds_ppm)):
        raise ValueError("TDS values must be finite numbers")
    if raw_tds_ppm <= 0:
        raise ValueError("Raw-water TDS must be greater than zero")
    if output_tds_ppm < 0:
        raise ValueError("Output-water TDS cannot be negative")
    return 100.0 * (1.0 - output_tds_ppm / raw_tds_ppm)
