"""ETA (Estimated Time of Arrival) calculator for long-running operations.

Tracks elapsed time and computes an ETA based on the progress ratio.
Used to update the QGIS task manager / progress bar with human-friendly
text like "5/16 tiles (2:13 elapsed, ~5:01 remaining)".
"""

from __future__ import annotations

import time
from dataclasses import dataclass


def _format_seconds(seconds: float) -> str:
    """Format seconds as a human-readable string like '2:13' or '1:05:30'.

    Parameters
    ----------
    seconds:
        Non-negative number of seconds. Negative values are clamped to 0.
    """
    seconds = max(0, int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


@dataclass
class ETAMeter:
    """Track elapsed time and estimate remaining time for an operation.

    Example
    -------
    >>> eta = ETAMeter()
    >>> eta.start()
    >>> # ... do work, periodically:
    >>> eta.update(0.5)  # 50% complete
    >>> eta.elapsed_str()
    '0:30'
    >>> eta.eta_str()
    '0:30'
    """

    start_time: float = 0.0
    last_update: float = 0.0
    last_ratio: float = 0.0

    def start(self) -> None:
        """Mark the start of the operation."""
        self.start_time = time.monotonic()
        self.last_update = self.start_time
        self.last_ratio = 0.0

    def update(self, ratio: float) -> None:
        """Update progress.

        Parameters
        ----------
        ratio:
            Progress in [0, 1]. Values outside this range are clamped.
        """
        ratio = max(0.0, min(1.0, float(ratio)))
        self.last_update = time.monotonic()
        self.last_ratio = ratio

    def elapsed(self) -> float:
        """Elapsed time in seconds (since start)."""
        if self.start_time == 0.0:
            return 0.0
        return time.monotonic() - self.start_time

    def elapsed_str(self) -> str:
        """Elapsed time as 'M:SS' or 'H:MM:SS'."""
        return _format_seconds(self.elapsed())

    def eta_seconds(self) -> float:
        """Estimated remaining time in seconds, or 0 if progress is 0.

        Returns 0 when no time has accumulated yet (cannot divide by zero).
        """
        elapsed = self.elapsed()
        if self.last_ratio <= 0.0 or elapsed <= 0.0:
            return 0.0
        # remaining_fraction = (1 - last_ratio)
        # eta = elapsed * remaining_fraction / last_ratio
        return elapsed * (1.0 - self.last_ratio) / self.last_ratio

    def eta_str(self) -> str:
        """Estimated remaining time as 'M:SS' or 'H:MM:SS'."""
        return _format_seconds(self.eta_seconds())

    def progress_message(self, prefix: str = "", suffix: str = "") -> str:
        """Format a human-readable progress message.

        Parameters
        ----------
        prefix:
            Text shown before the timing info (e.g. "Tile 5/16").
        suffix:
            Text shown after the timing info (e.g. "Phase: vectorize").
        """
        parts = []
        if prefix:
            parts.append(prefix)
        parts.append(f"elapsed {self.elapsed_str()}")
        if self.last_ratio > 0.0:
            parts.append(f"ETA {self.eta_str()}")
        if suffix:
            parts.append(suffix)
        return " | ".join(parts)


__all__ = ["ETAMeter", "_format_seconds"]
