"""Unit tests for raster loading fallbacks and large-image handling."""

from __future__ import annotations

import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from qgis_vector_map.core.errors import ConfigurationError, DependencyError
from qgis_vector_map.core.raster import MAX_PILLOW_IMAGE_PIXELS, RasterFrame


class _FakeArray2D:
    ndim = 2

    def __init__(self, rows: list[list[int]]) -> None:
        self._rows = rows

    def tolist(self) -> list[list[int]]:
        return self._rows


class _FakeArray3D:
    ndim = 3

    def __init__(self, planes: list[list[list[int]]]) -> None:
        self._planes = planes
        self.shape = (len(planes), len(planes[0]), len(planes[0][0]))

    def tolist(self) -> list[list[list[int]]]:
        return self._planes


class _FakeBand:
    def __init__(self, data_type: int) -> None:
        self.DataType = data_type


class _FakeDataset:
    RasterXSize: int
    RasterYSize: int
    RasterCount: int

    def __init__(
        self,
        rows: list[list[int]],
        *,
        bands: int = 1,
        data_type: int = 1,
    ) -> None:
        self._rows = rows
        self._bands = bands
        self._data_type = data_type
        self.RasterYSize = len(rows)
        self.RasterXSize = len(rows[0]) if rows else 0
        self.RasterCount = bands

    def ReadAsArray(
        self,
        xoff: int = 0,
        yoff: int = 0,
        xsize: int | None = None,
        ysize: int | None = None,
    ):
        del xoff
        if xsize is None and ysize is None:
            xsize = self.RasterXSize
            ysize = self.RasterYSize
        if xsize is None or ysize is None:
            raise AssertionError("Both xsize and ysize are required for window reads.")
        sliced_rows = [row[:xsize] for row in self._rows[yoff : yoff + ysize]]
        if self._bands == 1:
            return _FakeArray2D(sliced_rows)
        stacked = [sliced_rows for _ in range(self._bands)]
        return _FakeArray3D(stacked)

    def GetRasterBand(self, index: int) -> _FakeBand:
        if index <= 0:
            raise AssertionError("GDAL bands are 1-based.")
        return _FakeBand(self._data_type)

    def ReadAsArrayNoWindow(self) -> _FakeArray2D:
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
        fake_gdal = types.SimpleNamespace(
            Open=lambda source: _FakeDataset([[1, 2], [3, 4]]),
            GetDataTypeSize=lambda data_type: 8 if data_type == 1 else 32,
        )
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
        fake_gdal = types.SimpleNamespace(
            Open=lambda source: (_ for _ in ()).throw(ConfigurationError("synthetic gdal error")),
            GetDataTypeSize=lambda data_type: 8,
        )
        fake_osgeo = types.SimpleNamespace(gdal=fake_gdal)

        with patch.dict(sys.modules, {"PIL": fake_pil, "osgeo": fake_osgeo}, clear=False):
            with self.assertRaises(DependencyError) as caught:
                RasterFrame.load(path)

        message = str(caught.exception)
        self.assertIn("GDAL path error", message)
        self.assertIn("Pillow fallback error", message)
        self.assertIn(f"{MAX_PILLOW_IMAGE_PIXELS:,}", message)

    def test_preflight_rejects_oversized_raster_before_read(self) -> None:
        path = self._make_temp_path()

        class _OversizedDataset(_FakeDataset):
            def __init__(self) -> None:
                super().__init__([[0]])
                self.RasterXSize = 50_000
                self.RasterYSize = 50_000
                self.RasterCount = 4

            def ReadAsArray(
                self,
                xoff: int = 0,
                yoff: int = 0,
                xsize: int | None = None,
                ysize: int | None = None,
            ):
                raise AssertionError("ReadAsArray should not run after preflight rejection.")

        fake_gdal = types.SimpleNamespace(
            Open=lambda source: _OversizedDataset(),
            GetDataTypeSize=lambda data_type: 16,
        )
        fake_osgeo = types.SimpleNamespace(gdal=fake_gdal)

        with patch.dict(sys.modules, {"osgeo": fake_osgeo}, clear=False):
            with self.assertRaises(ConfigurationError) as caught:
                RasterFrame.load(path)

        self.assertIn("Raster preflight aborted", str(caught.exception))
        self.assertIn("Recommended actions", str(caught.exception))
        self.assertIn("Suggested linear reduction factor", str(caught.exception))
        self.assertIn("estimated tile grid", str(caught.exception))

    def test_preflight_error_includes_profile_hint_for_edge_mode(self) -> None:
        path = self._make_temp_path()

        class _OversizedDataset(_FakeDataset):
            def __init__(self) -> None:
                super().__init__([[0]])
                self.RasterXSize = 50_000
                self.RasterYSize = 50_000
                self.RasterCount = 4

            def ReadAsArray(
                self,
                xoff: int = 0,
                yoff: int = 0,
                xsize: int | None = None,
                ysize: int | None = None,
            ):
                raise AssertionError("ReadAsArray should not run after preflight rejection.")

        fake_gdal = types.SimpleNamespace(
            Open=lambda source: _OversizedDataset(),
            GetDataTypeSize=lambda data_type: 16,
        )
        fake_osgeo = types.SimpleNamespace(gdal=fake_gdal)

        options = RasterFrame.LoadOptions.from_parameters({}, profile_mode="edge")
        with patch.dict(sys.modules, {"osgeo": fake_osgeo}, clear=False):
            with self.assertRaises(ConfigurationError) as caught:
                RasterFrame.load(path, options=options)

        self.assertIn("Switch to 'regional-high-precision'", str(caught.exception))

    def test_preflight_error_omits_profile_hint_for_regional_mode(self) -> None:
        path = self._make_temp_path()

        class _OversizedDataset(_FakeDataset):
            def __init__(self) -> None:
                super().__init__([[0]])
                self.RasterXSize = 50_000
                self.RasterYSize = 50_000
                self.RasterCount = 4

            def ReadAsArray(
                self,
                xoff: int = 0,
                yoff: int = 0,
                xsize: int | None = None,
                ysize: int | None = None,
            ):
                raise AssertionError("ReadAsArray should not run after preflight rejection.")

        fake_gdal = types.SimpleNamespace(
            Open=lambda source: _OversizedDataset(),
            GetDataTypeSize=lambda data_type: 16,
        )
        fake_osgeo = types.SimpleNamespace(gdal=fake_gdal)

        options = RasterFrame.LoadOptions.from_parameters({}, profile_mode="regional")
        with patch.dict(sys.modules, {"osgeo": fake_osgeo}, clear=False):
            with self.assertRaises(ConfigurationError) as caught:
                RasterFrame.load(path, options=options)

        self.assertNotIn("Switch to 'regional-high-precision'", str(caught.exception))

    def test_load_options_defaults_to_strict_memory_policy(self) -> None:
        options = RasterFrame.LoadOptions.from_parameters({"chunk_size": 1024}, profile_mode="regional")
        self.assertEqual(options.memory_policy, "strict")

    def test_load_options_accepts_known_memory_policies(self) -> None:
        for policy in ("strict", "expert-override", "regional-tiles"):
            options = RasterFrame.LoadOptions.from_parameters(
                {"memory_policy": policy},
                profile_mode="regional",
            )
            self.assertEqual(options.memory_policy, policy)

    def test_load_options_rejects_unknown_memory_policy(self) -> None:
        with self.assertRaises(ConfigurationError) as caught:
            RasterFrame.LoadOptions.from_parameters({"memory_policy": "aggressive"}, profile_mode="regional")
        self.assertIn("memory_policy", str(caught.exception))

    def test_memory_error_skips_pillow_fallback(self) -> None:
        path = self._make_temp_path()

        class _MemoryDataset(_FakeDataset):
            def ReadAsArray(
                self,
                xoff: int = 0,
                yoff: int = 0,
                xsize: int | None = None,
                ysize: int | None = None,
            ):
                del xoff, yoff, xsize, ysize
                raise MemoryError()

        fake_gdal = types.SimpleNamespace(
            Open=lambda source: _MemoryDataset([[1, 2], [3, 4]], bands=3),
            GetDataTypeSize=lambda data_type: 8,
        )
        fake_osgeo = types.SimpleNamespace(gdal=fake_gdal)
        fake_pillow = _FakePillowImage(
            size=(1, 1),
            pixels={(0, 0): (0, 0, 0)},
        )
        fake_pil = types.SimpleNamespace(Image=fake_pillow)

        with patch.dict(sys.modules, {"osgeo": fake_osgeo, "PIL": fake_pil}, clear=False):
            with self.assertRaises(DependencyError) as caught:
                RasterFrame.load(path)

        self.assertIn("Pillow fallback was skipped", str(caught.exception))

    def test_regional_mode_uses_chunked_gdal_loading(self) -> None:
        path = self._make_temp_path()
        read_calls: list[tuple[int, int, int, int] | str] = []

        class _WindowDataset(_FakeDataset):
            def ReadAsArray(
                self,
                xoff: int = 0,
                yoff: int = 0,
                xsize: int | None = None,
                ysize: int | None = None,
            ):
                if xsize is None or ysize is None:
                    read_calls.append("full")
                else:
                    read_calls.append((xoff, yoff, xsize, ysize))
                return super().ReadAsArray(xoff, yoff, xsize, ysize)

        fake_gdal = types.SimpleNamespace(
            Open=lambda source: _WindowDataset(
                [
                    [10, 20, 30, 40],
                    [50, 60, 70, 80],
                    [90, 100, 110, 120],
                    [130, 140, 150, 160],
                ],
                bands=1,
            ),
            GetDataTypeSize=lambda data_type: 8,
        )
        fake_osgeo = types.SimpleNamespace(gdal=fake_gdal)
        options = RasterFrame.LoadOptions.from_parameters(
            {"chunk_size": 2},
            profile_mode="regional",
        )

        with patch.dict(sys.modules, {"osgeo": fake_osgeo}, clear=False):
            raster = RasterFrame.load(path, options=options)

        self.assertEqual(raster.width, 4)
        self.assertEqual(raster.height, 4)
        self.assertEqual(raster.bands, 1)
        self.assertEqual(raster.metadata.get("load_strategy"), "gdal-regional-chunked")
        self.assertNotIn("full", read_calls)
        self.assertIn((0, 0, 4, 2), read_calls)
        self.assertIn((0, 2, 4, 2), read_calls)

    def test_regional_chunked_two_band_uses_zero_for_missing_blue_channel(self) -> None:
        path = self._make_temp_path()
        # Expected grayscale for (r=100, g=50, b=0): round(0.299*100 + 0.587*50) = 59
        base_rows = [[100]]
        fake_gdal = types.SimpleNamespace(
            Open=lambda source: _FakeDataset(base_rows, bands=2),
            GetDataTypeSize=lambda data_type: 8,
        )
        fake_osgeo = types.SimpleNamespace(gdal=fake_gdal)
        options = RasterFrame.LoadOptions.from_parameters(
            {"chunk_size": 1},
            profile_mode="regional",
        )

        class _TwoBandDataset(_FakeDataset):
            def ReadAsArray(
                self,
                xoff: int = 0,
                yoff: int = 0,
                xsize: int | None = None,
                ysize: int | None = None,
            ):
                del xoff, yoff
                if xsize is None:
                    xsize = 1
                if ysize is None:
                    ysize = 1
                band_r = [[100 for _ in range(xsize)] for _ in range(ysize)]
                band_g = [[50 for _ in range(xsize)] for _ in range(ysize)]
                return _FakeArray3D([band_r, band_g])

        fake_gdal = types.SimpleNamespace(
            Open=lambda source: _TwoBandDataset(base_rows, bands=2),
            GetDataTypeSize=lambda data_type: 8,
        )
        fake_osgeo = types.SimpleNamespace(gdal=fake_gdal)

        with patch.dict(sys.modules, {"osgeo": fake_osgeo}, clear=False):
            raster = RasterFrame.load(path, options=options)

        self.assertEqual(raster.pixel(0, 0), 59)

    def test_two_band_grayscale_is_consistent_between_standard_and_chunked_paths(self) -> None:
        standard = RasterFrame.from_matrix([[(100, 50)]])
        self.assertEqual(standard.grayscale_matrix(), ((59,),))

        path = self._make_temp_path()
        options = RasterFrame.LoadOptions.from_parameters(
            {"chunk_size": 1},
            profile_mode="regional",
        )

        class _TwoBandDataset(_FakeDataset):
            def ReadAsArray(
                self,
                xoff: int = 0,
                yoff: int = 0,
                xsize: int | None = None,
                ysize: int | None = None,
            ):
                del xoff, yoff
                if xsize is None:
                    xsize = 1
                if ysize is None:
                    ysize = 1
                band_r = [[100 for _ in range(xsize)] for _ in range(ysize)]
                band_g = [[50 for _ in range(xsize)] for _ in range(ysize)]
                return _FakeArray3D([band_r, band_g])

        fake_gdal = types.SimpleNamespace(
            Open=lambda source: _TwoBandDataset([[100]], bands=2),
            GetDataTypeSize=lambda data_type: 8,
        )
        fake_osgeo = types.SimpleNamespace(gdal=fake_gdal)
        with patch.dict(sys.modules, {"osgeo": fake_osgeo}, clear=False):
            chunked = RasterFrame.load(path, options=options)

        self.assertEqual(chunked.grayscale_matrix(), standard.grayscale_matrix())

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
