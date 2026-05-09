"""Integration tests for pipeline memory policies."""

from __future__ import annotations

import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from qgis_vector_map.core.errors import ConfigurationError
from qgis_vector_map.core.models import VectorizationRequest
from qgis_vector_map.core.pipeline import PipelineOrchestrator, run_vectorization
from qgis_vector_map.core.raster import RasterFrame
from qgis_vector_map.processing_profiles import ResolvedProfile


class _FakeArray2D:
    ndim = 2

    def __init__(self, rows: list[list[int]]) -> None:
        self._rows = rows

    def tolist(self) -> list[list[int]]:
        return self._rows


class _FakeBand:
    def __init__(self, data_type: int) -> None:
        self.DataType = data_type


class _WindowDataset:
    def __init__(self, rows: list[list[int]]) -> None:
        self._rows = rows
        self.RasterYSize = len(rows)
        self.RasterXSize = len(rows[0]) if rows else 0
        self.RasterCount = 1

    def ReadAsArray(
        self,
        xoff: int = 0,
        yoff: int = 0,
        xsize: int | None = None,
        ysize: int | None = None,
    ) -> _FakeArray2D:
        if xsize is None and ysize is None:
            return _FakeArray2D(self._rows)
        if xsize is None or ysize is None:
            raise AssertionError("Both xsize and ysize are required for window reads.")
        sliced_rows = [row[xoff : xoff + xsize] for row in self._rows[yoff : yoff + ysize]]
        return _FakeArray2D(sliced_rows)

    def GetRasterBand(self, index: int) -> _FakeBand:
        if index <= 0:
            raise AssertionError("GDAL bands are 1-based.")
        return _FakeBand(1)

    def GetProjection(self) -> str:
        return "EPSG:4326"

    def GetGeoTransform(self, can_return_null: bool = True) -> tuple[float, ...]:
        del can_return_null
        return (0.0, 1.0, 0.0, 0.0, 0.0, -1.0)


