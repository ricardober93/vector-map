"""Engine package exports."""

from .base import EngineRegistry, VectorizationEngine, build_default_registry
from .classic import ClassicVectorizationEngine

try:
    from .opencv import OpenCVVectorizationEngine
    _HAS_OPENCV_ENGINE = True
except Exception:
    OpenCVVectorizationEngine = None  # type: ignore[assignment,misc]
    _HAS_OPENCV_ENGINE = False

__all__ = [
    "ClassicVectorizationEngine",
    "EngineRegistry",
    "OpenCVVectorizationEngine",
    "VectorizationEngine",
    "build_default_registry",
]
