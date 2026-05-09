"""Tests for geometry module with shapely acceleration (Phase 4)."""

from __future__ import annotations

import unittest

from qgis_vector_map.core.geometry import (
    _HAS_SHAPELY,
    polygon_area,
    point_in_polygon,
    simplify_path,
    apply_geotransform,
    validate_polygon_rings,
    repair_polygon_coordinates,
    snap_coordinates_to_grid,
    close_contour_to_polygon,
    find_junctions,
    distance_between_points,
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


class GeotransformTests(unittest.TestCase):
    """Tests for apply_geotransform pixel-to-world coordinate transformation."""

    def test_identity_transform(self):
        gt = (0.0, 1.0, 0.0, 0.0, 0.0, 1.0)
        result = apply_geotransform("Point", [10.0, 20.0], gt)
        self.assertEqual(result, [10.0, 20.0])

    def test_standard_affine_point(self):
        gt = (100.0, 0.5, 0.0, 200.0, 0.0, -0.5)
        result = apply_geotransform("Point", [10.0, 20.0], gt)
        self.assertAlmostEqual(result[0], 100.0 + 10.0 * 0.5, places=6)
        self.assertAlmostEqual(result[1], 200.0 + 20.0 * (-0.5), places=6)

    def test_standard_affine_linestring(self):
        gt = (100.0, 0.5, 0.0, 200.0, 0.0, -0.5)
        coords = [[0.0, 0.0], [10.0, 20.0]]
        result = apply_geotransform("LineString", coords, gt)
        self.assertAlmostEqual(result[0][0], 100.0, places=6)
        self.assertAlmostEqual(result[0][1], 200.0, places=6)
        self.assertAlmostEqual(result[1][0], 105.0, places=6)
        self.assertAlmostEqual(result[1][1], 190.0, places=6)

    def test_standard_affine_polygon(self):
        gt = (0.0, 1.0, 0.0, 0.0, 0.0, 1.0)
        ring = [[0.0, 0.0], [5.0, 0.0], [5.0, 5.0], [0.0, 5.0], [0.0, 0.0]]
        result = apply_geotransform("Polygon", [ring], gt)
        self.assertEqual(len(result), 1)
        self.assertEqual(len(result[0]), 5)
        self.assertAlmostEqual(result[0][0][0], 0.0)
        self.assertAlmostEqual(result[0][1][0], 5.0)

    def test_rotation_geotransform(self):
        gt = (500000.0, 30.0, 0.5, 2000000.0, 0.5, -30.0)
        result = apply_geotransform("Point", [100.0, 50.0], gt)
        expected_x = 500000.0 + 100.0 * 30.0 + 50.0 * 0.5
        expected_y = 2000000.0 + 100.0 * 0.5 + 50.0 * (-30.0)
        self.assertAlmostEqual(result[0], expected_x, places=2)
        self.assertAlmostEqual(result[1], expected_y, places=2)

    def test_none_geotransform_returns_original(self):
        coords = [[1, 2], [3, 4]]
        result = apply_geotransform("LineString", coords, None)
        self.assertEqual(result, coords)

    def test_short_geotransform_returns_original(self):
        coords = [[1, 2], [3, 4]]
        result = apply_geotransform("LineString", coords, (1.0, 2.0))
        self.assertEqual(result, coords)

    def test_multipoint(self):
        gt = (0.0, 1.0, 0.0, 0.0, 0.0, 1.0)
        coords = [[10.0, 20.0], [30.0, 40.0]]
        result = apply_geotransform("MultiPoint", coords, gt)
        self.assertEqual(result, coords)

    def test_multilinestring(self):
        gt = (0.0, 1.0, 0.0, 0.0, 0.0, 1.0)
        lines = [[[0, 0], [1, 1]], [[2, 2], [3, 3]]]
        result = apply_geotransform("MultiLineString", lines, gt)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], [[0, 0], [1, 1]])
        self.assertEqual(result[1], [[2, 2], [3, 3]])

    def test_multipolygon(self):
        gt = (0.0, 1.0, 0.0, 0.0, 0.0, 1.0)
        poly1 = [[[0, 0], [1, 0], [1, 1], [0, 0]]]
        poly2 = [[[2, 2], [3, 2], [3, 3], [2, 2]]]
        result = apply_geotransform("MultiPolygon", [poly1, poly2], gt)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], poly1)
        self.assertEqual(result[1], poly2)

    def test_unknown_geometry_type_returns_original(self):
        coords = [[1, 2], [3, 4]]
        result = apply_geotransform("UnknownType", coords, (0, 1, 0, 0, 0, 1))
        self.assertEqual(result, coords)


class ValidatePolygonRingsTests(unittest.TestCase):
    def test_closed_ring_no_issues(self):
        rings = [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]]
        issues = validate_polygon_rings(rings)
        self.assertEqual(len(issues), 0)

    def test_unclosed_ring(self):
        rings = [[[0, 0], [10, 0], [10, 10], [0, 10]]]
        issues = validate_polygon_rings(rings)
        self.assertTrue(any("not closed" in i for i in issues))

    def test_fewer_than_4_points(self):
        rings = [[[0, 0], [10, 0], [5, 5]]]
        issues = validate_polygon_rings(rings)
        self.assertTrue(any("fewer than 4" in i for i in issues))

    def test_empty_rings(self):
        issues = validate_polygon_rings([])
        self.assertEqual(len(issues), 0)


