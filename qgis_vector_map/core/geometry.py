"""Pure-Python geometry and image analysis helpers."""

from __future__ import annotations

from collections import Counter, deque

try:
    from shapely.geometry import LineString as _ShapelyLineString
    from shapely.geometry import Point as _ShapelyPoint
    from shapely.geometry import Polygon as _ShapelyPolygon
    from shapely.prepared import prep as _shapely_prep

    _HAS_SHAPELY = True
except ImportError:
    _ShapelyLineString = None
    _ShapelyPoint = None
    _ShapelyPolygon = None
    _shapely_prep = None
    _HAS_SHAPELY = False
from math import hypot
from typing import Any, Iterable, Iterator, Sequence

Point = tuple[float, float]
GridPoint = tuple[int, int]
BinaryMatrix = Sequence[Sequence[int]]
LabelMatrix = Sequence[Sequence[int]]


def _dims(matrix: Sequence[Sequence[Any]]) -> tuple[int, int]:
    height = len(matrix)
    width = len(matrix[0]) if height else 0
    return width, height


def _neighbors_4(x: int, y: int) -> tuple[GridPoint, ...]:
    return ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1))


def _neighbors_8(x: int, y: int) -> tuple[GridPoint, ...]:
    return (
        (x - 1, y - 1),
        (x, y - 1),
        (x + 1, y - 1),
        (x - 1, y),
        (x + 1, y),
        (x - 1, y + 1),
        (x, y + 1),
        (x + 1, y + 1),
    )


def majority_filter(matrix: LabelMatrix, radius: int = 1) -> tuple[tuple[int, ...], ...]:
    width, height = _dims(matrix)
    if radius <= 0:
        return tuple(tuple(int(value) for value in row) for row in matrix)

    result: list[tuple[int, ...]] = []
    for y in range(height):
        row: list[int] = []
        for x in range(width):
            counts: Counter[int] = Counter()
            for yy in range(max(0, y - radius), min(height, y + radius + 1)):
                for xx in range(max(0, x - radius), min(width, x + radius + 1)):
                    counts[int(matrix[yy][xx])] += 1
            current = int(matrix[y][x])
            winner = max(counts.items(), key=lambda item: (item[1], item[0] == current, -item[0]))[0]
            row.append(winner)
        result.append(tuple(row))
    return tuple(result)


def binary_dilate(matrix: BinaryMatrix, radius: int = 1) -> tuple[tuple[int, ...], ...]:
    width, height = _dims(matrix)
    result: list[tuple[int, ...]] = []
    for y in range(height):
        row: list[int] = []
        for x in range(width):
            value = 0
            for yy in range(max(0, y - radius), min(height, y + radius + 1)):
                for xx in range(max(0, x - radius), min(width, x + radius + 1)):
                    if matrix[yy][xx]:
                        value = 1
                        break
                if value:
                    break
            row.append(value)
        result.append(tuple(row))
    return tuple(result)


def binary_erode(matrix: BinaryMatrix, radius: int = 1) -> tuple[tuple[int, ...], ...]:
    width, height = _dims(matrix)
    result: list[tuple[int, ...]] = []
    for y in range(height):
        row: list[int] = []
        for x in range(width):
            value = 1
            for yy in range(max(0, y - radius), min(height, y + radius + 1)):
                for xx in range(max(0, x - radius), min(width, x + radius + 1)):
                    if not matrix[yy][xx]:
                        value = 0
                        break
                if not value:
                    break
            row.append(value)
        result.append(tuple(row))
    return tuple(result)


def binary_open(matrix: BinaryMatrix, radius: int = 1) -> tuple[tuple[int, ...], ...]:
    return binary_dilate(binary_erode(matrix, radius=radius), radius=radius)


def binary_close(matrix: BinaryMatrix, radius: int = 1) -> tuple[tuple[int, ...], ...]:
    return binary_erode(binary_dilate(matrix, radius=radius), radius=radius)


def threshold_matrix(matrix: Sequence[Sequence[int]], threshold: int, *, polarity: str = "high") -> tuple[tuple[int, ...], ...]:
    result: list[tuple[int, ...]] = []
    if polarity not in {"high", "low"}:
        raise ValueError("polarity must be 'high' or 'low'")
    for row in matrix:
        out_row: list[int] = []
        for value in row:
            value = int(value)
            if polarity == "high":
                out_row.append(1 if value >= threshold else 0)
            else:
                out_row.append(1 if value <= threshold else 0)
        result.append(tuple(out_row))
    return tuple(result)


