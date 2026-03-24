"""QGIS Processing algorithm wrapper for image vectorization."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, cast

from ..core.errors import VectorMapError
from ..core.models import VectorizationRequest
from ..core.pipeline import run_vectorization

_QCoreApplication: Any
_QgsProcessingAlgorithm: Any
_QgsProcessingException: Any
_QgsProcessingParameterEnum: Any
_QgsProcessingParameterRasterLayer: Any
_QgsProcessingParameterString: Any
_QgsProcessingParameterVectorDestination: Any

try:  # pragma: no cover - available in local dev and QGIS runtimes
    from PyQt5.QtCore import QCoreApplication as _QCoreApplication
except Exception:  # pragma: no cover - import-safe fallback

    class _FallbackQCoreApplication:
        @staticmethod
        def translate(_context: str, message: str) -> str:
            return message

    _QCoreApplication = _FallbackQCoreApplication

try:  # pragma: no cover - optional QGIS dependency
    from qgis.core import (
        QgsProcessingAlgorithm as _QgsProcessingAlgorithm,
    )
    from qgis.core import (
        QgsProcessingException as _QgsProcessingException,
    )
    from qgis.core import (
        QgsProcessingParameterEnum as _QgsProcessingParameterEnum,
    )
    from qgis.core import (
        QgsProcessingParameterRasterLayer as _QgsProcessingParameterRasterLayer,
    )
    from qgis.core import (
        QgsProcessingParameterString as _QgsProcessingParameterString,
    )
    from qgis.core import (
        QgsProcessingParameterVectorDestination as _QgsProcessingParameterVectorDestination,
    )

    HAS_QGIS = True
except Exception:  # pragma: no cover - allow imports without QGIS
    HAS_QGIS = False

    class _FallbackQgsProcessingException(Exception):
        pass

    class _StubParameter:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.args = args
            self.kwargs = kwargs

    class _FallbackQgsProcessingAlgorithm:
        def tr(self, message: str) -> str:
            return message

    class _FallbackQgsProcessingParameterEnum(_StubParameter):
        pass

    class _FallbackQgsProcessingParameterRasterLayer(_StubParameter):
        pass

    class _FallbackQgsProcessingParameterVectorDestination(_StubParameter):
        pass

    class _FallbackQgsProcessingParameterString(_StubParameter):
        pass

    _QgsProcessingAlgorithm = _FallbackQgsProcessingAlgorithm
    _QgsProcessingException = _FallbackQgsProcessingException
    _QgsProcessingParameterEnum = _FallbackQgsProcessingParameterEnum
    _QgsProcessingParameterRasterLayer = _FallbackQgsProcessingParameterRasterLayer
    _QgsProcessingParameterString = _FallbackQgsProcessingParameterString
    _QgsProcessingParameterVectorDestination = _FallbackQgsProcessingParameterVectorDestination

QCoreApplication = cast(Any, _QCoreApplication)
QgsProcessingAlgorithm = cast(type[Any], _QgsProcessingAlgorithm)
QgsProcessingException = cast(type[Exception], _QgsProcessingException)
QgsProcessingParameterEnum = cast(type[Any], _QgsProcessingParameterEnum)
QgsProcessingParameterRasterLayer = cast(type[Any], _QgsProcessingParameterRasterLayer)
QgsProcessingParameterString = cast(type[Any], _QgsProcessingParameterString)
QgsProcessingParameterVectorDestination = cast(type[Any], _QgsProcessingParameterVectorDestination)


class VectorizeImageAlgorithm(QgsProcessingAlgorithm):
    """Processing algorithm that delegates to the local vectorization pipeline."""

    INPUT = "INPUT"
    PROFILE = "PROFILE"
    OUTPUT = "OUTPUT"
    OUTPUT_FORMAT = "OUTPUT_FORMAT"
    PARAMETERS = "PARAMETERS"
    LAYER_NAME = "LAYER_NAME"

    @staticmethod
    def _tr(message: str) -> str:
        return QCoreApplication.translate("VectorizeImageAlgorithm", message)

    def name(self) -> str:  # pragma: no cover - QGIS integration point
        return "vectorize_image"

    def displayName(self) -> str:  # pragma: no cover - QGIS integration point
        return self._tr("Vectorize Image")

    def group(self) -> str:  # pragma: no cover - QGIS integration point
        return self._tr("Vector Map")

    def groupId(self) -> str:  # pragma: no cover - QGIS integration point
        return "vector_map"

    def shortHelpString(self) -> str:  # pragma: no cover - QGIS integration point
        return self._tr(
            "Locally vectorize raster images using a modular "
            "preprocess/vectorize/postprocess/export pipeline."
        )

    def createInstance(
        self,
    ) -> VectorizeImageAlgorithm:  # pragma: no cover - QGIS integration point
        return VectorizeImageAlgorithm()

    def initAlgorithm(
        self, config: dict[str, Any] | None = None
    ) -> None:  # pragma: no cover - QGIS integration point
        if not HAS_QGIS:
            return
        self.addParameter(
            QgsProcessingParameterRasterLayer(self.INPUT, self._tr("Input raster layer"))
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.PROFILE,
                self._tr("Profile"),
                options=[
                    "regional-high-precision",
                    "edge-high-precision",
                    "linear-high-precision",
                ],
                defaultValue=0,
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.PARAMETERS,
                self._tr("Profile parameters (JSON)"),
                defaultValue="{}",
                multiLine=False,
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.LAYER_NAME,
                self._tr("Output layer name"),
                defaultValue="vectorized",
                multiLine=False,
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.OUTPUT_FORMAT,
                self._tr("Output format"),
                defaultValue="auto",
                multiLine=False,
            )
        )
        self.addParameter(
            QgsProcessingParameterVectorDestination(
                self.OUTPUT,
                self._tr("Output vector layer"),
            )
        )

    def _parse_parameters(self, raw_parameters: str | None) -> dict[str, Any]:
        if not raw_parameters:
            return {}
        try:
            parsed = json.loads(raw_parameters)
        except json.JSONDecodeError as exc:
            raise QgsProcessingException(f"Invalid JSON parameters: {exc}") from exc
        if not isinstance(parsed, dict):
            raise QgsProcessingException("Parameters JSON must decode to an object/dictionary.")
        return parsed

    def processAlgorithm(
        self, parameters: dict[str, Any], context: Any, feedback: Any
    ) -> dict[str, Any]:  # pragma: no cover - QGIS integration point
        if not HAS_QGIS:
            raise QgsProcessingException(
                "QGIS Processing is not available in this environment. "
                "Install QGIS to run the algorithm."
            )

        raster_layer = self.parameterAsRasterLayer(parameters, self.INPUT, context)
        if raster_layer is None:
            raise QgsProcessingException("Input raster layer is required.")
        input_path = raster_layer.source()
        if not input_path:
            raise QgsProcessingException("Could not resolve source path from input raster layer.")

        profile_options = [
            "regional-high-precision",
            "edge-high-precision",
            "linear-high-precision",
        ]
        profile_index = self.parameterAsEnum(parameters, self.PROFILE, context)
        if profile_index < 0 or profile_index >= len(profile_options):
            raise QgsProcessingException("Invalid profile selection.")
        profile_id = profile_options[profile_index]
        raw_parameters = self.parameterAsString(parameters, self.PARAMETERS, context)
        output_destination = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)
        if not output_destination:
            raise QgsProcessingException("Output destination is required.")

        layer_name = self.parameterAsString(parameters, self.LAYER_NAME, context) or "vectorized"
        output_format = self.parameterAsString(parameters, self.OUTPUT_FORMAT, context) or "auto"
        profile_parameters = self._parse_parameters(raw_parameters)

        output_path = Path(output_destination)
        inferred_format = output_format
        suffix = output_path.suffix.lower()
        if output_format == "auto":
            if suffix == ".gpkg":
                inferred_format = "gpkg"
            elif suffix in {".geojson", ".json"}:
                inferred_format = "geojson"

        # QGIS may pass a provider URI like memory: as destination; in that case
        # run pipeline to a temporary file and let Processing pick it from result.
        if ":" in output_destination and not output_destination.startswith("/"):
            temp_extension = ".gpkg" if inferred_format == "gpkg" else ".geojson"
            output_path = Path(tempfile.gettempdir()) / f"vector_map_{profile_id}{temp_extension}"

        request = VectorizationRequest(
            source=input_path,
            profile_id=profile_id,
            output_path=output_path,
            output_format=inferred_format,
            layer_name=layer_name,
            parameters=profile_parameters,
            metadata={"processing_provider": "vector_map"},
        )

        try:
            result = run_vectorization(
                request,
                progress_callback=lambda stage, progress, message: feedback.pushInfo(
                    f"[{stage.value}] {message} ({progress:.0%})"
                ),
                cancel_callback=getattr(feedback, "isCanceled", lambda: False),
            )
        except VectorMapError as exc:
            raise QgsProcessingException(str(exc)) from exc

        return {
            self.OUTPUT: str(result.output_path),
            self.PROFILE: result.profile_id,
            self.LAYER_NAME: result.vector_layer.name,
            self.PARAMETERS: json.dumps(
                result.metadata.get("requested_parameters", {}), sort_keys=True
            ),
        }
