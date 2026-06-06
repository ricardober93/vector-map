"""Tests for CRS output selector and _LightweightCRS fallback."""

from __future__ import annotations

import unittest

from qgis_vector_map.algorithms.vectorize_image_algorithm import (
    _LightweightCRS,
    _resolve_crs_from_index,
    _CRS_OPTION_INPUT,
    _CRS_OPTION_EPSG_4326,
    _CRS_OPTION_EPSG_3857,
    _CRS_OPTION_EPSG_32618,
    _CRS_OPTION_EPSG_32619,
    _CRS_OPTION_CUSTOM,
)


class LightweightCRSTests(unittest.TestCase):
    """Tests for the fallback CRS wrapper."""

    def test_valid_epsg_is_valid(self):
        crs = _LightweightCRS("EPSG:4326")
        self.assertTrue(crs.isValid())
        self.assertEqual(crs.authid(), "EPSG:4326")

    def test_invalid_format_is_not_valid(self):
        crs = _LightweightCRS("not-a-crs")
        self.assertFalse(crs.isValid())

    def test_uppercase_epsg_is_valid(self):
        crs = _LightweightCRS("EPSG:3857")
        self.assertTrue(crs.isValid())

    def test_lowercase_epsg_is_valid(self):
        crs = _LightweightCRS("epsg:3116")
        self.assertTrue(crs.isValid())

    def test_description(self):
        crs = _LightweightCRS("EPSG:4326")
        desc = crs.description()
        self.assertIn("EPSG:4326", desc)

    def test_equality(self):
        a = _LightweightCRS("EPSG:4326")
        b = _LightweightCRS("EPSG:4326")
        c = _LightweightCRS("EPSG:3857")
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)

    def test_hashable(self):
        a = _LightweightCRS("EPSG:4326")
        b = _LightweightCRS("EPSG:4326")
        s = {a, b}
        self.assertEqual(len(s), 1)

    def test_repr(self):
        crs = _LightweightCRS("EPSG:4326")
        self.assertIn("EPSG:4326", repr(crs))


class ResolveCRSFromIndexTests(unittest.TestCase):
    """Tests for the pure-logic _resolve_crs_from_index function."""

    def test_input_index_returns_input(self):
        input_crs = _LightweightCRS("EPSG:32619")
        result = _resolve_crs_from_index(_CRS_OPTION_INPUT, "", input_crs)
        self.assertEqual(result, input_crs)

    def test_epsg_4326(self):
        result = _resolve_crs_from_index(
            _CRS_OPTION_EPSG_4326, "", _LightweightCRS("EPSG:32619")
        )
        self.assertEqual(result.authid(), "EPSG:4326")

    def test_epsg_3857(self):
        result = _resolve_crs_from_index(
            _CRS_OPTION_EPSG_3857, "", _LightweightCRS("EPSG:4326")
        )
        self.assertEqual(result.authid(), "EPSG:3857")

    def test_epsg_32618(self):
        result = _resolve_crs_from_index(
            _CRS_OPTION_EPSG_32618, "", _LightweightCRS("EPSG:4326")
        )
        self.assertEqual(result.authid(), "EPSG:32618")

    def test_epsg_32619(self):
        result = _resolve_crs_from_index(
            _CRS_OPTION_EPSG_32619, "", _LightweightCRS("EPSG:4326")
        )
        self.assertEqual(result.authid(), "EPSG:32619")

    def test_custom_crs(self):
        result = _resolve_crs_from_index(
            _CRS_OPTION_CUSTOM, "EPSG:3116", _LightweightCRS("EPSG:4326")
        )
        self.assertEqual(result.authid(), "EPSG:3116")

    def test_custom_crs_strips_whitespace(self):
        result = _resolve_crs_from_index(
            _CRS_OPTION_CUSTOM, "  EPSG:3116  ", _LightweightCRS("EPSG:4326")
        )
        self.assertEqual(result.authid(), "EPSG:3116")

    def test_custom_crs_empty_falls_back_to_input(self):
        input_crs = _LightweightCRS("EPSG:32619")
        result = _resolve_crs_from_index(
            _CRS_OPTION_CUSTOM, "", input_crs
        )
        self.assertEqual(result, input_crs)

    def test_custom_crs_whitespace_only_falls_back_to_input(self):
        input_crs = _LightweightCRS("EPSG:32619")
        result = _resolve_crs_from_index(
            _CRS_OPTION_CUSTOM, "   ", input_crs
        )
        self.assertEqual(result, input_crs)

    def test_custom_crs_none_value_falls_back_to_input(self):
        input_crs = _LightweightCRS("EPSG:32619")
        result = _resolve_crs_from_index(
            _CRS_OPTION_CUSTOM, None, input_crs
        )
        self.assertEqual(result, input_crs)

    def test_out_of_range_index_falls_back_to_input(self):
        input_crs = _LightweightCRS("EPSG:32619")
        result = _resolve_crs_from_index(99, "", input_crs)
        self.assertEqual(result, input_crs)

    def test_negative_index_falls_back_to_input(self):
        input_crs = _LightweightCRS("EPSG:32619")
        result = _resolve_crs_from_index(-1, "", input_crs)
        self.assertEqual(result, input_crs)


if __name__ == "__main__":
    unittest.main()
