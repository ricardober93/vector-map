"""Vector Map QGIS plugin package."""

from __future__ import annotations

from .background import BackgroundCallbacks, run_vectorization_async
from .plugin import VectorMapPlugin

__all__ = [
    "BackgroundCallbacks",
    "classFactory",
    "run_vectorization_async",
    "VectorMapPlugin",
]
__version__ = "0.2.0"


def classFactory(iface):
    """QGIS entry point.

    Parameters
    ----------
    iface:
        QGIS interface object provided by the application.
    """

    return VectorMapPlugin(iface)
