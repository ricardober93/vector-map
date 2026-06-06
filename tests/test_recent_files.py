"""Tests for RecentFilesManager."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from qgis_vector_map.utils.recent_files import (
    MAX_RECENT,
    RECENT_FILENAME,
    RecentFilesManager,
)


class RecentFilesManagerTests(unittest.TestCase):
    """Tests for RecentFilesManager with a temporary storage dir."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmpdir = Path(self._tmp.name)
        self.mgr = RecentFilesManager(storage_dir=self.tmpdir)

    def test_empty_initially(self):
        self.assertEqual(self.mgr.list_recent(), [])

    def test_storage_path_inside_dir(self):
        self.assertEqual(self.mgr.storage_path, self.tmpdir / RECENT_FILENAME)

    def test_add_single_file(self):
        self.mgr.add_recent("/path/to/raster.tif")
        self.assertEqual(self.mgr.list_recent(), ["/path/to/raster.tif"])

    def test_add_multiple_files(self):
        paths = [f"/path/to/file{i}.tif" for i in range(3)]
        for p in paths:
            self.mgr.add_recent(p)
        # Newest first
        self.assertEqual(self.mgr.list_recent(), list(reversed(paths)))

    def test_add_moves_to_top(self):
        self.mgr.add_recent("/a.tif")
        self.mgr.add_recent("/b.tif")
        self.mgr.add_recent("/c.tif")
        # Re-add /a.tif -> it should be at the top
        self.mgr.add_recent("/a.tif")
        self.assertEqual(
            self.mgr.list_recent(),
            ["/a.tif", "/c.tif", "/b.tif"],
        )

    def test_max_recent_cap(self):
        for i in range(MAX_RECENT + 3):
            self.mgr.add_recent(f"/file{i}.tif")
        result = self.mgr.list_recent()
        self.assertEqual(len(result), MAX_RECENT)
        # The newest MAX_RECENT should be kept
        expected_newest = f"/file{MAX_RECENT + 2}.tif"
        self.assertEqual(result[0], expected_newest)

    def test_add_empty_path_ignored(self):
        self.mgr.add_recent("")
        self.mgr.add_recent("/real.tif")
        self.mgr.add_recent(None)
        self.assertEqual(self.mgr.list_recent(), ["/real.tif"])

    def test_remove_recent_existing(self):
        self.mgr.add_recent("/a.tif")
        self.mgr.add_recent("/b.tif")
        result = self.mgr.remove_recent("/a.tif")
        self.assertTrue(result)
        self.assertEqual(self.mgr.list_recent(), ["/b.tif"])

    def test_remove_recent_nonexistent(self):
        self.mgr.add_recent("/a.tif")
        result = self.mgr.remove_recent("/not-there.tif")
        self.assertFalse(result)
        self.assertEqual(self.mgr.list_recent(), ["/a.tif"])

    def test_remove_recent_from_empty(self):
        result = self.mgr.remove_recent("/a.tif")
        self.assertFalse(result)

    def test_clear_recent(self):
        for i in range(3):
            self.mgr.add_recent(f"/file{i}.tif")
        self.mgr.clear_recent()
        self.assertEqual(self.mgr.list_recent(), [])

    def test_persistence_across_instances(self):
        """A new instance with the same dir should see the previous data."""
        self.mgr.add_recent("/persisted.tif")
        new_mgr = RecentFilesManager(storage_dir=self.tmpdir)
        self.assertEqual(new_mgr.list_recent(), ["/persisted.tif"])

    def test_storage_file_format(self):
        """The JSON file should be valid and have the expected keys."""
        self.mgr.add_recent("/some.tif")
        with open(self.mgr.storage_path, "r") as f:
            data = json.load(f)
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        entry = data[0]
        self.assertIn("path", entry)
        self.assertIn("added_at", entry)
        self.assertEqual(entry["path"], "/some.tif")

    def test_corrupted_file_recovers_gracefully(self):
        """If the JSON file is corrupted, list_recent should return []."""
        self.mgr.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.mgr.storage_path, "w") as f:
            f.write("not valid json {{{")
        result = self.mgr.list_recent()
        self.assertEqual(result, [])

    def test_corrupted_file_can_be_overwritten(self):
        """After reading corrupted data, add should still work."""
        self.mgr.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.mgr.storage_path, "w") as f:
            f.write("garbage")
        self.mgr.add_recent("/new.tif")
        self.assertEqual(self.mgr.list_recent(), ["/new.tif"])

    def test_non_list_data_recovers(self):
        """If the JSON contains a dict instead of a list, recover as []."""
        with open(self.mgr.storage_path, "w") as f:
            json.dump({"not": "a list"}, f)
        self.assertEqual(self.mgr.list_recent(), [])

    def test_filter_invalid_entries(self):
        """Entries without a 'path' key should be dropped."""
        with open(self.mgr.storage_path, "w") as f:
            json.dump(
                [
                    {"path": "/valid.tif", "added_at": "2026-01-01T00:00:00"},
                    {"no_path": True},
                    "string entry",
                    42,
                    {"path": "/also-valid.tif", "added_at": "2026-01-02T00:00:00"},
                ],
                f,
            )
        result = self.mgr.list_recent()
        self.assertEqual(result, ["/valid.tif", "/also-valid.tif"])

    def test_prune_missing(self):
        existing = self.tmpdir / "exists.tif"
        existing.write_text("data")
        missing_path = "/does/not/exist.tif"
        self.mgr.add_recent(str(existing))
        self.mgr.add_recent(missing_path)
        removed = self.mgr.prune_missing()
        self.assertEqual(removed, 1)
        self.assertEqual(self.mgr.list_recent(), [str(existing)])

    def test_prune_missing_keeps_all_when_all_exist(self):
        for i in range(3):
            f = self.tmpdir / f"file{i}.tif"
            f.write_text("data")
            self.mgr.add_recent(str(f))
        removed = self.mgr.prune_missing()
        self.assertEqual(removed, 0)
        self.assertEqual(len(self.mgr.list_recent()), 3)

    def test_path_object_accepted(self):
        p = Path("/a/b/c.tif")
        self.mgr.add_recent(p)
        self.assertEqual(self.mgr.list_recent(), [str(p)])


class RecentFilesIntegrationTests(unittest.TestCase):
    """Integration-style tests using a fresh tmpdir for each test."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.mgr = RecentFilesManager(storage_dir=self._tmp.name)

    def test_workflow(self):
        # Empty start
        self.assertEqual(self.mgr.list_recent(), [])

        # Add some files
        self.mgr.add_recent("/a.tif")
        self.mgr.add_recent("/b.tif")
        self.mgr.add_recent("/c.tif")
        self.assertEqual(
            self.mgr.list_recent(),
            ["/c.tif", "/b.tif", "/a.tif"],
        )

        # Re-add /a -> moves to top
        self.mgr.add_recent("/a.tif")
        self.assertEqual(
            self.mgr.list_recent(),
            ["/a.tif", "/c.tif", "/b.tif"],
        )

        # Remove /c
        self.assertTrue(self.mgr.remove_recent("/c.tif"))
        self.assertEqual(
            self.mgr.list_recent(),
            ["/a.tif", "/b.tif"],
        )

        # Clear
        self.mgr.clear_recent()
        self.assertEqual(self.mgr.list_recent(), [])


if __name__ == "__main__":
    unittest.main()
