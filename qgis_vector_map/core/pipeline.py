"""Pipeline orchestrator and execution helpers."""

from __future__ import annotations

import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ..engines.base import VectorizationEngine, build_default_registry
from ..processing_profiles import ResolvedProfile, resolve_profile
from .errors import ConfigurationError, DependencyError, PipelineError, StageExecutionError
from .models import (
    CancelCallback,
    PipelineContext,
    PipelineResult,
    ProgressCallback,
    StageName,
    StageReport,
    VectorFeature,
    VectorizationRequest,
    VectorLayer,
)
from .geometry import apply_geotransform, stitch_line_features
from .raster import RasterFrame


class PipelineOrchestrator:
    """Execute the preprocess -> vectorize -> postprocess -> export pipeline."""

    def __init__(self, *, engine_registry: Any | None = None) -> None:
        self.engine_registry = engine_registry or build_default_registry()

    def resolve_engine(self, profile: ResolvedProfile) -> VectorizationEngine:
        engine = self.engine_registry.resolve(profile)
        if engine is None:
            raise ConfigurationError(f"No engine is registered for profile '{profile.profile_id}'.")
        return engine

    def _check_cancelled(self, cancel_callback: CancelCallback | None, stage: StageName) -> None:
        if cancel_callback is not None and cancel_callback():
            raise PipelineError(f"Vectorization cancelled before stage '{stage.value}'.")

    def _make_stage_report(self, stage: StageName, context: PipelineContext) -> StageReport:
        report = StageReport(stage=stage)
        context.stage_reports.append(report)
        return report

    def _run_stage(
        self,
        *,
        context: PipelineContext,
        engine: VectorizationEngine,
        stage: StageName,
        handler: Callable[[PipelineContext], PipelineContext],
        progress_callback: ProgressCallback | None,
        cancel_callback: CancelCallback | None,
    ) -> PipelineContext:
        self._check_cancelled(cancel_callback, stage)
        report = self._make_stage_report(stage, context)
        report.mark_running()
        if progress_callback is not None:
            progress_callback(stage, 0.0, f"Starting {stage.value}")
        try:
            updated_context = handler(context)
        except Exception as exc:
            report.mark_failed(str(exc))
            raise StageExecutionError(stage.value, str(exc), cause=exc) from exc
        report.mark_completed(f"{stage.value} completed")
        if progress_callback is not None:
            progress_callback(stage, 1.0, f"Completed {stage.value}")
        return updated_context

    def _build_working_directory(self, request: VectorizationRequest) -> Path:
        working_directory = (
            Path(request.working_directory)
            if request.working_directory is not None
            else Path(tempfile.gettempdir()) / "qgis_vector_map"
        )
        working_directory.mkdir(parents=True, exist_ok=True)
        return working_directory

    def _build_base_metadata(
        self,
        *,
        request: VectorizationRequest,
        profile: ResolvedProfile,
        raster_load_options: RasterFrame.LoadOptions,
    ) -> dict[str, Any]:
        return {
            "request_metadata": dict(request.metadata),
            "requested_parameters": dict(request.parameters),
            "profile_id": profile.profile_id,
            "profile_mode": profile.mode,
            "engine_name": profile.engine_name,
            "execution_mode": getattr(request, "execution_mode", "auto"),
            "memory_policy": raster_load_options.memory_policy,
            "raster_load_options": {
                "max_pixels": raster_load_options.max_pixels,
                "max_estimated_bytes": raster_load_options.max_estimated_bytes,
                "chunk_size": raster_load_options.chunk_size,
                "memory_policy": raster_load_options.memory_policy,
            },
        }

    def _resolve_memory_policy(
        self,
        *,
        request: VectorizationRequest,
        raster_load_options: RasterFrame.LoadOptions,
    ) -> tuple[str, list[str]]:
        policy = raster_load_options.memory_policy
        warnings: list[str] = []
        if policy == "expert-override":
            has_explicit_override = (
                "max_pixels" in request.parameters or "max_estimated_bytes" in request.parameters
            )
            if not has_explicit_override:
                raise ConfigurationError(
                    "memory_policy='expert-override' requires explicit "
                    "'max_pixels' and/or 'max_estimated_bytes' in request parameters."
                )
            warnings.append(
                "memory_policy='expert-override' enabled: execution may use higher memory "
                "than strict defaults."
            )
        return policy, warnings

    def _check_auto_threshold(
        self,
        *,
        source: Any,
        max_pixels: int,
    ) -> tuple[bool, int, int]:
        """Check if raster exceeds auto-detection threshold without loading pixel data.

        Returns:
            (exceeds_threshold, pixel_count, threshold)
        """
        threshold = int(max_pixels * 0.75)

        if isinstance(source, RasterFrame):
            return False, source.width * source.height, threshold

        if isinstance(source, (str, Path)):
            source_path = Path(source)
            if source_path.exists():
                try:
                    from osgeo import gdal
                except Exception:
                    return False, 0, threshold
                dataset = gdal.Open(str(source_path))
                if dataset is not None:
                    width = int(getattr(dataset, "RasterXSize", 0) or 0)
                    height = int(getattr(dataset, "RasterYSize", 0) or 0)
                    pixels = width * height
                    return pixels > threshold, pixels, threshold
        return False, 0, threshold

    def _resolve_execution_mode(
        self,
        *,
        request: VectorizationRequest,
        raster_load_options: RasterFrame.LoadOptions,
        profile: ResolvedProfile,
    ) -> tuple[str, list[str]]:
        """Resolve execution_mode to effective memory_policy with auto-detection."""
        execution_mode = getattr(request, "execution_mode", "auto")
        warnings: list[str] = []

        if execution_mode == "auto":
            exceeds, pixels, threshold = self._check_auto_threshold(
                source=request.source,
                max_pixels=raster_load_options.max_pixels,
            )

            if exceeds:
                policy = "regional-tiles" if profile.mode == "regional" else "tiled"
                warnings.append(
                    f"Auto mode: tiled execution activated "
                    f"({pixels:,} px exceeds {threshold:,} threshold)."
                )
                if profile.mode != "regional":
                    warnings.append(
                        "Tiled execution for non-regional profiles: "
                        "line features at tile boundaries may be split."
                    )
            else:
                policy = "strict"
        elif execution_mode == "strict":
            exceeds, pixels, threshold = self._check_auto_threshold(
                source=request.source,
                max_pixels=raster_load_options.max_pixels,
            )
            if exceeds:
                warnings.append(
                    f"Strict mode: raster exceeds auto-detection threshold "
                    f"({pixels:,} > {threshold:,} px). "
                    f"May fail due to memory pressure. "
                    f"Consider switching to 'Tiled' execution mode."
                )
            policy = "strict"
        elif execution_mode == "tiled":
            policy = "regional-tiles" if profile.mode == "regional" else "tiled"
            if profile.mode != "regional":
                warnings.append(
                    "Tiled execution for non-regional profiles: "
                    "line features at tile boundaries may be split."
                )
        else:
            raise ConfigurationError(
                f"Invalid execution_mode: {execution_mode}. Must be one of: auto, strict, tiled."
            )

        return policy, warnings

    def _offset_coordinates(
        self, geometry_type: str, coordinates: Any, *, x_off: int, y_off: int
    ) -> Any:
        if geometry_type == "Point":
            x, y = coordinates
            return [float(x) + x_off, float(y) + y_off]
        if geometry_type in {"LineString", "MultiPoint"}:
            return [[float(x) + x_off, float(y) + y_off] for x, y in coordinates]
        if geometry_type == "Polygon":
            return [
                [[float(x) + x_off, float(y) + y_off] for x, y in ring] for ring in coordinates
            ]
        if geometry_type == "MultiLineString":
            return [
                [[float(x) + x_off, float(y) + y_off] for x, y in line] for line in coordinates
            ]
        if geometry_type == "MultiPolygon":
            return [
                [
                    [[float(x) + x_off, float(y) + y_off] for x, y in ring]
                    for ring in polygon
                ]
                for polygon in coordinates
            ]
        return coordinates

    def _apply_geotransform_to_layer(
        self, layer: VectorLayer, geotransform: tuple[float, ...] | None
    ) -> VectorLayer:
        if geotransform is None or len(geotransform) < 6:
            return layer
        transformed_features = [
            VectorFeature(
                geometry_type=feature.geometry_type,
                coordinates=apply_geotransform(
                    feature.geometry_type, feature.coordinates, geotransform
                ),
                properties=feature.properties,
            )
            for feature in layer.features
        ]
        return VectorLayer(
            features=transformed_features,
            name=layer.name,
            crs=layer.crs,
            geotransform=geotransform,
            metadata=layer.metadata,
        )

    def _to_grayscale(self, channels: list[int]) -> int:
        if len(channels) == 1:
            value = channels[0]
            return max(0, min(255, int(value)))
        rgb = (channels + [0, 0, 0])[:3]
        gray = int(round(0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]))
        return max(0, min(255, gray))

    def _load_raster_tile(
        self,
        *,
        dataset: Any,
        source_name: str,
        x_off: int,
        y_off: int,
        x_size: int,
        y_size: int,
        source_metadata: dict[str, Any],
    ) -> RasterFrame:
        window = dataset.ReadAsArray(x_off, y_off, x_size, y_size)
        if window is None:
            raise ConfigurationError(
                f"GDAL returned no data for tile x={x_off}:{x_off + x_size}, "
                f"y={y_off}:{y_off + y_size}."
            )
        # Use numpy-backed tile loading via RasterFrame._window_to_grayscale_ndarray
        grayscale_array = RasterFrame._window_to_grayscale_ndarray(window, x_size, y_size)
        tile_metadata = {
            **source_metadata,
            "load_strategy": "gdal-tiles",
            "tile_origin": [x_off, y_off],
            "tile_size": [x_size, y_size],
        }
        return RasterFrame(
            pixels=grayscale_array,
            width=x_size,
            height=y_size,
            bands=1,
            source_name=source_name,
            metadata=tile_metadata,
        )

    def _run_standard_pipeline(
        self,
        *,
        request: VectorizationRequest,
        profile: ResolvedProfile,
        engine: VectorizationEngine,
        raster_load_options: RasterFrame.LoadOptions,
        progress_callback: ProgressCallback | None,
        cancel_callback: CancelCallback | None,
        warnings: list[str],
    ) -> PipelineResult:
        raster = RasterFrame.load(request.source, options=raster_load_options)
        context = PipelineContext(
            request=request,
            profile=profile,
            raster=raster,
            working_directory=self._build_working_directory(request),
            metadata=self._build_base_metadata(
                request=request,
                profile=profile,
                raster_load_options=raster_load_options,
            ),
        )
        context.warnings.extend(warnings)
        context.metadata["resolved_engine"] = engine.name
        if warnings:
            context.metadata["memory_policy_warnings"] = list(warnings)

        if progress_callback is not None:
            progress_callback(StageName.PREPROCESS, 0.0, "Resolved engine and raster input")

        context = self._run_stage(
            context=context,
            engine=engine,
            stage=StageName.PREPROCESS,
            handler=engine.preprocess,
            progress_callback=progress_callback,
            cancel_callback=cancel_callback,
        )
        context = self._run_stage(
            context=context,
            engine=engine,
            stage=StageName.VECTORIZE,
            handler=engine.vectorize,
            progress_callback=progress_callback,
            cancel_callback=cancel_callback,
        )
        context = self._run_stage(
            context=context,
            engine=engine,
            stage=StageName.POSTPROCESS,
            handler=engine.postprocess,
            progress_callback=progress_callback,
            cancel_callback=cancel_callback,
        )

        geotransform = raster.metadata.get("geotransform")
        if geotransform is not None:
            layer = context.artifacts["vector_layer"]
            if isinstance(layer, VectorLayer):
                transformed = self._apply_geotransform_to_layer(layer, tuple(geotransform))
                context.store_artifact("vector_layer", transformed)
        else:
            context.add_warning(
                "No geotransform found in raster metadata; "
                "output coordinates will be in pixel space."
            )

        context = self._run_stage(
            context=context,
            engine=engine,
            stage=StageName.EXPORT,
            handler=engine.export,
            progress_callback=progress_callback,
            cancel_callback=cancel_callback,
        )

        vector_layer: VectorLayer = context.artifacts["vector_layer"]
        output_path: Path = context.artifacts["output_path"]
        return PipelineResult(
            output_path=output_path,
            vector_layer=vector_layer,
            stage_reports=list(context.stage_reports),
            profile_id=profile.profile_id,
            engine_name=engine.name,
            metadata=dict(context.metadata),
            warnings=list(context.warnings),
        )

    def _run_tiled_pipeline(
        self,
        *,
        request: VectorizationRequest,
        profile: ResolvedProfile,
        engine: VectorizationEngine,
        raster_load_options: RasterFrame.LoadOptions,
        progress_callback: ProgressCallback | None,
        cancel_callback: CancelCallback | None,
        warnings: list[str],
    ) -> PipelineResult:
        is_regional = profile.mode == "regional"
        load_strategy = "regional-tiles" if is_regional else "tiled"
        if not is_regional:
            warnings.append(
                "Tiled execution for non-regional profiles: "
                "line features at tile boundaries may be split."
            )
        if not isinstance(request.source, (str, Path)):
            raise ConfigurationError(
                "memory_policy='tiled' requires a raster path source."
            )
        source_path = Path(request.source)
        if not source_path.exists():
            raise ConfigurationError(f"Raster input does not exist: {source_path}")
        try:
            from osgeo import gdal  # type: ignore
        except Exception as exc:
            raise DependencyError(
                "memory_policy='tiled' requires GDAL (osgeo)."
            ) from exc

        dataset = gdal.Open(str(source_path))
        if dataset is None:
            raise ConfigurationError(f"GDAL could not open raster file: {source_path}")

        width = int(getattr(dataset, "RasterXSize", 0) or 0)
        height = int(getattr(dataset, "RasterYSize", 0) or 0)
        bands = max(1, int(getattr(dataset, "RasterCount", 1) or 1))
        if width <= 0 or height <= 0:
            raise ConfigurationError(
                f"GDAL returned invalid raster dimensions for '{source_path}': {width}x{height}."
            )
        tile_size = int(profile.parameter("tile_size", profile.parameter("chunk_size", 2048)))
        if tile_size <= 0:
            raise ConfigurationError("Invalid tile_size for tiled mode. Expected > 0.")

        projection = dataset.GetProjection()
        geotransform = dataset.GetGeoTransform(can_return_null=True)
        source_metadata: dict[str, Any] = {"source_path": str(source_path)}
        if projection:
            source_metadata["crs_wkt"] = projection
        if geotransform:
            source_metadata["geotransform"] = tuple(float(value) for value in geotransform)

        tile_plan: list[tuple[int, int, int, int]] = []
        for y_off in range(0, height, tile_size):
            y_size = min(tile_size, height - y_off)
            for x_off in range(0, width, tile_size):
                x_size = min(tile_size, width - x_off)
                tile_plan.append((x_off, y_off, x_size, y_size))

        context = PipelineContext(
            request=request,
            profile=profile,
            raster=RasterFrame.from_matrix(
                [[0]],
                source_name=source_path.name,
                metadata={**source_metadata, "load_strategy": load_strategy},
            ),
            working_directory=self._build_working_directory(request),
            metadata=self._build_base_metadata(
                request=request,
                profile=profile,
                raster_load_options=raster_load_options,
            ),
        )
        context.warnings.extend(warnings)
        context.metadata["resolved_engine"] = engine.name
        context.metadata["tile_execution"] = {
            "tile_size": tile_size,
            "tile_count": len(tile_plan),
            "source_width": width,
            "source_height": height,
            "source_bands": bands,
        }
        if warnings:
            context.metadata["memory_policy_warnings"] = list(warnings)

        def _preprocess_tiled(tile_context: PipelineContext) -> PipelineContext:
            tile_context.store_artifact("tile_plan", tile_plan)
            tile_context.metadata["preprocess"] = {
                "mode": load_strategy,
                "tile_count": len(tile_plan),
                "tile_size": tile_size,
            }
            return tile_context

        def _vectorize_tiled(tile_context: PipelineContext) -> PipelineContext:
            merged_features: list[VectorFeature] = []
            tile_stats: list[dict[str, Any]] = []
            total_tiles = max(1, len(tile_plan))
            for tile_index, (x_off, y_off, x_size, y_size) in enumerate(tile_plan):
                self._check_cancelled(cancel_callback, StageName.VECTORIZE)
                tile_raster = self._load_raster_tile(
                    dataset=dataset,
                    source_name=source_path.name,
                    x_off=x_off,
                    y_off=y_off,
                    x_size=x_size,
                    y_size=y_size,
                    source_metadata=source_metadata,
                )
                tile_request = VectorizationRequest(
                    source=tile_raster,
                    profile_id=profile.profile_id,
                    output_path=request.output_path,
                    output_format=request.output_format,
                    layer_name=request.layer_name,
                    parameters=profile.parameters,
                    metadata={
                        **dict(request.metadata),
                        "tile_index": tile_index,
                        "tile_origin": [x_off, y_off],
                    },
                    working_directory=request.working_directory,
                )
                tile_execution_context = PipelineContext(
                    request=tile_request,
                    profile=profile,
                    raster=tile_raster,
                    working_directory=tile_context.working_directory,
                )
                tile_execution_context = engine.preprocess(tile_execution_context)
                tile_execution_context = engine.vectorize(tile_execution_context)
                tile_layer = tile_execution_context.artifact("vector_layer")
                if not isinstance(tile_layer, VectorLayer):
                    raise ConfigurationError("Tile vectorization did not produce a valid vector layer.")
                for feature in tile_layer.features:
                    shifted = self._offset_coordinates(
                        feature.geometry_type,
                        feature.coordinates,
                        x_off=x_off,
                        y_off=y_off,
                    )
                    merged_features.append(
                        VectorFeature(
                            geometry_type=feature.geometry_type,
                            coordinates=shifted,
                            properties={
                                **dict(feature.properties),
                                "feature_index": len(merged_features),
                                "tile_index": tile_index,
                                "tile_origin_x": x_off,
                                "tile_origin_y": y_off,
                            },
                        )
                    )
                tile_stats.append(
                    {
                        "tile_index": tile_index,
                        "origin": [x_off, y_off],
                        "size": [x_size, y_size],
                        "feature_count": tile_layer.feature_count(),
                    }
                )
                if progress_callback is not None:
                    progress_callback(
                        StageName.VECTORIZE,
                        float(tile_index + 1) / float(total_tiles),
                        f"Processed tile {tile_index + 1}/{total_tiles}",
                    )

            merged_layer = VectorLayer(
                features=merged_features,
                name=request.layer_name,
                crs=str(source_metadata.get("crs_wkt")) if source_metadata.get("crs_wkt") else None,
                metadata={
                    "profile": profile.profile_id,
                    "parameters": dict(profile.parameters),
                    "source": source_path.name,
                    "load_strategy": load_strategy,
                    "tile_size": tile_size,
                    "tile_count": len(tile_plan),
                },
            )
            tile_context.store_artifact("vector_layer", merged_layer)
            tile_context.metadata["vectorize"] = {
                "feature_count": merged_layer.feature_count(),
                "tile_count": len(tile_plan),
                "tile_stats": tile_stats,
                "geometry_types": sorted(
                    {feature.geometry_type for feature in merged_layer.features}
                ),
            }
            return tile_context

        context = self._run_stage(
            context=context,
            engine=engine,
            stage=StageName.PREPROCESS,
            handler=_preprocess_tiled,
            progress_callback=progress_callback,
            cancel_callback=cancel_callback,
        )
        context = self._run_stage(
            context=context,
            engine=engine,
            stage=StageName.VECTORIZE,
            handler=_vectorize_tiled,
            progress_callback=progress_callback,
            cancel_callback=cancel_callback,
        )
        context = self._run_stage(
            context=context,
            engine=engine,
            stage=StageName.POSTPROCESS,
            handler=engine.postprocess,
            progress_callback=progress_callback,
            cancel_callback=cancel_callback,
        )

        raster_geotransform = context.raster.metadata.get("geotransform")
        if raster_geotransform is not None:
            layer = context.artifacts["vector_layer"]
            if isinstance(layer, VectorLayer):
                transformed = self._apply_geotransform_to_layer(
                    layer, tuple(raster_geotransform)
                )
                context.store_artifact("vector_layer", transformed)
        else:
            context.add_warning(
                "No geotransform found in raster metadata; "
                "output coordinates will be in pixel space."
            )

        if profile.mode != "regional":
            layer = context.artifacts["vector_layer"]
            if isinstance(layer, VectorLayer):
                tolerance = float(profile.parameter("simplify_tolerance", 0.5))
                stitched = stitch_line_features(layer.features, snap_tolerance=max(tolerance, 1.0))
                layer = VectorLayer(
                    features=stitched,
                    name=layer.name,
                    crs=layer.crs,
                    geotransform=layer.geotransform,
                    metadata=layer.metadata,
                )
                context.store_artifact("vector_layer", layer)

        context = self._run_stage(
            context=context,
            engine=engine,
            stage=StageName.EXPORT,
            handler=engine.export,
            progress_callback=progress_callback,
            cancel_callback=cancel_callback,
        )

        vector_layer: VectorLayer = context.artifacts["vector_layer"]
        output_path: Path = context.artifacts["output_path"]
        return PipelineResult(
            output_path=output_path,
            vector_layer=vector_layer,
            stage_reports=list(context.stage_reports),
            profile_id=profile.profile_id,
            engine_name=engine.name,
            metadata=dict(context.metadata),
            warnings=list(context.warnings),
        )

    def run(
        self,
        request: VectorizationRequest,
        *,
        progress_callback: ProgressCallback | None = None,
        cancel_callback: CancelCallback | None = None,
    ) -> PipelineResult:
        profile = resolve_profile(request.profile_id, request.parameters)
        raster_load_options = RasterFrame.LoadOptions.from_parameters(
            profile.parameters,
            profile_mode=profile.mode,
        )
        engine = self.resolve_engine(profile)
        memory_policy, warnings = self._resolve_execution_mode(
            request=request,
            raster_load_options=raster_load_options,
            profile=profile,
        )
        if memory_policy in ("regional-tiles", "tiled"):
            return self._run_tiled_pipeline(
                request=request,
                profile=profile,
                engine=engine,
                raster_load_options=raster_load_options,
                progress_callback=progress_callback,
                cancel_callback=cancel_callback,
                warnings=warnings,
            )
        return self._run_standard_pipeline(
            request=request,
            profile=profile,
            engine=engine,
            raster_load_options=raster_load_options,
            progress_callback=progress_callback,
            cancel_callback=cancel_callback,
            warnings=warnings,
        )


_DEFAULT_ORCHESTRATOR = PipelineOrchestrator()


def run_vectorization(
    request: VectorizationRequest,
    *,
    progress_callback: ProgressCallback | None = None,
    cancel_callback: CancelCallback | None = None,
) -> PipelineResult:
    return _DEFAULT_ORCHESTRATOR.run(
        request,
        progress_callback=progress_callback,
        cancel_callback=cancel_callback,
    )
