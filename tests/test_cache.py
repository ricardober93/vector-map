"""Tests for the result cache."""

from __future__ import annotations

import json
import tempfile
import time
import unittest
from pathlib import Path

from qgis_vector_map.core.cache import (
    CACHE_DIRNAME,
    CACHE_VERSION,
    CacheEntry,
    CacheKey,
    ResultCache,
    compute_cache_key,
    hash_parameters,
)


def _write_raster(path: Path, content: bytes = b"fake raster data") -> Path:
    path.write_bytes(content)
    return path


class HashParametersTests(unittest.TestCase):
    """Tests for the hash_parameters helper."""

    def test_empty_dict(self):
        h = hash_parameters({})
        self.assertEqual(len(h), 16)

    def test_same_dict_same_hash(self):
        h1 = hash_parameters({"a": 1, "b": 2})
        h2 = hash_parameters({"b": 2, "a": 1})
        self.assertEqual(h1, h2)

    def test_different_dict_different_hash(self):
        h1 = hash_parameters({"a": 1})
        h2 = hash_parameters({"a": 2})
        self.assertNotEqual(h1, h2)

    def test_handles_nested_dicts(self):
        h1 = hash_parameters({"a": {"b": 1, "c": 2}})
        h2 = hash_parameters({"a": {"b": 1, "c": 2}})
        self.assertEqual(h1, h2)

    def test_handles_lists(self):
        h1 = hash_parameters({"a": [1, 2, 3]})
        h2 = hash_parameters({"a": [1, 2, 3]})
        self.assertEqual(h1, h2)

    def test_handles_non_string_values(self):
        h = hash_parameters({"a": 1.5, "b": True, "c": None})
        self.assertEqual(len(h), 16)


