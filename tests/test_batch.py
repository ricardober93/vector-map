"""Tests for BatchProcessor."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from qgis_vector_map.core.batch import (
    BatchProcessor,
    BatchResult,
    FileOutcome,
)
from qgis_vector_map.core.errors import PipelineError
from qgis_vector_map.core.models import (
    PipelineResult,
    VectorLayer,
)


def _make_pipeline_result(feature_count: int = 5) -> PipelineResult:
    """Create a minimal PipelineResult for testing."""
    return PipelineResult(
        output_path=Path("/tmp/out.gpkg"),
        vector_layer=VectorLayer(features=[MagicMock()] * feature_count),
        stage_reports=[],
        profile_id="regional-high-precision",
        engine_name="classic-local",
    )


class _FakeStage:
    """Lightweight stand-in for StageName to avoid QGIS dependency in tests."""

    def __init__(self, value: str) -> None:
        self.value = value

    def __eq__(self, other):
        return self.value == getattr(other, "value", other)

    def __hash__(self):
        return hash(self.value)


class BatchResultTests(unittest.TestCase):
    """Tests for the BatchResult dataclass."""

    def test_empty_result(self):
        result = BatchResult()
        self.assertEqual(result.total, 0)
        self.assertEqual(result.succeeded, 0)
        self.assertEqual(result.failed, 0)
        self.assertEqual(result.cancelled_count, 0)
        self.assertEqual(result.total_features, 0)
        self.assertEqual(result.summary(), "0/0 succeeded, 0 failed")

    def test_all_success(self):
        result = BatchResult(
            outcomes=[
                FileOutcome(source_path="/a", status="success", feature_count=10),
                FileOutcome(source_path="/b", status="success", feature_count=5),
            ]
        )
        self.assertEqual(result.total, 2)
        self.assertEqual(result.succeeded, 2)
        self.assertEqual(result.failed, 0)
        self.assertEqual(result.total_features, 15)
        self.assertEqual(result.summary(), "2/2 succeeded, 0 failed")

    def test_mixed_outcomes(self):
        result = BatchResult(
            outcomes=[
                FileOutcome(source_path="/a", status="success", feature_count=10),
                FileOutcome(source_path="/b", status="failed", error="boom"),
                FileOutcome(source_path="/c", status="cancelled"),
            ],
            cancelled=True,
        )
        self.assertEqual(result.succeeded, 1)
        self.assertEqual(result.failed, 1)
        self.assertEqual(result.cancelled_count, 1)
        self.assertEqual(
            result.summary(),
            "1/3 succeeded, 1 failed, 1 cancelled (batch aborted)",
        )

    def test_failures_helper(self):
        result = BatchResult(
            outcomes=[
                FileOutcome(source_path="/a", status="success"),
                FileOutcome(source_path="/b", status="failed", error="x"),
                FileOutcome(source_path="/c", status="failed", error="y"),
            ]
        )
        fails = result.failures()
        self.assertEqual(len(fails), 2)
        self.assertEqual([f.source_path for f in fails], ["/b", "/c"])

    def test_cancelled_flag(self):
        result = BatchResult(cancelled=True)
        self.assertTrue(result.cancelled)


class BatchProcessorRunTests(unittest.TestCase):
    """Tests for BatchProcessor.run with mocked run_vectorization."""

    def _mock_run(self, results_by_path: dict):
        """Build a fake run_vectorization that returns results by path."""
        def fake_run(request, progress_callback=None, cancel_callback=None):
            if str(request.source) in results_by_path:
                result = results_by_path[str(request.source)]
                if isinstance(result, Exception):
                    raise result
                return result
            raise PipelineError(f"Unexpected source: {request.source}")
        return fake_run

    def test_empty_sources_returns_empty(self):
        processor = BatchProcessor()
        result = processor.run([])
        self.assertEqual(result.total, 0)
        self.assertFalse(result.cancelled)

    def test_single_file_success(self):
        with tempfile_TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "a.tif"
            source.write_text("fake raster")
            processor = BatchProcessor()
            with patch(
                "qgis_vector_map.core.batch.run_vectorization",
                self._mock_run({str(source): _make_pipeline_result(3)}),
            ):
                result = processor.run([str(source)])
            self.assertEqual(result.total, 1)
            self.assertEqual(result.succeeded, 1)
            self.assertEqual(result.total_features, 3)

    def test_multiple_files_sequential(self):
        with tempfile_TemporaryDirectory() as tmpdir:
            sources = []
            for i in range(3):
                s = Path(tmpdir) / f"file{i}.tif"
                s.write_text("fake")
                sources.append(str(s))
            processor = BatchProcessor()
            with patch(
                "qgis_vector_map.core.batch.run_vectorization",
                self._mock_run({s: _make_pipeline_result(i + 1) for i, s in enumerate(sources)}),
            ):
                result = processor.run(sources)
            self.assertEqual(result.total, 3)
            self.assertEqual(result.succeeded, 3)
            self.assertEqual(result.total_features, 6)  # 1+2+3

    def test_continues_after_failure_by_default(self):
        with tempfile_TemporaryDirectory() as tmpdir:
            sources = []
            for i in range(3):
                s = Path(tmpdir) / f"file{i}.tif"
                s.write_text("fake")
                sources.append(str(s))
            processor = BatchProcessor()
            with patch(
                "qgis_vector_map.core.batch.run_vectorization",
                self._mock_run(
                    {
                        sources[0]: _make_pipeline_result(1),
                        sources[1]: PipelineError("boom"),
                        sources[2]: _make_pipeline_result(2),
                    }
                ),
            ):
                result = processor.run(sources)
            self.assertEqual(result.succeeded, 2)
            self.assertEqual(result.failed, 1)
            self.assertEqual(result.failures()[0].source_path, sources[1])
            self.assertIn("boom", result.failures()[0].error)

    def test_stop_on_error_aborts_after_first_failure(self):
        with tempfile_TemporaryDirectory() as tmpdir:
            sources = []
            for i in range(3):
                s = Path(tmpdir) / f"file{i}.tif"
                s.write_text("fake")
                sources.append(str(s))
            processor = BatchProcessor(stop_on_error=True)
            with patch(
                "qgis_vector_map.core.batch.run_vectorization",
                self._mock_run(
                    {
                        sources[0]: _make_pipeline_result(1),
                        sources[1]: PipelineError("boom"),
                        sources[2]: _make_pipeline_result(2),
                    }
                ),
            ):
                result = processor.run(sources)
            self.assertEqual(result.succeeded, 1)
            self.assertEqual(result.failed, 1)
            # The third file should not have been processed
            self.assertEqual(result.total, 2)

    def test_cancellation_aborts_batch(self):
        with tempfile_TemporaryDirectory() as tmpdir:
            sources = []
            for i in range(3):
                s = Path(tmpdir) / f"file{i}.tif"
                s.write_text("fake")
                sources.append(str(s))
            processor = BatchProcessor()
            with patch(
                "qgis_vector_map.core.batch.run_vectorization",
                self._mock_run({s: _make_pipeline_result(1) for s in sources}),
            ):
                # Cancel after first file
                state = {"count": 0}

                def cancel_cb():
                    state["count"] += 1
                    return state["count"] > 1  # Cancel after first check

                result = processor.run(sources, cancel_callback=cancel_cb)
            self.assertTrue(result.cancelled)
            self.assertGreater(result.cancelled_count, 0)
            self.assertLess(result.total, 3)

    def test_missing_file_marked_as_failed(self):
        processor = BatchProcessor()
        result = processor.run(["/does/not/exist.tif"])
        self.assertEqual(result.failed, 1)
        self.assertEqual(result.succeeded, 0)
        self.assertIn("not found", result.failures()[0].error.lower())

    def test_progress_callback_invoked(self):
        with tempfile_TemporaryDirectory() as tmpdir:
            sources = []
            for i in range(2):
                s = Path(tmpdir) / f"file{i}.tif"
                s.write_text("fake")
                sources.append(str(s))
            progress_events = []

            def progress(stage, ratio, message):
                progress_events.append((stage, ratio, message))

            # The mock must call progress_callback to verify global wrapping
            def fake_run(request, progress_callback=None, cancel_callback=None):
                if progress_callback is not None:
                    progress_callback(
                        _FakeStage("vectorize"), 0.5, "tile 1/2"
                    )
                return _make_pipeline_result(1)

            processor = BatchProcessor()
            with patch(
                "qgis_vector_map.core.batch.run_vectorization",
                side_effect=fake_run,
            ):
                processor.run(sources, progress_callback=progress)
            self.assertGreater(len(progress_events), 0)
            # Each call should have ratio between 0 and 1
            for _, ratio, _ in progress_events:
                self.assertGreaterEqual(ratio, 0.0)
                self.assertLessEqual(ratio, 1.0)

    def test_per_file_callback_invoked_after_each_file(self):
        with tempfile_TemporaryDirectory() as tmpdir:
            sources = []
            for i in range(3):
                s = Path(tmpdir) / f"file{i}.tif"
                s.write_text("fake")
                sources.append(str(s))
            events = []

            def per_file(path, index, total, result):
                events.append((path, index, total, result is not None))

            processor = BatchProcessor()
            with patch(
                "qgis_vector_map.core.batch.run_vectorization",
                self._mock_run({s: _make_pipeline_result(1) for s in sources}),
            ):
                processor.run(sources, per_file_callback=per_file)
            self.assertEqual(len(events), 3)
            # Each event should have the correct total
            for e in events:
                self.assertEqual(e[2], 3)
            # All should be success
            self.assertTrue(all(e[3] for e in events))

    def test_layer_name_template(self):
        with tempfile_TemporaryDirectory() as tmpdir:
            s = Path(tmpdir) / "ortho.tif"
            s.write_text("fake")
            captured = {}

            def fake_run(request, progress_callback=None, cancel_callback=None):
                captured["layer_name"] = request.layer_name
                captured["output_path"] = str(request.output_path)
                return _make_pipeline_result(1)

            processor = BatchProcessor()
            with patch(
                "qgis_vector_map.core.batch.run_vectorization",
                side_effect=fake_run,
            ):
                processor.run([str(s)], layer_name_template="{stem}_batch_{index}")
            self.assertEqual(captured["layer_name"], "ortho_batch_1")


class BatchOutputPathTests(unittest.TestCase):
    """Tests for the output path resolution helper."""

    def test_default_extension_gpkg(self):
        ext = BatchProcessor._default_extension("gpkg", ".tif")
        self.assertEqual(ext, ".gpkg")

    def test_default_extension_geojson(self):
        ext = BatchProcessor._default_extension("geojson", ".tif")
        self.assertEqual(ext, ".geojson")

    def test_default_extension_shp(self):
        ext = BatchProcessor._default_extension("shp", ".tif")
        self.assertEqual(ext, ".shp")

    def test_default_extension_auto_keeps_source(self):
        ext = BatchProcessor._default_extension("auto", ".tif")
        self.assertEqual(ext, ".tif")

    def test_default_extension_auto_no_source_suffix(self):
        ext = BatchProcessor._default_extension("auto", "")
        self.assertEqual(ext, ".gpkg")

    def test_resolve_output_path_with_dir(self):
        with tempfile_TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "a.tif"
            source.write_text("fake")
            out_dir = Path(tmpdir) / "out"
            path = BatchProcessor._resolve_output_path(
                source=source,
                output_dir=out_dir,
                output_format="auto",
            )
            self.assertEqual(path.parent, out_dir)
            self.assertTrue(path.name.endswith("a_vectorized.tif"))


def tempfile_TemporaryDirectory():
    """Local import to avoid cluttering module top with try/except."""
    import tempfile
    return tempfile.TemporaryDirectory()


if __name__ == "__main__":
    unittest.main()
