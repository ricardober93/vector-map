"""Pipeline orchestrator and execution helpers."""

from __future__ import annotations

import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ..engines.base import VectorizationEngine, build_default_registry
from ..processing_profiles import ResolvedProfile, resolve_profile
from .errors import ConfigurationError, PipelineError, StageExecutionError
from .models import (
    CancelCallback,
    PipelineContext,
    PipelineResult,
    ProgressCallback,
    StageName,
    StageReport,
    VectorizationRequest,
    VectorLayer,
)
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
        raster = RasterFrame.load(request.source, options=raster_load_options)
        working_directory = (
            Path(request.working_directory)
            if request.working_directory is not None
            else Path(tempfile.gettempdir()) / "qgis_vector_map"
        )
        working_directory.mkdir(parents=True, exist_ok=True)

        context = PipelineContext(
            request=request,
            profile=profile,
            raster=raster,
            working_directory=working_directory,
            metadata={
                "request_metadata": dict(request.metadata),
                "requested_parameters": dict(request.parameters),
                "profile_id": profile.profile_id,
                "profile_mode": profile.mode,
                "engine_name": profile.engine_name,
                "raster_load_options": {
                    "max_pixels": raster_load_options.max_pixels,
                    "max_estimated_bytes": raster_load_options.max_estimated_bytes,
                    "chunk_size": raster_load_options.chunk_size,
                },
            },
        )

        engine = self.resolve_engine(profile)
        context.metadata["resolved_engine"] = engine.name

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
