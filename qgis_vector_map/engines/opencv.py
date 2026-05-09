"""OpenCV-based vectorization engine with regional, edge, and linear modes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterator

from ..core.errors import DependencyError
from ..core.export import export_vector_layer
from ..core.geometry import validate_polygon_rings, repair_polygon_coordinates, snap_coordinates_to_grid, find_junctions, close_contour_to_polygon
from ..core.models import PipelineContext, ProgressCallback, StageName, VectorFeature, VectorLayer
from ..core.raster import RasterFrame
from .base import VectorizationEngine

try:
    import cv2
    import numpy as np

    _HAS_CV2 = True
except ImportError:
    cv2 = None  # type: ignore[assignment]
    np = None  # type: ignore[assignment]
    _HAS_CV2 = False


def _require_cv2() -> None:
    if not _HAS_CV2:
        raise DependencyError(
            "OpenCV (opencv-python-headless) is required for the OpenCV vectorization engine. "
            "Install it with: pip install opencv-python-headless>=4.8.0"
        )


@dataclass(frozen=True)
class _CVPreprocessedPayload:
    mode: str
    image: Any  # np.ndarray
    mask: Any | None = None  # np.ndarray binary mask
    contours: Any | None = None  # list of contours from cv2.findContours
    hierarchy: Any | None = None
    label_map: Any | None = None  # np.ndarray


class OpenCVVectorizationEngine(VectorizationEngine):
    """High-performance engine using OpenCV for contour detection and quantization."""

    name = "opencv-local"
    supported_modes = ("regional", "edge", "linear")

    def supports(self, profile: Any) -> bool:
        _require_cv2()
        mode = getattr(profile, "mode", None)
        if mode in self.supported_modes:
            return True
        return False

    def preprocess(self, context: PipelineContext) -> PipelineContext:
        _require_cv2()
        mode = getattr(context.profile, "mode", None)
        parameters = dict(getattr(context.profile, "parameters", {}))
        raster = context.raster
        if not isinstance(raster, RasterFrame):
            raise DependencyError("Pipeline context does not contain a valid raster frame.")

        # Get grayscale as numpy array
        gray = self._grayscale_to_numpy(raster)

        if mode == "regional":
            payload = self._preprocess_regional(gray, parameters)
        elif mode == "edge":
            payload = self._preprocess_edge(gray, parameters)
        elif mode == "linear":
            payload = self._preprocess_linear(gray, parameters)
        else:
            raise DependencyError(f"Unsupported profile mode: {mode!r}")

        context.store_artifact("preprocessed", payload)
        context.metadata["preprocess"] = {
            "mode": payload.mode,
            "grayscale_size": [raster.width, raster.height],
            "parameters": parameters,
        }
        return context

    def vectorize(self, context: PipelineContext) -> PipelineContext:
        _require_cv2()
        payload = context.artifact("preprocessed")
        mode = getattr(context.profile, "mode", None)
        parameters = dict(getattr(context.profile, "parameters", {}))
        if not isinstance(payload, _CVPreprocessedPayload):
            raise DependencyError("Preprocess stage did not produce the expected payload.")

        progress_cb: ProgressCallback | None = context.metadata.get("progress_callback")

        if mode == "regional":
            vector_layer = self._vectorize_regional(context, payload, parameters, progress_cb)
        elif mode == "edge":
            vector_layer = self._vectorize_edge(context, payload, parameters, progress_cb)
        elif mode == "linear":
            vector_layer = self._vectorize_linear(context, payload, parameters, progress_cb)
        else:
            raise DependencyError(f"Unsupported profile mode: {mode!r}")

        context.store_artifact("vector_layer", vector_layer)
        context.metadata["vectorize"] = {
            "feature_count": vector_layer.feature_count(),
            "geometry_types": sorted({f.geometry_type for f in vector_layer.features}),
        }
        return context

    def postprocess(self, context: PipelineContext) -> PipelineContext:
        _require_cv2()
        layer = context.artifact("vector_layer")
        if not isinstance(layer, VectorLayer):
            raise DependencyError("Vectorize stage did not produce a valid vector layer.")
        mode = getattr(context.profile, "mode", None)
        parameters = dict(getattr(context.profile, "parameters", {}))
        if mode == "regional":
            cleaned = self._postprocess_polygons(layer, parameters)
        else:
            cleaned = self._postprocess_lines(layer, parameters)
        context.store_artifact("vector_layer", cleaned)
        context.metadata["postprocess"] = {
            "feature_count": cleaned.feature_count(),
            "warnings": list(context.warnings),
        }
        return context

    def export(self, context: PipelineContext) -> PipelineContext:
        layer = context.artifact("vector_layer")
        if not isinstance(layer, VectorLayer):
            raise DependencyError("Postprocess stage did not produce a valid vector layer.")
        output_path = context.request.output_path
        requested_format = (
            getattr(context.profile, "export_format", None)
            or context.request.output_format
            or "auto"
        )
        exported_path = export_vector_layer(layer, output_path, requested_format=requested_format)
        context.store_artifact("output_path", exported_path)
        context.metadata["export"] = {
            "output_path": str(exported_path),
            "format": exported_path.suffix.lstrip(".") or requested_format,
        }
        return context

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _grayscale_to_numpy(raster: RasterFrame) -> np.ndarray:
        """Get grayscale data as a 2D uint8 numpy array."""
        arr = raster.array
        if arr is not None:
            if raster.bands == 1:
                return arr.copy()
            else:
                # Convert to grayscale
                if arr.ndim == 3:
                    if arr.shape[2] >= 3:
                        r = arr[:, :, 0].astype(np.float64)
                        g = arr[:, :, 1].astype(np.float64)
                        b = arr[:, :, 2].astype(np.float64)
                        gray = np.round(0.299 * r + 0.587 * g + 0.114 * b).astype(np.uint8)
                    else:
                        gray = arr[:, :, 0]
                    return gray
        # Fallback: convert from tuple representation
        gray_tuple = raster.grayscale_matrix()
        return np.array(gray_tuple, dtype=np.uint8)

    # ------------------------------------------------------------------
    # Regional
    # ------------------------------------------------------------------
    def _preprocess_regional(
        self, gray: np.ndarray, parameters: dict[str, Any]
    ) -> _CVPreprocessedPayload:
        max_colors = int(parameters.get("max_colors", 8))
        smoothing_radius = int(parameters.get("smoothing_radius", 0))

        kmeans_attempts = int(parameters.get("kmeans_attempts", 10))
        kmeans_eps = float(parameters.get("kmeans_eps", 0.01))
        data = gray.reshape((-1, 1)).astype(np.float32)
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, kmeans_eps)
        _, labels, centers = cv2.kmeans(
            data, max_colors, None, criteria, kmeans_attempts, cv2.KMEANS_PP_CENTERS
        )
        label_map = labels.reshape(gray.shape).astype(np.uint8)

        if smoothing_radius > 0:
            ksize = 2 * smoothing_radius + 1
            label_map = cv2.medianBlur(label_map, ksize)

        return _CVPreprocessedPayload(mode="regional", image=gray, label_map=label_map)

    def _vectorize_regional(
        self,
        context: PipelineContext,
        payload: _CVPreprocessedPayload,
        parameters: dict[str, Any],
        progress_cb: ProgressCallback | None,
    ) -> VectorLayer:
        label_map = payload.label_map
        if label_map is None:
            raise DependencyError("Regional preprocessing did not produce a label map.")

        min_area = int(parameters.get("min_region_area", 4))
        simplify_tolerance = float(parameters.get("simplify_tolerance", 0.0))
        drop_background = bool(parameters.get("drop_background", True))

        unique_labels = np.unique(label_map)
        if drop_background and len(unique_labels) > 0:
            from collections import Counter
            flat = label_map.flatten().tolist()
            counter = Counter(flat)
            bg_label = counter.most_common(1)[0][0]
        else:
            bg_label = -1

        features: list[VectorFeature] = []
        total_labels = len(unique_labels)
        progress_idx = 0

        for label in unique_labels:
            progress_idx += 1
            if progress_cb:
                progress_cb(
                    StageName.VECTORIZE,
                    progress_idx / max(1, total_labels),
                    f"Processing region {progress_idx}/{total_labels}",
                )
            if int(label) == int(bg_label):
                continue
            mask = (label_map == label).astype(np.uint8) * 255
            contours, hierarchy = cv2.findContours(
                mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_TC89_L1
            )

            # Group contours into polygon rings using hierarchy
            if hierarchy is not None:
                for idx, contour in enumerate(contours):
                    area = cv2.contourArea(contour)
                    if area < min_area:
                        continue

                    # Simplify with approxPolyDP
                    if simplify_tolerance > 0:
                        approx = cv2.approxPolyDP(contour, simplify_tolerance, True)
                    else:
                        approx = contour

                    rings = self._contour_to_polygon_rings(
                        idx, contours, hierarchy, min_area, simplify_tolerance
                    )
                    if not rings:
                        # Single contour without hierarchy — make a simple ring
                        ring = self._cv_contour_to_ring(approx)
                        if len(ring) >= 4:
                            rings = [ring]

                    if not rings:
                        continue

                    cleaned_rings = []
                    for ring in rings:
                        if len(ring) >= 4:
                            cleaned_rings.append([[float(x), float(y)] for x, y in ring])
                    if not cleaned_rings:
                        continue

                    features.append(
                        VectorFeature(
                            geometry_type="Polygon",
                            coordinates=cleaned_rings,
                            properties={
                                "feature_index": len(features),
                                "class_id": int(label),
                                "pixel_area": int(area),
                                "ring_count": len(cleaned_rings),
                                "profile": "regional-high-precision",
                            },
                        )
                    )
            else:
                # No hierarchy — each contour is independent
                for contour in contours:
                    area = cv2.contourArea(contour)
                    if area < min_area:
                        continue
                    if simplify_tolerance > 0:
                        approx = cv2.approxPolyDP(contour, simplify_tolerance, True)
                    else:
                        approx = contour
                    ring = self._cv_contour_to_ring(approx)
                    if len(ring) < 4:
                        continue
                    cleaned_rings = [[[float(x), float(y)] for x, y in ring]]
                    features.append(
                        VectorFeature(
                            geometry_type="Polygon",
                            coordinates=cleaned_rings,
                            properties={
                                "feature_index": len(features),
                                "class_id": int(label),
                                "pixel_area": int(area),
                                "ring_count": 1,
                                "profile": "regional-high-precision",
                            },
                        )
                    )

        return VectorLayer(
            features=features,
            name=context.request.layer_name,
            crs=str(context.raster.metadata.get("crs_wkt"))
            if context.raster.metadata.get("crs_wkt")
            else None,
            metadata={
                "profile": "regional-high-precision",
                "parameters": parameters,
                "source": context.raster.source_name,
            },
        )

    def _contour_to_polygon_rings(
        self, parent_idx: int, contours: list, hierarchy: Any,
        min_area: int, simplify_tolerance: float,
    ) -> list[list[tuple[float, float]]]:
        """Build outer ring + hole rings from a parent contour and its hierarchy children."""
        hierarchy = hierarchy[0]
        rings = []
        outer = contours[parent_idx]
        area = cv2.contourArea(outer)
        if area < min_area:
            return rings
        if simplify_tolerance > 0:
            outer_approx = cv2.approxPolyDP(outer, simplify_tolerance, True)
        else:
            outer_approx = outer
        outer_ring = self._cv_contour_to_ring(outer_approx)
        if len(outer_ring) < 4:
            return rings
        rings.append(outer_ring)

        # Find child contours (holes)
        child_idx = hierarchy[parent_idx][2]  # first child
        while child_idx != -1:
            child = contours[child_idx]
            child_area = cv2.contourArea(child)
            if child_area >= min_area:
                if simplify_tolerance > 0:
                    child_approx = cv2.approxPolyDP(child, simplify_tolerance, True)
                else:
                    child_approx = child
                child_ring = self._cv_contour_to_ring(child_approx)
                if len(child_ring) >= 4:
                    rings.append(child_ring)
            child_idx = hierarchy[child_idx][0]  # next sibling
        return rings

    @staticmethod
    def _cv_contour_to_ring(contour: Any) -> list[tuple[float, float]]:
        """Convert an OpenCV contour to a closed ring of (x, y) tuples."""
        if contour is None or len(contour) == 0:
            return []
        points = []
        for point in contour:
            x, y = float(point[0][0]), float(point[0][1])
            points.append((x, y))
        if points and points[0] != points[-1]:
            points.append(points[0])
        return points

    def _postprocess_polygons(self, layer: VectorLayer, parameters: dict[str, Any]) -> VectorLayer:
        min_area = float(parameters.get("min_region_area", 4))
        tolerance = float(parameters.get("simplify_tolerance", 0.0))
        cleaned: list[VectorFeature] = []
        for feature in layer.features:
            if feature.geometry_type != "Polygon":
                continue
            rings: list[list[list[float]]] = []
            for ring in feature.coordinates:
                if len(ring) < 4:
                    continue
                area = _polygon_area_shoelace(ring)
                if abs(area) < min_area:
                    continue
                rings.append(ring)

            rings = repair_polygon_coordinates(rings)
            snap_grid_size = float(parameters.get("snap_grid_size", 0.0))
            if snap_grid_size > 0:
                rings = snap_coordinates_to_grid(rings, "Polygon", snap_grid_size)
            if not rings:
                continue

            issues = validate_polygon_rings(rings)

            cleaned.append(
                VectorFeature(
                    geometry_type="Polygon",
                    coordinates=rings,
                    properties={**dict(feature.properties), "validated": True},
                )
            )
        return VectorLayer(
            features=cleaned,
            name=layer.name,
            crs=layer.crs,
            metadata={**layer.metadata, "postprocess": "polygon-cleanup"},
        )

    # ------------------------------------------------------------------
    # Edge
    # ------------------------------------------------------------------
    def _preprocess_edge(
        self, gray: np.ndarray, parameters: dict[str, Any]
    ) -> _CVPreprocessedPayload:
        edge_threshold1 = float(parameters.get("edge_canny_low", 50))
        edge_threshold2 = float(parameters.get("edge_canny_high", 150))
        blur_size = int(parameters.get("edge_blur", 3))

        blurred = cv2.GaussianBlur(gray, (blur_size, blur_size), 0)
        edges = cv2.Canny(blurred, edge_threshold1, edge_threshold2)
        contours, hierarchy = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_TC89_L1)

        return _CVPreprocessedPayload(
            mode="edge", image=gray, mask=edges, contours=contours, hierarchy=hierarchy
        )

    def _vectorize_edge(
        self,
        context: PipelineContext,
        payload: _CVPreprocessedPayload,
        parameters: dict[str, Any],
        progress_cb: ProgressCallback | None,
    ) -> VectorLayer:
        contours = payload.contours
        if contours is None:
            return VectorLayer(features=[], name=context.request.layer_name)

        min_line_length = int(parameters.get("min_line_length", 2))
        simplify_tolerance = float(parameters.get("simplify_tolerance", 0.5))

        features: list[VectorFeature] = []
        for idx, contour in enumerate(contours):
            if progress_cb and idx % 100 == 0:
                progress_cb(
                    StageName.VECTORIZE,
                    idx / max(1, len(contours)),
                    f"Tracing edge contour {idx}/{len(contours)}",
                )
            if simplify_tolerance > 0:
                approx = cv2.approxPolyDP(contour, simplify_tolerance, True)
            else:
                approx = contour
            ring = self._cv_contour_to_ring(approx)
            if len(ring) < min_line_length:
                continue
            coords = [[float(x), float(y)] for x, y in ring]
            features.append(
                VectorFeature(
                    geometry_type="LineString",
                    coordinates=coords,
                    properties={
                        "feature_index": len(features),
                        "profile": "edge-high-precision",
                        "path_length_px": _polyline_length(coords),
                    },
                )
            )

        return VectorLayer(
            features=features,
            name=context.request.layer_name,
            crs=str(context.raster.metadata.get("crs_wkt"))
            if context.raster.metadata.get("crs_wkt")
            else None,
            metadata={"profile": "edge-high-precision", "parameters": parameters},
        )

    def _postprocess_lines(self, layer: VectorLayer, parameters: dict[str, Any]) -> VectorLayer:
        tolerance = float(parameters.get("simplify_tolerance", 0.5))
        min_line_length = int(parameters.get("min_line_length", 2))
        extract_topology = bool(parameters.get("extract_topology", False))
        close_contours = bool(parameters.get("close_contours", False))

        cleaned: list[VectorFeature] = []
        for feature in layer.features:
            if feature.geometry_type != "LineString":
                continue
            points = [(float(x), float(y)) for x, y in feature.coordinates]
            if len(points) < min_line_length:
                continue
            cleaned.append(
                VectorFeature(
                    geometry_type="LineString",
                    coordinates=[[float(x), float(y)] for x, y in points],
                    properties={**dict(feature.properties), "validated": True},
                )
            )

        if close_contours:
            polygon_features = []
            line_features = []
            for feature in cleaned:
                if feature.geometry_type == "LineString" and len(feature.coordinates) >= 3:
                    closed = close_contour_to_polygon(feature.coordinates, max_gap=2.0)
                    if closed is not None:
                        polygon_features.append(
                            VectorFeature(
                                geometry_type="Polygon",
                                coordinates=closed,
                                properties=dict(feature.properties),
                            )
                        )
                        continue
                line_features.append(feature)
            cleaned = polygon_features + line_features

        junction_count = 0
        if extract_topology and cleaned:
            junctions = find_junctions(cleaned, snap_tolerance=tolerance)
            junction_count = len(junctions)
            annotated: list[VectorFeature] = []
            for idx, feature in enumerate(cleaned):
                connected_at = 0
                for junc_coord, feature_indices in junctions.items():
                    if idx in feature_indices:
                        connected_at += 1
                annotated.append(
                    VectorFeature(
                        geometry_type=feature.geometry_type,
                        coordinates=feature.coordinates,
                        properties={**dict(feature.properties), "junction_connections": connected_at},
                    )
                )
            cleaned = annotated

        return VectorLayer(
            features=cleaned,
            name=layer.name,
            crs=layer.crs,
            metadata={**layer.metadata, "postprocess": "line-cleanup", "junction_count": junction_count},
        )

    # ------------------------------------------------------------------
    # Linear
    # ------------------------------------------------------------------
    def _preprocess_linear(
        self, gray: np.ndarray, parameters: dict[str, Any]
    ) -> _CVPreprocessedPayload:
        threshold = parameters.get("foreground_threshold")
        polarity = str(parameters.get("foreground_polarity", "dark"))
        if threshold is None:
            if polarity == "dark":
                _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            else:
                _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        else:
            thresh_type = cv2.THRESH_BINARY_INV if polarity == "dark" else cv2.THRESH_BINARY
            _, binary = cv2.threshold(gray, int(threshold), 255, thresh_type)

        open_radius = int(parameters.get("open_radius", 1))
        close_radius = int(parameters.get("close_radius", 1))
        if open_radius > 0:
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * open_radius + 1, 2 * open_radius + 1))
            binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
        if close_radius > 0:
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * close_radius + 1, 2 * close_radius + 1))
            binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

        # Thinning via morphological operations
        skeleton = self._thin_image(binary)

        contours, hierarchy = cv2.findContours(skeleton, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
        return _CVPreprocessedPayload(
            mode="linear", image=gray, mask=skeleton, contours=contours, hierarchy=hierarchy
        )

    def _thin_image(self, binary: np.ndarray) -> np.ndarray:
        """Thin a binary image using morphological erosion."""
        try:
            from cv2 import ximgproc
            skeleton = ximgproc.thinning(binary)
            return skeleton
        except (ImportError, AttributeError):
            pass
        # Fallback: use Zhang-Suen-like thinning or just return the binary
        # For a safe fallback, use hit-or-miss based skeleton
        skeleton = np.zeros_like(binary)
        temp = binary.copy()
        element = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
        done = False
        max_iter = max(binary.shape) * 2
        iteration = 0
        while not done and iteration < max_iter:
            eroded = cv2.erode(temp, element)
            dilated = cv2.dilate(eroded, element)
            subtracted = cv2.subtract(temp, dilated)
            skeleton = cv2.bitwise_or(skeleton, subtracted)
            temp = eroded.copy()
            done = cv2.countNonZero(temp) == 0
            iteration += 1
        return skeleton

    def _vectorize_linear(
        self,
        context: PipelineContext,
        payload: _CVPreprocessedPayload,
        parameters: dict[str, Any],
        progress_cb: ProgressCallback | None,
    ) -> VectorLayer:
        contours = payload.contours
        if contours is None:
            return VectorLayer(features=[], name=context.request.layer_name)

        min_line_length = int(parameters.get("min_line_length", 2))
        simplify_tolerance = float(parameters.get("simplify_tolerance", 0.5))

        features: list[VectorFeature] = []
        for idx, contour in enumerate(contours):
            if progress_cb and idx % 100 == 0:
                progress_cb(
                    StageName.VECTORIZE,
                    idx / max(1, len(contours)),
                    f"Tracing linear contour {idx}/{len(contours)}",
                )
            if simplify_tolerance > 0:
                approx = cv2.approxPolyDP(contour, simplify_tolerance, True)
            else:
                approx = contour
            ring = self._cv_contour_to_ring(approx)
            if len(ring) < min_line_length:
                continue
            coords = [[float(x), float(y)] for x, y in ring]
            features.append(
                VectorFeature(
                    geometry_type="LineString",
                    coordinates=coords,
                    properties={
                        "feature_index": len(features),
                        "profile": "linear-high-precision",
                        "path_length_px": _polyline_length(coords),
                    },
                )
            )

        return VectorLayer(
            features=features,
            name=context.request.layer_name,
            crs=str(context.raster.metadata.get("crs_wkt"))
            if context.raster.metadata.get("crs_wkt")
            else None,
            metadata={"profile": "linear-high-precision", "parameters": parameters},
        )


# ------------------------------------------------------------------
# Utility functions
# ------------------------------------------------------------------
def _polygon_area_shoelace(ring: list[list[float]]) -> float:
    """Compute polygon area using the shoelace formula."""
    if len(ring) < 4:
        return 0.0
    area = 0.0
    for i in range(len(ring) - 1):
        x1, y1 = ring[i]
        x2, y2 = ring[i + 1]
        area += x1 * y2 - x2 * y1
    return area / 2.0


def _polyline_length(coords: list[list[float]]) -> float:
    """Compute polyline length."""
    if len(coords) < 2:
        return 0.0
    total = 0.0
    for i in range(len(coords) - 1):
        dx = coords[i + 1][0] - coords[i][0]
        dy = coords[i + 1][1] - coords[i][1]
        total += (dx * dx + dy * dy) ** 0.5
    return round(total, 3)
