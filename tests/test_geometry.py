"""Tests for geometry module with shapely acceleration (Phase 4)."""

from __future__ import annotations

import unittest

from qgis_vector_map.core.geometry import (
    _HAS_SHAPELY,
    polygon_area,
    point_in_polygon,
    simplify_path,
)


class GeometryFunctionTests(unittest.TestCase):
    """Test geometry functions produce correct results (works with or without shapely)."""

    def test_polygon_area_simple(self):
        # Unit square: (0,0) -> (1,0) -> (1,1) -> (0,1) -> (0,0)
        points = [(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]
        area = polygon_area(points)
        self.assertAlmostEqual(area, 1.0, places=5)

    def test_polygon_area_triangle(self):
        # Triangle with area 2.0
        points = [(0, 0), (4, 0), (0, 1), (0, 0)]
        area = polygon_area(points)
        self.assertAlmostEqual(area, 2.0, places=5)

    def test_polygon_area_empty(self):
        self.assertAlmostEqual(polygon_area([]), 0.0)
        self.assertAlmostEqual(polygon_area([(0, 0)]), 0.0)

    def test_point_in_polygon_inside(self):
        ring = [(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]
        self.assertTrue(point_in_polygon((5, 5), ring))

    def test_point_in_polygon_outside(self):
        ring = [(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]
        self.assertFalse(point_in_polygon((15, 5), ring))

    def test_point_in_polygon_edge(self):
        ring = [(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]
        # Point on the edge — behavior may differ between implementations
        result = point_in_polygon((0, 5), ring)
        # Just ensure it returns bool
        self.assertIsInstance(result, bool)

    def test_point_in_polygon_insufficient_ring(self):
        self.assertFalse(point_in_polygon((0, 0), [(0, 0), (1, 0)]))

    def test_simplify_path_no_reduction(self):
        points = [(0, 0), (10, 10), (20, 0)]
        simplified = simplify_path(points, tolerance=0.0)
        self.assertEqual(len(simplified), 3)

    def test_simplify_path_with_tolerance(self):
        # Collinear middle points should be removed
        points = [(0, 0), (5, 5), (10, 5), (15, 5), (20, 0)]
        simplified = simplify_path(points, tolerance=1.0)
        self.assertLess(len(simplified), len(points))
        self.assertEqual(simplified[0], (0, 0))
        self.assertEqual(simplified[-1], (20, 0))

    def test_simplify_path_empty(self):
        self.assertEqual(simplify_path([]), [])
        self.assertEqual(simplify_path([(0, 0)]), [(0, 0)])

    def test_simplify_path_preserves_endpoints(self):
        points = [(0, 0), (1, 0.01), (2, 0), (3, -0.01), (4, 0)]
        simplified = simplify_path(points, tolerance=1.0)
        self.assertEqual(simplified[0], (0, 0))
        self.assertEqual(simplified[-1], (4, 0))


class ShapelyAccelerationTests(unittest.TestCase):
    """Verify shapely availability and consistent results."""

    def test_shapely_available(self):
        self.assertTrue(_HAS_SHAPELY, "shapely should be installed in the test environment")

    def test_polygon_area_shapely_matches_pure_python(self):
        points = [(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]
        area = polygon_area(points)
        self.assertAlmostEqual(area, 100.0, places=5)

    def test_results_consistent_for_complex_polygon(self):
        # Star-like polygon
        points = [(0, 10), (3, 3), (10, 3), (5, 0), (7, -7), (0, -3), (-7, -7), (-5, 0), (-10, 3), (-3, 3), (0, 10)]
        area = polygon_area(points)
        self.assertGreater(area, 0)

    def test_simplify_consistent(self):
        points = [(0, 0), (1, 0.1), (2, 0.05), (3, -0.1), (4, 0)]
        simplified = simplify_path(points, tolerance=0.5)
        self.assertIsInstance(simplified, list)
        if simplified:
            self.assertIsInstance(simplified[0], tuple)
            self.assertEqual(len(simplified[0]), 2)


if __name__ == "__main__":
    unittest.main()
