"""Core dataclasses shared by the pipeline and engines."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Mapping, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - imported only for typing
    from .raster import RasterFrame
    from ..processing_profiles import ResolvedProfile


class StageName(str, Enum):
    """Canonical pipeline stage names."""

    PREPROCESS = "preprocess"
    VECTORIZE = "vectorize"
    POSTPROCESS = "postprocess"
    EXPORT = "export"


class StageStatus(str, Enum):
    """Lifecycle state for a pipeline stage."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class VectorizationRequest:
    """User request for a vectorization job."""

    source: Any
    profile_id: str = "regional-high-precision"
    output_path: str | Path | None = None
    output_format: str = "auto"
    layer_name: str = "vectorized"
    parameters: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    working_directory: str | Path | None = None
    execution_mode: str = "auto"


@dataclass(frozen=True)
class VectorFeature:
    """A single vector feature in GeoJSON-compatible form."""

    geometry_type: str
    coordinates: Any
    properties: Mapping[str, Any] = field(default_factory=dict)


@dataclass
class VectorLayer:
    """Collection of vector features and associated metadata."""

    features: list[VectorFeature] = field(default_factory=list)
    name: str = "vectorized"
    crs: str | None = None
    geotransform: tuple[float, ...] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def feature_count(self) -> int:
        return len(self.features)


@dataclass
class StageReport:
    """Execution report for a single pipeline stage."""

    stage: StageName
    status: StageStatus = StageStatus.PENDING
    started_at: datetime | None = None
    finished_at: datetime | None = None
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def mark_running(self) -> None:
        self.status = StageStatus.RUNNING
        self.started_at = datetime.now(timezone.utc)
        self.finished_at = None
        self.message = ""

    def mark_completed(self, message: str = "") -> None:
        self.status = StageStatus.COMPLETED
        self.finished_at = datetime.now(timezone.utc)
        self.message = message

    def mark_failed(self, message: str) -> None:
        self.status = StageStatus.FAILED
        self.finished_at = datetime.now(timezone.utc)
        self.message = message


@dataclass
class PipelineContext:
    """Mutable execution state shared across the pipeline stages."""

    request: VectorizationRequest
    profile: Any
    raster: RasterFrame
    working_directory: Path
    artifacts: dict[str, Any] = field(default_factory=dict)
    stage_reports: list[StageReport] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def artifact(self, key: str, default: Any = None) -> Any:
        return self.artifacts.get(key, default)

    def store_artifact(self, key: str, value: Any) -> Any:
        self.artifacts[key] = value
        return value

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)


@dataclass
class PipelineResult:
    """Final result returned by the orchestrator."""

    output_path: Path
    vector_layer: VectorLayer
    stage_reports: list[StageReport]
    profile_id: str
    engine_name: str
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


ProgressCallback = Callable[[StageName, float, str], None]
CancelCallback = Callable[[], bool]
