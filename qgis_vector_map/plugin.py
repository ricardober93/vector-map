"""Main plugin entry points for Vector Map."""

from __future__ import annotations

try:  # pragma: no cover - exercised inside QGIS
    from qgis.core import QgsApplication
except Exception:  # pragma: no cover - import-safe fallback for local tests
    class QgsApplication:  # type: ignore[override]
        @staticmethod
        def processingRegistry():
            return None

from .provider import VectorMapProcessingProvider


class VectorMapPlugin:
    """Minimal QGIS plugin shell.

    The plugin owns a single processing provider and registers it when the
    GUI is initialized. When QGIS is unavailable, the class still imports and
    can be instantiated safely for unit tests or packaging checks.
    """

    def __init__(self, iface):
        self.iface = iface
        self.provider = None

    def _processing_registry(self):
        registry = QgsApplication.processingRegistry()
        return registry

    def initGui(self):
        """Register the processing provider with QGIS."""

        if self.provider is None:
            self.provider = VectorMapProcessingProvider()

        registry = self._processing_registry()
        if registry is None:
            return

        providers = []
        if hasattr(registry, "providers"):
            try:
                providers = list(registry.providers())
            except Exception:
                providers = []

        if self.provider not in providers:
            registry.addProvider(self.provider)

    def unload(self):
        """Unregister the processing provider from QGIS."""

        registry = self._processing_registry()
        if registry is None or self.provider is None:
            return

        try:
            registry.removeProvider(self.provider)
        except Exception:
            pass