class PipelineMemoryPolicyTests(unittest.TestCase):
    def _make_temp_path(self, suffix: str = ".tif") -> Path:
        temp_handle = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        temp_handle.close()
        self.addCleanup(lambda: Path(temp_handle.name).unlink(missing_ok=True))
        return Path(temp_handle.name)

    def _make_output_path(self) -> Path:
        temp_handle = tempfile.NamedTemporaryFile(suffix=".geojson", delete=False)
        temp_handle.close()
        path = Path(temp_handle.name)
        path.unlink(missing_ok=True)
        self.addCleanup(lambda: path.unlink(missing_ok=True))
        return path

    def test_expert_override_requires_explicit_limits(self) -> None:
        request = VectorizationRequest(
            source=[[0, 1], [1, 0]],
            profile_id="regional-high-precision",
            output_path=self._make_output_path(),
            output_format="geojson",
            parameters={"memory_policy": "expert-override"},
        )
        with self.assertRaises(ConfigurationError) as caught:
            run_vectorization(request)
        self.assertIn("memory_policy='expert-override' requires explicit", str(caught.exception))

    def test_expert_override_records_warning(self) -> None:
        request = VectorizationRequest(
            source=[[0, 1], [1, 0]],
            profile_id="regional-high-precision",
            output_path=self._make_output_path(),
            output_format="geojson",
            parameters={
                "memory_policy": "expert-override",
                "max_pixels": 400_000_000,
                "drop_background": False,
                "smoothing_radius": 0,
                "min_region_area": 1,
                "min_hole_area": 1,
            },
        )
        result = run_vectorization(request)
        self.assertTrue(any("expert-override" in warning for warning in result.warnings))
        self.assertEqual(result.metadata.get("memory_policy"), "expert-override")

    def test_regional_tiles_matches_strict_for_tile_aligned_regions(self) -> None:
        rows = [
            [50, 50, 100, 100],
            [50, 50, 100, 100],
            [150, 150, 200, 200],
            [150, 150, 200, 200],
        ]
        source_path = self._make_temp_path()
        strict_output = self._make_output_path()
        tiled_output = self._make_output_path()

        fake_dataset = _WindowDataset(rows)
        fake_gdal = types.SimpleNamespace(
            Open=lambda source: fake_dataset,
            GetDataTypeSize=lambda data_type: 8 if data_type == 1 else 16,
        )
        fake_osgeo = types.SimpleNamespace(gdal=fake_gdal)
        base_parameters = {
            "drop_background": False,
            "smoothing_radius": 0,
            "min_region_area": 1,
            "min_hole_area": 1,
            "simplify_tolerance": 0.0,
            "chunk_size": 2,
            "tile_size": 2,
        }
        with patch.dict(sys.modules, {"osgeo": fake_osgeo}, clear=False):
            strict_result = run_vectorization(
                VectorizationRequest(
                    source=source_path,
                    profile_id="regional-high-precision",
                    output_path=strict_output,
                    output_format="geojson",
                    parameters={**base_parameters, "memory_policy": "strict"},
                )
            )
            tiled_result = run_vectorization(
                VectorizationRequest(
                    source=source_path,
                    profile_id="regional-high-precision",
                    output_path=tiled_output,
                    output_format="geojson",
                    parameters={**base_parameters, "memory_policy": "regional-tiles"},
                )
            )

        self.assertEqual(strict_result.profile_id, tiled_result.profile_id)
        self.assertEqual(
            strict_result.vector_layer.feature_count(),
            tiled_result.vector_layer.feature_count(),
        )
        self.assertEqual(
            strict_result.metadata.get("memory_policy"),
            "strict",
        )
        self.assertEqual(
            tiled_result.metadata.get("memory_policy"),
            "regional-tiles",
        )
        self.assertEqual(
            tiled_result.metadata.get("tile_execution", {}).get("tile_count"),
            4,
        )

        strict_signatures = sorted(
            str(feature.coordinates) for feature in strict_result.vector_layer.features
        )
        tiled_signatures = sorted(
            str(feature.coordinates) for feature in tiled_result.vector_layer.features
        )
        self.assertEqual(strict_signatures, tiled_signatures)


if __name__ == "__main__":
    unittest.main()

class TiledProgressTests(unittest.TestCase):
    """Tests for tiled processing with progress callback."""

    def _make_temp_path(self, suffix: str = ".tif") -> Path:
        temp_handle = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        temp_handle.close()
        self.addCleanup(lambda: Path(temp_handle.name).unlink(missing_ok=True))
        return Path(temp_handle.name)

    def _make_output_path(self) -> Path:
        temp_handle = tempfile.NamedTemporaryFile(suffix=".geojson", delete=False)
        temp_handle.close()
        path = Path(temp_handle.name)
        path.unlink(missing_ok=True)
        self.addCleanup(lambda: path.unlink(missing_ok=True))
        return path

    def test_tiled_pipeline_reports_progress(self) -> None:
        rows = [
            [50, 50, 100, 100],
            [50, 50, 100, 100],
            [150, 150, 200, 200],
            [150, 150, 200, 200],
        ]
        source_path = self._make_temp_path()
        output_path = self._make_output_path()

        class _DS:
            RasterYSize = 4
            RasterXSize = 4
            RasterCount = 1
            def ReadAsArray(self, xoff=0, yoff=0, xsize=None, ysize=None):
                if xsize is None and ysize is None:
                    return _WindowDataset._to_fake(rows)
                sliced = [row[xoff:xoff+xsize] for row in rows[yoff:yoff+ysize]]
                return _WindowDataset._to_fake(sliced)
            def GetRasterBand(self, i):
                class B:
                    DataType = 1
                return B()
            def GetProjection(self):
                return ""
            def GetGeoTransform(self, can_return_null=True):
                return (0.0, 1.0, 0.0, 0.0, 0.0, -1.0)

        class _Arr:
            ndim = 2
            def __init__(self, data):
                self._data = data
            def tolist(self):
                return self._data

        class _WindowDataset:
            @staticmethod
            def _to_fake(r):
                return _Arr(r)

        fake_gdal = types.SimpleNamespace(
            Open=lambda s: _DS(),
            GetDataTypeSize=lambda dt: 8,
        )
        fake_osgeo = types.SimpleNamespace(gdal=fake_gdal)

        progress_calls: list[tuple] = []

        def progress_cb(stage, progress, message):
            progress_calls.append((stage, progress, message))

        base_params = {
            "drop_background": False,
            "smoothing_radius": 0,
            "min_region_area": 1,
            "min_hole_area": 1,
            "simplify_tolerance": 0.0,
            "chunk_size": 2,
            "tile_size": 2,
        }
        with patch.dict(sys.modules, {"osgeo": fake_osgeo}, clear=False):
            _ = run_vectorization(
                VectorizationRequest(
                    source=source_path,
                    profile_id="regional-high-precision",
                    output_path=output_path,
                    output_format="geojson",
                    parameters={**base_params, "memory_policy": "regional-tiles"},
                ),
                progress_callback=progress_cb,
            )

        # Progress should have been reported
        self.assertTrue(len(progress_calls) > 0, "Progress callback was never invoked")


