"""Background execution helpers for QGIS task manager."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .core.models import PipelineResult, VectorizationRequest
from .core.pipeline import run_vectorization

try:  # pragma: no cover - requires QGIS runtime
    from qgis.core import QgsApplication, QgsTask

    HAS_QGIS = True
except Exception:  # pragma: no cover - import-safe fallback
    HAS_QGIS = False
    QgsApplication = None  # type: ignore[assignment]
    QgsTask = object  # type: ignore[assignment]


@dataclass
class BackgroundCallbacks:
    """Optional callbacks for async execution lifecycle."""

    on_success: Callable[[PipelineResult], None] | None = None
    on_error: Callable[[Exception], None] | None = None
    on_progress: Callable[[str, float, str], None] | None = None


if HAS_QGIS:

    class VectorizationTask(QgsTask):  # pragma: no cover - requires QGIS runtime
        """Run vectorization in QGIS background task manager."""

        def __init__(self, request: VectorizationRequest, callbacks: BackgroundCallbacks | None = None) -> None:
            super().__init__(f"Vectorize: {request.profile_id}", QgsTask.CanCancel)
            self._request = request
            self._callbacks = callbacks or BackgroundCallbacks()
            self.result: PipelineResult | None = None
            self.error: Exception | None = None

        def run(self) -> bool:
            try:
                self.result = run_vectorization(
                    self._request,
                    progress_callback=self._emit_progress,
                    cancel_callback=self.isCanceled,
                )
                return True
            except Exception as exc:
                self.error = exc
                return False

        def finished(self, ok: bool) -> None:
            if ok and self.result is not None and self._callbacks.on_success is not None:
                self._callbacks.on_success(self.result)
                return
            if self.error is not None and self._callbacks.on_error is not None:
                self._callbacks.on_error(self.error)

        def _emit_progress(self, stage: Any, progress: float, message: str) -> None:
            self.setProgress(max(0.0, min(100.0, progress * 100.0)))
            if self._callbacks.on_progress is not None:
                stage_name = getattr(stage, "value", str(stage))
                self._callbacks.on_progress(stage_name, progress, message)


def run_vectorization_async(
    request: VectorizationRequest,
    callbacks: BackgroundCallbacks | None = None,
) -> Any:
    """Schedule vectorization in background when QGIS is present.

    Returns the created task in QGIS mode; otherwise runs synchronously and
    returns a PipelineResult for compatibility in non-QGIS environments.
    """

    if not HAS_QGIS:
        return run_vectorization(
            request,
            progress_callback=(
                lambda stage, progress, message: callbacks.on_progress(
                    getattr(stage, "value", str(stage)), progress, message
                )
                if callbacks and callbacks.on_progress
                else None
            ),
        )

    task = VectorizationTask(request=request, callbacks=callbacks)
    manager = QgsApplication.taskManager()
    manager.addTask(task)
    return task
