import unittest

from pydantic import ValidationError

from app import NrelInput, SensorInput, nrel_flow, predict
from core import salt_rejection


HEALTHY = {
    "current_a": 1.5,
    "flow_l_min": 1.7,
    "pressure_bar": 6.6,
    "raw_tds_ppm": 520,
    "output_tds_ppm": 34,
    "cumulative_litres": 2200,
    "filter_age_days": 90,
    "runtime_hours": 170,
    "flow_trend_pct_week": -0.4,
    "current_trend_pct_week": 0.2,
    "pressure_trend_pct_week": 0.1,
}


class MonitorTests(unittest.TestCase):
    def test_rejection_and_invalid_raw_tds(self):
        self.assertEqual(salt_rejection(500, 50), 90)
        with self.assertRaises(ValueError):
            salt_rejection(0, 50)

    def test_healthy_scenario(self):
        result = predict(SensorInput(**HEALTHY))
        self.assertEqual(result["status"], "normal")
        self.assertAlmostEqual(result["salt_rejection_pct"], 93.46, places=2)
        self.assertIsNone(result["remaining_life_days"])

    def test_pump_off_is_not_called_healthy(self):
        result = predict(SensorInput(**{**HEALTHY, "current_a": 0, "flow_l_min": 0}))
        self.assertEqual(result["status"], "off")
        self.assertEqual(result["model_status"], "not_evaluated")

    def test_active_pump_with_zero_flow_is_critical(self):
        result = predict(SensorInput(**{**HEALTHY, "flow_l_min": 0}))
        self.assertEqual(result["status"], "critical")
        self.assertIn("no permeate flow", result["notes"][0])

    def test_invalid_physical_reading_and_negative_input(self):
        result = predict(SensorInput(**{**HEALTHY, "output_tds_ppm": 600}))
        self.assertEqual(result["status"], "critical")
        with self.assertRaises(ValidationError):
            SensorInput(**{**HEALTHY, "pressure_bar": -1})

    def test_nrel_prediction_is_finite(self):
        result = nrel_flow(NrelInput(
            pressure_bar=50,
            feed_flow_l_min=22,
            feed_conductivity_ms_cm=55,
            temperature_c=20,
        ))
        self.assertGreater(result["predicted_permeate_flow_l_min"], 0)


if __name__ == "__main__":
    unittest.main()
