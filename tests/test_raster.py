"""Unit tests for raster loading fallbacks and large-image handling."""

from __future__ import annotations

import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from qgis_vector_map.core.errors import DependencyError
from qgis_vector_map.core.raster import MAX_PILLOW_IMAGE_PIXELS, RasterFrame


class _FakeArray2D:
    ndim = 2

    def __init__(self, rows: list[list[int]]) -> None:
        self._rows = rows

    def tolist(self) -> list[list[int]]:
        return self._rows


class _FakeDataset:
    def __init__(self, rows: list[list[int]]) -> None:
        self._rows = rows

    def ReadAsArray(self) -> _FakeArray2D:
        return _FakeArray2D(self._rows)

    def GetProjection(self) -> str:
        return "EPSG:4326"

    def GetGeoTransform(self, can_return_null: bool = True) -> tuple[float, ...]:
        del can_return_null
        return (0.0, 1.0, 0.0, 0.0, 0.0, -1.0)


class _FakePillowImage:
    MAX_IMAGE_PIXELS = 10

    def __init__(
        self,
        *,
        size: tuple[int, int],
        pixels: dict[tuple[int, int], tuple[int, int, int]],
    ) -> None:
        self.size = size
        self._pixels = pixels

    def open(self, path: Path) -> _FakeImageContext:
        del path
        return _FakeImageContext(self)

    def convert(self, mode: str) -> _FakePillowImage:
        if mode != "RGB":
            raise AssertionError(f"Unexpected conversion mode: {mode}")
        return self

    def getpixel(self, coords: tuple[int, int]) -> tuple[int, int, int]:
        return self._pixels[coords]


class _FakeImageContext:
    def __init__(self, image: _FakePillowImage) -> None:
        self._image = image

    def __enter__(self) -> _FakePillowImage:
        return self._image

    def __exit__(self, exc_type, exc, tb) -> bool:
        del exc_type, exc, tb
        return False


class _RaisingPillowImage:
    MAX_IMAGE_PIXELS = 25

    def __init__(self, exc_type: type[Exception]) -> None:
        self._exc_type = exc_type

    def open(self, path: Path) -> _RaisingImageContext:
        del path
        return _RaisingImageContext(self._exc_type("synthetic pillow failure"))


class _RaisingImageContext:
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    def __enter__(self):
        raise self._exc

    def __exit__(self, exc_type, exc, tb) -> bool:
        del exc_type, exc, tb
        return False


class RasterFrameLoadTests(unittest.TestCase):
    def _make_temp_path(self) -> Path:
        temp_handle = tempfile.NamedTemporaryFile(suffix=".tif", delete=False)
        temp_handle.close()
        self.addCleanup(lambda: Path(temp_handle.name).unlink(missing_ok=True))
        return Path(temp_handle.name)

    def test_prefers_gdal_for_disk_rasters(self) -> None:
        path = self._make_temp_path()
        fake_gdal = types.SimpleNamespace(Open=lambda source: _FakeDataset([[1, 2], [3, 4]]))
        fake_osgeo = types.SimpleNamespace(gdal=fake_gdal)

        def _unexpected_pillow_import(name: str, *args, **kwargs):
            if name == "PIL":
                raise AssertionError("Pillow import should not be reached when GDAL succeeds.")
            return original_import(name, *args, **kwargs)

        original_import = __import__
        with patch("builtins.__import__", side_effect=_unexpected_pillow_import):
            with patch.dict(sys.modules, {"osgeo": fake_osgeo}):
                raster = RasterFrame.load(path)

        self.assertEqual(raster.width, 2)
        self.assertEqual(raster.height, 2)
        self.assertEqual(raster.bands, 1)
        self.assertEqual(raster.pixel(1, 1), 4)

    def test_falls_back_to_pillow_and_restores_limit(self) -> None:
        path = self._make_temp_path()
        fake_image = _FakePillowImage(
            size=(2, 1),
            pixels={(0, 0): (10, 20, 30), (1, 0): (40, 50, 60)},
        )
        fake_pil = types.SimpleNamespace(Image=fake_image)

        original_limit = fake_image.MAX_IMAGE_PIXELS
        with patch.dict(sys.modules, {"PIL": fake_pil}, clear=False):
            sys.modules.pop("osgeo", None)
            raster = RasterFrame.load(path)

        self.assertEqual(raster.width, 2)
        self.assertEqual(raster.height, 1)
        self.assertEqual(raster.pixel(0, 0), (10, 20, 30))
        self.assertEqual(fake_image.MAX_IMAGE_PIXELS, original_limit)

    def test_raises_actionable_error_when_gdal_and_pillow_fail(self) -> None:
        path = self._make_temp_path()
        decompression_error = type("DecompressionBombError", (RuntimeError,), {})
        fake_pil = types.SimpleNamespace(Image=_RaisingPillowImage(decompression_error))

        with patch.dict(sys.modules, {"PIL": fake_pil}, clear=False):
            sys.modules.pop("osgeo", None)
            with self.assertRaises(DependencyError) as caught:
                RasterFrame.load(path)

        message = str(caught.exception)
        self.assertIn("GDAL path error", message)
        self.assertIn("Pillow fallback error", message)
        self.assertIn(f"{MAX_PILLOW_IMAGE_PIXELS:,}", message)

    def test_small_pillow_load_preserves_existing_behavior(self) -> None:
        path = self._make_temp_path()
        fake_image = _FakePillowImage(
            size=(1, 2),
            pixels={(0, 0): (0, 0, 0), (0, 1): (255, 255, 255)},
        )
        fake_pil = types.SimpleNamespace(Image=fake_image)

        with patch.dict(sys.modules, {"PIL": fake_pil}, clear=False):
            sys.modules.pop("osgeo", None)
            raster = RasterFrame.load(path)

        self.assertEqual(raster.rgb_matrix(), (((0, 0, 0),), ((255, 255, 255),)))


if __name__ == "__main__":
    unittest.main()
