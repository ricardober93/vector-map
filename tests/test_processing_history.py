"""Tests for ProcessingHistoryManager and HistoryEntry."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from qgis_vector_map.utils.processing_history import (
    HISTORY_FILENAME,
    MAX_HISTORY,
    HistoryEntry,
    ProcessingHistoryManager,
    make_entry_from_result,
)


def _entry(**overrides):
    """Build a HistoryEntry with sensible defaults."""
    base = dict(
        timestamp=datetime(2026, 6, 5, 12, 0, 0, tzinfo=timezone.utc).isoformat(),
        source_path="/data/raster.tif",
        output_path="/data/out.gpkg",
        profile_id="regional-high-precision",
        engine="auto",
        execution_mode="auto",
        output_format="gpkg",
        layer_name="vectorized",
        duration_seconds=1.5,
        feature_count=42,
        status="success",
    )
    base.update(overrides)
    return HistoryEntry(**base)


class HistoryEntryTests(unittest.TestCase):
    """Tests for the HistoryEntry dataclass."""

    def test_default_construction(self):
        entry = _entry()
        self.assertEqual(entry.status, "success")
        self.assertEqual(entry.feature_count, 42)
        self.assertIsNone(entry.error)
        self.assertEqual(entry.metadata, {})

    def test_is_success(self):
        self.assertTrue(_entry(status="success").is_success)
        self.assertFalse(_entry(status="failed").is_success)
        self.assertFalse(_entry(status="cancelled").is_success)

    def test_is_failure(self):
        self.assertTrue(_entry(status="failed").is_failure)
        self.assertFalse(_entry(status="success").is_failure)

    def test_is_cancelled(self):
        self.assertTrue(_entry(status="cancelled").is_cancelled)
        self.assertFalse(_entry(status="failed").is_cancelled)

    def test_to_dict_roundtrip(self):
        entry = _entry()
        data = entry.to_dict()
        restored = HistoryEntry.from_dict(data)
        self.assertEqual(restored.source_path, entry.source_path)
        self.assertEqual(restored.feature_count, entry.feature_count)
        self.assertEqual(restored.status, entry.status)

    def test_from_dict_ignores_unknown_fields(self):
        data = {
            "timestamp": "2026-01-01T00:00:00",
            "source_path": "/x.tif",
            "output_path": "/x.gpkg",
            "profile_id": "regional",
            "engine": "auto",
            "execution_mode": "auto",
            "output_format": "gpkg",
            "layer_name": "x",
            "duration_seconds": 1.0,
            "feature_count": 5,
            "status": "success",
            "unknown_field": "should be ignored",
            "another_unknown": 42,
        }
        entry = HistoryEntry.from_dict(data)
        self.assertEqual(entry.source_path, "/x.tif")

    def test_from_dict_invalid_size_bytes_becomes_none(self):
        data = {
            "timestamp": "2026-01-01T00:00:00",
            "source_path": "/x.tif",
            "output_path": "/x.gpkg",
            "profile_id": "regional",
            "engine": "auto",
            "execution_mode": "auto",
            "output_format": "gpkg",
            "layer_name": "x",
            "duration_seconds": 1.0,
            "feature_count": 5,
            "status": "success",
            "source_size_bytes": "not a number",
        }
        entry = HistoryEntry.from_dict(data)
        self.assertIsNone(entry.source_size_bytes)

    def test_display_label_contains_status_icon(self):
        entry = _entry(status="success")
        self.assertIn("✓", entry.display_label)
        entry = _entry(status="failed")
        self.assertIn("✗", entry.display_label)
        entry = _entry(status="cancelled")
        self.assertIn("⊘", entry.display_label)

    def test_display_label_contains_stem(self):
        entry = _entry(source_path="/data/my_orthophoto.tif")
        self.assertIn("my_orthophoto", entry.display_label)

    def test_display_label_contains_profile(self):
        entry = _entry(profile_id="edge-high-precision")
        self.assertIn("edge", entry.display_label)


class ProcessingHistoryManagerTests(unittest.TestCase):
    """Tests for ProcessingHistoryManager with a temp storage dir."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmpdir = Path(self._tmp.name)
        self.mgr = ProcessingHistoryManager(storage_dir=self.tmpdir)

    def test_empty_initially(self):
        self.assertEqual(self.mgr.list_entries(), [])

    def test_storage_path(self):
        self.assertEqual(self.mgr.storage_path, self.tmpdir / HISTORY_FILENAME)

    def test_add_single_entry(self):
        self.mgr.add_entry(_entry(source_path="/a.tif"))
        entries = self.mgr.list_entries()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].source_path, "/a.tif")

    def test_newest_first(self):
        self.mgr.add_entry(_entry(timestamp="2026-01-01T00:00:00", source_path="/a"))
        self.mgr.add_entry(_entry(timestamp="2026-01-02T00:00:00", source_path="/b"))
        self.mgr.add_entry(_entry(timestamp="2026-01-03T00:00:00", source_path="/c"))
        paths = [e.source_path for e in self.mgr.list_entries()]
        self.assertEqual(paths, ["/c", "/b", "/a"])

    def test_max_history_cap(self):
        for i in range(MAX_HISTORY + 10):
            self.mgr.add_entry(
                _entry(source_path=f"/f{i}.tif", timestamp=f"2026-01-01T00:{i:02d}:00")
            )
        self.assertEqual(len(self.mgr.list_entries()), MAX_HISTORY)

    def test_dedup_same_source_and_output_and_timestamp(self):
        """Re-adding with same source+output+timestamp replaces (no duplicate)."""
        self.mgr.add_entry(
            _entry(
                source_path="/a.tif",
                output_path="/a.gpkg",
                timestamp="2026-01-01T00:00:00",
                feature_count=10,
            )
        )
        self.mgr.add_entry(
            _entry(
                source_path="/a.tif",
                output_path="/a.gpkg",
                timestamp="2026-01-01T00:00:00",
                feature_count=20,
            )
        )
        entries = self.mgr.list_entries()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].feature_count, 20)

    def test_different_timestamps_same_path_both_kept(self):
        """Same path + output but different timestamps should both be kept."""
        self.mgr.add_entry(
            _entry(
                source_path="/a.tif",
                output_path="/a.gpkg",
                timestamp="2026-01-01T00:00:00",
            )
        )
        self.mgr.add_entry(
            _entry(
                source_path="/a.tif",
                output_path="/a.gpkg",
                timestamp="2026-01-02T00:00:00",
            )
        )
        entries = self.mgr.list_entries()
        self.assertEqual(len(entries), 2)

    def test_find_by_source(self):
        self.mgr.add_entry(_entry(source_path="/a.tif", timestamp="2026-01-01"))
        self.mgr.add_entry(_entry(source_path="/b.tif", timestamp="2026-01-02"))
        self.mgr.add_entry(_entry(source_path="/a.tif", timestamp="2026-01-03"))
        results = self.mgr.find_by_source("/a.tif")
        self.assertEqual(len(results), 2)
        # Newest first
        self.assertEqual(results[0].timestamp, "2026-01-03")

    def test_find_by_source_empty(self):
        self.assertEqual(self.mgr.find_by_source("/nonexistent.tif"), [])

    def test_find_latest_success(self):
        self.mgr.add_entry(_entry(timestamp="2026-01-01", status="failed"))
        self.mgr.add_entry(_entry(timestamp="2026-01-02", status="success"))
        self.mgr.add_entry(_entry(timestamp="2026-01-03", status="cancelled"))
        result = self.mgr.find_latest_success()
        self.assertIsNotNone(result)
        self.assertEqual(result.timestamp, "2026-01-02")

    def test_find_latest_success_when_none(self):
        self.mgr.add_entry(_entry(status="failed"))
        self.assertIsNone(self.mgr.find_latest_success())

    def test_clear(self):
        for i in range(3):
            self.mgr.add_entry(_entry(source_path=f"/f{i}.tif"))
        self.mgr.clear()
        self.assertEqual(self.mgr.list_entries(), [])

    def test_remove_existing(self):
        entry = _entry(source_path="/a.tif", timestamp="2026-01-01")
        self.mgr.add_entry(entry)
        self.assertTrue(self.mgr.remove(entry))
        self.assertEqual(self.mgr.list_entries(), [])

    def test_remove_nonexistent(self):
        self.mgr.add_entry(_entry(source_path="/a.tif"))
        result = self.mgr.remove(_entry(source_path="/b.tif"))
        self.assertFalse(result)

    def test_remove_from_empty(self):
        result = self.mgr.remove(_entry(source_path="/a.tif"))
        self.assertFalse(result)

    def test_prune_failures(self):
        self.mgr.add_entry(_entry(source_path="/a.tif", status="success"))
        self.mgr.add_entry(_entry(source_path="/b.tif", status="failed"))
        self.mgr.add_entry(_entry(source_path="/c.tif", status="cancelled"))
        self.mgr.add_entry(_entry(source_path="/d.tif", status="failed"))
        removed = self.mgr.prune_failures()
        self.assertEqual(removed, 3)
        remaining = self.mgr.list_entries()
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0].status, "success")

    def test_stats(self):
        self.mgr.add_entry(_entry(source_path="/a", status="success"))
        self.mgr.add_entry(_entry(source_path="/b", status="success"))
        self.mgr.add_entry(_entry(source_path="/c", status="failed"))
        self.mgr.add_entry(_entry(source_path="/d", status="cancelled"))
        stats = self.mgr.stats()
        self.assertEqual(stats["total"], 4)
        self.assertEqual(stats["success"], 2)
        self.assertEqual(stats["failed"], 1)
        self.assertEqual(stats["cancelled"], 1)

    def test_persistence(self):
        """A new manager with the same dir should see the previous data."""
        self.mgr.add_entry(_entry(source_path="/persistent.tif"))
        new_mgr = ProcessingHistoryManager(storage_dir=self.tmpdir)
        entries = new_mgr.list_entries()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].source_path, "/persistent.tif")

    def test_corrupted_file_recovers(self):
        self.mgr.storage_path.write_text("garbage")
        self.assertEqual(self.mgr.list_entries(), [])

    def test_non_list_data_recovers(self):
        self.mgr.storage_path.write_text('{"not": "a list"}')
        self.assertEqual(self.mgr.list_entries(), [])

    def test_list_filtered_to_dicts(self):
        self.mgr.storage_path.write_text(
            '[{"timestamp": "2026-01-01", "source_path": "/a.tif", '
            '"output_path": "/a.gpkg", "profile_id": "regional", '
            '"engine": "auto", "execution_mode": "auto", '
            '"output_format": "gpkg", "layer_name": "x", '
            '"duration_seconds": 1.0, "feature_count": 5, "status": "success"},'
            '"string entry", 42, null]'
        )
        entries = self.mgr.list_entries()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].source_path, "/a.tif")


