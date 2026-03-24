"""Domain-specific errors for vector map vectorization."""

from __future__ import annotations


class VectorMapError(RuntimeError):
    """Base error for the vectorization pipeline."""


class DependencyError(VectorMapError):
    """Raised when an optional runtime dependency is required but unavailable."""


class ConfigurationError(VectorMapError):
    """Raised when user supplied configuration or profile data is invalid."""


class PipelineError(VectorMapError):
    """Raised when the pipeline cannot complete successfully."""


class StageExecutionError(PipelineError):
    """Raised when an individual pipeline stage fails."""

    def __init__(self, stage: str, message: str, *, cause: Exception | None = None) -> None:
        self.stage = stage
        self.cause = cause
        super().__init__(f"Stage '{stage}' failed: {message}")


class ExportError(PipelineError):
    """Raised when vector output cannot be written."""


class GeometryError(PipelineError):
    """Raised when geometries cannot be repaired or validated."""
