"""Processing history manager: track past vectorization runs.

Each successful/failed run is recorded with metadata: file, profile,
engine, timing, feature count, status. Entries are persisted to
``~/.qgis_vector_map/history.json`` so they survive QGIS restarts.

The history powers the "Recent runs" panel in the dialog, lets the
user re-apply a previous configuration, and provides observability
for debugging user-reported issues.

API
---
- :class:`HistoryEntry`: dataclass for a single run
- :class:`ProcessingHistoryManager`: add/list/clear/purge
- :func:`add_entry` / :func:`list_entries` / :func:`clear_history`
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


# Maximum entries to retain
MAX_HISTORY = 50

# Storage filename
HISTORY_FILENAME = "history.json"


@dataclass
class HistoryEntry:
    """A single vectorization run."""

    timestamp: str  # ISO 8601 UTC
    source_path: str
    output_path: str
    profile_id: str
    engine: str
    execution_mode: str
    output_format: str
    duration_seconds: float
    feature_count: int
    status: str  # "success" | "failed" | "cancelled"
    error: Optional[str] = None
    layer_name: str = "vectorized"
    source_size_bytes: Optional[int] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HistoryEntry":
        """Build a HistoryEntry from a JSON dict, dropping unknown fields."""
        valid_fields = {f for f in cls.__dataclass_fields__}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        # Normalize optional ints (None is fine)
        if filtered.get("source_size_bytes") is not None:
            try:
                filtered["source_size_bytes"] = int(filtered["source_size_bytes"])
            except (ValueError, TypeError):
                filtered["source_size_bytes"] = None
        return cls(**filtered)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def is_success(self) -> bool:
        return self.status == "success"

    @property
    def is_failure(self) -> bool:
        return self.status == "failed"

    @property
    def is_cancelled(self) -> bool:
        return self.status == "cancelled"

    @property
    def display_label(self) -> str:
        """One-line label suitable for list/table display."""
        ts = self.timestamp
        # Truncate ISO timestamp to date + HH:MM
        try:
            dt = datetime.fromisoformat(ts)
            ts = dt.strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            pass
        stem = Path(self.source_path).stem or self.source_path
        status_icon = {
            "success": "✓",
            "failed": "✗",
            "cancelled": "⊘",
        }.get(self.status, "?")
        return f"{status_icon} {ts}  {stem}  ({self.profile_id})"


class ProcessingHistoryManager:
    """Manage the processing history file.

    Entries are stored newest-first. The list is capped at
    :data:`MAX_HISTORY` to avoid unbounded growth.
    """

    def __init__(self, storage_dir: Path | str | None = None) -> None:
        if storage_dir is None:
            storage_dir = Path.home() / ".qgis_vector_map"
        self._storage_dir = Path(storage_dir)
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._path = self._storage_dir / HISTORY_FILENAME

    @property
    def storage_path(self) -> Path:
        return self._path

    def _read(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return []
        if not isinstance(data, list):
            return []
        return [e for e in data if isinstance(e, dict)]

    def _write(self, entries: list[dict[str, Any]]) -> None:
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(entries, f, indent=2)
        except OSError:
            pass  # History is a UX feature, not critical path

    def add_entry(self, entry: HistoryEntry) -> None:
        """Add an entry to the top of the history.

        If an entry with the same source path, output path, AND timestamp
        already exists, it is removed first to avoid duplicates. This
        allows multiple runs of the same file (different timestamps) to
        coexist in the history.
        """
        entries = self._read()
        entries = [
            e
            for e in entries
            if not (
                e.get("source_path") == entry.source_path
                and e.get("output_path") == entry.output_path
                and e.get("timestamp") == entry.timestamp
            )
        ]
        entries.insert(0, entry.to_dict())
        entries = entries[:MAX_HISTORY]
        self._write(entries)

    def list_entries(self) -> list[HistoryEntry]:
        """Return all entries (newest first), at most MAX_HISTORY."""
        raw = self._read()
        result: list[HistoryEntry] = []
        for e in raw[:MAX_HISTORY]:
            try:
                result.append(HistoryEntry.from_dict(e))
            except Exception:
                # Skip malformed entries
                continue
        return result

    def find_by_source(self, source_path: str) -> list[HistoryEntry]:
        """Return all entries for a given source path, newest first."""
        return [
            e
            for e in self.list_entries()
            if e.source_path == source_path
        ]

    def find_latest_success(self) -> Optional[HistoryEntry]:
        """Return the most recent successful entry, or None."""
        for entry in self.list_entries():
            if entry.is_success:
                return entry
        return None

    def clear(self) -> None:
        """Erase the entire history."""
        self._write([])

    def remove(self, entry: HistoryEntry) -> bool:
        """Remove a single entry by matching timestamp + source path."""
        entries = self._read()
        new_entries = [
            e
            for e in entries
            if not (
                e.get("timestamp") == entry.timestamp
                and e.get("source_path") == entry.source_path
            )
        ]
        if len(new_entries) == len(entries):
            return False
        self._write(new_entries)
        return True

    def prune_failures(self) -> int:
        """Remove all failed/cancelled entries. Returns count removed."""
        entries = self._read()
        kept = [e for e in entries if e.get("status") == "success"]
        removed = len(entries) - len(kept)
        if removed > 0:
            self._write(kept)
        return removed

    def stats(self) -> dict[str, int]:
        """Return summary statistics about the history."""
        entries = self.list_entries()
        return {
            "total": len(entries),
            "success": sum(1 for e in entries if e.is_success),
            "failed": sum(1 for e in entries if e.is_failure),
            "cancelled": sum(1 for e in entries if e.is_cancelled),
        }


def make_entry_from_result(
    *,
    source_path: str,
    output_path: str,
    profile_id: str,
    engine: str,
    execution_mode: str,
    output_format: str,
    layer_name: str,
    duration_seconds: float,
    feature_count: int,
    status: str = "success",
    error: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> HistoryEntry:
    """Convenience constructor for a success entry."""
    return HistoryEntry(
        timestamp=datetime.now(timezone.utc).isoformat(),
        source_path=source_path,
        output_path=output_path,
        profile_id=profile_id,
        engine=engine,
        execution_mode=execution_mode,
        output_format=output_format,
        layer_name=layer_name,
        duration_seconds=duration_seconds,
        feature_count=feature_count,
        status=status,
        error=error,
        metadata=dict(metadata or {}),
    )


__all__ = [
    "HISTORY_FILENAME",
    "HistoryEntry",
    "MAX_HISTORY",
    "ProcessingHistoryManager",
    "make_entry_from_result",
]