def auto_threshold(matrix: Sequence[Sequence[int]]) -> int:
    values = [int(value) for row in matrix for value in row]
    if not values:
        return 0
    values.sort()
    return values[len(values) // 2]


def otsu_threshold(matrix: Sequence[Sequence[int]]) -> int:
    values = [max(0, min(255, int(value))) for row in matrix for value in row]
    if not values:
        return 0

    histogram = [0] * 256
    for value in values:
        histogram[value] += 1

    total = len(values)
    sum_total = sum(index * count for index, count in enumerate(histogram))
    sum_background = 0.0
    weight_background = 0
    max_variance = -1.0
    threshold = 0

    for index, count in enumerate(histogram):
        weight_background += count
        if weight_background == 0:
            continue
        weight_foreground = total - weight_background
        if weight_foreground == 0:
            break
        sum_background += index * count
        mean_background = sum_background / weight_background
        mean_foreground = (sum_total - sum_background) / weight_foreground
        between_class_variance = weight_background * weight_foreground * (mean_background - mean_foreground) ** 2
        if between_class_variance > max_variance:
            max_variance = between_class_variance
            threshold = index
    return threshold


def sobel_edge_magnitude(matrix: Sequence[Sequence[int]]) -> tuple[tuple[int, ...], ...]:
    width, height = _dims(matrix)
    if width == 0 or height == 0:
        return tuple()

    result: list[tuple[int, ...]] = []
    for y in range(height):
        row: list[int] = []
        for x in range(width):
            def sample(xx: int, yy: int) -> int:
                xx = min(width - 1, max(0, xx))
                yy = min(height - 1, max(0, yy))
                return int(matrix[yy][xx])

            gx = (
                -sample(x - 1, y - 1)
                + sample(x + 1, y - 1)
                - 2 * sample(x - 1, y)
                + 2 * sample(x + 1, y)
                - sample(x - 1, y + 1)
                + sample(x + 1, y + 1)
            )
            gy = (
                -sample(x - 1, y - 1)
                - 2 * sample(x, y - 1)
                - sample(x + 1, y - 1)
                + sample(x - 1, y + 1)
                + 2 * sample(x, y + 1)
                + sample(x + 1, y + 1)
            )
            row.append(int(abs(gx) + abs(gy)))
        result.append(tuple(row))
    return tuple(result)


def connected_components(matrix: BinaryMatrix, target_value: int = 1, connectivity: int = 4) -> list[list[GridPoint]]:
    width, height = _dims(matrix)
    visited: set[GridPoint] = set()
    components: list[list[GridPoint]] = []
    if connectivity not in {4, 8}:
        raise ValueError("connectivity must be 4 or 8")
    neighbors = _neighbors_4 if connectivity == 4 else _neighbors_8

    for y in range(height):
        for x in range(width):
            if (x, y) in visited or int(matrix[y][x]) != int(target_value):
                continue
            queue: deque[GridPoint] = deque([(x, y)])
            visited.add((x, y))
            component: list[GridPoint] = []
            while queue:
                cx, cy = queue.popleft()
                component.append((cx, cy))
                for nx, ny in neighbors(cx, cy):
                    if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in visited and int(matrix[ny][nx]) == int(target_value):
                        visited.add((nx, ny))
                        queue.append((nx, ny))
            components.append(component)
    return components


def label_components(label_map: LabelMatrix, label: int, connectivity: int = 4) -> list[list[GridPoint]]:
    binary = tuple(tuple(1 if int(value) == int(label) else 0 for value in row) for row in label_map)
    return connected_components(binary, target_value=1, connectivity=connectivity)


def _remove_consecutive_duplicates(points: Sequence[Point]) -> list[Point]:
    cleaned: list[Point] = []
    for point in points:
        if not cleaned or cleaned[-1] != point:
            cleaned.append(point)
    if len(cleaned) > 1 and cleaned[0] == cleaned[-1]:
        cleaned.pop()
    return cleaned


def _remove_collinear_points(points: Sequence[Point]) -> list[Point]:
    if len(points) <= 3:
        return list(points)
    ring = list(points)
    cleaned: list[Point] = []
    count = len(ring)
    for index in range(count):
        prev_point = ring[index - 1]
        point = ring[index]
        next_point = ring[(index + 1) % count]
        dx1 = point[0] - prev_point[0]
        dy1 = point[1] - prev_point[1]
        dx2 = next_point[0] - point[0]
        dy2 = next_point[1] - point[1]
        if dx1 * dy2 != dy1 * dx2:
            cleaned.append(point)
    return cleaned or list(points)


def close_ring(points: Sequence[Point]) -> list[Point]:
    cleaned = _remove_consecutive_duplicates(points)
    if not cleaned:
        return []
    if cleaned[0] != cleaned[-1]:
        cleaned.append(cleaned[0])
    return cleaned


def polygon_area(points: Sequence[Point]) -> float:
    ring = close_ring(points)
    if len(ring) < 4:
        return 0.0
    if _HAS_SHAPELY:
        try:
            return float(_ShapelyPolygon(ring).area)
        except Exception:
            pass
    area = 0.0
    for index in range(len(ring) - 1):
        x1, y1 = ring[index]
        x2, y2 = ring[index + 1]
        area += (x1 * y2) - (x2 * y1)
    return area / 2.0


def ring_length(points: Sequence[Point]) -> float:
    ring = close_ring(points)
    if len(ring) < 2:
        return 0.0
    total = 0.0
    for index in range(len(ring) - 1):
        total += hypot(ring[index + 1][0] - ring[index][0], ring[index + 1][1] - ring[index][1])
    return total


def polyline_length(points: Sequence[Point]) -> float:
    if len(points) < 2:
        return 0.0
    total = 0.0
    for index in range(len(points) - 1):
        total += hypot(points[index + 1][0] - points[index][0], points[index + 1][1] - points[index][1])
    return total


def polygon_centroid(points: Sequence[Point]) -> Point:
    ring = close_ring(points)
    if len(ring) < 4:
        if not ring:
            return (0.0, 0.0)
        x = sum(point[0] for point in ring[:-1]) / max(1, len(ring) - 1)
        y = sum(point[1] for point in ring[:-1]) / max(1, len(ring) - 1)
        return (x, y)
    area = polygon_area(ring)
    if area == 0:
        x = sum(point[0] for point in ring[:-1]) / max(1, len(ring) - 1)
        y = sum(point[1] for point in ring[:-1]) / max(1, len(ring) - 1)
        return (x, y)
    cx = 0.0
    cy = 0.0
    for index in range(len(ring) - 1):
        x1, y1 = ring[index]
        x2, y2 = ring[index + 1]
        factor = (x1 * y2) - (x2 * y1)
        cx += (x1 + x2) * factor
        cy += (y1 + y2) * factor
    scale = 1.0 / (6.0 * area)
    return (cx * scale, cy * scale)


def point_in_polygon(point: Point, ring: Sequence[Point]) -> bool:
    cleaned = close_ring(ring)
    if len(cleaned) < 4:
        return False
    if _HAS_SHAPELY:
        try:
            poly = _ShapelyPolygon(cleaned)
            prepared = _shapely_prep(poly)
            return bool(prepared.contains(_ShapelyPoint(point)))
        except Exception:
            pass
    x, y = point
    inside = False
    for index in range(len(cleaned) - 1):
        x1, y1 = cleaned[index]
        x2, y2 = cleaned[index + 1]
        intersects = ((y1 > y) != (y2 > y)) and (x < (x2 - x1) * (y - y1) / ((y2 - y1) or 1e-12) + x1)
        if intersects:
            inside = not inside
    return inside


def simplify_path(points: Sequence[Point], tolerance: float = 0.0) -> list[Point]:
    cleaned = _remove_consecutive_duplicates(points)
    if len(cleaned) <= 2 or tolerance <= 0.0:
        return list(cleaned)
    if _HAS_SHAPELY:
        try:
            simplified = _ShapelyLineString(cleaned).simplify(tolerance, preserve_topology=True)
            if simplified.is_empty:
                return list(cleaned)
            coords = list(simplified.coords)
            if len(coords) >= 2:
                return [(float(x), float(y)) for x, y in coords]
        except Exception:
            pass

    def _rdp(segment: Sequence[Point]) -> list[Point]:
        if len(segment) <= 2:
            return list(segment)
        start = segment[0]
        end = segment[-1]
        max_distance = -1.0
        split_index = -1
        for index in range(1, len(segment) - 1):
            point = segment[index]
            numerator = abs((end[1] - start[1]) * point[0] - (end[0] - start[0]) * point[1] + end[0] * start[1] - end[1] * start[0])
            denominator = hypot(end[0] - start[0], end[1] - start[1]) or 1e-12
            distance = numerator / denominator
            if distance > max_distance:
                max_distance = distance
                split_index = index
        if max_distance <= tolerance:
            return [start, end]
        left = _rdp(segment[: split_index + 1])
        right = _rdp(segment[split_index:])
        return left[:-1] + right

    return _rdp(cleaned)


def component_boundary_edges(component: Sequence[GridPoint]) -> list[tuple[Point, Point]]:
    component_set = set(component)
    edges: list[tuple[Point, Point]] = []
    for x, y in component:
        if (x, y - 1) not in component_set:
            edges.append(((x, y), (x + 1, y)))
        if (x + 1, y) not in component_set:
            edges.append(((x + 1, y), (x + 1, y + 1)))
        if (x, y + 1) not in component_set:
            edges.append(((x + 1, y + 1), (x, y + 1)))
        if (x - 1, y) not in component_set:
            edges.append(((x, y + 1), (x, y)))
    return edges


def trace_directed_cycles(edges: Sequence[tuple[Point, Point]]) -> list[list[Point]]:
    next_map: dict[Point, Point] = {}
    for start, end in edges:
        if start in next_map and next_map[start] != end:
            raise ValueError(f"Boundary graph is ambiguous at {start!r}.")
        next_map[start] = end

    visited: set[Point] = set()
    cycles: list[list[Point]] = []
    for start in sorted(next_map):
        if start in visited:
            continue
        cycle = [start]
        current = start
        while True:
            visited.add(current)
            nxt = next_map.get(current)
            if nxt is None:
                break
            cycle.append(nxt)
            current = nxt
            if current == start:
                break
        if len(cycle) >= 4 and cycle[0] == cycle[-1]:
            cycles.append(_remove_collinear_points(cycle[:-1]))
    return cycles


def _interior_probe_point(ring: Sequence[Point]) -> Point:
    centroid = polygon_centroid(ring)
    if point_in_polygon(centroid, ring):
        return centroid
    xs = [point[0] for point in ring]
    ys = [point[1] for point in ring]
    bbox_center = ((min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0)
    if point_in_polygon(bbox_center, ring):
        return bbox_center
    if len(ring) >= 2:
        return ((ring[0][0] + ring[1][0]) / 2.0, (ring[0][1] + ring[1][1]) / 2.0)
    return centroid


def assemble_polygon_rings(cycles: Sequence[Sequence[Point]]) -> list[list[list[Point]]]:
    ring_data: list[dict[str, Any]] = []
    for cycle in cycles:
        ring = close_ring(_remove_collinear_points(_remove_consecutive_duplicates(cycle)))
        if len(ring) < 4:
            continue
        area = polygon_area(ring)
        if abs(area) <= 1e-9:
            continue
        ring_data.append(
            {
                "ring": ring,
                "abs_area": abs(area),
                "area": area,
                "probe": _interior_probe_point(ring),
            }
        )
    ring_data.sort(key=lambda item: (-item["abs_area"], item["probe"][1], item["probe"][0]))
    parents: dict[int, int | None] = {index: None for index in range(len(ring_data))}
    for index, ring in enumerate(ring_data):
        for parent_index in range(index):
            if point_in_polygon(ring["probe"], ring_data[parent_index]["ring"]):
                parents[index] = parent_index
                break

    children: dict[int, list[int]] = {index: [] for index in range(len(ring_data))}
    for child_index, parent_index in parents.items():
        if parent_index is not None:
            children[parent_index].append(child_index)

    polygons: list[list[list[Point]]] = []
    for index, ring in enumerate(ring_data):
        if parents[index] is not None:
            continue
        polygon_rings = [ring["ring"]]
        for child_index in children[index]:
            child_ring = ring_data[child_index]["ring"]
            if abs(ring_data[child_index]["abs_area"]) > 0.0:
                polygon_rings.append(child_ring)
        polygons.append(polygon_rings)
    return polygons


def polygonize_label_component(component: Sequence[GridPoint], *, min_area: int = 1) -> list[list[list[Point]]]:
    if len(component) < min_area:
        return []
    cycles = trace_directed_cycles(component_boundary_edges(component))
    return assemble_polygon_rings(cycles)


def polygonize_label_map(
    label_map: LabelMatrix,
    *,
    min_component_area: int = 1,
    background_label: int | None = None,
    connectivity: int = 4,
) -> list[dict[str, Any]]:
    labels = sorted({int(value) for row in label_map for value in row})
    features: list[dict[str, Any]] = []
    for label in labels:
        if background_label is not None and label == int(background_label):
            continue
        components = label_components(label_map, label, connectivity=connectivity)
        for component in components:
            if len(component) < min_component_area:
                continue
            polygons = polygonize_label_component(component, min_area=min_component_area)
            for polygon in polygons:
                features.append(
                    {
                        "geometry_type": "Polygon",
                        "coordinates": [[list(point) for point in ring] for ring in polygon],
                        "label": label,
                        "area_px": len(component),
                        "ring_count": len(polygon),
                    }
                )
    return features


def _neighbors_for_skeleton(x: int, y: int) -> tuple[GridPoint, ...]:
    return _neighbors_8(x, y)


def zhang_suen_thinning(matrix: BinaryMatrix) -> tuple[tuple[int, ...], ...]:
    width, height = _dims(matrix)
    image = [list(int(value) for value in row) for row in matrix]
    if width == 0 or height == 0:
        return tuple()

    changed = True
    while changed:
        changed = False
        for step in (0, 1):
            removals: list[GridPoint] = []
            for y in range(1, height - 1):
                for x in range(1, width - 1):
                    if image[y][x] == 0:
                        continue
                    p2 = image[y - 1][x]
                    p3 = image[y - 1][x + 1]
                    p4 = image[y][x + 1]
                    p5 = image[y + 1][x + 1]
                    p6 = image[y + 1][x]
                    p7 = image[y + 1][x - 1]
                    p8 = image[y][x - 1]
                    p9 = image[y - 1][x - 1]
                    neighbors = [p2, p3, p4, p5, p6, p7, p8, p9]
                    transitions = sum(1 for index in range(8) if neighbors[index] == 0 and neighbors[(index + 1) % 8] == 1)
                    count = sum(neighbors)
                    if 2 <= count <= 6 and transitions == 1:
                        if step == 0 and p2 * p4 * p6 == 0 and p4 * p6 * p8 == 0:
                            removals.append((x, y))
                        elif step == 1 and p2 * p4 * p8 == 0 and p2 * p6 * p8 == 0:
                            removals.append((x, y))
            if removals:
                changed = True
                for x, y in removals:
                    image[y][x] = 0
    return tuple(tuple(row) for row in image)


def trace_skeleton_paths(matrix: BinaryMatrix, *, min_length: int = 2) -> list[list[Point]]:
    width, height = _dims(matrix)
    foreground = {(x, y) for y in range(height) for x in range(width) if int(matrix[y][x])}
    if not foreground:
        return []

    neighbor_map: dict[GridPoint, list[GridPoint]] = {}
    for x, y in foreground:
        neighbors = [point for point in _neighbors_8(x, y) if point in foreground]
        neighbor_map[(x, y)] = neighbors

    degree = {point: len(neighbors) for point, neighbors in neighbor_map.items()}
    endpoints = sorted(point for point, deg in degree.items() if deg == 1)
    junctions = {point for point, deg in degree.items() if deg != 2}
    visited_edges: set[tuple[GridPoint, GridPoint]] = set()
    paths: list[list[Point]] = []

    def _mark_edge(a: GridPoint, b: GridPoint) -> None:
        visited_edges.add((a, b))
        visited_edges.add((b, a))

    def _edge_visited(a: GridPoint, b: GridPoint) -> bool:
        return (a, b) in visited_edges

    def _trace(start: GridPoint) -> list[GridPoint]:
        path = [start]
        current = start
        previous: GridPoint | None = None
        while True:
            neighbors = sorted(neighbor_map[current])
            candidates = [point for point in neighbors if point != previous and not _edge_visited(current, point)]
            if not candidates:
                break
            candidates.sort(key=lambda point: (point[1], point[0]))
            nxt = candidates[0]
            _mark_edge(current, nxt)
            path.append(nxt)
            previous, current = current, nxt
            if current in junctions and current != start:
                break
        return path

    for endpoint in endpoints:
        if all(_edge_visited(endpoint, neighbor) for neighbor in neighbor_map[endpoint]):
            continue
        path = _trace(endpoint)
        if len(path) >= min_length:
            paths.append([(x + 0.5, y + 0.5) for x, y in path])

    for point in sorted(foreground, key=lambda p: (p[1], p[0])):
        if all(_edge_visited(point, neighbor) for neighbor in neighbor_map[point]):
            continue
        path = _trace(point)
        if len(path) >= min_length:
            paths.append([(x + 0.5, y + 0.5) for x, y in path])

    return [simplify_path(path, tolerance=0.0) for path in paths if len(path) >= min_length]
