"""Recent files manager for the Vector Map dialog.

Stores the last 5 raster files processed by the user, persisted to
~/.qgis_vector_map/recent.json. Recent files are shown in a dropdown
in the dialog so the user can re-run vectorization with one click.

API
---
- RecentFilesManager: main entry point
- list_recent(): get the 5 most recent files (newest first)
- add_recent(path): add a file to the top of the list (deduped)
- remove_recent(path): remove a specific path
- clear_recent(): wipe the list
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


# Maximum number of recent files to remember
MAX_RECENT = 5

# File name where recent files are stored
RECENT_FILENAME = "recent.json"


class RecentFilesManager:
    """Manage the user's recent raster files.

    The list is persisted to disk so it survives QGIS restarts.
    Most recently used file is first in the list.
    """

    def __init__(self, storage_dir: Path | str | None = None) -> None:
        """Initialize the manager.

        Parameters
        ----------
        storage_dir:
            Where to store the recent.json file. Defaults to
            ~/.qgis_vector_map/. Mainly for testing.
        """
        if storage_dir is None:
            storage_dir = Path.home() / ".qgis_vector_map"
        self._storage_dir = Path(storage_dir)
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._path = self._storage_dir / RECENT_FILENAME

    @property
    def storage_path(self) -> Path:
        """Where the recent files are persisted."""
        return self._path

    def _read(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                return []
            return [e for e in data if isinstance(e, dict) and "path" in e]
        except (json.JSONDecodeError, OSError):
            return []

    def _write(self, entries: list[dict[str, Any]]) -> None:
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(entries, f, indent=2)
        except OSError:
            # If we can't write, fail silently - this is a UX feature
            # not a critical path
            pass

    def list_recent(self) -> list[str]:
        """Return the most recent file paths, newest first.

        Returns at most MAX_RECENT entries.
        """
        entries = self._read()
        return [e["path"] for e in entries[:MAX_RECENT]]

    def list_recent_with_metadata(self) -> list[dict[str, Any]]:
        """Return recent entries with their metadata.

        Each entry has keys: path, added_at (ISO 8601 timestamp).
        """
        return self._read()[:MAX_RECENT]

    def add_recent(self, path: str | Path | None) -> None:
        """Add a file path to the top of the recent list.

        If the path is already in the list, it is moved to the top
        (most recently used). The list is capped at MAX_RECENT.

        Parameters
        ----------
        path:
            File path to add. None and empty strings are silently ignored.
        """
        if path is None:
            return
        path_str = str(path)
        if not path_str:
            return
        entries = self._read()
        # Remove existing entry for this path (case-insensitive on Windows,
        # but we use exact match for cross-platform consistency)
        entries = [e for e in entries if e.get("path") != path_str]

        from datetime import datetime, timezone
        entries.insert(
            0,
            {
                "path": path_str,
                "added_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        entries = entries[:MAX_RECENT]
        self._write(entries)

    def remove_recent(self, path: str | Path) -> bool:
        """Remove a specific path from the recent list.

        Returns True if the path was found and removed, False otherwise.
        """
        path_str = str(path)
        entries = self._read()
        new_entries = [e for e in entries if e.get("path") != path_str]
        if len(new_entries) == len(entries):
            return False
        self._write(new_entries)
        return True

    def clear_recent(self) -> None:
        """Remove all entries from the recent list."""
        self._write([])

    def prune_missing(self) -> int:
        """Remove entries whose files no longer exist on disk.

        Returns the number of entries removed.
        """
        entries = self._read()
        kept = [e for e in entries if Path(e["path"]).exists()]
        removed = len(entries) - len(kept)
        if removed > 0:
            self._write(kept)
        return removed


__all__ = ["MAX_RECENT", "RECENT_FILENAME", "RecentFilesManager"]