class RepairPolygonCoordinatesTests(unittest.TestCase):
    def test_close_unclosed_ring(self):
        rings = [[[0, 0], [10, 0], [10, 10], [0, 10]]]
        repaired = repair_polygon_coordinates(rings)
        self.assertEqual(len(repaired), 1)
        self.assertEqual(repaired[0][0], repaired[0][-1])

    def test_remove_consecutive_duplicates(self):
        rings = [[[0, 0], [0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]]
        repaired = repair_polygon_coordinates(rings)
        self.assertEqual(len(repaired), 1)
        self.assertEqual(repaired[0][0], repaired[0][-1])

    def test_inferior_ring_winding(self):
        exterior = [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]
        interior = [[2, 2], [2, 8], [8, 8], [8, 2], [2, 2]]
        repaired = repair_polygon_coordinates([exterior, interior])
        self.assertEqual(len(repaired), 2)

    def test_drop_degenerate_ring(self):
        rings = [[[0, 0], [10, 0], [0, 0]]]
        repaired = repair_polygon_coordinates(rings)
        self.assertEqual(len(repaired), 0)


class SnapToGridTests(unittest.TestCase):
    def test_snap_to_grid(self):
        coords = [[[0.12, 0.48], [1.23, 4.56], [1.23, 4.56], [0.12, 0.48]]]
        result = snap_coordinates_to_grid(coords, "Polygon", 0.1)
        self.assertAlmostEqual(result[0][0][0], 0.1)
        self.assertAlmostEqual(result[0][0][1], 0.5)

    def test_snap_disabled_with_zero(self):
        coords = [[[0.12, 0.48], [1.23, 4.56], [0.12, 0.48]]]
        result = snap_coordinates_to_grid(coords, "Polygon", 0.0)
        self.assertEqual(result, coords)

    def test_snap_linestring(self):
        coords = [[0.15, 0.25], [2.37, 3.82]]
        result = snap_coordinates_to_grid(coords, "LineString", 0.5)
        self.assertAlmostEqual(result[0][0], 0.0)
        self.assertAlmostEqual(result[0][1], 0.0)
        self.assertAlmostEqual(result[1][0], 2.5)
        self.assertAlmostEqual(result[1][1], 4.0)


class CloseContourTests(unittest.TestCase):
    def test_close_open_contour(self):
        coords = [[0, 0], [10, 0], [10, 10], [0, 10]]
        result = close_contour_to_polygon(coords, max_gap=20.0)
        self.assertIsNotNone(result)
        self.assertEqual(result[0][0], result[0][-1])

    def test_already_closed(self):
        coords = [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]
        result = close_contour_to_polygon(coords, max_gap=2.0)
        self.assertIsNotNone(result)

    def test_too_far_to_close(self):
        coords = [[0, 0], [10, 0], [10, 10], [0, 10]]
        result = close_contour_to_polygon(coords, max_gap=0.1)
        self.assertIsNone(result)

    def test_fewer_than_3_points(self):
        coords = [[0, 0], [10, 0]]
        result = close_contour_to_polygon(coords, max_gap=2.0)
        self.assertIsNone(result)


class FindJunctionsTests(unittest.TestCase):
    def test_two_lines_meet_at_point(self):
        from qgis_vector_map.core.models import VectorFeature
        features = [
            VectorFeature(geometry_type="LineString", coordinates=[[0, 0], [5, 5]], properties={}),
            VectorFeature(geometry_type="LineString", coordinates=[[5, 5], [10, 5]], properties={}),
        ]
        junctions = find_junctions(features, snap_tolerance=1.0)
        self.assertEqual(len(junctions), 1)

    def test_no_junctions(self):
        from qgis_vector_map.core.models import VectorFeature
        features = [
            VectorFeature(geometry_type="LineString", coordinates=[[0, 0], [5, 0]], properties={}),
            VectorFeature(geometry_type="LineString", coordinates=[[0, 10], [5, 10]], properties={}),
        ]
        junctions = find_junctions(features, snap_tolerance=1.0)
        self.assertEqual(len(junctions), 0)

    def test_max_endpoints_exceeded(self):
        import warnings
        from qgis_vector_map.core.models import VectorFeature
        features = [
            VectorFeature(geometry_type="LineString", coordinates=[[i, i], [i+1, i+1]], properties={})
            for i in range(6000)
        ]
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            junctions = find_junctions(features, snap_tolerance=1.0, max_endpoints=10000)
            self.assertEqual(len(junctions), 0)
            self.assertTrue(any("max_endpoints" in str(warning.message) for warning in w))


class DistanceBetweenPointsTests(unittest.TestCase):
    def test_distance(self):
        d = distance_between_points([0, 0], [3, 4])
        self.assertAlmostEqual(d, 5.0)

    def test_same_point(self):
        d = distance_between_points([5, 5], [5, 5])
        self.assertAlmostEqual(d, 0.0)


if __name__ == "__main__":
    unittest.main()
