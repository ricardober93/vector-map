"""Tests for UX improvements in VectorizeImageAlgorithm."""

from __future__ import annotations

import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock


class SmartNamingTests(unittest.TestCase):
    """Tests for smart output layer naming."""

    def test_generate_default_layer_name_format(self):
        """Layer name should follow expected format with profile and timestamp."""
        from qgis_vector_map.algorithms.vectorize_image_algorithm import VectorizeImageAlgorithm

        profile_ids = [
            "regional-high-precision",
            "edge-high-precision",
            "linear-high-precision",
        ]

        for profile_id in profile_ids:
            name = VectorizeImageAlgorithm._generate_default_layer_name(profile_id)

            # Should start with "vectorized_"
            self.assertTrue(name.startswith("vectorized_"), f"Name '{name}' should start with 'vectorized_'")

            # Should contain profile short name
            expected_short = profile_id.replace("-high-precision", "").replace("-", "_")
            self.assertIn(expected_short, name, f"Name '{name}' should contain '{expected_short}'")

            # Should contain timestamp
            timestamp_format = "%Y%m%d_%H%M%S"
            timestamp_start = datetime.now().strftime("%Y%m%d")
            self.assertTrue(
                any(part.startswith(timestamp_start) for part in name.split("_")),
                f"Name '{name}' should contain timestamp starting with '{timestamp_start}'"
            )

    def test_generate_default_layer_name_unique(self):
        """Generated names should contain timestamp."""
        from qgis_vector_map.algorithms.vectorize_image_algorithm import VectorizeImageAlgorithm

        profile_id = "regional-high-precision"
        name = VectorizeImageAlgorithm._generate_default_layer_name(profile_id)

        # Should contain timestamp
        self.assertIn("2026", name, f"Name '{name}' should contain year 2026")
        # Should be a valid format
        self.assertTrue(name.startswith("vectorized_regional_"), f"Name '{name}' should follow format")

    def test_layer_name_contains_profile_short(self):
        """Profile short names should be: regional, edge, linear."""
        from qgis_vector_map.algorithms.vectorize_image_algorithm import VectorizeImageAlgorithm

        test_cases = [
            ("regional-high-precision", "regional"),
            ("edge-high-precision", "edge"),
            ("linear-high-precision", "linear"),
        ]

        for profile_id, expected_short in test_cases:
            name = VectorizeImageAlgorithm._generate_default_layer_name(profile_id)
            self.assertIn(expected_short, name, f"Name '{name}' should contain '{expected_short}'")


class TiledValidationTests(unittest.TestCase):
    """Tests for tiled execution mode validation."""

    def setUp(self):
        self.alg = self._make_algorithm()

    def _make_algorithm(self):
        """Create algorithm instance for testing."""
        from qgis_vector_map.algorithms.vectorize_image_algorithm import VectorizeImageAlgorithm
        return VectorizeImageAlgorithm()

    def test_tiled_accepted_for_regional(self):
        """Tiled mode should be accepted for regional profile."""
        try:
            self.alg._validate_execution_mode_for_profile("tiled", "regional-high-precision")
            # No exception means validation passed
        except Exception as exc:
            self.fail(f"Tiled should be accepted for regional profile, got: {exc}")

    def test_tiled_rejected_for_edge(self):
        """Tiled mode should be rejected for edge profile."""
        from qgis_vector_map.algorithms.vectorize_image_algorithm import _QgsProcessingException

        with self.assertRaises(_QgsProcessingException) as ctx:
            self.alg._validate_execution_mode_for_profile("tiled", "edge-high-precision")

        self.assertIn("regional-high-precision", str(ctx.exception))
        self.assertIn("edge", str(ctx.exception).lower())

    def test_tiled_rejected_for_linear(self):
        """Tiled mode should be rejected for linear profile."""
        from qgis_vector_map.algorithms.vectorize_image_algorithm import _QgsProcessingException

        with self.assertRaises(_QgsProcessingException) as ctx:
            self.alg._validate_execution_mode_for_profile("tiled", "linear-high-precision")

        self.assertIn("regional-high-precision", str(ctx.exception))
        self.assertIn("linear", str(ctx.exception).lower())

    def test_auto_accepted_for_all_profiles(self):
        """Auto mode should be accepted for all profiles."""
        profiles = ["regional-high-precision", "edge-high-precision", "linear-high-precision"]
        for profile in profiles:
            try:
                self.alg._validate_execution_mode_for_profile("auto", profile)
            except Exception as exc:
                self.fail(f"Auto should be accepted for {profile}, got: {exc}")

    def test_strict_accepted_for_all_profiles(self):
        """Strict mode should be accepted for all profiles."""
        profiles = ["regional-high-precision", "edge-high-precision", "linear-high-precision"]
        for profile in profiles:
            try:
                self.alg._validate_execution_mode_for_profile("strict", profile)
            except Exception as exc:
                self.fail(f"Strict should be accepted for {profile}, got: {exc}")


