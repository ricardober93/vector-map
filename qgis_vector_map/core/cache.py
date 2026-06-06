"""Result cache: avoid re-processing identical raster + configuration combos.

When the same input file is processed with the same parameters, the
output is deterministic. This module stores a fingerprint of (input +
config + algorithm version) and lets callers check whether a cached
result exists before running the pipeline.

Design
------
- :class:`CacheKey`: deterministic hash of all inputs that affect the output
- :class:`ResultCache`: stores/loads cached results on disk
- :func:`compute_cache_key`: convenience function

Cache invalidation
------------------
The cache key includes:
- Absolute path of the input file
- File mtime + size (so a modified file invalidates the cache)
- Profile ID, engine, execution mode, output format
- All vectorization parameters
- Algorithm version (so upgrading the plugin invalidates old caches)

This means a developer changing the algorithm will NOT serve stale results
to end users; only files + config combos that haven't changed since the
last run will hit the cache.

Cache storage
-------------
The cache lives in ``~/.qgis_vector_map/cache/`` and is keyed by
SHA-256 hash (first 16 hex chars). Each cache entry is a JSON file
containing metadata; the actual output is the same file the pipeline
wrote, so the cache entry is just a pointer + fingerprint.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


# Cache directory name
CACHE_DIRNAME = "cache"
CACHE_VERSION = "1.0.0"  # Bump to invalidate ALL cached entries


@dataclass(frozen=True)
class CacheKey:
    """Deterministic fingerprint of a (file, config, version) tuple.

    Two CacheKey instances are equal if all their fields match.
    """

    file_path: str
    file_size: int
    file_mtime: float
    profile_id: str
    engine: str
    execution_mode: str
    output_format: str
    output_path: str
    parameters_hash: str  # Hash of all parameters dict
    algorithm_version: str

    def to_hex(self, length: int = 16) -> str:
        """Compute a stable hex digest of this key (default 16 chars)."""
        payload = json.dumps(
            {
                "file_path": self.file_path,
                "file_size": self.file_size,
                "file_mtime": self.file_mtime,
                "profile_id": self.profile_id,
                "engine": self.engine,
                "execution_mode": self.execution_mode,
                "output_format": self.output_format,
                "output_path": self.output_path,
                "parameters_hash": self.parameters_hash,
                "algorithm_version": self.algorithm_version,
                "cache_version": CACHE_VERSION,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return digest[:length]


@dataclass
class CacheEntry:
    """Metadata for a single cached result."""

    cache_key: str  # hex digest
    timestamp: str  # ISO 8601 UTC
    output_path: str
    file_size: int
    file_mtime: float
    profile_id: str
    engine: str
    execution_mode: str
    output_format: str
    feature_count: int
    algorithm_version: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CacheEntry":
        valid = {f for f in cls.__dataclass_fields__}
        filtered = {k: v for k, v in data.items() if k in valid}
        return cls(**filtered)


def hash_parameters(parameters: dict[str, Any]) -> str:
    """Compute a stable hash of a parameters dict.

    Handles nested dicts and lists. Order-independent (sorted by key).
    """
    payload = json.dumps(parameters, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def compute_cache_key(
    *,
    file_path: str | Path,
    profile_id: str,
    engine: str,
    execution_mode: str,
    output_format: str,
    output_path: str | Path,
    parameters: dict[str, Any] | None = None,
    algorithm_version: str = CACHE_VERSION,
) -> CacheKey:
    """Build a CacheKey from a file path + config.

    Parameters
    ----------
    file_path:
        Path to the input raster. Must exist; otherwise raises FileNotFoundError.
    profile_id, engine, execution_mode, output_format, output_path:
        Vectorization configuration.
    parameters:
        Extra parameters dict (anything that affects the output).
    algorithm_version:
        Plugin version. Bumping this invalidates all old cache entries.
    """
    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(f"Input file not found: {file_path}")
    stat = p.stat()
    return CacheKey(
        file_path=str(p.resolve()),
        file_size=stat.st_size,
        file_mtime=stat.st_mtime,
        profile_id=profile_id,
        engine=engine,
        execution_mode=execution_mode,
        output_format=output_format,
        output_path=str(Path(output_path).resolve()),
        parameters_hash=hash_parameters(dict(parameters or {})),
        algorithm_version=algorithm_version,
    )


class ResultCache:
    """Disk-backed cache for vectorization results."""

    def __init__(self, storage_dir: Path | str | None = None) -> None:
        if storage_dir is None:
            storage_dir = Path.home() / ".qgis_vector_map"
        self._storage_dir = Path(storage_dir)
        self._cache_dir = self._storage_dir / CACHE_DIRNAME
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    @property
    def cache_dir(self) -> Path:
        return self._cache_dir

    def _entry_path(self, cache_key_hex: str) -> Path:
        return self._cache_dir / f"{cache_key_hex}.json"

    def has(self, key: CacheKey) -> bool:
        """Return True if a cached entry exists for this key AND the
        output file still exists on disk."""
        entry_path = self._entry_path(key.to_hex())
        if not entry_path.exists():
            return False
        # Also check the output file still exists
        if not Path(key.output_path).exists():
            return False
        return True

    def get(self, key: CacheKey) -> Optional[CacheEntry]:
        """Return the cached entry, or None if not present."""
        entry_path = self._entry_path(key.to_hex())
        if not entry_path.exists():
            return None
        try:
            with open(entry_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return None
        if not isinstance(data, dict):
            return None
        try:
            return CacheEntry.from_dict(data)
        except Exception:
            return None

    def put(
        self,
        key: CacheKey,
        *,
        feature_count: int,
        metadata: dict[str, Any] | None = None,
    ) -> CacheEntry:
        """Store a cache entry for the given key.

        The caller is responsible for having already written the output
        file; this method just records the metadata so future lookups
        can confirm the cached result is still valid.
        """
        entry = CacheEntry(
            cache_key=key.to_hex(),
            timestamp=datetime.now(timezone.utc).isoformat(),
            output_path=key.output_path,
            file_size=key.file_size,
            file_mtime=key.file_mtime,
            profile_id=key.profile_id,
            engine=key.engine,
            execution_mode=key.execution_mode,
            output_format=key.output_format,
            feature_count=feature_count,
            algorithm_version=key.algorithm_version,
            metadata=dict(metadata or {}),
        )
        entry_path = self._entry_path(key.to_hex())
        try:
            with open(entry_path, "w", encoding="utf-8") as f:
                json.dump(entry.to_dict(), f, indent=2)
        except OSError:
            pass  # Cache is a perf feature, not critical path
        return entry

    def invalidate(self, key: CacheKey) -> bool:
        """Remove the cache entry for this key. Returns True if removed."""
        entry_path = self._entry_path(key.to_hex())
        if not entry_path.exists():
            return False
        try:
            entry_path.unlink()
            return True
        except OSError:
            return False

    def clear(self) -> int:
        """Remove all cache entries. Returns count removed."""
        removed = 0
        for f in self._cache_dir.glob("*.json"):
            try:
                f.unlink()
                removed += 1
            except OSError:
                pass
        return removed

    def size(self) -> int:
        """Return the number of cached entries."""
        return len(list(self._cache_dir.glob("*.json")))

    def stats(self) -> dict[str, Any]:
        """Return summary statistics about the cache."""
        entries = []
        for entry_file in self._cache_dir.glob("*.json"):
            try:
                with open(entry_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    entries.append(data)
            except (json.JSONDecodeError, OSError):
                pass
        total_features = sum(e.get("feature_count", 0) for e in entries)
        profiles: dict[str, int] = {}
        for e in entries:
            p = e.get("profile_id", "unknown")
            profiles[p] = profiles.get(p, 0) + 1
        return {
            "total_entries": len(entries),
            "total_features": total_features,
            "by_profile": profiles,
        }

    def prune_missing_outputs(self) -> int:
        """Remove cache entries whose output files no longer exist."""
        removed = 0
        for entry_file in self._cache_dir.glob("*.json"):
            try:
                with open(entry_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, dict):
                    continue
                output_path = data.get("output_path")
                if output_path and not Path(output_path).exists():
                    entry_file.unlink()
                    removed += 1
            except (json.JSONDecodeError, OSError):
                # Treat unreadable entries as missing
                try:
                    entry_file.unlink()
                    removed += 1
                except OSError:
                    pass
        return removed


__all__ = [
    "CACHE_DIRNAME",
    "CACHE_VERSION",
    "CacheEntry",
    "CacheKey",
    "ResultCache",
    "compute_cache_key",
    "hash_parameters",
]
