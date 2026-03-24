"""Classic local vectorization engine."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..core.errors import ConfigurationError, GeometryError
from ..core.export import export_vector_layer
from ..core.geometry import (
    auto_threshold,
    binary_close,
    binary_dilate,
    binary_erode,
    binary_open,
    close_ring,
    connected_components,
    majority_filter,
    polygon_area,
    polygon_centroid,
    polygonize_label_map,
    polyline_length,
    point_in_polygon,
    otsu_threshold,
    simplify_path,
    sobel_edge_magnitude,
    threshold_matrix,
    trace_skeleton_paths,
    zhang_suen_thinning,
)
from ..core.models import PipelineContext, VectorFeature, VectorLayer
from ..core.raster import RasterFrame


@dataclass(frozen=True)
class _PreprocessedPayload:
    mode: str
    grayscale: tuple[tuple[int, ...], ...]
    label_map: tuple[tuple[int, ...], ...] | None = None
    palette: tuple[Any, ...] | None = None
    binary_mask: tuple[tuple[int, ...], ...] | None = None
    edge_map: tuple[tuple[int, ...], ...] | None = None
    background_label: int | None = None


class ClassicVectorizationEngine:
    """High-precision local engine with regional, edge, and linear profiles."""

    name = "classic-local"
    supported_modes = ("regional", "edge", "linear")

    def supports(self, profile: Any) -> bool:
        mode = getattr(profile, "mode", None)
        if mode in self.supported_modes:
            return True
        return False

    # ------------------------------------------------------------------
    # Stage helpers
    # ------------------------------------------------------------------
    def preprocess(self, context: PipelineContext) -> PipelineContext:
        mode = getattr(context.profile, "mode", None)
        parameters = dict(getattr(context.profile, "parameters", {}))
        raster = context.raster
        if not isinstance(raster, RasterFrame):
            raise ConfigurationError("Pipeline context does not contain a valid raster frame.")

        grayscale = raster.grayscale_matrix()
        if mode == "regional":
            payload = self._preprocess_regional(grayscale, parameters)
        elif mode == "edge":
            payload = self._preprocess_edge(grayscale, parameters)
        elif mode == "linear":
            payload = self._preprocess_linear(grayscale, parameters)
        else:
            raise ConfigurationError(f"Unsupported profile mode: {mode!r}")

        context.store_artifact("preprocessed", payload)
        context.metadata["preprocess"] = {
            "mode": payload.mode,
            "grayscale_size": [raster.width, raster.height],
            "parameters": parameters,
        }
        return context

    def vectorize(self, context: PipelineContext) -> PipelineContext:
        payload = context.artifact("preprocessed")
        mode = getattr(context.profile, "mode", None)
        parameters = dict(getattr(context.profile, "parameters", {}))
        if not isinstance(payload, _PreprocessedPayload):
            raise ConfigurationError("Preprocess stage did not produce the expected payload.")

        if mode == "regional":
            vector_layer = self._vectorize_regional(context, payload, parameters)
        elif mode == "edge":
            vector_layer = self._vectorize_edge(context, payload, parameters)
        elif mode == "linear":
            vector_layer = self._vectorize_linear(context, payload, parameters)
        else:
            raise ConfigurationError(f"Unsupported profile mode: {mode!r}")

        context.store_artifact("vector_layer", vector_layer)
        context.metadata["vectorize"] = {
            "feature_count": vector_layer.feature_count(),
            "geometry_types": sorted({feature.geometry_type for feature in vector_layer.features}),
        }
        return context

    def postprocess(self, context: PipelineContext) -> PipelineContext:
        layer = context.artifact("vector_layer")
        if not isinstance(layer, VectorLayer):
            raise ConfigurationError("Vectorize stage did not produce a valid vector layer.")

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
            raise ConfigurationError("Postprocess stage did not produce a valid vector layer.")
        output_path = context.request.output_path
        requested_format = getattr(context.profile, "export_format", None) or context.request.output_format or "auto"
        exported_path = export_vector_layer(layer, output_path, requested_format=requested_format)
        context.store_artifact("output_path", exported_path)
        context.metadata["export"] = {
            "output_path": str(exported_path),
            "format": exported_path.suffix.lstrip(".") or requested_format,
        }
        return context

    # ------------------------------------------------------------------
    # Regional profile
    # ------------------------------------------------------------------
    def _preprocess_regional(self, grayscale: tuple[tuple[int, ...], ...], parameters: dict[str, Any]) -> _PreprocessedPayload:
        max_colors = int(parameters.get("max_colors", 8))
        background_policy = str(parameters.get("background_policy", "dominant"))
        smoothing_radius = int(parameters.get("smoothing_radius", 1))
        unique_values = Counter(value for row in grayscale for value in row)
        width = len(grayscale[0]) if grayscale else 0
        height = len(grayscale)

        if len(unique_values) <= max_colors:
            sorted_labels = [value for value, _ in unique_values.most_common()]
            palette = tuple(sorted_labels)
            label_index = {value: index for index, value in enumerate(sorted_labels)}
            label_map = tuple(tuple(label_index[value] for value in row) for row in grayscale)
        else:
            bucket_count = max(2, round(max_colors ** 0.5))
            bucket_size = max(1, 256 // bucket_count)
            labels = tuple(tuple(min(max_colors - 1, value // bucket_size) for value in row) for row in grayscale)
            palette = tuple(sorted(set(value for row in labels for value in row)))
            label_map = labels

        if smoothing_radius > 0:
            label_map = majority_filter(label_map, radius=smoothing_radius)

        label_counter = Counter(value for row in label_map for value in row)
        background_label = label_counter.most_common(1)[0][0] if background_policy == "dominant" and label_counter else None
        return _PreprocessedPayload(
            mode="regional",
            grayscale=grayscale,
            label_map=label_map,
            palette=palette,
            background_label=background_label,
        )

    def _vectorize_regional(
        self,
        context: PipelineContext,
        payload: _PreprocessedPayload,
        parameters: dict[str, Any],
    ) -> VectorLayer:
        if payload.label_map is None:
            raise ConfigurationError("Regional preprocessing did not produce a label map.")
        min_region_area = int(parameters.get("min_region_area", 4))
        min_hole_area = int(parameters.get("min_hole_area", 4))
        simplify_tolerance = float(parameters.get("simplify_tolerance", 0.0))
        drop_background = bool(parameters.get("drop_background", True))

        raw_features = polygonize_label_map(
            payload.label_map,
            min_component_area=min_region_area,
            background_label=payload.background_label if drop_background else None,
            connectivity=int(parameters.get("connectivity", 4)),
        )

        features: list[VectorFeature] = []
        for index, feature in enumerate(raw_features):
            cleaned_rings = []
            for ring in feature["coordinates"]:
                simplified = simplify_path([tuple(point) for point in ring], tolerance=simplify_tolerance)
                if len(simplified) < 4:
                    continue
                ring_points = close_ring(simplified)
                if abs(polygon_area(ring_points)) < float(min_hole_area):
                    continue
                cleaned_rings.append([[float(x), float(y)] for x, y in ring_points])
            if not cleaned_rings:
                continue
            properties = {
                "feature_index": index,
                "class_id": int(feature["label"]),
                "pixel_area": int(feature["area_px"]),
                "ring_count": int(feature["ring_count"]),
                "profile": "regional-high-precision",
            }
            features.append(VectorFeature(geometry_type="Polygon", coordinates=cleaned_rings, properties=properties))

        layer = VectorLayer(
            features=features,
            name=context.request.layer_name,
            crs=str(context.raster.metadata.get("crs_wkt")) if context.raster.metadata.get("crs_wkt") else None,
            metadata={
                "profile": "regional-high-precision",
                "parameters": parameters,
                "source": context.raster.source_name,
            },
        )
        return layer

    def _postprocess_polygons(self, layer: VectorLayer, parameters: dict[str, Any]) -> VectorLayer:
        min_area = float(parameters.get("min_region_area", 4))
        tolerance = float(parameters.get("simplify_tolerance", 0.0))
        cleaned_features: list[VectorFeature] = []
        for feature in layer.features:
            if feature.geometry_type != "Polygon":
                continue
            rings: list[list[list[float]]] = []
            for ring in feature.coordinates:
                points = [(float(x), float(y)) for x, y in ring]
                simplified = simplify_path(points, tolerance=tolerance)
                if len(simplified) < 4:
                    continue
                cleaned_ring = close_ring(simplified)
                if abs(polygon_area(cleaned_ring)) < min_area:
                    continue
                rings.append([[float(x), float(y)] for x, y in cleaned_ring])
            if not rings:
                continue
            cleaned_features.append(
                VectorFeature(
                    geometry_type="Polygon",
                    coordinates=rings,
                    properties={**dict(feature.properties), "validated": True},
                )
            )
        return VectorLayer(
            features=cleaned_features,
            name=layer.name,
            crs=layer.crs,
            metadata={**layer.metadata, "postprocess": "polygon-cleanup"},
        )

    # ------------------------------------------------------------------
    # Edge profile
    # ------------------------------------------------------------------
    def _preprocess_edge(self, grayscale: tuple[tuple[int, ...], ...], parameters: dict[str, Any]) -> _PreprocessedPayload:
        edge_threshold = int(parameters.get("edge_threshold", 0) or 0)
        edge_map = sobel_edge_magnitude(grayscale)
        if edge_threshold <= 0:
            edge_threshold = otsu_threshold(edge_map) or auto_threshold(edge_map)
        binary = threshold_matrix(edge_map, edge_threshold, polarity="high")
        closing_radius = int(parameters.get("close_radius", 1))
        if closing_radius > 0:
            binary = binary_close(binary, radius=closing_radius)
        return _PreprocessedPayload(mode="edge", grayscale=grayscale, binary_mask=binary, edge_map=edge_map)

    def _vectorize_edge(self, context: PipelineContext, payload: _PreprocessedPayload, parameters: dict[str, Any]) -> VectorLayer:
        if payload.binary_mask is None:
            raise ConfigurationError("Edge preprocessing did not produce a binary mask.")
        min_line_length = int(parameters.get("min_line_length", 2))
        simplify_tolerance = float(parameters.get("simplify_tolerance", 0.5))
        paths = trace_skeleton_paths(zhang_suen_thinning(payload.binary_mask), min_length=min_line_length)
        features = [
            VectorFeature(
                geometry_type="LineString",
                coordinates=[[float(x), float(y)] for x, y in simplify_path(path, tolerance=simplify_tolerance)],
                properties={
                    "feature_index": index,
                    "profile": "edge-high-precision",
                    "path_length_px": round(polyline_length(path), 3),
                },
            )
            for index, path in enumerate(paths)
            if len(path) >= min_line_length
        ]
        return VectorLayer(
            features=features,
            name=context.request.layer_name,
            crs=str(context.raster.metadata.get("crs_wkt")) if context.raster.metadata.get("crs_wkt") else None,
            metadata={"profile": "edge-high-precision", "parameters": parameters},
        )

    def _postprocess_lines(self, layer: VectorLayer, parameters: dict[str, Any]) -> VectorLayer:
        tolerance = float(parameters.get("simplify_tolerance", 0.5))
        min_line_length = int(parameters.get("min_line_length", 2))
        cleaned: list[VectorFeature] = []
        for feature in layer.features:
            if feature.geometry_type != "LineString":
                continue
            points = [(float(x), float(y)) for x, y in feature.coordinates]
            simplified = simplify_path(points, tolerance=tolerance)
            if len(simplified) < min_line_length:
                continue
            cleaned.append(
                VectorFeature(
                    geometry_type="LineString",
                    coordinates=[[float(x), float(y)] for x, y in simplified],
                    properties={**dict(feature.properties), "validated": True},
                )
            )
        return VectorLayer(
            features=cleaned,
            name=layer.name,
            crs=layer.crs,
            metadata={**layer.metadata, "postprocess": "line-cleanup"},
        )

    # ------------------------------------------------------------------
    # Linear profile
    # ------------------------------------------------------------------
    def _preprocess_linear(self, grayscale: tuple[tuple[int, ...], ...], parameters: dict[str, Any]) -> _PreprocessedPayload:
        threshold = parameters.get("foreground_threshold")
        if threshold is None:
            threshold = otsu_threshold(grayscale) or auto_threshold(grayscale)
        polarity = str(parameters.get("foreground_polarity", "dark"))
        binary = threshold_matrix(grayscale, int(threshold), polarity="low" if polarity == "dark" else "high")
        open_radius = int(parameters.get("open_radius", 1))
        close_radius = int(parameters.get("close_radius", 1))
        if open_radius > 0:
            binary = binary_open(binary, radius=open_radius)
        if close_radius > 0:
            binary = binary_close(binary, radius=close_radius)
        skeleton = zhang_suen_thinning(binary) if bool(parameters.get("skeletonize", True)) else binary
        return _PreprocessedPayload(mode="linear", grayscale=grayscale, binary_mask=binary, edge_map=skeleton)

    def _vectorize_linear(self, context: PipelineContext, payload: _PreprocessedPayload, parameters: dict[str, Any]) -> VectorLayer:
        skeleton = payload.edge_map or payload.binary_mask
        if skeleton is None:
            raise ConfigurationError("Linear preprocessing did not produce a skeleton or binary mask.")
        min_line_length = int(parameters.get("min_line_length", 2))
        simplify_tolerance = float(parameters.get("simplify_tolerance", 0.5))
        paths = trace_skeleton_paths(skeleton, min_length=min_line_length)
        features = [
            VectorFeature(
                geometry_type="LineString",
                coordinates=[[float(x), float(y)] for x, y in simplify_path(path, tolerance=simplify_tolerance)],
                properties={
                    "feature_index": index,
                    "profile": "linear-high-precision",
                    "path_length_px": round(polyline_length(path), 3),
                },
            )
            for index, path in enumerate(paths)
            if len(path) >= min_line_length
        ]
        return VectorLayer(
            features=features,
            name=context.request.layer_name,
            crs=str(context.raster.metadata.get("crs_wkt")) if context.raster.metadata.get("crs_wkt") else None,
            metadata={"profile": "linear-high-precision", "parameters": parameters},
        )
