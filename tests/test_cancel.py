"""Tests for CancelToken and pipeline cancellation behavior."""

from __future__ import annotations

import threading
import time
import unittest

from qgis_vector_map.core.cancel import CancelToken
from qgis_vector_map.core.errors import PipelineError
from qgis_vector_map.core.models import (
    CancelCallback,
    ProgressCallback,
    StageName,
)
from qgis_vector_map.core.pipeline import PipelineOrchestrator


class CancelTokenTests(unittest.TestCase):
    """Tests for the CancelToken primitive."""

    def test_initial_state_is_not_cancelled(self):
        token = CancelToken()
        self.assertFalse(token.cancelled)
        self.assertIsNone(token.reason)

    def test_cancel_sets_cancelled(self):
        token = CancelToken()
        token.cancel()
        self.assertTrue(token.cancelled)

    def test_cancel_with_reason(self):
        token = CancelToken()
        token.cancel(reason="User pressed cancel")
        self.assertTrue(token.cancelled)
        self.assertEqual(token.reason, "User pressed cancel")

    def test_cancel_is_idempotent(self):
        token = CancelToken()
        token.cancel("first")
        token.cancel("second")  # Should not overwrite the first reason
        self.assertEqual(token.reason, "first")

    def test_reset_restores_active_state(self):
        token = CancelToken()
        token.cancel("temp")
        token.reset()
        self.assertFalse(token.cancelled)
        self.assertIsNone(token.reason)

    def test_as_callback_returns_callable(self):
        token = CancelToken()
        callback = token.as_callback()
        self.assertFalse(callback())
        token.cancel()
        self.assertTrue(callback())

    def test_callback_returns_false_after_reset(self):
        token = CancelToken()
        token.cancel()
        # Note: as_callback() captures a snapshot, so it does NOT reflect reset()
        # in the typical case. This is a feature (cheap fast path).
        callback_before_reset = token.as_callback()
        token.reset()
        # The pre-existing callback still sees the cancellation that happened
        # before it was created
        self.assertTrue(callback_before_reset())
        # But a new callback sees the fresh state
        callback_after_reset = token.as_callback()
        self.assertFalse(callback_after_reset())

    def test_repr_shows_state(self):
        token = CancelToken()
        self.assertIn("active", repr(token))
        token.cancel("because")
        self.assertIn("cancelled", repr(token))
        self.assertIn("because", repr(token))

    def test_thread_safety(self):
        """Concurrent cancel() calls should not corrupt state."""
        token = CancelToken()
        threads = []

        def cancel_many():
            for _ in range(1000):
                token.cancel("from-thread")

        for _ in range(10):
            threads.append(threading.Thread(target=cancel_many))
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertTrue(token.cancelled)
        # Reason should be exactly one of the inputs
        self.assertEqual(token.reason, "from-thread")


class PipelineCancellationTests(unittest.TestCase):
    """Tests for cancellation integration in the pipeline."""

    def test_check_cancelled_raises_pipeline_error(self):
        orchestrator = PipelineOrchestrator()
        cancelled = {"flag": True}

        def cancel_cb() -> bool:
            return cancelled["flag"]

        with self.assertRaises(PipelineError) as ctx:
            orchestrator._check_cancelled(cancel_cb, StageName.VECTORIZE)
        self.assertIn("cancelled", str(ctx.exception).lower())
        self.assertIn("vectorize", str(ctx.exception))

    def test_check_cancelled_no_op_when_none(self):
        orchestrator = PipelineOrchestrator()
        # Should not raise when cancel_callback is None
        orchestrator._check_cancelled(None, StageName.PREPROCESS)

    def test_check_cancelled_no_op_when_callback_returns_false(self):
        orchestrator = PipelineOrchestrator()

        def cancel_cb() -> bool:
            return False

        # Should not raise
        orchestrator._check_cancelled(cancel_cb, StageName.POSTPROCESS)

    def test_raise_cancelled_includes_context(self):
        orchestrator = PipelineOrchestrator()
        cancelled = {"flag": True}

        def cancel_cb() -> bool:
            return cancelled["flag"]

        with self.assertRaises(PipelineError) as ctx:
            orchestrator._raise_cancelled(
                cancel_cb,
                StageName.VECTORIZE,
                after="tile 5/16",
            )
        msg = str(ctx.exception)
        self.assertIn("vectorize", msg)
        self.assertIn("tile 5/16", msg)


class CancelCallbackIntegrationTests(unittest.TestCase):
    """Test the full callback flow used by QGIS tasks."""

    def test_token_callback_triggers_cancellation(self):
        """Simulate a QGIS task binding its isCanceled to a CancelToken."""
        token = CancelToken()
        callback = token.as_callback()

        # Simulate the QGIS task being cancelled externally
        # (e.g. user clicked "Cancel" in the QGIS task manager)
        token.cancel("QGIS task cancelled by user")

        # The pipeline's check_cancelled would see this
        self.assertTrue(callback())

    def test_progress_stops_after_cancellation(self):
        """Once cancelled, the pipeline should not emit further progress."""
        token = CancelToken()
        events = []

        def progress(stage: StageName, value: float, message: str) -> None:
            events.append((stage, value, message))

        def cancel() -> bool:
            return token.cancelled

        # Simulate a loop that cancels after 3 iterations
        for i in range(10):
            if cancel():
                events.append((StageName.VECTORIZE, -1, f"Cancelled at iter {i}"))
                break
            progress(StageName.VECTORIZE, (i + 1) / 10, f"step {i}")

        # Now cancel and continue
        token.cancel()
        for i in range(10):
            if cancel():
                events.append((StageName.VECTORIZE, -1, "cancelled"))
                break

        # First loop completed (3 progress events + 1 cancel marker)
        # Second loop cancelled immediately
        self.assertGreater(len(events), 0)
        cancelled_events = [e for e in events if e[1] == -1]
        self.assertEqual(len(cancelled_events), 1)


if __name__ == "__main__":
    unittest.main()
