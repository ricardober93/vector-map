"""Tests for the dialog tooltips."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from qgis_vector_map.core import i18n
from qgis_vector_map.ui import i18n_helper
from qgis_vector_map.ui.dialog import VectorMapDialog


class TooltipTranslationsTests(unittest.TestCase):
    """Verify all tooltip keys exist in both languages."""

    REQUIRED_TIP_KEYS = [
        "tip_input_raster",
        "tip_browse",
        "tip_profile",
        "tip_engine",
        "tip_execution_mode",
        "tip_output_format",
        "tip_output_crs",
        "tip_layer_name",
        "tip_output_file",
        "tip_save_preset",
        "tip_load_preset",
        "tip_vectorize",
        "tip_cancel",
    ]

    def test_all_required_keys_present(self):
        translations = i18n._TRANSLATIONS
        for key in self.REQUIRED_TIP_KEYS:
            self.assertIn(key, translations, f"Missing translation key: {key}")

    def test_all_tooltips_have_english(self):
        for key in self.REQUIRED_TIP_KEYS:
            entry = i18n._TRANSLATIONS.get(key, {})
            self.assertIn("en", entry, f"Missing English for: {key}")
            self.assertTrue(
                len(entry["en"]) > 5,
                f"English tooltip too short for {key}",
            )

    def test_all_tooltips_have_spanish(self):
        for key in self.REQUIRED_TIP_KEYS:
            entry = i18n._TRANSLATIONS.get(key, {})
            self.assertIn("es", entry, f"Missing Spanish for: {key}")
            self.assertTrue(
                len(entry["es"]) > 5,
                f"Spanish tooltip too short for {key}",
            )

    def test_english_and_spanish_differ(self):
        """Make sure translations are not just copies."""
        for key in self.REQUIRED_TIP_KEYS:
            entry = i18n._TRANSLATIONS.get(key, {})
            en = entry.get("en", "")
            es = entry.get("es", "")
            self.assertNotEqual(
                en,
                es,
                f"EN and ES identical for {key} - looks like a copy-paste",
            )


class I18nHelperTests(unittest.TestCase):
    """Tests for the UI i18n_helper module."""

    def setUp(self):
        i18n.set_language(i18n.DEFAULT_LANGUAGE)

    def tearDown(self):
        i18n.set_language(i18n.DEFAULT_LANGUAGE)

    def test_tr_returns_translation(self):
        result = i18n_helper.tr("tip_browse")
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_tr_english(self):
        i18n.set_language("en")
        result = i18n_helper.tr("tip_browse")
        self.assertEqual(result, "Open a file picker to select a raster file.")

    def test_tr_spanish(self):
        i18n.set_language("es")
        result = i18n_helper.tr("tip_browse")
        self.assertEqual(
            result,
            "Abrir un selector de archivos para elegir un ráster.",
        )

    def test_tr_falls_back_when_missing(self):
        result = i18n_helper.tr("nonexistent.tip")
        self.assertEqual(result, "nonexistent.tip")


class ApplyTooltipTests(unittest.TestCase):
    """Tests for VectorMapDialog._apply_tooltip."""

    def test_applies_translated_tooltip_to_widget(self):
        dialog = VectorMapDialog.__new__(VectorMapDialog)
        widget = MagicMock()
        dialog._apply_tooltip(widget, "tip_browse")
        widget.setToolTip.assert_called_once()
        # The tooltip text should not be the key itself
        tooltip_text = widget.setToolTip.call_args[0][0]
        self.assertNotEqual(tooltip_text, "tip_browse")
        self.assertGreater(len(tooltip_text), 5)

    def test_does_nothing_for_missing_key(self):
        dialog = VectorMapDialog.__new__(VectorMapDialog)
        widget = MagicMock()
        dialog._apply_tooltip(widget, "nonexistent.tip.key")
        # setToolTip should NOT be called for unknown keys
        widget.setToolTip.assert_not_called()

    def test_handles_widget_without_settooltip(self):
        """If widget raises on setToolTip, the helper should swallow it."""
        dialog = VectorMapDialog.__new__(VectorMapDialog)
        widget = MagicMock()
        widget.setToolTip.side_effect = RuntimeError("no tooltip support")
        # Should not raise
        dialog._apply_tooltip(widget, "tip_browse")


if __name__ == "__main__":
    unittest.main()
