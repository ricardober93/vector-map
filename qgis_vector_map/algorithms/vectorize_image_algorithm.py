"""QGIS Processing algorithm wrapper for image vectorization."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from ..core.errors import ConfigurationError, DependencyError, VectorMapError
from ..core.models import VectorizationRequest
from ..core.pipeline import run_vectorization

try:  # pragma: no cover - optional QGIS dependency
    from qgis.core import (
        QgsProcessing,
        QgsProcessingAlgorithm,
        QgsProcessingException,
        QgsProcessingParameterEnum,
        QgsProcessingParameterFile,
        QgsProcessingParameterFolderDestination,
        QgsProcessingParameterString,
    )
    HAS_QGIS = True
except Exception:  # pragma: no cover - allow imports without QGIS
    HAS_QGIS = False

    class QgsProcessingException(Exception):
        pass

    class _StubParameter:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.args = args
            self.kwargs = kwargs

    class QgsProcessingAlgorithm:  # type: ignore[override]
        def tr(self, message: str) -> str:
            return message

    class QgsProcessingParameterEnum(_StubParameter):
        pass

    class QgsProcessingParameterFile(_StubParameter):
        pass

    class QgsProcessingParameterFolderDestination(_StubParameter):
        pass

    class QgsProcessingParameterString(_StubParameter):
        pass

    class QgsProcessing:
        TypeFile = 0


class VectorizeImageAlgorithm(QgsProcessingAlgorithm):
    """Processing algorithm that delegates to the local vectorization pipeline."""

    INPUT = "INPUT"
    PROFILE = "PROFILE"
    OUTPUT = "OUTPUT"
    OUTPUT_FORMAT = "OUTPUT_FORMAT"
    PARAMETERS = "PARAMETERS"
    LAYER_NAME = "LAYER_NAME"

    def name(self) -> str:  # pragma: no cover - QGIS integration point
        return "vectorize_image"

    def displayName(self) -> str:  # pragma: no cover - QGIS integration point
        return self.tr("Vectorize Image")

    def group(self) -> str:  # pragma: no cover - QGIS integration point
        return self.tr("Vector Map")

    def groupId(self) -> str:  # pragma: no cover - QGIS integration point
        return "vector_map"

    def shortHelpString(self) -> str:  # pragma: no cover - QGIS integration point
        return self.tr("Locally vectorize raster images using a modular preprocess/vectorize/postprocess/export pipeline.")

    def createInstance(self) -> "VectorizeImageAlgorithm":  # pragma: no cover - QGIS integration point
        return VectorizeImageAlgorithm()

    def initAlgorithm(self, config: dict[str, Any] | None = None) -> None:  # pragma: no cover - QGIS integration point
        if not HAS_QGIS:
            return
        self.addParameter(QgsProcessingParameterFile(self.INPUT, self.tr("Input raster"), behavior=QgsProcessing.TypeFile))
        self.addParameter(
            QgsProcessingParameterEnum(
                self.PROFILE,
                self.tr("Profile"),
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
                self.tr("Profile parameters (JSON)"),
                defaultValue="{}",
                multiLine=False,
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.LAYER_NAME,
                self.tr("Output layer name"),
                defaultValue="vectorized",
                multiLine=False,
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.OUTPUT_FORMAT,
                self.tr("Output format"),
                defaultValue="auto",
                multiLine=False,
            )
        )
        self.addParameter(QgsProcessingParameterFolderDestination(self.OUTPUT, self.tr("Output folder")))

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

    def processAlgorithm(self, parameters: dict[str, Any], context: Any, feedback: Any) -> dict[str, Any]:  # pragma: no cover - QGIS integration point
        if not HAS_QGIS:
            raise QgsProcessingException(
                "QGIS Processing is not available in this environment. Install QGIS to run the algorithm."
            )

        input_path = self.parameterAsFile(parameters, self.INPUT, context)
        profile_options = ["regional-high-precision", "edge-high-precision", "linear-high-precision"]
        profile_index = self.parameterAsEnum(parameters, self.PROFILE, context)
        profile_id = profile_options[profile_index]
        raw_parameters = self.parameterAsString(parameters, self.PARAMETERS, context)
        output_folder = self.parameterAsString(parameters, self.OUTPUT, context)
        layer_name = self.parameterAsString(parameters, self.LAYER_NAME, context) or "vectorized"
        output_format = self.parameterAsString(parameters, self.OUTPUT_FORMAT, context) or "auto"
        profile_parameters = self._parse_parameters(raw_parameters)

        output_extension = ".gpkg" if output_format == "gpkg" else ".geojson"
        output_path = Path(output_folder) / f"{Path(input_path).stem}_{profile_id}{output_extension}"

        request = VectorizationRequest(
            source=input_path,
            profile_id=profile_id,
            output_path=output_path,
            output_format=output_format,
            layer_name=layer_name,
            parameters=profile_parameters,
            metadata={"processing_provider": "vector_map"},
        )

        try:
            result = run_vectorization(
                request,
                progress_callback=lambda stage, progress, message: feedback.pushInfo(f"[{stage.value}] {message} ({progress:.0%})"),
                cancel_callback=getattr(feedback, "isCanceled", lambda: False),
            )
        except VectorMapError as exc:
            raise QgsProcessingException(str(exc)) from exc

        return {
            self.OUTPUT: str(result.output_path),
            self.PROFILE: result.profile_id,
            self.LAYER_NAME: result.vector_layer.name,
            self.PARAMETERS: json.dumps(result.metadata.get("requested_parameters", {}), sort_keys=True),
        }
