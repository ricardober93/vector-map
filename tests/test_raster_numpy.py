"""Tests for numpy-backed RasterFrame (Phase 1)."""

from __future__ import annotations

import unittest

import numpy as np

from qgis_vector_map.core.raster import RasterFrame


class NumpyRasterFrameTests(unittest.TestCase):
    """Verify that numpy backing works correctly and backward compat is preserved."""

    def test_from_matrix_creates_numpy_backing(self):
        raster = RasterFrame.from_matrix([[0, 128, 255], [64, 192, 32]])
        self.assertIsNotNone(raster.array)
        self.assertIsInstance(raster.array, np.ndarray)
        self.assertEqual(raster.array.dtype, np.uint8)
        self.assertEqual(raster.width, 3)
        self.assertEqual(raster.height, 2)
        self.assertEqual(raster.bands, 1)

    def test_pixels_property_returns_tuples(self):
        raster = RasterFrame.from_matrix([[0, 128], [64, 192]])
        pixels = raster.pixels
        self.assertEqual(pixels[0][0], 0)
        self.assertEqual(pixels[0][1], 128)
        self.assertEqual(pixels[1][0], 64)
        self.assertEqual(pixels[1][1], 192)
        self.assertIsInstance(pixels, tuple)
        self.assertIsInstance(pixels[0], tuple)

    def test_pixels_rgb_pixels_property(self):
        raster = RasterFrame.from_matrix([[(255, 0, 0), (0, 255, 0)], [(0, 0, 255), (128, 128, 128)]])
        pixels = raster.pixels
        self.assertEqual(pixels[0][0], (255, 0, 0))
        self.assertEqual(pixels[1][1], (128, 128, 128))
        self.assertEqual(raster.bands, 3)

    def test_pixel_access_single_band(self):
        raster = RasterFrame.from_matrix([[10, 20], [30, 40]])
        self.assertEqual(raster.pixel(0, 0), 10)
        self.assertEqual(raster.pixel(1, 1), 40)

    def test_pixel_access_rgb_band(self):
        raster = RasterFrame.from_matrix([[(255, 0, 0)]])
        self.assertEqual(raster.pixel(0, 0), (255, 0, 0))

    def test_grayscale_matrix_single_band(self):
        raster = RasterFrame.from_matrix([[0, 100, 255]])
        gray = raster.grayscale_matrix()
        self.assertEqual(gray, ((0, 100, 255),))

    def test_grayscale_matrix_rgb(self):
        # (100, 50, 0) -> round(0.299*100 + 0.587*50 + 0.114*0) = round(29.9+29.35) = 59
        raster = RasterFrame.from_matrix([[(100, 50, 0)]])
        gray = raster.grayscale_matrix()
        self.assertEqual(gray, ((59,),))

    def test_rgb_matrix_single_band_expands(self):
        raster = RasterFrame.from_matrix([[128]])
        rgb = raster.rgb_matrix()
        self.assertEqual(rgb, (((128, 128, 128),),))

    def test_rgb_matrix_rgb(self):
        raster = RasterFrame.from_matrix([[(10, 20, 30)]])
        rgb = raster.rgb_matrix()
        self.assertEqual(rgb, (((10, 20, 30),),))

    def test_direct_numpy_construction(self):
        arr = np.array([[0, 50, 100], [150, 200, 255]], dtype=np.uint8)
        raster = RasterFrame(pixels=arr, width=3, height=2, bands=1)
        self.assertEqual(raster.width, 3)
        self.assertEqual(raster.height, 2)
        self.assertEqual(raster.bands, 1)
        self.assertEqual(raster.pixel(1, 1), 200)
        self.assertEqual(raster.array.shape, (2, 3))

    def test_direct_numpy_rgb_construction(self):
        arr = np.array([[[255, 0, 0], [0, 255, 0]], [[0, 0, 255], [128, 128, 128]]], dtype=np.uint8)
        raster = RasterFrame(pixels=arr, width=2, height=2, bands=3)
        self.assertEqual(raster.pixel(0, 0), (255, 0, 0))
        self.assertEqual(raster.pixel(1, 0), (0, 255, 0))

    def test_array_is_uint8_contiguous(self):
        raster = RasterFrame.from_matrix([[100]])
        self.assertTrue(raster.array.flags['C_CONTIGUOUS'])
        self.assertEqual(raster.array.dtype, np.uint8)

    def test_metadata_and_source_name_preserved(self):
        raster = RasterFrame.from_matrix([[0]], source_name="test.tif", metadata={"key": "val"})
        self.assertEqual(raster.source_name, "test.tif")
        self.assertEqual(raster.metadata["key"], "val")

    def test_load_with_sequence_uses_numpy(self):
        raster = RasterFrame.load([[10, 20], [30, 40]])
        self.assertIsNotNone(raster.array)
        self.assertEqual(raster.pixel(0, 0), 10)


if __name__ == "__main__":
    unittest.main()
