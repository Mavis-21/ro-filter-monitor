"""Reproducible domestic RO scenarios for an educational prototype.

These are generated examples, not measurements or verified failure labels.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from core import salt_rejection


def make_simulated_lifecycles(count: int = 260, seed: int = 20261030) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    records = []
    fault_types = ("fouling", "membrane", "pump", "mixed")

    for lifecycle_id in range(count):
        points = int(rng.integers(65, 116))
        lifetime_days = float(rng.uniform(170, 460))
        base_current = float(rng.uniform(0.85, 2.5))
        base_flow = float(rng.uniform(0.75, 2.4))
        base_pressure = float(rng.uniform(4.3, 9.2))
        base_raw_tds = float(rng.uniform(160, 950))
        healthy_rejection = float(rng.uniform(89, 98))
        daily_litres = float(rng.uniform(8, 55))
        daily_runtime = float(rng.uniform(0.4, 3.3))
        onset = float(rng.uniform(0.36, 0.7))
        fault = str(rng.choice(fault_types))
        ages = np.linspace(0, lifetime_days * 1.12, points)

        for age in ages:
            fraction = age / lifetime_days
            wear = np.clip((fraction - onset) / (1.0 - onset), 0, 1.15)
            severity = float(np.clip(wear * rng.uniform(0.88, 1.13), 0, 1.12))
            if rng.random() < 0.025:
                severity = float(np.clip(severity + rng.uniform(0.14, 0.45), 0, 1.12))

            if severity < 0.36:
                label = "normal"
            elif severity < 0.72:
                label = "warning"
            else:
                label = "critical"

            # Different hidden faults create overlapping sensor signatures.
            flow_loss = {"fouling": 0.46, "membrane": 0.12, "pump": 0.49, "mixed": 0.38}[fault]
            current_gain = {"fouling": 0.27, "membrane": 0.04, "pump": 0.31, "mixed": 0.24}[fault]
            pressure_gain = {"fouling": 0.23, "membrane": 0.02, "pump": -0.39, "mixed": 0.04}[fault]
            rejection_loss = {"fouling": 3.3, "membrane": 23.0, "pump": 1.8, "mixed": 13.5}[fault]

            current = max(0.05, base_current * (1 + current_gain * severity) + rng.normal(0, 0.075))
            flow = max(0.02, base_flow * (1 - flow_loss * severity) + rng.normal(0, 0.075))
            pressure = max(0.3, base_pressure * (1 + pressure_gain * severity) + rng.normal(0, 0.23))
            raw_tds = max(30, base_raw_tds * (1 + rng.normal(0, 0.035)))
            rejection = np.clip(healthy_rejection - rejection_loss * severity + rng.normal(0, 1.1), 30, 99.5)
            output_tds = max(0.1, raw_tds * (1 - rejection / 100))

            records.append(
                {
                    "lifecycle_id": lifecycle_id,
                    "current_a": round(current, 4),
                    "flow_l_min": round(flow, 4),
                    "pressure_bar": round(pressure, 4),
                    "raw_tds_ppm": round(raw_tds, 4),
                    "output_tds_ppm": round(output_tds, 4),
                    "salt_rejection_pct": round(salt_rejection(raw_tds, output_tds), 4),
                    "cumulative_litres": round(age * daily_litres * rng.uniform(0.96, 1.04), 2),
                    "filter_age_days": round(age, 2),
                    "runtime_hours": round(age * daily_runtime * rng.uniform(0.96, 1.04), 2),
                    "flow_trend_pct_week": round(-flow_loss * severity * 10 + rng.normal(0, 1.65), 3),
                    "current_trend_pct_week": round(current_gain * severity * 10 + rng.normal(0, 1.25), 3),
                    "pressure_trend_pct_week": round(pressure_gain * severity * 10 + rng.normal(0, 1.3), 3),
                    "label": label,
                    "fault_type": fault,
                }
            )

    return pd.DataFrame.from_records(records)
