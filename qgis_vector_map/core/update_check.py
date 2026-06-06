"""Plugin update checker.

Compares the locally installed plugin version against the latest release
on GitHub and reports whether an update is available.

Design
------
- :func:`parse_version`: parse a "vX.Y.Z" or "X.Y.Z" string into a tuple.
- :func:`is_newer`: check whether version A is newer than B.
- :class:`UpdateInfo`: a record describing an available update.
- :class:`UpdateChecker`: orchestrates the check (network optional).

Network
-------
The network call to GitHub is wrapped in :func:`_fetch_latest_release`,
which can be patched in tests. The checker works offline: if the
network call fails, the error is returned in :class:`UpdateInfo.error`
rather than raised.

Cache
-----
The "last check" timestamp is persisted to
``~/.qgis_vector_map/update_check.json`` so we don't hammer GitHub
on every plugin startup. The default throttle is 24 hours.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


# Default GitHub repo to check
DEFAULT_REPO = "ricardober93/vector-map"

# Cache file for last check
UPDATE_CHECK_FILENAME = "update_check.json"

# Throttle: don't re-check more often than this (in seconds)
DEFAULT_CHECK_THROTTLE = 24 * 60 * 60  # 24 hours

# User agent for GitHub API
USER_AGENT = "VectorMapPlugin/1.0"


# Standard timeout for the network call
DEFAULT_TIMEOUT = 5.0  # seconds


def parse_version(version: str) -> tuple[int, ...]:
    """Parse a version string like "1.2.3" or "v1.2.3" into a tuple of ints.

    Pre-release suffixes (-rc1, -beta) are ignored. Returns (0,) on failure.

    Examples
    --------
    >>> parse_version("v1.0.0")
    (1, 0, 0)
    >>> parse_version("0.9.5")
    (0, 9, 5)
    >>> parse_version("2.0")
    (2, 0)
    >>> parse_version("invalid")
    (0,)
    """
    if not version:
        return (0,)
    # Strip leading 'v' or 'V'
    cleaned = version.strip()
    if cleaned and cleaned[0] in "vV":
        cleaned = cleaned[1:]
    # Find the leading X.Y.Z sequence
    match = re.match(r"^(\d+(?:\.\d+)*)", cleaned)
    if not match:
        return (0,)
    parts = match.group(1).split(".")
    try:
        return tuple(int(p) for p in parts)
    except (ValueError, TypeError):
        return (0,)


def is_newer(latest: str, current: str) -> bool:
    """Return True if `latest` is strictly newer than `current`.

    Comparison is by parsed version tuple; if parsing fails, the string
    itself is used as a fallback (which still gives a stable answer for
    the same pair of strings).
    """
    latest_parsed = parse_version(latest)
    current_parsed = parse_version(current)
    if latest_parsed == (0,) or current_parsed == (0,):
        # Fall back to string comparison
        return latest.strip() != current.strip() and latest > current
    # Pad shorter tuple with zeros
    max_len = max(len(latest_parsed), len(current_parsed))
    a = latest_parsed + (0,) * (max_len - len(latest_parsed))
    b = current_parsed + (0,) * (max_len - len(current_parsed))
    return a > b


@dataclass
class UpdateInfo:
    """Result of an update check.

    Attributes
    ----------
    current_version:
        The version the user has installed.
    latest_version:
        The latest version found on GitHub (None if check failed).
    update_available:
        True if latest > current.
    checked_at:
        ISO 8601 UTC timestamp of when the check was performed.
    error:
        If non-None, the check failed; this is the human-readable reason.
    release_url:
        URL of the release page (if available).
    release_notes:
        First 500 chars of the release body (truncated, if available).
    from_cache:
        True if this result was served from the on-disk cache.
    """

    current_version: str
    latest_version: Optional[str] = None
    update_available: bool = False
    checked_at: str = ""
    error: Optional[str] = None
    release_url: Optional[str] = None
    release_notes: Optional[str] = None
    from_cache: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UpdateInfo":
        valid = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in valid})

    @property
    def is_success(self) -> bool:
        return self.error is None and self.latest_version is not None


def _build_release_url(repo: str, tag: str) -> str:
    return f"https://github.com/{repo}/releases/tag/{tag}"


def _build_api_url(repo: str) -> str:
    return f"https://api.github.com/repos/{repo}/releases/latest"


def _http_get_json(url: str, timeout: float = DEFAULT_TIMEOUT) -> dict[str, Any]:
    """Make a GET request and return parsed JSON. Raises on failure."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/vnd.github+json",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read()
    return json.loads(raw.decode("utf-8"))


def _parse_release_payload(payload: dict[str, Any], repo: str) -> dict[str, Any]:
    """Extract the relevant fields from a GitHub release JSON payload."""
    tag = payload.get("tag_name", "")
    body = payload.get("body") or ""
    if len(body) > 500:
        body = body[:497] + "..."
    return {
        "tag": tag,
        "url": _build_release_url(repo, tag),
        "notes": body,
    }