class MakeEntryFromResultTests(unittest.TestCase):
    """Tests for the make_entry_from_result helper."""

    def test_minimal_call(self):
        entry = make_entry_from_result(
            source_path="/a.tif",
            output_path="/a.gpkg",
            profile_id="regional",
            engine="auto",
            execution_mode="auto",
            output_format="gpkg",
            layer_name="vectorized",
            duration_seconds=1.5,
            feature_count=10,
        )
        self.assertEqual(entry.status, "success")
        self.assertIsNone(entry.error)
        # Timestamp is auto-set to now
        self.assertIsNotNone(entry.timestamp)

    def test_with_error(self):
        entry = make_entry_from_result(
            source_path="/a.tif",
            output_path="/a.gpkg",
            profile_id="regional",
            engine="auto",
            execution_mode="auto",
            output_format="gpkg",
            layer_name="x",
            duration_seconds=0.5,
            feature_count=0,
            status="failed",
            error="out of memory",
        )
        self.assertEqual(entry.status, "failed")
        self.assertEqual(entry.error, "out of memory")

    def test_with_metadata(self):
        entry = make_entry_from_result(
            source_path="/a.tif",
            output_path="/a.gpkg",
            profile_id="regional",
            engine="auto",
            execution_mode="auto",
            output_format="gpkg",
            layer_name="x",
            duration_seconds=1.0,
            feature_count=5,
            metadata={"tile_count": 16, "user": "ric"},
        )
        self.assertEqual(entry.metadata["tile_count"], 16)
        self.assertEqual(entry.metadata["user"], "ric")


if __name__ == "__main__":
    unittest.main()
