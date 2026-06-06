"""GPU acceleration detection and capability layer.

Provides a uniform way to check whether GPU acceleration is available
via cuPy (NVIDIA) or cv2-CUDA (built into OpenCV). The detection is
cached and thread-safe.

Design
------
- :class:`GPUCapability` describes what is available (none, cupy, cv2-cuda)
- :func:`detect_capability` probes the system and returns the result
- :func:`is_available` is a fast boolean check
- :func:`get_backend_name` returns a human-readable backend name

The actual GPU computation lives in the engines (opencv, etc.). This
module is purely the detection layer.

Typical usage
-------------
>>> from qgis_vector_map.core.gpu import is_available, get_backend_name
>>> if is_available():
...     print(f"GPU ready: {get_backend_name()}")
... else:
...     print("GPU not available, using CPU")
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class GPUCapability:
    """Describes the available GPU capability on this machine.

    Attributes
    ----------
    available:
        True if at least one GPU backend can be used.
    backend:
        Name of the best available backend ("cupy", "cv2-cuda") or None.
    device_count:
        Number of visible devices (0 if none).
    device_names:
        Names of the visible devices, in order.
    """

    available: bool
    backend: Optional[str] = None
    device_count: int = 0
    device_names: tuple[str, ...] = ()

    def __bool__(self) -> bool:  # pragma: no cover - convenience
        return self.available


# None = not yet detected
_capability_cache: Optional[GPUCapability] = None
_cache_lock = threading.Lock()


def _probe_cupy() -> Optional[GPUCapability]:
    """Try to import and initialize cuPy. Returns capability or None."""
    try:
        import cupy  # type: ignore
    except ImportError:
        return None
    try:
        device_count = cupy.cuda.runtime.getDeviceCount()
    except Exception:
        return None
    if device_count <= 0:
        return None
    try:
        names = []
        for i in range(device_count):
            with cupy.cuda.Device(i):
                props = cupy.cuda.runtime.getDeviceProperties(i)
                name = props.get("name", b"unknown")
                if isinstance(name, bytes):
                    name = name.decode("utf-8", errors="replace")
                names.append(name)
    except Exception:
        names = []
    return GPUCapability(
        available=True,
        backend="cupy",
        device_count=device_count,
        device_names=tuple(names),
    )


def _probe_cv2_cuda() -> Optional[GPUCapability]:
    """Try to use OpenCV's CUDA backend. Returns capability or None."""
    try:
        import cv2  # type: ignore
    except ImportError:
        return None
    try:
        cuda_count = cv2.cuda.getCudaEnabledDeviceCount()
    except Exception:
        return None
    if cuda_count <= 0:
        return None
    names: list[str] = []
    try:
        for i in range(cuda_count):
            info = cv2.cuda.DeviceInfo(i)
            name = getattr(info, "name", lambda: f"CUDA device {i}")()
            if isinstance(name, bytes):
                name = name.decode("utf-8", errors="replace")
            names.append(name)
    except Exception:
        # Even if we can't get names, the count tells us GPUs are there
        names = [f"CUDA device {i}" for i in range(cuda_count)]
    return GPUCapability(
        available=True,
        backend="cv2-cuda",
        device_count=cuda_count,
        device_names=tuple(names),
    )


def detect_capability(force_refresh: bool = False) -> GPUCapability:
    """Detect GPU capability on this machine.

    Parameters
    ----------
    force_refresh:
        If True, ignore the cached result and re-probe. Useful for tests
        or when the user has just installed a new GPU library.

    Returns
    -------
    GPUCapability describing what is available. If no GPU is detected,
    returns a capability with available=False.
    """
    global _capability_cache
    with _cache_lock:
        if _capability_cache is not None and not force_refresh:
            return _capability_cache

        # Probe in order of preference: cupy first, then cv2-cuda
        cap = _probe_cupy()
        if cap is None:
            cap = _probe_cv2_cuda()
        if cap is None:
            cap = GPUCapability(available=False)

        _capability_cache = cap
        return cap


def is_available() -> bool:
    """Quick boolean check: is any GPU backend usable?"""
    return detect_capability().available


def get_backend_name() -> Optional[str]:
    """Return the best available GPU backend name, or None."""
    return detect_capability().backend


def get_device_count() -> int:
    """Return the number of visible GPU devices, or 0."""
    return detect_capability().device_count


def get_device_names() -> tuple[str, ...]:
    """Return the names of visible GPU devices."""
    return detect_capability().device_names


def reset_cache() -> None:
    """Clear the capability cache (mainly for tests)."""
    global _capability_cache
    with _cache_lock:
        _capability_cache = None


# Convenience for engine code
def gpu_info_string() -> str:
    """Human-readable one-line description of the GPU state.

    Examples
    --------
    >>> gpu_info_string()
    'GPU: NVIDIA A100 (1 device, cupy)'
    >>> gpu_info_string()
    'CPU only (no GPU detected)'
    """
    cap = detect_capability()
    if not cap.available:
        return "CPU only (no GPU detected)"
    if cap.device_count == 1 and cap.device_names:
        return f"GPU: {cap.device_names[0]} (1 device, {cap.backend})"
    return (
        f"GPU: {cap.device_count} devices "
        f"({', '.join(cap.device_names) or 'unknown'}, {cap.backend})"
    )


__all__ = [
    "GPUCapability",
    "detect_capability",
    "get_backend_name",
    "get_device_count",
    "get_device_names",
    "gpu_info_string",
    "is_available",
    "reset_cache",
]
