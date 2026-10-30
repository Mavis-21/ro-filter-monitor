import unittest

from pydantic import ValidationError

from fastapi import HTTPException

from app import SensorInput, hardware_predict, random_sample, LivePredictionInput, predict
from core import salt_rejection
from hardware import SensorBridge


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

    def test_random_example_is_from_held_out_lifecycle(self):
        sample = random_sample()
        self.assertIn(sample["expected_label"], ("normal", "warning", "critical"))
        self.assertEqual(sample["correct"], sample["expected_label"] == sample["predicted_label"])

    def test_sensor_check_requires_a_fresh_complete_packet(self):
        bridge = SensorBridge()
        bridge.ingest('{"current_a":1.5,"flow_l_min":1.7}')
        self.assertEqual(bridge.status()["sensor_status"]["pressure_bar"], "waiting")
        bridge.ingest('{"current_a":1.5,"flow_l_min":1.7,"pressure_bar":6.6,"raw_tds_ppm":520,"output_tds_ppm":34}')
        self.assertTrue(all(value == "replying" for value in bridge.status()["sensor_status"].values()))
        bridge.disconnect()
        self.assertFalse(bridge.status()["fresh"])

    def test_live_prediction_requires_connected_board(self):
        with self.assertRaises(HTTPException) as error:
            hardware_predict(LivePredictionInput(filter_age_days=90))
        self.assertEqual(error.exception.status_code, 409)


if __name__ == "__main__":
    unittest.main()
