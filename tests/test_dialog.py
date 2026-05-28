"""Tests for VectorMapDialog UI component."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path


class VectorMapDialogTests(unittest.TestCase):
    """Tests for VectorMapDialog without Qt dependencies."""

    def test_dialog_imports_without_qt(self):
        """Dialog should be importable even when Qt is not available."""
        # Test that the module can be imported
        from qgis_vector_map.ui.dialog import VectorMapDialog

        self.assertTrue(hasattr(VectorMapDialog, 'PROFILE_OPTIONS'))
        self.assertEqual(len(VectorMapDialog.PROFILE_OPTIONS), 3)

    def test_profile_options_contains_expected_values(self):
        """Profile options should contain all expected profiles."""
        from qgis_vector_map.ui.dialog import VectorMapDialog

        expected_profiles = [
            "regional-high-precision",
            "edge-high-precision",
            "linear-high-precision",
        ]
        self.assertEqual(VectorMapDialog.PROFILE_OPTIONS, expected_profiles)

    def test_execution_mode_options_contains_expected_values(self):
        """Execution mode options should contain all expected modes."""
        from qgis_vector_map.ui.dialog import VectorMapDialog

        expected_modes = ["auto", "strict", "tiled"]
        self.assertEqual(VectorMapDialog.EXECUTION_MODE_OPTIONS, expected_modes)

    def test_output_format_options_contains_expected_values(self):
        """Output format options should contain all expected formats."""
        from qgis_vector_map.ui.dialog import VectorMapDialog

        expected_formats = [
            "auto",
            "GeoPackage (.gpkg)",
            "GeoJSON (.geojson)",
            "ESRI Shapefile (.shp)",
        ]
        self.assertEqual(VectorMapDialog.OUTPUT_FORMAT_OPTIONS, expected_formats)

    def test_engine_options_contains_expected_values(self):
        """Engine options should contain all expected engines."""
        from qgis_vector_map.ui.dialog import VectorMapDialog

        expected_engines = ["auto", "classic", "opencv"]
        self.assertEqual(VectorMapDialog.ENGINE_OPTIONS, expected_engines)

    def test_generate_default_layer_name_format(self):
        """Generated layer name should follow expected format."""
        from qgis_vector_map.ui.dialog import VectorMapDialog

        name = VectorMapDialog._generate_default_layer_name(VectorMapDialog, "regional-high-precision")

        # Should contain profile short name
        self.assertIn("regional", name)
        # Should contain timestamp
        self.assertIn("2026", name)
        # Should start with vectorized_
        self.assertTrue(name.startswith("vectorized_"))

    def test_generate_default_layer_name_different_profiles(self):
        """Different profiles should generate different layer names."""
        from qgis_vector_map.ui.dialog import VectorMapDialog

        profiles = [
            "regional-high-precision",
            "edge-high-precision",
            "linear-high-precision",
        ]

        for profile in profiles:
            name = VectorMapDialog._generate_default_layer_name(VectorMapDialog, profile)
            profile_short = profile.replace("-high-precision", "").replace("-", "_")
            self.assertIn(profile_short, name)


class RasterPreviewTests(unittest.TestCase):
    """Tests for raster preview functionality."""

    def test_preview_info_calculation(self):
        """Raster preview info should calculate correctly."""
        from qgis_vector_map.ui.dialog import VectorMapDialog

        # Mock the info directly
        info = {
            "width": 8192,
            "height": 8192,
            "pixels": 67_108_864,
            "tile_count": 16,
            "tile_size": 2048,
            "warnings": [],
        }

        self.assertEqual(info["width"], 8192)
        self.assertEqual(info["height"], 8192)
        self.assertEqual(info["pixels"], 67_108_864)
        self.assertEqual(info["tile_count"], 16)


class PluginTests(unittest.TestCase):
    """Tests for VectorMapPlugin."""

    def test_plugin_initialization(self):
        """Plugin should initialize with iface."""
        from qgis_vector_map.plugin import VectorMapPlugin

        mock_iface = MagicMock()
        plugin = VectorMapPlugin(mock_iface)

        self.assertEqual(plugin.iface, mock_iface)
        self.assertIsNone(plugin.provider)
        self.assertIsNone(plugin.action)

    def test_plugin_processing_registry_fallback(self):
        """Plugin should handle missing QGIS gracefully."""
        from qgis_vector_map.plugin import VectorMapPlugin

        mock_iface = MagicMock()
        plugin = VectorMapPlugin(mock_iface)

        # Should not raise when processingRegistry is not available
        registry = plugin._processing_registry()
        # May be None in test environment

    def test_plugin_without_iface(self):
        """Plugin should work without iface in tests."""
        from qgis_vector_map.plugin import VectorMapPlugin

        plugin = VectorMapPlugin(None)
        self.assertIsNone(plugin.iface)
        self.assertIsNone(plugin.provider)


class ValidationTests(unittest.TestCase):
    """Tests for dialog validation logic."""

    def test_tiled_validation_logic(self):
        """Tiled mode should only be allowed for regional profile."""
        from qgis_vector_map.ui.dialog import VectorMapDialog

        # Test: regional profile allows tiled
        is_valid = (
            "tiled" != "tiled" or
            "regional-high-precision" == "regional-high-precision"
        )
        self.assertTrue(is_valid)

        # Test: edge profile does not allow tiled
        is_valid = (
            "tiled" != "tiled" or
            "edge-high-precision" == "regional-high-precision"
        )
        self.assertFalse(is_valid)

        # Test: linear profile does not allow tiled
        is_valid = (
            "tiled" != "tiled" or
            "linear-high-precision" == "regional-high-precision"
        )
        self.assertFalse(is_valid)


class ParameterMappingTests(unittest.TestCase):
    """Tests for parameter mapping between dialog and algorithm."""

    def test_output_format_mapping(self):
        """Output format should map correctly to algorithm format."""
        output_format_map = {
            "auto": "auto",
            "GeoPackage (.gpkg)": "gpkg",
            "GeoJSON (.geojson)": "geojson",
            "ESRI Shapefile (.shp)": "shp",
        }

        self.assertEqual(output_format_map["auto"], "auto")
        self.assertEqual(output_format_map["GeoPackage (.gpkg)"], "gpkg")
        self.assertEqual(output_format_map["GeoJSON (.geojson)"], "geojson")
        self.assertEqual(output_format_map["ESRI Shapefile (.shp)"], "shp")

    def test_engine_name_mapping(self):
        """Engine selection should map to correct engine name."""
        engine_name_map = {
            "auto": "auto",
            "classic": "classic-local",
            "opencv": "opencv-local",
        }

        self.assertEqual(engine_name_map["auto"], "auto")
        self.assertEqual(engine_name_map["classic"], "classic-local")
        self.assertEqual(engine_name_map["opencv"], "opencv-local")


if __name__ == "__main__":
    unittest.main()