class OutputFormatParsingTests(unittest.TestCase):
    """Tests for output format parsing from enum."""

    def test_resolve_output_format_auto(self):
        """Auto format should resolve correctly."""
        from qgis_vector_map.algorithms.vectorize_image_algorithm import VectorizeImageAlgorithm

        alg = VectorizeImageAlgorithm()
        mock_params = {"OUTPUT_FORMAT": 0}
        mock_context = MagicMock()

        result = alg._resolve_output_format(mock_params, mock_context)

        self.assertEqual(result, "auto")

    def test_resolve_output_format_gpkg(self):
        """GeoPackage format should resolve correctly."""
        from qgis_vector_map.algorithms.vectorize_image_algorithm import VectorizeImageAlgorithm

        alg = VectorizeImageAlgorithm()
        mock_params = {"OUTPUT_FORMAT": 1}
        mock_context = MagicMock()

        result = alg._resolve_output_format(mock_params, mock_context)

        self.assertEqual(result, "gpkg")

    def test_resolve_output_format_geojson(self):
        """GeoJSON format should resolve correctly."""
        from qgis_vector_map.algorithms.vectorize_image_algorithm import VectorizeImageAlgorithm

        alg = VectorizeImageAlgorithm()
        mock_params = {"OUTPUT_FORMAT": 2}
        mock_context = MagicMock()

        result = alg._resolve_output_format(mock_params, mock_context)

        self.assertEqual(result, "geojson")

    def test_resolve_output_format_shp(self):
        """Shapefile format should resolve correctly."""
        from qgis_vector_map.algorithms.vectorize_image_algorithm import VectorizeImageAlgorithm

        alg = VectorizeImageAlgorithm()
        mock_params = {"OUTPUT_FORMAT": 3}
        mock_context = MagicMock()

        result = alg._resolve_output_format(mock_params, mock_context)

        self.assertEqual(result, "shp")

    def test_resolve_output_format_fallback(self):
        """Invalid index should fallback to 'auto'."""
        from qgis_vector_map.algorithms.vectorize_image_algorithm import VectorizeImageAlgorithm

        alg = VectorizeImageAlgorithm()
        mock_params = {"OUTPUT_FORMAT": 99}
        mock_context = MagicMock()

        result = alg._resolve_output_format(mock_params, mock_context)

        self.assertEqual(result, "auto")


class BackwardCompatibilityTests(unittest.TestCase):
    """Tests for backward compatibility with string-based parameters."""

    def test_parse_output_format_parameter_auto(self):
        """String parameter 'auto' should be parsed correctly."""
        from qgis_vector_map.algorithms.vectorize_image_algorithm import VectorizeImageAlgorithm

        params = {"OUTPUT_FORMAT": "auto"}
        result = VectorizeImageAlgorithm._parse_output_format_parameter(params, None)

        self.assertEqual(result, "auto")

    def test_parse_output_format_parameter_gpkg(self):
        """String parameter 'gpkg' should be parsed correctly."""
        from qgis_vector_map.algorithms.vectorize_image_algorithm import VectorizeImageAlgorithm

        params = {"OUTPUT_FORMAT": "gpkg"}
        result = VectorizeImageAlgorithm._parse_output_format_parameter(params, None)

        self.assertEqual(result, "gpkg")

    def test_parse_output_format_parameter_geojson(self):
        """String parameter 'geojson' should be parsed correctly."""
        from qgis_vector_map.algorithms.vectorize_image_algorithm import VectorizeImageAlgorithm

        params = {"OUTPUT_FORMAT": "geojson"}
        result = VectorizeImageAlgorithm._parse_output_format_parameter(params, None)

        self.assertEqual(result, "geojson")

    def test_parse_output_format_parameter_invalid(self):
        """Invalid format should fallback to 'auto'."""
        from qgis_vector_map.algorithms.vectorize_image_algorithm import VectorizeImageAlgorithm

        params = {"OUTPUT_FORMAT": "invalid_format"}
        result = VectorizeImageAlgorithm._parse_output_format_parameter(params, None)

        self.assertEqual(result, "auto")


if __name__ == "__main__":
    unittest.main()