class ComputeCacheKeyTests(unittest.TestCase):
    """Tests for the compute_cache_key function."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmpdir = Path(self._tmp.name)

    def test_basic_construction(self):
        raster = _write_raster(self.tmpdir / "a.tif")
        key = compute_cache_key(
            file_path=raster,
            profile_id="regional",
            engine="auto",
            execution_mode="auto",
            output_format="gpkg",
            output_path=self.tmpdir / "out.gpkg",
        )
        self.assertEqual(key.profile_id, "regional")
        self.assertEqual(key.file_size, raster.stat().st_size)
        self.assertEqual(key.file_mtime, raster.stat().st_mtime)

    def test_uses_absolute_path(self):
        raster = _write_raster(self.tmpdir / "a.tif")
        key = compute_cache_key(
            file_path=raster,
            profile_id="regional",
            engine="auto",
            execution_mode="auto",
            output_format="gpkg",
            output_path=self.tmpdir / "out.gpkg",
        )
        self.assertTrue(Path(key.file_path).is_absolute())

    def test_raises_for_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            compute_cache_key(
                file_path=self.tmpdir / "does_not_exist.tif",
                profile_id="regional",
                engine="auto",
                execution_mode="auto",
                output_format="gpkg",
                output_path=self.tmpdir / "out.gpkg",
            )

    def test_same_inputs_same_key(self):
        raster = _write_raster(self.tmpdir / "a.tif")
        out = self.tmpdir / "out.gpkg"
        key1 = compute_cache_key(
            file_path=raster,
            profile_id="regional",
            engine="auto",
            execution_mode="auto",
            output_format="gpkg",
            output_path=out,
        )
        key2 = compute_cache_key(
            file_path=raster,
            profile_id="regional",
            engine="auto",
            execution_mode="auto",
            output_format="gpkg",
            output_path=out,
        )
        self.assertEqual(key1, key2)
        self.assertEqual(key1.to_hex(), key2.to_hex())

    def test_different_profile_different_key(self):
        raster = _write_raster(self.tmpdir / "a.tif")
        out = self.tmpdir / "out.gpkg"
        k1 = compute_cache_key(
            file_path=raster, profile_id="regional", engine="auto",
            execution_mode="auto", output_format="gpkg", output_path=out,
        )
        k2 = compute_cache_key(
            file_path=raster, profile_id="edge", engine="auto",
            execution_mode="auto", output_format="gpkg", output_path=out,
        )
        self.assertNotEqual(k1.to_hex(), k2.to_hex())

    def test_modified_file_invalidates_key(self):
        raster = _write_raster(self.tmpdir / "a.tif", b"version 1")
        out = self.tmpdir / "out.gpkg"
        k1 = compute_cache_key(
            file_path=raster, profile_id="regional", engine="auto",
            execution_mode="auto", output_format="gpkg", output_path=out,
        )
        time.sleep(0.05)
        # Modify the file (different size + new mtime)
        _write_raster(raster, b"version 2 with more content")
        k2 = compute_cache_key(
            file_path=raster, profile_id="regional", engine="auto",
            execution_mode="auto", output_format="gpkg", output_path=out,
        )
        self.assertNotEqual(k1.to_hex(), k2.to_hex())

    def test_different_algorithm_version_different_key(self):
        raster = _write_raster(self.tmpdir / "a.tif")
        out = self.tmpdir / "out.gpkg"
        k1 = compute_cache_key(
            file_path=raster, profile_id="regional", engine="auto",
            execution_mode="auto", output_format="gpkg", output_path=out,
            algorithm_version="1.0.0",
        )
        k2 = compute_cache_key(
            file_path=raster, profile_id="regional", engine="auto",
            execution_mode="auto", output_format="gpkg", output_path=out,
            algorithm_version="1.1.0",
        )
        self.assertNotEqual(k1.to_hex(), k2.to_hex())

    def test_parameters_affect_key(self):
        raster = _write_raster(self.tmpdir / "a.tif")
        out = self.tmpdir / "out.gpkg"
        k1 = compute_cache_key(
            file_path=raster, profile_id="regional", engine="auto",
            execution_mode="auto", output_format="gpkg", output_path=out,
            parameters={"max_colors": 8},
        )
        k2 = compute_cache_key(
            file_path=raster, profile_id="regional", engine="auto",
            execution_mode="auto", output_format="gpkg", output_path=out,
            parameters={"max_colors": 16},
        )
        self.assertNotEqual(k1.to_hex(), k2.to_hex())


class CacheKeyTests(unittest.TestCase):
    """Tests for the CacheKey dataclass and to_hex()."""

    def test_to_hex_length_default(self):
        key = CacheKey(
            file_path="/a.tif",
            file_size=100,
            file_mtime=1.0,
            profile_id="regional",
            engine="auto",
            execution_mode="auto",
            output_format="gpkg",
            output_path="/a.gpkg",
            parameters_hash="abc",
            algorithm_version="1.0.0",
        )
        self.assertEqual(len(key.to_hex()), 16)

    def test_to_hex_custom_length(self):
        key = CacheKey(
            file_path="/a.tif",
            file_size=100,
            file_mtime=1.0,
            profile_id="regional",
            engine="auto",
            execution_mode="auto",
            output_format="gpkg",
            output_path="/a.gpkg",
            parameters_hash="abc",
            algorithm_version="1.0.0",
        )
        self.assertEqual(len(key.to_hex(8)), 8)
        self.assertEqual(len(key.to_hex(32)), 32)
        # 64 is the full SHA-256 hex length
        self.assertEqual(len(key.to_hex(64)), 64)

    def test_to_hex_deterministic(self):
        key1 = CacheKey(
            file_path="/a.tif", file_size=1, file_mtime=1.0,
            profile_id="p", engine="e", execution_mode="m",
            output_format="f", output_path="/o", parameters_hash="h",
            algorithm_version="v",
        )
        key2 = CacheKey(
            file_path="/a.tif", file_size=1, file_mtime=1.0,
            profile_id="p", engine="e", execution_mode="m",
            output_format="f", output_path="/o", parameters_hash="h",
            algorithm_version="v",
        )
        self.assertEqual(key1.to_hex(), key2.to_hex())

    def test_frozen(self):
        key = CacheKey(
            file_path="/a.tif", file_size=1, file_mtime=1.0,
            profile_id="p", engine="e", execution_mode="m",
            output_format="f", output_path="/o", parameters_hash="h",
            algorithm_version="v",
        )
        with self.assertRaises(Exception):  # FrozenInstanceError
            key.file_size = 999  # type: ignore[misc]


class ResultCacheTests(unittest.TestCase):
    """Tests for the ResultCache class."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmpdir = Path(self._tmp.name)
        self.cache = ResultCache(storage_dir=self.tmpdir)
        self.raster = _write_raster(self.tmpdir / "a.tif")
        self.output = self.tmpdir / "out.gpkg"
        self.output.write_text("fake output")
        self.key = compute_cache_key(
            file_path=self.raster,
            profile_id="regional",
            engine="auto",
            execution_mode="auto",
            output_format="gpkg",
            output_path=self.output,
        )

    def test_empty_initially(self):
        self.assertEqual(self.cache.size(), 0)
        self.assertFalse(self.cache.has(self.key))

    def test_cache_dir_created(self):
        self.assertTrue(self.cache.cache_dir.exists())
        self.assertEqual(self.cache.cache_dir.name, CACHE_DIRNAME)

    def test_put_and_has(self):
        self.cache.put(self.key, feature_count=100)
        self.assertTrue(self.cache.has(self.key))
        self.assertEqual(self.cache.size(), 1)

    def test_get_returns_entry(self):
        self.cache.put(self.key, feature_count=42, metadata={"tile": 3})
        entry = self.cache.get(self.key)
        self.assertIsNotNone(entry)
        self.assertEqual(entry.feature_count, 42)
        self.assertEqual(entry.metadata["tile"], 3)
        self.assertEqual(entry.profile_id, "regional")
        self.assertEqual(entry.engine, "auto")

    def test_get_returns_none_for_missing(self):
        self.assertIsNone(self.cache.get(self.key))

    def test_has_requires_output_file_exists(self):
        self.cache.put(self.key, feature_count=10)
        self.assertTrue(self.cache.has(self.key))
        # Delete the output file - now has() should return False
        self.output.unlink()
        self.assertFalse(self.cache.has(self.key))

    def test_invalidate_removes_entry(self):
        self.cache.put(self.key, feature_count=10)
        self.assertTrue(self.cache.invalidate(self.key))
        self.assertFalse(self.cache.has(self.key))

    def test_invalidate_returns_false_when_missing(self):
        self.assertFalse(self.cache.invalidate(self.key))

    def test_clear_removes_all(self):
        # Add multiple entries
        for i in range(3):
            raster = _write_raster(self.tmpdir / f"f{i}.tif")
            out = self.tmpdir / f"out{i}.gpkg"
            out.write_text("data")
            key = compute_cache_key(
                file_path=raster, profile_id="regional", engine="auto",
                execution_mode="auto", output_format="gpkg", output_path=out,
            )
            self.cache.put(key, feature_count=i * 10)
        self.assertEqual(self.cache.size(), 3)
        removed = self.cache.clear()
        self.assertEqual(removed, 3)
        self.assertEqual(self.cache.size(), 0)

    def test_clear_empty(self):
        self.assertEqual(self.cache.clear(), 0)

    def test_stats(self):
        # Add a few entries with different profiles
        for i, profile in enumerate(["regional", "edge", "regional"]):
            raster = _write_raster(self.tmpdir / f"f{i}.tif")
            out = self.tmpdir / f"out{i}.gpkg"
            out.write_text("data")
            key = compute_cache_key(
                file_path=raster, profile_id=profile, engine="auto",
                execution_mode="auto", output_format="gpkg", output_path=out,
            )
            self.cache.put(key, feature_count=(i + 1) * 10)
        stats = self.cache.stats()
        self.assertEqual(stats["total_entries"], 3)
        self.assertEqual(stats["total_features"], 60)
        self.assertEqual(stats["by_profile"]["regional"], 2)
        self.assertEqual(stats["by_profile"]["edge"], 1)

    def test_prune_missing_outputs(self):
        # Add an entry whose output we'll delete
        self.cache.put(self.key, feature_count=10)
        # Add another with output still present
        raster2 = _write_raster(self.tmpdir / "b.tif")
        out2 = self.tmpdir / "out2.gpkg"
        out2.write_text("data")
        key2 = compute_cache_key(
            file_path=raster2, profile_id="regional", engine="auto",
            execution_mode="auto", output_format="gpkg", output_path=out2,
        )
        self.cache.put(key2, feature_count=20)
        self.assertEqual(self.cache.size(), 2)
        # Delete the first output
        self.output.unlink()
        removed = self.cache.prune_missing_outputs()
        self.assertEqual(removed, 1)
        self.assertEqual(self.cache.size(), 1)

    def test_corrupted_entry_file_recovers(self):
        """Manually write a bad JSON file, get() should return None."""
        entry_path = self.cache._entry_path(self.key.to_hex())
        entry_path.write_text("not valid json {")
        self.assertIsNone(self.cache.get(self.key))

    def test_entry_persistence(self):
        """A new cache instance with the same dir should see old entries."""
        self.cache.put(self.key, feature_count=10)
        new_cache = ResultCache(storage_dir=self.tmpdir)
        self.assertTrue(new_cache.has(self.key))
        entry = new_cache.get(self.key)
        self.assertEqual(entry.feature_count, 10)


