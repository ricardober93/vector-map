"""Shared core package for the vector map plugin."""

from .errors import ConfigurationError, DependencyError, ExportError, GeometryError, PipelineError, StageExecutionError, VectorMapError
from .models import (
    CancelCallback,
    PipelineContext,
    PipelineResult,
    ProgressCallback,
    StageName,
    StageReport,
    StageStatus,
    VectorFeature,
    VectorLayer,
    VectorizationRequest,
)
from .raster import RasterFrame

__all__ = [
    "CancelCallback",
    "ConfigurationError",
    "DependencyError",
    "ExportError",
    "GeometryError",
    "PipelineContext",
    "PipelineError",
    "PipelineResult",
    "ProgressCallback",
    "RasterFrame",
    "StageExecutionError",
    "StageName",
    "StageReport",
    "StageStatus",
    "VectorFeature",
    "VectorLayer",
    "VectorMapError",
    "VectorizationRequest",
]
