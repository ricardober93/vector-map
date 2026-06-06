"""Batch processing: run vectorization on a list of rasters sequentially.

Allows processing N rasters in sequence, with:
- Per-file progress reported as "X/N" (so 1/N ... N/N)
- Cancellation propagated to the current file
- Summary of per-file outcomes (success / failure / cancelled)
- A `BatchProgressCallback` that wraps a per-file callback into a global one

Example
-------
>>> from qgis_vector_map.core.batch import BatchProcessor
>>> processor = BatchProcessor()
>>> results = processor.run(
...     ["/a.tif", "/b.tif", "/c.tif"],
...     profile_id="regional-high-precision",
...     output_dir="/out",
... )
>>> print(results.summary())
'3/3 succeeded, 0 failed'
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from .cancel import CancelToken
from .errors import PipelineError
from .eta import ETAMeter
from .models import (
    CancelCallback,
    PipelineResult,
    ProgressCallback,
    StageName,
    VectorizationRequest,
)
from .pipeline import run_vectorization


# Type aliases
PerFileProgressCallback = Callable[[str, int, int, Optional[PipelineResult]], None]
"""Called after each file completes. Args: (path, index, total, result_or_none)."""


@dataclass
class FileOutcome:
    """The result of running a single file in a batch."""

    source_path: str
    status: str  # "success", "failed", "cancelled"
    result: PipelineResult | None = None
    error: str | None = None
    elapsed_seconds: float = 0.0
    feature_count: int = 0


@dataclass
class BatchResult:
    """The aggregate result of a batch run."""

    outcomes: list[FileOutcome] = field(default_factory=list)
    cancelled: bool = False

    @property
    def total(self) -> int:
        return len(self.outcomes)

    @property
    def succeeded(self) -> int:
        return sum(1 for o in self.outcomes if o.status == "success")

    @property
    def failed(self) -> int:
        return sum(1 for o in self.outcomes if o.status == "failed")

    @property
    def cancelled_count(self) -> int:
        return sum(1 for o in self.outcomes if o.status == "cancelled")

    @property
    def total_features(self) -> int:
        return sum(o.feature_count for o in self.outcomes)

    def summary(self) -> str:
        """Human-readable summary, e.g. '3/5 succeeded, 1 failed, 1 cancelled'."""
        if self.cancelled:
            return (
                f"{self.succeeded}/{self.total} succeeded, "
                f"{self.failed} failed, {self.cancelled_count} cancelled (batch aborted)"
            )
        if self.cancelled_count > 0:
            return (
                f"{self.succeeded}/{self.total} succeeded, "
                f"{self.failed} failed, {self.cancelled_count} cancelled"
            )
        return f"{self.succeeded}/{self.total} succeeded, {self.failed} failed"

    def failures(self) -> list[FileOutcome]:
        return [o for o in self.outcomes if o.status == "failed"]


class BatchProcessor:
    """Run vectorization on a list of raster files sequentially.

    Files are processed in the given order. If one file fails, the batch
    continues with the next (configurable via `stop_on_error`).

    Cancellation works mid-file: if cancel_callback returns True during
    a file, that file is marked as "cancelled" and the batch stops.
    """

    def __init__(self, *, stop_on_error: bool = False) -> None:
        """Parameters
        ----------
        stop_on_error:
            If True, abort the batch on the first failure. If False (default),
            continue processing remaining files even after a failure.
        """
        self._stop_on_error = stop_on_error

    def run(
        self,
        sources: Iterable[str | Path],
        *,
        profile_id: str = "regional-high-precision",
        output_dir: str | Path | None = None,
        output_format: str = "auto",
        layer_name_template: str = "{stem}_vectorized",
        parameters: dict[str, Any] | None = None,
        cancel_callback: CancelCallback | None = None,
        progress_callback: ProgressCallback | None = None,
        per_file_callback: PerFileProgressCallback | None = None,
    ) -> BatchResult:
        """Run the batch.

        Parameters
        ----------
        sources:
            Iterable of raster file paths.
        profile_id:
            Profile to use for every file.
        output_dir:
            Where to write outputs. If None, outputs are written next to
            each input file (sibling directory).
        output_format:
            Forwarded to each VectorizationRequest.
        layer_name_template:
            Template for output layer names. Available placeholders:
            - {stem}: file stem (e.g. "ortho" from "ortho.tif")
            - {index}: 1-based file index in the batch
        cancel_callback:
            If provided and returns True, the batch aborts gracefully.
        progress_callback:
            Global progress callback. Receives (stage, ratio, message).
            Ratio is computed across the whole batch (not per-file).
        per_file_callback:
            Called after each file completes (or fails).

        Returns
        -------
        BatchResult with per-file outcomes.
        """
        # Materialize the list to allow len() and indexing
        source_list = [str(p) for p in sources]
        if not source_list:
            return BatchResult()

        batch_eta = ETAMeter()
        batch_eta.start()

        # Per-file progress -> global progress translation
        def file_progress(stage: StageName, ratio: float, message: str) -> None:
            if progress_callback is None:
                return
            # Global ratio = (file_index + file_ratio) / total_files
            global_ratio = (file_index + ratio) / total_files
            global_ratio = max(0.0, min(1.0, global_ratio))
            batch_eta.update(global_ratio)
            # Re-format message with global ETA
            eta_msg = batch_eta.progress_message(
                prefix=f"File {file_index + 1}/{total_files}",
                suffix=message,
            )
            progress_callback(stage, global_ratio, eta_msg)

        # Cancel propagates from outer callback to inner
        cancel_token = CancelToken()
        if cancel_callback is not None:
            # Wire the existing callback into the token
            cancel_token.cancel(reason="batch: pre-cancelled by caller")

        def combined_cancel() -> bool:
            if cancel_token.cancelled:
                return True
            if cancel_callback is not None and cancel_callback():
                cancel_token.cancel(reason="batch: outer callback returned True")
                return True
            return False

        outcomes: list[FileOutcome] = []
        cancelled = False
        total_files = len(source_list)
        file_index = 0
        for file_index, source_str in enumerate(source_list):
            # Check cancellation before starting each file
            if combined_cancel():
                cancelled = True
                # Record the skipped file as cancelled
                outcomes.append(
                    FileOutcome(
                        source_path=source_str,
                        status="cancelled",
                    )
                )
                break

            source = Path(source_str)
            if not source.exists():
                outcome = FileOutcome(
                    source_path=source_str,
                    status="failed",
                    error=f"File not found: {source_str}",
                )
                outcomes.append(outcome)
                if per_file_callback is not None:
                    per_file_callback(source_str, file_index, total_files, None)
                if self._stop_on_error:
                    outcomes.append(
                        FileOutcome(
                            source_path="<aborted>",
                            status="cancelled",
                        )
                    )
                    break
                continue

            # Build output path
            output_path = self._resolve_output_path(
                source=source,
                output_dir=output_dir,
                output_format=output_format,
            )

            # Build layer name
            layer_name = layer_name_template.format(
                stem=source.stem,
                index=file_index + 1,
            )

            request = VectorizationRequest(
                source=str(source),
                profile_id=profile_id,
                output_path=output_path,
                output_format=output_format,
                layer_name=layer_name,
                parameters=dict(parameters or {}),
            )

            # Track elapsed time for this file
            file_eta = ETAMeter()
            file_eta.start()

            try:
                result = run_vectorization(
                    request,
                    progress_callback=file_progress,
                    cancel_callback=combined_cancel,
                )
                outcome = FileOutcome(
                    source_path=source_str,
                    status="success",
                    result=result,
                    elapsed_seconds=file_eta.elapsed(),
                    feature_count=result.vector_layer.feature_count(),
                )
                outcomes.append(outcome)
            except PipelineError as exc:
                if combined_cancel():
                    outcome = FileOutcome(
                        source_path=source_str,
                        status="cancelled",
                        elapsed_seconds=file_eta.elapsed(),
                    )
                    cancelled = True
                else:
                    outcome = FileOutcome(
                        source_path=source_str,
                        status="failed",
                        error=str(exc),
                        elapsed_seconds=file_eta.elapsed(),
                    )
                outcomes.append(outcome)
            except Exception as exc:  # pragma: no cover - defensive
                outcome = FileOutcome(
                    source_path=source_str,
                    status="failed",
                    error=f"{type(exc).__name__}: {exc}",
                    elapsed_seconds=file_eta.elapsed(),
                )
                outcomes.append(outcome)

            if per_file_callback is not None:
                per_file_callback(
                    source_str,
                    file_index,
                    total_files,
                    outcome.result,
                )

            # Stop if cancellation was triggered
            if combined_cancel():
                cancelled = True
                break

            # Stop on first error if configured
            if (
                self._stop_on_error
                and outcomes
                and outcomes[-1].status == "failed"
            ):
                break

        return BatchResult(outcomes=outcomes, cancelled=cancelled)

    @staticmethod
    def _resolve_output_path(
        *,
        source: Path,
        output_dir: str | Path | None,
        output_format: str,
    ) -> Path:
        """Resolve the output path for a single file."""
        if output_dir is not None:
            out_dir = Path(output_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            ext = BatchProcessor._default_extension(output_format, source.suffix)
            return out_dir / f"{source.stem}_vectorized{ext}"

        # Default: sibling "_vectorized" directory
        sibling = source.parent / f"{source.stem}_vectorized"
        sibling.mkdir(parents=True, exist_ok=True)
        ext = BatchProcessor._default_extension(output_format, source.suffix)
        return sibling / f"{source.stem}{ext}"

    @staticmethod
    def _default_extension(output_format: str, source_suffix: str) -> str:
        """Pick a default extension based on format or source suffix."""
        if output_format == "gpkg":
            return ".gpkg"
        if output_format == "geojson":
            return ".geojson"
        if output_format == "shp":
            return ".shp"
        # auto: keep source suffix
        return source_suffix or ".gpkg"


__all__ = [
    "BatchProcessor",
    "BatchResult",
    "FileOutcome",
    "PerFileProgressCallback",
]
