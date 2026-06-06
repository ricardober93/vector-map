"""Tests for the update checker."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from qgis_vector_map.core.update_check import (
    DEFAULT_CHECK_THROTTLE,
    DEFAULT_REPO,
    UPDATE_CHECK_FILENAME,
    UpdateChecker,
    UpdateInfo,
    _build_api_url,
    _build_release_url,
    _parse_release_payload,
    is_newer,
    parse_version,
)


class ParseVersionTests(unittest.TestCase):
    """Tests for parse_version."""

    def test_simple(self):
        self.assertEqual(parse_version("1.0.0"), (1, 0, 0))

    def test_with_v_prefix(self):
        self.assertEqual(parse_version("v1.0.0"), (1, 0, 0))
        self.assertEqual(parse_version("V2.5.1"), (2, 5, 1))

    def test_two_parts(self):
        self.assertEqual(parse_version("1.0"), (1, 0))

    def test_four_parts(self):
        self.assertEqual(parse_version("1.2.3.4"), (1, 2, 3, 4))

    def test_with_prerelease(self):
        """Pre-release suffixes are ignored."""
        self.assertEqual(parse_version("1.0.0-rc1"), (1, 0, 0))
        self.assertEqual(parse_version("2.0.0-beta"), (2, 0, 0))

    def test_empty(self):
        self.assertEqual(parse_version(""), (0,))

    def test_invalid(self):
        self.assertEqual(parse_version("not-a-version"), (0,))

    def test_with_whitespace(self):
        self.assertEqual(parse_version("  1.0.0  "), (1, 0, 0))


class IsNewerTests(unittest.TestCase):
    """Tests for is_newer."""

    def test_strict_newer(self):
        self.assertTrue(is_newer("1.0.0", "0.9.0"))

    def test_strict_older(self):
        self.assertFalse(is_newer("0.9.0", "1.0.0"))

    def test_same_version(self):
        self.assertFalse(is_newer("1.0.0", "1.0.0"))

    def test_minor_bump(self):
        self.assertTrue(is_newer("1.1.0", "1.0.0"))

    def test_patch_bump(self):
        self.assertTrue(is_newer("1.0.1", "1.0.0"))

    def test_major_bump(self):
        self.assertTrue(is_newer("2.0.0", "1.9.9"))

    def test_v_prefix(self):
        self.assertTrue(is_newer("v1.0.0", "v0.9.0"))

    def test_mixed_prefix(self):
        self.assertTrue(is_newer("v1.0.0", "0.9.0"))
        self.assertTrue(is_newer("1.0.0", "v0.9.0"))

    def test_padding_zeros(self):
        """1.0 is considered older than 1.0.0? No - they should be equal."""
        self.assertFalse(is_newer("1.0", "1.0.0"))
        self.assertFalse(is_newer("1.0.0", "1.0"))

    def test_four_vs_three_parts(self):
        self.assertTrue(is_newer("1.0.0.1", "1.0.0"))
        self.assertFalse(is_newer("1.0.0", "1.0.0.1"))


class UpdateInfoTests(unittest.TestCase):
    """Tests for the UpdateInfo dataclass."""

    def test_default_construction(self):
        info = UpdateInfo(current_version="1.0.0")
        self.assertEqual(info.current_version, "1.0.0")
        self.assertFalse(info.update_available)
        self.assertIsNone(info.latest_version)
        self.assertIsNone(info.error)

    def test_is_success(self):
        info_ok = UpdateInfo(
            current_version="1.0.0", latest_version="1.0.0"
        )
        self.assertTrue(info_ok.is_success)

        info_err = UpdateInfo(
            current_version="1.0.0", error="network down"
        )
        self.assertFalse(info_err.is_success)

    def test_to_dict_roundtrip(self):
        info = UpdateInfo(
            current_version="1.0.0",
            latest_version="1.1.0",
            update_available=True,
            checked_at="2026-01-01T00:00:00",
            release_url="https://example.com",
            release_notes="New features",
        )
        data = info.to_dict()
        restored = UpdateInfo.from_dict(data)
        self.assertEqual(restored.latest_version, "1.1.0")
        self.assertTrue(restored.update_available)

    def test_from_dict_ignores_unknown(self):
        data = {
            "current_version": "1.0.0",
            "latest_version": "1.1.0",
            "unknown_field": "ignored",
        }
        info = UpdateInfo.from_dict(data)
        self.assertEqual(info.current_version, "1.0.0")


class BuildUrlTests(unittest.TestCase):
    def test_build_api_url(self):
        self.assertEqual(
            _build_api_url("foo/bar"),
            "https://api.github.com/repos/foo/bar/releases/latest",
        )

    def test_build_release_url(self):
        self.assertEqual(
            _build_release_url("foo/bar", "v1.0.0"),
            "https://github.com/foo/bar/releases/tag/v1.0.0",
        )


class ParseReleasePayloadTests(unittest.TestCase):
    def test_basic_payload(self):
        payload = {
            "tag_name": "v1.2.3",
            "body": "Some release notes",
        }
        parsed = _parse_release_payload(payload, "foo/bar")
        self.assertEqual(parsed["tag"], "v1.2.3")
        self.assertIn("v1.2.3", parsed["url"])
        self.assertEqual(parsed["notes"], "Some release notes")

    def test_long_body_truncated(self):
        payload = {"tag_name": "v1.0", "body": "x" * 1000}
        parsed = _parse_release_payload(payload, "foo/bar")
        self.assertLessEqual(len(parsed["notes"]), 500)

    def test_missing_body(self):
        payload = {"tag_name": "v1.0"}
        parsed = _parse_release_payload(payload, "foo/bar")
        self.assertEqual(parsed["notes"], "")

    def test_null_body(self):
        payload = {"tag_name": "v1.0", "body": None}
        parsed = _parse_release_payload(payload, "foo/bar")
        self.assertEqual(parsed["notes"], "")


class UpdateCheckerTests(unittest.TestCase):
    """Tests for UpdateChecker with mocked network."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmpdir = Path(self._tmp.name)

    def _make_checker(self, **kwargs):
        defaults = dict(
            current_version="1.0.0",
            repo="foo/bar",
            storage_dir=self.tmpdir,
            throttle_seconds=3600,
            timeout=1.0,
        )
        defaults.update(kwargs)
        return UpdateChecker(**defaults)

    def test_default_repo(self):
        checker = UpdateChecker(current_version="1.0.0", storage_dir=self.tmpdir)
        self.assertEqual(checker.repo, DEFAULT_REPO)

    def test_current_version_property(self):
        checker = self._make_checker(current_version="2.5.1")
        self.assertEqual(checker.current_version, "2.5.1")

    def test_cache_path_in_storage_dir(self):
        checker = self._make_checker()
        self.assertEqual(checker.cache_path, self.tmpdir / UPDATE_CHECK_FILENAME)

    def test_should_check_when_no_cache(self):
        checker = self._make_checker()
        self.assertTrue(checker.should_check())

    def test_should_check_returns_false_within_throttle(self):
        checker = self._make_checker()
        # Cache a recent check
        info = UpdateInfo(current_version="1.0.0", latest_version="1.0.0")
        checker._write_cache(info)
        self.assertFalse(checker.should_check())

    def test_should_check_returns_true_after_throttle(self):
        checker = self._make_checker(throttle_seconds=0)
        info = UpdateInfo(current_version="1.0.0", latest_version="1.0.0")
        checker._write_cache(info)
        self.assertTrue(checker.should_check())

    def test_time_until_next_check_when_no_cache(self):
        checker = self._make_checker()
        self.assertEqual(checker.time_until_next_check(), 0.0)

    def test_time_until_next_check_after_recent_check(self):
        checker = self._make_checker(throttle_seconds=3600)
        info = UpdateInfo(current_version="1.0.0", latest_version="1.0.0")
        checker._write_cache(info)
        # Should be close to 3600 seconds remaining
        remaining = checker.time_until_next_check()
        self.assertGreater(remaining, 3500)
        self.assertLessEqual(remaining, 3600)

    def test_get_cached_returns_none_when_empty(self):
        checker = self._make_checker()
        self.assertIsNone(checker.get_cached())

    def test_get_cached_returns_info(self):
        checker = self._make_checker()
        info = UpdateInfo(
            current_version="1.0.0",
            latest_version="1.0.0",
            checked_at="2026-01-01",
        )
        checker._write_cache(info)
        cached = checker.get_cached()
        self.assertIsNotNone(cached)
        self.assertTrue(cached.from_cache)
        self.assertEqual(cached.latest_version, "1.0.0")

    def test_check_returns_cached_when_throttled(self):
        checker = self._make_checker()
        # Pre-populate cache
        info = UpdateInfo(current_version="1.0.0", latest_version="2.0.0")
        checker._write_cache(info)
        # should_check() returns False -> check() returns cached
        result = checker.check()
        self.assertEqual(result.latest_version, "2.0.0")
        self.assertTrue(result.from_cache)

    def test_check_force_bypasses_throttle(self):
        checker = self._make_checker()
        info = UpdateInfo(current_version="1.0.0", latest_version="1.0.0")
        checker._write_cache(info)
        # Even though throttled, force=True should hit the network
        mock_payload = {
            "tag_name": "v9.9.9",
            "body": "huge release",
        }
        with patch(
            "qgis_vector_map.core.update_check._http_get_json",
            return_value=mock_payload,
        ):
            result = checker.check(force=True)
        self.assertEqual(result.latest_version, "v9.9.9")
        self.assertTrue(result.update_available)

    def test_check_success(self):
        checker = self._make_checker(current_version="1.0.0")
        mock_payload = {"tag_name": "v1.1.0", "body": "minor bump"}
        with patch(
            "qgis_vector_map.core.update_check._http_get_json",
            return_value=mock_payload,
        ):
            result = checker.check(force=True)
        self.assertEqual(result.latest_version, "v1.1.0")
        self.assertTrue(result.update_available)
        self.assertIsNone(result.error)
        self.assertIn("v1.1.0", result.release_url)

    def test_check_no_update_needed(self):
        checker = self._make_checker(current_version="2.0.0")
        mock_payload = {"tag_name": "v1.0.0", "body": ""}
        with patch(
            "qgis_vector_map.core.update_check._http_get_json",
            return_value=mock_payload,
        ):
            result = checker.check(force=True)
        self.assertEqual(result.latest_version, "v1.0.0")
        self.assertFalse(result.update_available)

    def test_check_network_error_sets_error(self):
        import urllib.error
        checker = self._make_checker()
        with patch(
            "qgis_vector_map.core.update_check._http_get_json",
            side_effect=urllib.error.URLError("no internet"),
        ):
            result = checker.check(force=True)
        self.assertIsNone(result.latest_version)
        self.assertIsNotNone(result.error)
        self.assertIn("Network", result.error)

    def test_check_http_error(self):
        import urllib.error
        checker = self._make_checker()
        with patch(
            "qgis_vector_map.core.update_check._http_get_json",
            side_effect=urllib.error.HTTPError(
                "url", 404, "Not Found", {}, None
            ),
        ):
            result = checker.check(force=True)
        self.assertIn("HTTP error", result.error)
        self.assertIn("404", result.error)

    def test_check_json_error(self):
        checker = self._make_checker()
        with patch(
            "qgis_vector_map.core.update_check._http_get_json",
            side_effect=json.JSONDecodeError("err", "doc", 0),
        ):
            result = checker.check(force=True)
        self.assertIn("JSON", result.error)

    def test_check_successful_result_is_cached(self):
        checker = self._make_checker()
        with patch(
            "qgis_vector_map.core.update_check._http_get_json",
            return_value={"tag_name": "v1.0.0", "body": ""},
        ):
            checker.check(force=True)
        # Cache should be populated
        cached = checker.get_cached()
        self.assertIsNotNone(cached)
        self.assertEqual(cached.latest_version, "v1.0.0")

    def test_check_records_checked_at(self):
        checker = self._make_checker()
        with patch(
            "qgis_vector_map.core.update_check._http_get_json",
            return_value={"tag_name": "v1.0.0", "body": ""},
        ):
            result = checker.check(force=True)
        self.assertNotEqual(result.checked_at, "")

    def test_check_handles_corrupt_cache(self):
        checker = self._make_checker()
        # Write garbage to the cache
        checker.cache_path.write_text("not json")
        # should_check should still return True
        self.assertTrue(checker.should_check())
        # get_cached should return None
        self.assertIsNone(checker.get_cached())


if __name__ == "__main__":
    unittest.main()
