"""Tests for ETAMeter and time formatting utilities."""

from __future__ import annotations

import time
import unittest

from qgis_vector_map.core.eta import ETAMeter, _format_seconds


class FormatSecondsTests(unittest.TestCase):
    """Tests for _format_seconds helper."""

    def test_zero(self):
        self.assertEqual(_format_seconds(0), "0:00")

    def test_subminute(self):
        self.assertEqual(_format_seconds(5), "0:05")
        self.assertEqual(_format_seconds(45), "0:45")

    def test_minutes(self):
        self.assertEqual(_format_seconds(60), "1:00")
        self.assertEqual(_format_seconds(125), "2:05")
        self.assertEqual(_format_seconds(600), "10:00")

    def test_hours(self):
        self.assertEqual(_format_seconds(3600), "1:00:00")
        self.assertEqual(_format_seconds(3661), "1:01:01")
        self.assertEqual(_format_seconds(7325), "2:02:05")

    def test_negative_clamps_to_zero(self):
        self.assertEqual(_format_seconds(-5), "0:00")
        self.assertEqual(_format_seconds(-100), "0:00")

    def test_float_seconds_truncates(self):
        self.assertEqual(_format_seconds(5.9), "0:05")
        self.assertEqual(_format_seconds(59.99), "0:59")


class ETAMeterTests(unittest.TestCase):
    """Tests for the ETAMeter class."""

    def test_initial_state(self):
        eta = ETAMeter()
        self.assertEqual(eta.elapsed(), 0.0)
        self.assertEqual(eta.eta_seconds(), 0.0)
        self.assertEqual(eta.elapsed_str(), "0:00")
        self.assertEqual(eta.eta_str(), "0:00")

    def test_start_records_time(self):
        eta = ETAMeter()
        eta.start()
        time.sleep(0.05)  # small but measurable
        self.assertGreater(eta.elapsed(), 0.0)

    def test_update_clamps_ratio(self):
        eta = ETAMeter()
        eta.start()
        eta.update(1.5)  # should clamp to 1.0
        self.assertEqual(eta.last_ratio, 1.0)
        eta.update(-0.5)  # should clamp to 0.0
        self.assertEqual(eta.last_ratio, 0.0)

    def test_eta_zero_when_no_progress(self):
        eta = ETAMeter()
        eta.start()
        time.sleep(0.05)
        # 0% progress -> cannot estimate
        self.assertEqual(eta.eta_seconds(), 0.0)
        self.assertEqual(eta.eta_str(), "0:00")

    def test_eta_zero_when_not_started(self):
        eta = ETAMeter()
        # never called start()
        self.assertEqual(eta.eta_seconds(), 0.0)

    def test_eta_at_50_percent(self):
        eta = ETAMeter()
        eta.start()
        time.sleep(0.1)
        eta.update(0.5)
        # At 50%, remaining time should roughly equal elapsed
        eta_sec = eta.eta_seconds()
        elapsed = eta.elapsed()
        # Allow some tolerance because of sleep timing
        self.assertAlmostEqual(eta_sec, elapsed, delta=elapsed * 0.5 + 0.1)

    def test_eta_at_25_percent(self):
        eta = ETAMeter()
        eta.start()
        time.sleep(0.1)
        eta.update(0.25)
        # At 25%, remaining = elapsed * 0.75 / 0.25 = 3 * elapsed
        eta_sec = eta.eta_seconds()
        elapsed = eta.elapsed()
        # Expected: ~3 * elapsed (plus some timing slop)
        self.assertGreater(eta_sec, elapsed * 2.0)
        self.assertLess(eta_sec, elapsed * 4.0)

    def test_eta_at_99_percent(self):
        eta = ETAMeter()
        eta.start()
        time.sleep(0.1)
        eta.update(0.99)
        eta_sec = eta.eta_seconds()
        # At 99%, remaining should be very small
        self.assertLess(eta_sec, 0.5)

    def test_progress_message_with_prefix_and_suffix(self):
        eta = ETAMeter()
        eta.start()
        time.sleep(0.05)
        eta.update(0.5)
        msg = eta.progress_message(prefix="Tile 5/16", suffix="Phase: vectorize")
        self.assertIn("Tile 5/16", msg)
        self.assertIn("elapsed", msg)
        self.assertIn("ETA", msg)
        self.assertIn("Phase: vectorize", msg)

    def test_progress_message_no_prefix(self):
        eta = ETAMeter()
        eta.start()
        time.sleep(0.05)
        eta.update(0.5)
        msg = eta.progress_message()
        self.assertIn("elapsed", msg)
        self.assertIn("ETA", msg)

    def test_progress_message_omits_eta_when_no_progress(self):
        eta = ETAMeter()
        eta.start()
        msg = eta.progress_message(prefix="Working")
        self.assertIn("Working", msg)
        self.assertIn("elapsed", msg)
        self.assertNotIn("ETA", msg)

    def test_repeated_updates(self):
        """Multiple updates should keep last_ratio and eta consistent."""
        eta = ETAMeter()
        eta.start()
        for r in (0.1, 0.2, 0.3, 0.4, 0.5):
            time.sleep(0.01)
            eta.update(r)
        self.assertEqual(eta.last_ratio, 0.5)
        # After 5 updates averaging ~0.01s apart, elapsed ~0.05s
        # ETA at 50% should be ~elapsed
        self.assertGreater(eta.elapsed(), 0.0)
        self.assertGreater(eta.eta_seconds(), 0.0)


if __name__ == "__main__":
    unittest.main()
