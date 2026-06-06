"""Tests for GPU detection capability."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from qgis_vector_map.core.gpu import (
    GPUCapability,
    detect_capability,
    get_backend_name,
    get_device_count,
    get_device_names,
    gpu_info_string,
    is_available,
    reset_cache,
)


class GPUCapabilityTests(unittest.TestCase):
    """Tests for the GPUCapability dataclass."""

    def test_default_is_unavailable(self):
        cap = GPUCapability(available=False)
        self.assertFalse(cap.available)
        self.assertIsNone(cap.backend)
        self.assertEqual(cap.device_count, 0)
        self.assertEqual(cap.device_names, ())

    def test_cupy_capability(self):
        cap = GPUCapability(
            available=True,
            backend="cupy",
            device_count=2,
            device_names=("GPU 0", "GPU 1"),
        )
        self.assertTrue(cap.available)
        self.assertEqual(cap.backend, "cupy")
        self.assertEqual(cap.device_count, 2)

    def test_frozen(self):
        cap = GPUCapability(available=False)
        with self.assertRaises(Exception):  # FrozenInstanceError
            cap.available = True

    def test_bool_conversion(self):
        cap_available = GPUCapability(available=True)
        cap_unavailable = GPUCapability(available=False)
        self.assertTrue(bool(cap_available))
        self.assertFalse(bool(cap_unavailable))


class DetectCapabilityTests(unittest.TestCase):
    """Tests for detect_capability with mocked backends."""

    def setUp(self):
        reset_cache()

    def tearDown(self):
        reset_cache()

    def test_no_backends_available(self):
        """When neither cupy nor cv2 is available, return False."""
        with patch.dict("sys.modules", {"cupy": None, "cv2": None}):
            cap = detect_capability(force_refresh=True)
        self.assertFalse(cap.available)
        self.assertIsNone(cap.backend)

    def test_cupy_available(self):
        """When cupy is available and reports devices, use cupy."""
        fake_cupy = MagicMock()
        fake_cupy.cuda.runtime.getDeviceCount.return_value = 1
        fake_cupy.cuda.runtime.getDeviceProperties.return_value = {
            "name": b"NVIDIA A100"
        }

        # Use a context manager for cupy.cuda.Device
        class FakeDevice:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        fake_cupy.cuda.Device.return_value = FakeDevice()

        with patch.dict("sys.modules", {"cupy": fake_cupy, "cv2": None}):
            cap = detect_capability(force_refresh=True)
        self.assertTrue(cap.available)
        self.assertEqual(cap.backend, "cupy")
        self.assertEqual(cap.device_count, 1)
        self.assertEqual(cap.device_names, ("NVIDIA A100",))

    def test_cupy_zero_devices_falls_back(self):
        """If cupy is installed but no devices, try cv2-cuda."""
        fake_cupy = MagicMock()
        fake_cupy.cuda.runtime.getDeviceCount.return_value = 0

        fake_cv2 = MagicMock()
        fake_cv2.cuda.getCudaEnabledDeviceCount.return_value = 1
        fake_cv2.cuda.DeviceInfo.return_value.name.return_value = "CUDA GPU"

        with patch.dict(
            "sys.modules", {"cupy": fake_cupy, "cv2": fake_cv2}
        ):
            cap = detect_capability(force_refresh=True)
        self.assertTrue(cap.available)
        self.assertEqual(cap.backend, "cv2-cuda")

    def test_cupy_import_error_falls_back_to_cv2(self):
        """If cupy import fails, try cv2-cuda."""
        fake_cv2 = MagicMock()
        fake_cv2.cuda.getCudaEnabledDeviceCount.return_value = 2
        fake_cv2.cuda.DeviceInfo.return_value.name.return_value = "GPU"

        with patch.dict("sys.modules", {"cupy": None, "cv2": fake_cv2}):
            cap = detect_capability(force_refresh=True)
        self.assertTrue(cap.available)
        self.assertEqual(cap.backend, "cv2-cuda")
        self.assertEqual(cap.device_count, 2)

    def test_cupy_probe_error_returns_none(self):
        """If cupy probe raises an exception, treat as unavailable."""
        fake_cupy = MagicMock()
        fake_cupy.cuda.runtime.getDeviceCount.side_effect = RuntimeError("boom")

        with patch.dict("sys.modules", {"cupy": fake_cupy, "cv2": None}):
            cap = detect_capability(force_refresh=True)
        self.assertFalse(cap.available)

    def test_caching(self):
        """detect_capability should cache the result."""
        fake_cupy = MagicMock()
        fake_cupy.cuda.runtime.getDeviceCount.return_value = 1
        fake_cupy.cuda.runtime.getDeviceProperties.return_value = {
            "name": b"GPU"
        }

        class FakeDevice:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        fake_cupy.cuda.Device.return_value = FakeDevice()

        with patch.dict("sys.modules", {"cupy": fake_cupy, "cv2": None}):
            cap1 = detect_capability()
            # Change the mock to return different values
            fake_cupy.cuda.runtime.getDeviceCount.return_value = 99
            # Without force_refresh, should return cached value
            cap2 = detect_capability()
        self.assertEqual(cap1, cap2)
        self.assertEqual(cap1.device_count, 1)

    def test_force_refresh_bypasses_cache(self):
        fake_cupy = MagicMock()
        fake_cupy.cuda.runtime.getDeviceCount.return_value = 1
        fake_cupy.cuda.runtime.getDeviceProperties.return_value = {
            "name": b"GPU"
        }

        class FakeDevice:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        fake_cupy.cuda.Device.return_value = FakeDevice()

        with patch.dict("sys.modules", {"cupy": fake_cupy, "cv2": None}):
            detect_capability()
            fake_cupy.cuda.runtime.getDeviceCount.return_value = 5
            cap = detect_capability(force_refresh=True)
        self.assertEqual(cap.device_count, 5)


class ConvenienceFunctionTests(unittest.TestCase):
    """Tests for the convenience functions."""

    def setUp(self):
        reset_cache()

    def tearDown(self):
        reset_cache()

    def test_is_available_when_no_gpu(self):
        with patch.dict("sys.modules", {"cupy": None, "cv2": None}):
            self.assertFalse(is_available())

    def test_is_available_when_gpu(self):
        fake_cupy = MagicMock()
        fake_cupy.cuda.runtime.getDeviceCount.return_value = 1
        fake_cupy.cuda.runtime.getDeviceProperties.return_value = {
            "name": b"GPU"
        }

        class FakeDevice:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        fake_cupy.cuda.Device.return_value = FakeDevice()

        with patch.dict("sys.modules", {"cupy": fake_cupy, "cv2": None}):
            self.assertTrue(is_available())

    def test_get_backend_name(self):
        with patch.dict("sys.modules", {"cupy": None, "cv2": None}):
            self.assertIsNone(get_backend_name())

    def test_get_device_count(self):
        with patch.dict("sys.modules", {"cupy": None, "cv2": None}):
            self.assertEqual(get_device_count(), 0)

    def test_get_device_names(self):
        with patch.dict("sys.modules", {"cupy": None, "cv2": None}):
            self.assertEqual(get_device_names(), ())

    def test_gpu_info_string_no_gpu(self):
        with patch.dict("sys.modules", {"cupy": None, "cv2": None}):
            info = gpu_info_string()
        self.assertIn("CPU", info)
        self.assertIn("no GPU", info)

    def test_gpu_info_string_with_one_device(self):
        fake_cupy = MagicMock()
        fake_cupy.cuda.runtime.getDeviceCount.return_value = 1
        fake_cupy.cuda.runtime.getDeviceProperties.return_value = {
            "name": b"NVIDIA A100"
        }

        class FakeDevice:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        fake_cupy.cuda.Device.return_value = FakeDevice()

        with patch.dict("sys.modules", {"cupy": fake_cupy, "cv2": None}):
            info = gpu_info_string()
        self.assertIn("NVIDIA A100", info)
        self.assertIn("cupy", info)

    def test_gpu_info_string_with_multiple_devices(self):
        fake_cupy = MagicMock()
        fake_cupy.cuda.runtime.getDeviceCount.return_value = 2
        fake_cupy.cuda.runtime.getDeviceProperties.return_value = {
            "name": b"NVIDIA A100"
        }

        class FakeDevice:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        fake_cupy.cuda.Device.return_value = FakeDevice()

        with patch.dict("sys.modules", {"cupy": fake_cupy, "cv2": None}):
            info = gpu_info_string()
        self.assertIn("2 devices", info)


class ResetCacheTests(unittest.TestCase):
    def test_reset_clears_cache(self):
        # First call: no GPU
        with patch.dict("sys.modules", {"cupy": None, "cv2": None}):
            cap1 = detect_capability()
            self.assertFalse(cap1.available)

        # Reset
        reset_cache()

        # Now simulate a GPU appearing
        fake_cupy = MagicMock()
        fake_cupy.cuda.runtime.getDeviceCount.return_value = 1
        fake_cupy.cuda.runtime.getDeviceProperties.return_value = {
            "name": b"GPU"
        }

        class FakeDevice:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        fake_cupy.cuda.Device.return_value = FakeDevice()

        with patch.dict("sys.modules", {"cupy": fake_cupy, "cv2": None}):
            cap2 = detect_capability()
        self.assertTrue(cap2.available)


if __name__ == "__main__":
    unittest.main()
