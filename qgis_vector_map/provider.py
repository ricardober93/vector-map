"""Processing provider for Vector Map."""

from __future__ import annotations

from typing import Any, cast

from .algorithms.vectorize_image_algorithm import VectorizeImageAlgorithm

_Qgis: Any
_QgsMessageLog: Any
_QgsProcessingAlgorithm: Any
_QgsProcessingProvider: Any

try:  # pragma: no cover - exercised inside QGIS
    from qgis.core import (
        Qgis as _Qgis,
    )
    from qgis.core import (
        QgsMessageLog as _QgsMessageLog,
    )
    from qgis.core import (
        QgsProcessingAlgorithm as _QgsProcessingAlgorithm,
    )
    from qgis.core import (
        QgsProcessingProvider as _QgsProcessingProvider,
    )
except Exception:  # pragma: no cover - import-safe fallback for local tests

    class _FallbackQgsProcessingAlgorithm:
        """Fallback base class that mirrors the QGIS API surface we use."""

        def createInstance(self):
            return self.__class__()

        def initAlgorithm(self, config=None):  # noqa: D401
            return None

        def processAlgorithm(self, parameters, context, feedback):  # noqa: D401
            return {}

    class _FallbackQgsProcessingProvider:
        """Fallback provider used when QGIS is not installed."""

        def __init__(self):
            self._algorithms = []

        def addAlgorithm(self, algorithm):
            self._algorithms.append(algorithm)

        def algorithms(self):
            return list(self._algorithms)

    class _FallbackQgsMessageLog:
        @staticmethod
        def logMessage(_message, _tag="Vector Map", _level=None):
            return None

    class _FallbackQgis:
        class MessageLevel:
            Info = 0
            Warning = 1
            Critical = 2

    _Qgis = _FallbackQgis
    _QgsMessageLog = _FallbackQgsMessageLog
    _QgsProcessingAlgorithm = _FallbackQgsProcessingAlgorithm
    _QgsProcessingProvider = _FallbackQgsProcessingProvider

Qgis = cast(Any, _Qgis)
QgsMessageLog = cast(Any, _QgsMessageLog)
QgsProcessingAlgorithm = cast(type[Any], _QgsProcessingAlgorithm)
QgsProcessingProvider = cast(type[Any], _QgsProcessingProvider)


class VectorMapScaffoldAlgorithm(QgsProcessingAlgorithm):
    """Minimal healthcheck algorithm kept for debug and installation checks."""

    ALG_ID = "vector_map_scaffold"
    ALG_NAME = "Vector Map scaffold"
    ALG_GROUP = "Vector Map"

    def name(self):
        return self.ALG_ID

    def displayName(self):
        return self.ALG_NAME

    def group(self):
        return self.ALG_GROUP

    def groupId(self):
        return "vector_map"

    def shortHelpString(self):
        return (
            "Placeholder Processing algorithm for the Vector Map plugin. "
            "It exists to register the provider and reserve the algorithm "
            "contract for the real vectorization pipeline."
        )

    def createInstance(self):
        return VectorMapScaffoldAlgorithm()

    def initAlgorithm(self, config=None):
        return None

    def processAlgorithm(self, parameters, context, feedback):
        return {}


class VectorMapProcessingProvider(QgsProcessingProvider):
    """Processing provider that owns the plugin's algorithm list."""

    PROVIDER_ID = "vector_map"
    PROVIDER_NAME = "Vector Map"
    ALGORITHM_FACTORIES = (VectorizeImageAlgorithm, VectorMapScaffoldAlgorithm)
    LOG_TAG = "Vector Map"

    def _log(self, message, level=None):
        level_value = level if level is not None else getattr(Qgis.MessageLevel, "Info", None)
        QgsMessageLog.logMessage(message, self.LOG_TAG, level_value)

    def id(self):
        return self.PROVIDER_ID

    def name(self):
        return self.PROVIDER_NAME

    def longName(self):
        return self.PROVIDER_NAME

    def load(self):
        """Load provider and ensure algorithms are registered in QGIS."""

        self._log("Loading processing provider")
        super_load = getattr(super(), "load", None)
        if callable(super_load):
            return bool(super_load())
        # Fallback path for non-QGIS stub runtime.
        self.loadAlgorithms()
        return True

    def loadAlgorithms(self):
        for algorithm in self.createAlgorithms():
            self.addAlgorithm(algorithm)
        self._log(f"Registered {len(self.algorithmClasses())} algorithm(s)")

    @classmethod
    def algorithmClasses(cls):
        return cls.ALGORITHM_FACTORIES

    def createAlgorithms(self):
        """Create the algorithm instances owned by this provider."""

        return [algorithm_class() for algorithm_class in self.algorithmClasses()]

    def unload(self):
        self._log("Unloading processing provider")
        return None