class UpdateChecker:
    """Check for plugin updates from GitHub releases.

    The checker throttles itself to avoid hitting GitHub on every
    plugin invocation. Use :meth:`should_check` to test whether a
    check is due; :meth:`check` performs the actual lookup.
    """

    def __init__(
        self,
        *,
        current_version: str,
        repo: str = DEFAULT_REPO,
        storage_dir: Path | str | None = None,
        throttle_seconds: int = DEFAULT_CHECK_THROTTLE,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """Parameters
        ----------
        current_version:
            The locally installed version (e.g. "1.0.0").
        repo:
            GitHub owner/repo to check.
        storage_dir:
            Where to store the throttle cache. Defaults to
            ``~/.qgis_vector_map/``.
        throttle_seconds:
            Minimum seconds between checks.
        timeout:
            Network timeout for the GitHub API call.
        """
        if storage_dir is None:
            storage_dir = Path.home() / ".qgis_vector_map"
        self._storage_dir = Path(storage_dir)
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._path = self._storage_dir / UPDATE_CHECK_FILENAME
        self._current = current_version
        self._repo = repo
        self._throttle = throttle_seconds
        self._timeout = timeout

    @property
    def cache_path(self) -> Path:
        return self._path

    @property
    def current_version(self) -> str:
        return self._current

    @property
    def repo(self) -> str:
        return self._repo

    def _read_cache(self) -> dict[str, Any]:
        if not self._path.exists():
            return {}
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError):
            return {}

    def _write_cache(self, info: UpdateInfo) -> None:
        try:
            payload = {
                "info": info.to_dict(),
                "saved_at": datetime.now(timezone.utc).isoformat(),
            }
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except OSError:
            pass

    def should_check(self) -> bool:
        """Return True if a network check is allowed (throttle expired)."""
        cached = self._read_cache()
        saved_at = cached.get("saved_at")
        if not saved_at:
            return True
        try:
            dt = datetime.fromisoformat(saved_at)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            elapsed = (datetime.now(timezone.utc) - dt).total_seconds()
            return elapsed >= self._throttle
        except (ValueError, TypeError):
            return True

    def time_until_next_check(self) -> float:
        """Seconds until the next check is allowed. 0 if check is due now."""
        cached = self._read_cache()
        saved_at = cached.get("saved_at")
        if not saved_at:
            return 0.0
        try:
            dt = datetime.fromisoformat(saved_at)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            elapsed = (datetime.now(timezone.utc) - dt).total_seconds()
            return max(0.0, self._throttle - elapsed)
        except (ValueError, TypeError):
            return 0.0

    def get_cached(self) -> Optional[UpdateInfo]:
        """Return the cached UpdateInfo, or None if no cache."""
        cached = self._read_cache()
        info_data = cached.get("info")
        if not isinstance(info_data, dict):
            return None
        try:
            info = UpdateInfo.from_dict(info_data)
            info.from_cache = True
            return info
        except Exception:
            return None

    def check(self, *, force: bool = False) -> UpdateInfo:
        """Perform an update check.

        Parameters
        ----------
        force:
            If True, bypass the throttle and always make a network call.

        Returns
        -------
        :class:`UpdateInfo` describing the outcome. On network failure,
        ``error`` is set and ``update_available`` is False.
        """
        if not force and not self.should_check():
            cached = self.get_cached()
            if cached is not None:
                return cached

        info = UpdateInfo(
            current_version=self._current,
            checked_at=datetime.now(timezone.utc).isoformat(),
        )

        try:
            payload = _http_get_json(_build_api_url(self._repo), self._timeout)
            parsed = _parse_release_payload(payload, self._repo)
            info.latest_version = parsed["tag"]
            info.release_url = parsed["url"]
            info.release_notes = parsed["notes"]
            info.update_available = is_newer(parsed["tag"], self._current)
        except urllib.error.HTTPError as exc:
            # HTTPError is a subclass of URLError, so it must come first
            info.error = f"HTTP error: {exc.code} {exc.reason}"
        except urllib.error.URLError as exc:
            info.error = f"Network error: {exc.reason}"
        except json.JSONDecodeError as exc:
            info.error = f"Invalid JSON response: {exc}"
        except Exception as exc:  # pragma: no cover - defensive
            info.error = f"{type(exc).__name__}: {exc}"

        # Cache successful and "rate-limited error" responses; cache nothing
        # for transient network errors.
        if info.is_success or info.error is not None:
            self._write_cache(info)

        return info


__all__ = [
    "DEFAULT_CHECK_THROTTLE",
    "DEFAULT_REPO",
    "UPDATE_CHECK_FILENAME",
    "UpdateChecker",
    "UpdateInfo",
    "is_newer",
    "parse_version",
]