class CacheEntryTests(unittest.TestCase):
    """Tests for the CacheEntry dataclass."""

    def test_to_dict_roundtrip(self):
        entry = CacheEntry(
            cache_key="abc",
            timestamp="2026-01-01T00:00:00",
            output_path="/a.gpkg",
            file_size=100,
            file_mtime=1.0,
            profile_id="regional",
            engine="auto",
            execution_mode="auto",
            output_format="gpkg",
            feature_count=42,
            algorithm_version="1.0.0",
            metadata={"x": 1},
        )
        data = entry.to_dict()
        restored = CacheEntry.from_dict(data)
        self.assertEqual(restored.cache_key, "abc")
        self.assertEqual(restored.feature_count, 42)
        self.assertEqual(restored.metadata, {"x": 1})

    def test_from_dict_ignores_unknown(self):
        data = {
            "cache_key": "abc",
            "timestamp": "2026-01-01",
            "output_path": "/a",
            "file_size": 1,
            "file_mtime": 1.0,
            "profile_id": "p",
            "engine": "e",
            "execution_mode": "m",
            "output_format": "f",
            "feature_count": 0,
            "algorithm_version": "1.0.0",
            "unknown_field": "ignored",
        }
        entry = CacheEntry.from_dict(data)
        self.assertEqual(entry.cache_key, "abc")


if __name__ == "__main__":
    unittest.main()
