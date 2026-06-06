"""Thread-safe cancel token for long-running operations.

A CancelToken allows a background task to be cancelled from the UI thread
in a safe, idempotent way. It also supports being bound to a QGIS task
so cancellation flows through the standard QGIS task lifecycle.
"""

from __future__ import annotations

import threading
from typing import Callable


class CancelToken:
    """Thread-safe token to signal cancellation of an in-progress operation.

    Use cases:
    - User clicks "Cancel" button in dialog while vectorization runs
    - QGIS task is cancelled (closed project, etc.)
    - Timeout exceeded
    - Error in another step

    The token is one-way: once cancelled, it stays cancelled. It is safe to
    call cancel() multiple times - only the first call has any effect.
    """

    def __init__(self) -> None:
        self._cancelled = False
        self._lock = threading.Lock()
        self._reason: str | None = None

    def cancel(self, reason: str | None = None) -> None:
        """Mark the operation as cancelled. Idempotent.

        Parameters
        ----------
        reason:
            Optional human-readable reason for cancellation. Useful for
            logging or user feedback.
        """
        with self._lock:
            if not self._cancelled:
                self._cancelled = True
                if reason is not None:
                    self._reason = reason

    @property
    def cancelled(self) -> bool:
        """True if cancel() has been called."""
        return self._cancelled

    @property
    def reason(self) -> str | None:
        """The reason given when cancel() was called, if any."""
        return self._reason

    def as_callback(self) -> Callable[[], bool]:
        """Return a zero-arg callable suitable for CancelCallback.

        The returned function does NOT acquire the lock on every call
        (a fast path for the common case where cancellation has not occurred).
        """
        cancelled = self._cancelled  # fast snapshot
        return lambda: cancelled or self._cancelled

    def reset(self) -> None:
        """Reset the token to non-cancelled state.

        Primarily for testing. Production code should create a new token
        per operation rather than reusing one.
        """
        with self._lock:
            self._cancelled = False
            self._reason = None

    def __enter__(self) -> "CancelToken":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        # No-op: token is just a signal, not a context manager with side effects
        pass

    def __repr__(self) -> str:
        state = "cancelled" if self._cancelled else "active"
        return f"CancelToken({state}, reason={self._reason!r})"


__all__ = ["CancelToken"]
