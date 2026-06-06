"""Tests for drag & drop support in VectorMapDialog.

We test the pure-logic helpers (is_raster_path, filter_raster_urls)
that do not require a live Qt event loop. The actual Qt event
handlers are also exercised through the helpers' integration.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import MagicMock

from qgis_vector_map.ui.dialog import VectorMapDialog


class IsRasterPathTests(unittest.TestCase):
    """Tests for VectorMapDialog.is_raster_path."""

    def test_tif_extension(self):
        self.assertTrue(VectorMapDialog.is_raster_path("/data/ortho.tif"))

    def test_tiff_extension(self):
        self.assertTrue(VectorMapDialog.is_raster_path("/data/ortho.tiff"))

    def test_uppercase_tif(self):
        self.assertTrue(VectorMapDialog.is_raster_path("/data/ORTHO.TIF"))

    def test_mixed_case(self):
        self.assertTrue(VectorMapDialog.is_raster_path("/data/Ortho.Tif"))

    def test_png(self):
        self.assertTrue(VectorMapDialog.is_raster_path("/data/raster.png"))

    def test_jpg(self):
        self.assertTrue(VectorMapDialog.is_raster_path("/data/raster.jpg"))

    def test_jpeg(self):
        self.assertTrue(VectorMapDialog.is_raster_path("/data/raster.jpeg"))

    def test_bmp(self):
        self.assertTrue(VectorMapDialog.is_raster_path("/data/raster.bmp"))

    def test_gif(self):
        self.assertTrue(VectorMapDialog.is_raster_path("/data/raster.gif"))

    def test_webp(self):
        self.assertTrue(VectorMapDialog.is_raster_path("/data/raster.webp"))

    def test_no_extension_rejected(self):
        self.assertFalse(VectorMapDialog.is_raster_path("/data/raster"))

    def test_unsupported_extension_rejected(self):
        self.assertFalse(VectorMapDialog.is_raster_path("/data/file.txt"))
        self.assertFalse(VectorMapDialog.is_raster_path("/data/file.pdf"))
        self.assertFalse(VectorMapDialog.is_raster_path("/data/file.docx"))
        self.assertFalse(VectorMapDialog.is_raster_path("/data/file.gpkg"))

    def test_empty_string_rejected(self):
        self.assertFalse(VectorMapDialog.is_raster_path(""))

    def test_query_string_stripped(self):
        """Drag-dropped URLs from some managers include ?query at the end."""
        self.assertTrue(
            VectorMapDialog.is_raster_path("/data/raster.tif?some=1")
        )

    def test_fragment_stripped(self):
        self.assertTrue(
            VectorMapDialog.is_raster_path("/data/raster.tif#section")
        )

    def test_dotfile_rejected(self):
        self.assertFalse(VectorMapDialog.is_raster_path("/data/.hidden"))


class FilterRasterUrlsTests(unittest.TestCase):
    """Tests for VectorMapDialog.filter_raster_urls."""

    def _url(self, local_path: str):
        """Build a mock QUrl-like object with toLocalFile()."""
        u = MagicMock()
        u.toLocalFile.return_value = local_path
        return u

    def test_filters_keep_only_rasters(self):
        urls = [
            self._url("/data/raster.tif"),
            self._url("/data/notes.txt"),
            self._url("/data/another.png"),
            self._url("/data/file.pdf"),
            self._url("/data/ortho.TIFF"),
        ]
        result = VectorMapDialog.filter_raster_urls(urls)
        self.assertEqual(
            result,
            [
                "/data/raster.tif",
                "/data/another.png",
                "/data/ortho.TIFF",
            ],
        )

    def test_empty_input(self):
        self.assertEqual(VectorMapDialog.filter_raster_urls([]), [])

    def test_all_unsupported(self):
        urls = [
            self._url("/data/file.txt"),
            self._url("/data/file.pdf"),
        ]
        self.assertEqual(VectorMapDialog.filter_raster_urls(urls), [])

    def test_accepts_string_urls(self):
        """If the input is a list of strings (not QUrl), still works."""
        result = VectorMapDialog.filter_raster_urls(
            ["/data/a.tif", "/data/b.txt", "/data/c.png"]
        )
        self.assertEqual(result, ["/data/a.tif", "/data/c.png"])

    def test_preserves_order(self):
        urls = [
            self._url("/c.tif"),
            self._url("/a.tif"),
            self._url("/b.tif"),
        ]
        result = VectorMapDialog.filter_raster_urls(urls)
        self.assertEqual(result, ["/c.tif", "/a.tif", "/b.tif"])


class RasterExtensionsTests(unittest.TestCase):
    """Tests for the RASTER_EXTENSIONS constant."""

    def test_constant_is_frozenset(self):
        self.assertIsInstance(VectorMapDialog.RASTER_EXTENSIONS, frozenset)

    def test_minimum_required_extensions(self):
        # Sanity check that the most common extensions are present
        for ext in (".tif", ".tiff", ".png", ".jpg", ".jpeg"):
            self.assertIn(ext, VectorMapDialog.RASTER_EXTENSIONS)


class DropEventIntegrationTests(unittest.TestCase):
    """Integration test: simulate a drop and verify the dialog responds.

    These tests mock the QDialog's _update_preview to avoid pulling in
    GDAL during tests.
    """

    def _make_mime(self, paths: list[str]):
        """Build a mock QMimeData that reports the given paths as URLs."""
        mime = MagicMock()
        mime.hasUrls.return_value = True
        mime.urls.return_value = [self._url(p) for p in paths]
        return mime

    def _url(self, local_path: str):
        u = MagicMock()
        u.toLocalFile.return_value = local_path
        return u

    def _make_event(self, paths: list[str]):
        event = MagicMock()
        event.mimeData.return_value = self._make_mime(paths)
        return event

    def _create_dialog_with_mocks(self):
        """Create a dialog with the Qt-dependent parts mocked.

        We bypass __init__ to avoid setting up the real UI.
        """
        dialog = VectorMapDialog.__new__(VectorMapDialog)
        dialog.raster_path_edit = MagicMock()
        dialog.preview_label = MagicMock()
        dialog._update_preview = MagicMock()
        return dialog

    def test_single_file_drop_fills_path(self):
        dialog = self._create_dialog_with_mocks()
        event = self._make_event(["/data/raster.tif"])
        dialog.dropEvent(event)
        dialog.raster_path_edit.setText.assert_called_once_with("/data/raster.tif")
        dialog._update_preview.assert_called_once()
        event.acceptProposedAction.assert_called_once()

    def test_single_file_drop_calls_on_files_dropped_None(self):
        """Single file drop should NOT trigger batch callback."""
        dialog = self._create_dialog_with_mocks()
        dialog.on_files_dropped = MagicMock()
        event = self._make_event(["/data/raster.tif"])
        dialog.dropEvent(event)
        dialog.on_files_dropped.assert_not_called()

    def test_multi_file_drop_fills_first_and_invokes_callback(self):
        dialog = self._create_dialog_with_mocks()
        callback = MagicMock()
        dialog.on_files_dropped = callback
        event = self._make_event(
            ["/data/a.tif", "/data/b.tif", "/data/c.tif"]
        )
        dialog.dropEvent(event)
        # First file populates the field
        dialog.raster_path_edit.setText.assert_called_once_with("/data/a.tif")
        # All files passed to callback
        callback.assert_called_once_with(
            ["/data/a.tif", "/data/b.tif", "/data/c.tif"]
        )

    def test_multi_file_drop_without_callback_does_not_crash(self):
        dialog = self._create_dialog_with_mocks()
        dialog.on_files_dropped = None
        event = self._make_event(["/data/a.tif", "/data/b.tif"])
        # Should not raise
        dialog.dropEvent(event)
        dialog.raster_path_edit.setText.assert_called_once_with("/data/a.tif")

    def test_drop_with_no_raster_files_is_ignored(self):
        dialog = self._create_dialog_with_mocks()
        event = self._make_event(["/data/notes.txt", "/data/file.pdf"])
        dialog.dropEvent(event)
        dialog.raster_path_edit.setText.assert_not_called()
        event.ignore.assert_called_once()

    def test_drop_with_no_urls_is_ignored(self):
        dialog = self._create_dialog_with_mocks()
        event = MagicMock()
        event.mimeData.return_value.hasUrls.return_value = False
        dialog.dropEvent(event)
        dialog.raster_path_edit.setText.assert_not_called()
        event.ignore.assert_called_once()

    def test_callback_exception_does_not_break_drop(self):
        """If the callback raises, the drop should still complete."""
        dialog = self._create_dialog_with_mocks()

        def bad_callback(paths):
            raise RuntimeError("oops")

        dialog.on_files_dropped = bad_callback
        event = self._make_event(["/data/a.tif", "/data/b.tif"])
        # Should not raise despite bad callback
        dialog.dropEvent(event)
        dialog.raster_path_edit.setText.assert_called_once_with("/data/a.tif")


class DragEnterEventTests(unittest.TestCase):
    """Tests for dragEnterEvent."""

    def _url(self, path):
        u = MagicMock()
        u.toLocalFile.return_value = path
        return u

    def _create_dialog_with_mocks(self):
        dialog = VectorMapDialog.__new__(VectorMapDialog)
        return dialog

    def test_accepts_when_raster_present(self):
        dialog = self._create_dialog_with_mocks()
        mime = MagicMock()
        mime.hasUrls.return_value = True
        mime.urls.return_value = [self._url("/data/raster.tif")]
        event = MagicMock()
        event.mimeData.return_value = mime

        dialog.dragEnterEvent(event)
        event.acceptProposedAction.assert_called_once()
        event.ignore.assert_not_called()

    def test_rejects_when_no_urls(self):
        dialog = self._create_dialog_with_mocks()
        mime = MagicMock()
        mime.hasUrls.return_value = False
        event = MagicMock()
        event.mimeData.return_value = mime

        dialog.dragEnterEvent(event)
        event.ignore.assert_called_once()
        event.acceptProposedAction.assert_not_called()

    def test_rejects_when_only_non_rasters(self):
        dialog = self._create_dialog_with_mocks()
        mime = MagicMock()
        mime.hasUrls.return_value = True
        mime.urls.return_value = [self._url("/data/notes.txt")]
        event = MagicMock()
        event.mimeData.return_value = mime

        dialog.dragEnterEvent(event)
        event.ignore.assert_called_once()
        event.acceptProposedAction.assert_not_called()


if __name__ == "__main__":
    unittest.main()
