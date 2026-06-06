"""Tests for the i18n translation system."""

from __future__ import annotations

import unittest

from qgis_vector_map.core import i18n
from qgis_vector_map.core.i18n import (
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    available_languages,
    get_language,
    register_translation,
    set_language,
    t,
)


class I18nBasicsTests(unittest.TestCase):
    """Basic tests for the translation function."""

    def setUp(self):
        # Reset to default before each test
        set_language(DEFAULT_LANGUAGE)

    def tearDown(self):
        set_language(DEFAULT_LANGUAGE)

    def test_default_language_is_english(self):
        self.assertEqual(get_language(), "en")

    def test_supported_languages(self):
        self.assertIn("en", SUPPORTED_LANGUAGES)
        self.assertIn("es", SUPPORTED_LANGUAGES)

    def test_available_languages(self):
        self.assertEqual(available_languages(), ("en", "es"))

    def test_translate_to_english(self):
        set_language("en")
        self.assertEqual(t("plugin_name"), "Vector Map")

    def test_translate_to_spanish(self):
        set_language("es")
        self.assertEqual(t("plugin_name"), "Vector Map")
        # Different translation for a different message
        self.assertEqual(t("dialog_title"), "Vectorizar Imagen")

    def test_unknown_key_returns_key(self):
        self.assertEqual(t("nonexistent.key"), "nonexistent.key")

    def test_format_kwargs(self):
        set_language("en")
        text = t("err_file_not_found", path="/tmp/foo.tif")
        self.assertEqual(text, "File not found: /tmp/foo.tif")

    def test_format_kwargs_spanish(self):
        set_language("es")
        text = t("err_file_not_found", path="/tmp/foo.tif")
        self.assertEqual(text, "Archivo no encontrado: /tmp/foo.tif")

    def test_format_with_multiple_kwargs(self):
        set_language("en")
        text = t(
            "err_cancelled",
            stage="vectorize",
            after="tile 5/16",
        )
        self.assertIn("vectorize", text)
        self.assertIn("tile 5/16", text)

    def test_short_alias(self):
        set_language("es")
        # The _ alias should equal t
        self.assertEqual(i18n._("dialog_title"), t("dialog_title"))

    def test_set_language_with_unknown_code_ignored(self):
        set_language("en")
        set_language("fr")  # not supported, should be ignored
        self.assertEqual(get_language(), "en")

    def test_set_language_roundtrip(self):
        set_language("es")
        self.assertEqual(get_language(), "es")
        set_language("en")
        self.assertEqual(get_language(), "en")


class I18nRegistrationTests(unittest.TestCase):
    """Tests for register_translation."""

    def setUp(self):
        set_language(DEFAULT_LANGUAGE)

    def tearDown(self):
        set_language(DEFAULT_LANGUAGE)

    def test_register_new_key(self):
        register_translation("my.new.key", en="Hello", es="Hola")
        self.assertEqual(t("my.new.key"), "Hello")
        set_language("es")
        self.assertEqual(t("my.new.key"), "Hola")

    def test_register_existing_key_raises_without_overwrite(self):
        with self.assertRaises(ValueError):
            register_translation("plugin_name", en="x", es="y")

    def test_register_existing_key_with_overwrite(self):
        register_translation(
            "plugin_name", en="New Name", es="Nuevo Nombre", overwrite=True
        )
        set_language("en")
        self.assertEqual(t("plugin_name"), "New Name")
        set_language("es")
        self.assertEqual(t("plugin_name"), "Nuevo Nombre")


class I18nFallbackTests(unittest.TestCase):
    """Tests for translation fallback behavior."""

    def setUp(self):
        set_language(DEFAULT_LANGUAGE)

    def tearDown(self):
        set_language(DEFAULT_LANGUAGE)

    def test_falls_back_to_english_when_spanish_missing(self):
        # Register a key that only has English
        _TRANSLATIONS = i18n._TRANSLATIONS
        original = _TRANSLATIONS.get("test.only.english")
        _TRANSLATIONS["test.only.english"] = {"en": "English only"}
        try:
            set_language("es")
            self.assertEqual(t("test.only.english"), "English only")
        finally:
            if original is None:
                _TRANSLATIONS.pop("test.only.english", None)
            else:
                _TRANSLATIONS["test.only.english"] = original

    def test_format_with_missing_kwargs_returns_raw(self):
        # If a translated string references a placeholder not in kwargs,
        # .format() raises KeyError and we return the raw text.
        set_language("en")
        text = t("err_file_not_found")  # no 'path' kwarg
        # Should still be a string, not raise
        self.assertIsInstance(text, str)
        self.assertIn("{path}", text)


class I18nProgressMessagesTests(unittest.TestCase):
    """Tests for the ETA / progress message translations."""

    def setUp(self):
        set_language(DEFAULT_LANGUAGE)

    def tearDown(self):
        set_language(DEFAULT_LANGUAGE)

    def test_tile_progress_english(self):
        set_language("en")
        self.assertEqual(t("progress_tile", current=5, total=16), "Tile 5/16")

    def test_tile_progress_spanish(self):
        set_language("es")
        self.assertEqual(t("progress_tile", current=5, total=16), "Tesela 5/16")

    def test_elapsed_eta_format(self):
        set_language("en")
        self.assertEqual(t("progress_elapsed", time="1:23"), "elapsed 1:23")
        set_language("es")
        self.assertEqual(t("progress_elapsed", time="1:23"), "transcurrido 1:23")

    def test_batch_summary(self):
        set_language("en")
        text = t("batch_summary", succeeded=3, total=5, failed=2)
        self.assertEqual(text, "3/5 succeeded, 2 failed")


if __name__ == "__main__":
    unittest.main()
