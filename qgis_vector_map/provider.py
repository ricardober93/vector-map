"""Processing provider for Vector Map."""

from __future__ import annotations

try:  # pragma: no cover - exercised inside QGIS
    from qgis.core import QgsProcessingAlgorithm, QgsProcessingProvider
except Exception:  # pragma: no cover - import-safe fallback for local tests
    class QgsProcessingAlgorithm:  # type: ignore[override]
        """Fallback base class that mirrors the QGIS API surface we use."""

        def createInstance(self):
            return self.__class__()

        def initAlgorithm(self, config=None):  # noqa: D401
            return None

        def processAlgorithm(self, parameters, context, feedback):  # noqa: D401
            return {}


    class QgsProcessingProvider:  # type: ignore[override]
        """Fallback provider used when QGIS is not installed."""

        def __init__(self):
            self._algorithms = []

        def addAlgorithm(self, algorithm):
            self._algorithms.append(algorithm)

        def algorithms(self):
            return list(self._algorithms)


from .algorithms.vectorize_image_algorithm import VectorizeImageAlgorithm


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

    def id(self):
        return self.PROVIDER_ID

    def name(self):
        return self.PROVIDER_NAME

    def longName(self):
        return self.PROVIDER_NAME

    def load(self):
        """Compatibility hook for import-safe fallback environments."""

        return True

    def loadAlgorithms(self):
        for algorithm in self.createAlgorithms():
            self.addAlgorithm(algorithm)

    @classmethod
    def algorithmClasses(cls):
        return cls.ALGORITHM_FACTORIES

    def createAlgorithms(self):
        """Create the algorithm instances owned by this provider."""

        return [algorithm_class() for algorithm_class in self.algorithmClasses()]

    def unload(self):
        return None