class ExecutionModeResolutionTests(unittest.TestCase):
    """Tests for _resolve_execution_mode memory policy resolution."""

    def _make_orchestrator(self) -> PipelineOrchestrator:
        return PipelineOrchestrator()

    def _make_load_options(
        self, *, max_pixels: int = 500_000_000, profile_mode: str | None = None
    ) -> RasterFrame.LoadOptions:
        return RasterFrame.LoadOptions(
            max_pixels=max_pixels,
            max_estimated_bytes=16 * 1024 * 1024 * 1024,
            profile_mode=profile_mode,
        )

    def _make_profile(self, mode: str = "regional") -> ResolvedProfile:
        return ResolvedProfile(
            profile_id=f"{mode}-high-precision",
            display_name=f"{mode.title()} High Precision",
            mode=mode,
            description="Test profile",
            parameters={},
        )

    def test_auto_regional_below_threshold_returns_strict(self) -> None:
        orch = self._make_orchestrator()
        request = VectorizationRequest(
            source=[[0, 1], [1, 0]],
            profile_id="regional-high-precision",
            output_path=Path("/tmp/out.geojson"),
            execution_mode="auto",
        )
        options = self._make_load_options(profile_mode="regional")
        profile = self._make_profile(mode="regional")
        policy, warnings = orch._resolve_execution_mode(
            request=request, raster_load_options=options, profile=profile
        )
        self.assertEqual(policy, "strict")
        self.assertEqual(len(warnings), 0)

    def test_auto_regional_above_threshold_returns_tiled(self) -> None:
        orch = self._make_orchestrator()
        source_path = Path("/tmp/huge_raster.tif")
        request = VectorizationRequest(
            source=str(source_path),
            profile_id="regional-high-precision",
            output_path=Path("/tmp/out.geojson"),
            execution_mode="auto",
        )
        options = self._make_load_options(max_pixels=1, profile_mode="regional")
        profile = self._make_profile(mode="regional")
        threshold_result = (True, 7_429_106_145, 375_000_000)
        with patch.object(orch, "_check_auto_threshold", return_value=threshold_result):
            policy, warnings = orch._resolve_execution_mode(
                request=request, raster_load_options=options, profile=profile
            )
        self.assertEqual(policy, "regional-tiles")
        self.assertTrue(any("tiled execution activated" in w for w in warnings))

    def test_auto_edge_above_threshold_returns_tiled(self) -> None:
        orch = self._make_orchestrator()
        source_path = Path("/tmp/huge_raster.tif")
        request = VectorizationRequest(
            source=str(source_path),
            profile_id="edge-high-precision",
            output_path=Path("/tmp/out.geojson"),
            execution_mode="auto",
        )
        options = self._make_load_options(max_pixels=1, profile_mode="edge")
        profile = self._make_profile(mode="edge")
        threshold_result = (True, 7_429_106_145, 375_000_000)
        with patch.object(orch, "_check_auto_threshold", return_value=threshold_result):
            policy, warnings = orch._resolve_execution_mode(
                request=request, raster_load_options=options, profile=profile
            )
        self.assertEqual(policy, "tiled")
        self.assertTrue(any("tiled execution activated" in w for w in warnings))

    def test_auto_linear_above_threshold_returns_tiled(self) -> None:
        orch = self._make_orchestrator()
        source_path = Path("/tmp/huge_raster.tif")
        request = VectorizationRequest(
            source=str(source_path),
            profile_id="linear-high-precision",
            output_path=Path("/tmp/out.geojson"),
            execution_mode="auto",
        )
        options = self._make_load_options(max_pixels=1, profile_mode="linear")
        profile = self._make_profile(mode="linear")
        threshold_result = (True, 7_429_106_145, 375_000_000)
        with patch.object(orch, "_check_auto_threshold", return_value=threshold_result):
            policy, warnings = orch._resolve_execution_mode(
                request=request, raster_load_options=options, profile=profile
            )
        self.assertEqual(policy, "tiled")
        self.assertTrue(any("tiled execution activated" in w for w in warnings))

    def test_strict_regional_above_threshold_warns(self) -> None:
        orch = self._make_orchestrator()
        source_path = Path("/tmp/huge_raster.tif")
        request = VectorizationRequest(
            source=str(source_path),
            profile_id="regional-high-precision",
            output_path=Path("/tmp/out.geojson"),
            execution_mode="strict",
        )
        options = self._make_load_options(max_pixels=1, profile_mode="regional")
        profile = self._make_profile(mode="regional")
        threshold_result = (True, 7_429_106_145, 375_000_000)
        with patch.object(orch, "_check_auto_threshold", return_value=threshold_result):
            policy, warnings = orch._resolve_execution_mode(
                request=request, raster_load_options=options, profile=profile
            )
        self.assertEqual(policy, "strict")
        self.assertTrue(any("Consider switching" in w for w in warnings))

    def test_tiled_regional_returns_tiled(self) -> None:
        orch = self._make_orchestrator()
        request = VectorizationRequest(
            source=[[0, 1], [1, 0]],
            profile_id="regional-high-precision",
            output_path=Path("/tmp/out.geojson"),
            execution_mode="tiled",
        )
        options = self._make_load_options(profile_mode="regional")
        profile = self._make_profile(mode="regional")
        policy, warnings = orch._resolve_execution_mode(
            request=request, raster_load_options=options, profile=profile
        )
        self.assertEqual(policy, "regional-tiles")

    def test_tiled_edge_returns_tiled_policy(self) -> None:
        orch = self._make_orchestrator()
        request = VectorizationRequest(
            source=[[0, 1], [1, 0]],
            profile_id="edge-high-precision",
            output_path=Path("/tmp/out.geojson"),
            execution_mode="tiled",
        )
        options = self._make_load_options(profile_mode="edge")
        profile = self._make_profile(mode="edge")
        policy, warnings = orch._resolve_execution_mode(
            request=request, raster_load_options=options, profile=profile
        )
        self.assertEqual(policy, "tiled")
        self.assertTrue(any("tile boundaries may be split" in w for w in warnings))

    def test_tiled_linear_returns_tiled_policy(self) -> None:
        orch = self._make_orchestrator()
        request = VectorizationRequest(
            source=[[0, 1], [1, 0]],
            profile_id="linear-high-precision",
            output_path=Path("/tmp/out.geojson"),
            execution_mode="tiled",
        )
        options = self._make_load_options(profile_mode="linear")
        profile = self._make_profile(mode="linear")
        policy, warnings = orch._resolve_execution_mode(
            request=request, raster_load_options=options, profile=profile
        )
        self.assertEqual(policy, "tiled")
        self.assertTrue(any("tile boundaries may be split" in w for w in warnings))
