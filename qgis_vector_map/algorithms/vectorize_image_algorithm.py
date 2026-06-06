"""QGIS Processing algorithm wrapper for image vectorization."""

from __future__ import annotations

import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from ..core.errors import VectorMapError
from ..core.models import VectorizationRequest
from ..core.pipeline import run_vectorization

_QCoreApplication: Any
_QgsCoordinateReferenceSystem: Any
_QgsFeature: Any
_QgsFeatureSink: Any
_QgsField: Any
_QgsFields: Any
_QgsGeometry: Any
_QgsPointXY: Any
_QgsProcessingAlgorithm: Any
_QgsProcessingException: Any
_QgsProcessingParameterEnum: Any
_QgsProcessingParameterRasterLayer: Any
_QgsProcessingParameterString: Any
_QgsProcessingParameterVectorDestination: Any
_QgsProject: Any
_QgsWkbTypes: Any
_QtVariantType: Any

try:  # pragma: no cover - available in local dev and QGIS runtimes
    from PyQt6.QtCore import QCoreApplication as _QCoreApplication
    _QtVariantType = str  # PyQt6 doesn't have QVariant, use str for field types
except ImportError:  # pragma: no cover - fall back to PyQt5
    try:
        from PyQt5.QtCore import QCoreApplication as _QCoreApplication
        from PyQt5.QtCore import QVariant as _QtVariantType
    except ImportError:
        _QCoreApplication = type('QtCore', (), {'translate': staticmethod(lambda _c, m: m)})()
        _QtVariantType = str

try:  # pragma: no cover - optional QGIS dependency
    from qgis.core import (
        QgsCoordinateReferenceSystem as _QgsCoordinateReferenceSystem,
    )
    from qgis.core import (
        QgsFeature as _QgsFeature,
    )
    from qgis.core import (
        QgsFeatureSink as _QgsFeatureSink,
    )
    from qgis.core import (
        QgsField as _QgsField,
    )
    from qgis.core import (
        QgsFields as _QgsFields,
    )
    from qgis.core import (
        QgsGeometry as _QgsGeometry,
    )
    from qgis.core import (
        QgsPointXY as _QgsPointXY,
    )
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
    from qgis.core import (
        QgsProject as _QgsProject,
    )
    from qgis.core import (
        QgsWkbTypes as _QgsWkbTypes,
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

    class _FallbackQgsCoordinateReferenceSystem:
        pass

    class _FallbackQgsFeature:
        def __init__(self, *args, **kwargs):
            pass
        def setGeometry(self, geom):
            pass
        def setAttribute(self, name, value):
            pass

    class _FallbackQgsFeatureSink:
        pass

    class _FallbackQgsField:
        def __init__(self, *args, **kwargs):
            pass

    class _FallbackQgsFields:
        def append(self, field):
            pass

    class _FallbackQgsGeometry:
        pass

    class _FallbackQgsPointXY:
        pass

    class _FallbackQgsProcessingParameterEnum(_StubParameter):
        pass

    class _FallbackQgsProcessingParameterRasterLayer(_StubParameter):
        pass

    class _FallbackQgsProcessingParameterVectorDestination(_StubParameter):
        pass

    class _FallbackQgsProcessingParameterString(_StubParameter):
        pass

    class _FallbackQgsProject:
        @classmethod
        def instance(cls):
            return cls()

        def crs(self):
            return None

    class _FallbackQgsWkbTypes:
        Unknown = 0
        Point = 1
        LineString = 2
        Polygon = 3
        MultiPoint = 4
        MultiLineString = 5
        MultiPolygon = 6

    _QgsCoordinateReferenceSystem = _FallbackQgsCoordinateReferenceSystem
    _QgsFeature = _FallbackQgsFeature
    _QgsFeatureSink = _FallbackQgsFeatureSink
    _QgsField = _FallbackQgsField
    _QgsFields = _FallbackQgsFields
    _QgsGeometry = _FallbackQgsGeometry
    _QgsPointXY = _FallbackQgsPointXY
    _QgsProcessingAlgorithm = _FallbackQgsProcessingAlgorithm
    _QgsProcessingException = _FallbackQgsProcessingException
    _QgsProcessingParameterEnum = _FallbackQgsProcessingParameterEnum
    _QgsProcessingParameterRasterLayer = _FallbackQgsProcessingParameterRasterLayer
    _QgsProcessingParameterString = _FallbackQgsProcessingParameterString
    _QgsProcessingParameterVectorDestination = _FallbackQgsProcessingParameterVectorDestination
    _QgsProject = _FallbackQgsProject
    _QgsWkbTypes = _FallbackQgsWkbTypes

QCoreApplication = cast(Any, _QCoreApplication)
QgsCoordinateReferenceSystem = cast(type[Any], _QgsCoordinateReferenceSystem)
QgsFeature = cast(type[Any], _QgsFeature)
QgsFeatureSink = cast(type[Any], _QgsFeatureSink)
QgsField = cast(type[Any], _QgsField)
QgsFields = cast(type[Any], _QgsFields)
QgsGeometry = cast(type[Any], _QgsGeometry)
QgsPointXY = cast(type[Any], _QgsPointXY)
QgsProcessingAlgorithm = cast(type[Any], _QgsProcessingAlgorithm)
QgsProcessingException = cast(type[Exception], _QgsProcessingException)
QgsProcessingParameterEnum = cast(type[Any], _QgsProcessingParameterEnum)
QgsProcessingParameterRasterLayer = cast(type[Any], _QgsProcessingParameterRasterLayer)
QgsProcessingParameterString = cast(type[Any], _QgsProcessingParameterString)
QgsProcessingParameterVectorDestination = cast(type[Any], _QgsProcessingParameterVectorDestination)
QgsProject = cast(type[Any], _QgsProject)
QgsWkbTypes = cast(type[Any], _QgsWkbTypes)
QtVariantType = cast(type[Any], _QtVariantType)

_GEOMETRY_TYPE_MAP = {
    "Point": "Point",
    "MultiPoint": "MultiPoint",
    "LineString": "LineString",
    "MultiLineString": "MultiLineString",
    "Polygon": "Polygon",
    "MultiPolygon": "MultiPolygon",
}

_WKB_TYPE_MAP = {
    "Point": QgsWkbTypes.Point,
    "MultiPoint": QgsWkbTypes.MultiPoint,
    "LineString": QgsWkbTypes.LineString,
    "MultiLineString": QgsWkbTypes.MultiLineString,
    "Polygon": QgsWkbTypes.Polygon,
    "MultiPolygon": QgsWkbTypes.MultiPolygon,
}


def _resolve_qgs_geometry_type(geometry_types: set[str]) -> Any:
    priority = ["Polygon", "MultiPolygon", "LineString", "MultiLineString", "Point", "MultiPoint"]
    for gt in priority:
        if gt in geometry_types:
            return _WKB_TYPE_MAP.get(gt, QgsWkbTypes.Unknown)
    return QgsWkbTypes.Unknown


def _build_qgs_geometry(geometry_type: str, coordinates: Any) -> Any:
    if geometry_type == "Point":
        if not coordinates or len(coordinates) < 2:
            return QgsGeometry()
        return QgsGeometry.fromPointXY(QgsPointXY(coordinates[0], coordinates[1]))

    if geometry_type in {"LineString", "MultiPoint"}:
        if not coordinates:
            return QgsGeometry()
        points = [QgsPointXY(pt[0], pt[1]) for pt in coordinates]
        return QgsGeometry.fromPolylineXY(points)

    if geometry_type == "Polygon":
        if not coordinates:
            return QgsGeometry()
        rings = [[QgsPointXY(pt[0], pt[1]) for pt in ring] for ring in coordinates]
        return QgsGeometry.fromPolygonXY(rings)

    if geometry_type == "MultiLineString":
        if not coordinates:
            return QgsGeometry()
        lines = [[QgsPointXY(pt[0], pt[1]) for pt in line] for line in coordinates]
        return QgsGeometry.fromMultiPolylineXY(lines)

    if geometry_type == "MultiPolygon":
        if not coordinates:
            return QgsGeometry()
        polygons = [
            [[QgsPointXY(pt[0], pt[1]) for pt in ring] for ring in polygon]
            for polygon in coordinates
        ]
        return QgsGeometry.fromMultiPolygonXY(polygons)

    return QgsGeometry()


def _write_features_to_sink(
    sink: Any,
    fields: Any,
    vector_layer: Any,
    crs: Any,
    feedback: Any,
) -> None:
    for idx, feature in enumerate(vector_layer.features):
        qgs_geom = _build_qgs_geometry(feature.geometry_type, feature.coordinates)
        if qgs_geom is None or qgs_geom.isNull():
            feedback.pushWarning(f"Skipping feature {idx}: could not build geometry")
            continue
        qgs_feature = QgsFeature(fields)
        qgs_feature.setGeometry(qgs_geom)
        props = dict(feature.properties)
        for field in fields:
            field_name = field.name()
            if field_name in props:
                qgs_feature.setAttribute(field_name, str(props[field_name]))
            else:
                qgs_feature.setAttribute(field_name, None)
        if not sink.addFeature(qgs_feature):
            feedback.pushWarning(f"Failed to write feature {idx} to output layer")


class VectorizeImageAlgorithm(QgsProcessingAlgorithm):
    """Processing algorithm that delegates to the local vectorization pipeline."""

    INPUT = "INPUT"
    PROFILE = "PROFILE"
    EXECUTION_MODE = "EXECUTION_MODE"
    EDGE_CANNY_LOW = "EDGE_CANNY_LOW"
    EDGE_CANNY_HIGH = "EDGE_CANNY_HIGH"
    EDGE_BLUR = "EDGE_BLUR"
    EDGE_TO_POLYGON = "EDGE_TO_POLYGON"
    DISSOLVE_ADJACENT = "DISSOLVE_ADJACENT"
    SIMPLIFY_TOLERANCE = "SIMPLIFY_TOLERANCE"
    OUTPUT = "OUTPUT"
    OUTPUT_FORMAT = "OUTPUT_FORMAT"
    OUTPUT_CRS = "OUTPUT_CRS"
    OUTPUT_CRS_CUSTOM = "OUTPUT_CRS_CUSTOM"
    PARAMETERS = "PARAMETERS"
    LAYER_NAME = "LAYER_NAME"
    ENGINE = "ENGINE"

    @staticmethod
    def _tr(message: str) -> str:
        return QCoreApplication.translate("VectorizeImageAlgorithm", message)

    @staticmethod
    def _generate_default_layer_name(profile_id: str) -> str:
        """Generate a descriptive layer name with profile and timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        profile_short = profile_id.replace("-high-precision", "").replace("-", "_")
        return f"vectorized_{profile_short}_{timestamp}"

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
            _QgsProcessingParameterEnum(
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
            _QgsProcessingParameterEnum(
                self.EXECUTION_MODE,
                self._tr("Execution mode"),
                options=["auto", "strict", "tiled"],
                defaultValue=0,
            )
        )
        self.addParameter(
            _QgsProcessingParameterString(
                self.EDGE_CANNY_LOW,
                self._tr("Edge Canny low threshold"),
                defaultValue="50",
                multiLine=False,
            )
        )
        self.addParameter(
            _QgsProcessingParameterString(
                self.EDGE_CANNY_HIGH,
                self._tr("Edge Canny high threshold"),
                defaultValue="150",
                multiLine=False,
            )
        )
        self.addParameter(
            _QgsProcessingParameterString(
                self.EDGE_BLUR,
                self._tr("Edge blur kernel size"),
                defaultValue="3",
                multiLine=False,
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
            _QgsProcessingParameterEnum(
                self.OUTPUT_FORMAT,
                self._tr("Output format"),
                options=["auto", "GeoPackage (.gpkg)", "GeoJSON (.geojson)", "ESRI Shapefile (.shp)"],
                defaultValue=0,
            )
        )
        self.addParameter(
            _QgsProcessingParameterEnum(
                self.ENGINE,
                self._tr("Engine"),
                options=["auto", "classic", "opencv"],
                defaultValue=0,
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.EDGE_TO_POLYGON,
                self._tr("Edge to polygon mode"),
                options=["no", "yes"],
                defaultValue=0,
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.DISSOLVE_ADJACENT,
                self._tr("Dissolve adjacent polygons"),
                options=["no", "yes"],
                defaultValue=0,
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.SIMPLIFY_TOLERANCE,
                self._tr("Simplify tolerance (pixels)"),
                defaultValue="0.5",
                multiLine=False,
            )
        )
        self.addParameter(
            QgsProcessingParameterVectorDestination(
                self.OUTPUT,
                self._tr("Output vector layer"),
            )
        )
        # CRS selector: choose from common EPSG codes or provide a custom one
        self.addParameter(
            QgsProcessingParameterEnum(
                self.OUTPUT_CRS,
                self._tr("Output CRS"),
                options=[
                    self._tr("Same as input raster"),
                    "EPSG:4326 (WGS 84)",
                    "EPSG:3857 (Web Mercator)",
                    "EPSG:32618 (UTM 18N)",
                    "EPSG:32619 (UTM 19N)",
                    self._tr("Custom (specify below)"),
                ],
                defaultValue=0,  # "Same as input raster"
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.OUTPUT_CRS_CUSTOM,
                self._tr("Custom CRS (e.g. EPSG:3116)"),
                defaultValue="",
                optional=True,
                multiLine=False,
            )
        )

    def _parse_parameters(self, raw_parameters: str | None) -> dict[str, Any]:
        if not raw_parameters:
            return {}
        try:
            parsed = json.loads(raw_parameters)
        except json.JSONDecodeError as exc:
            raise _QgsProcessingException(f"Invalid JSON parameters: {exc}") from exc
        if not isinstance(parsed, dict):
            raise _QgsProcessingException("Parameters JSON must decode to an object/dictionary.")
        return parsed

    def _resolve_execution_mode_parameter(self, parameters: dict[str, Any], context: Any) -> str:
        execution_mode_options = ["auto", "strict", "tiled"]
        mode_index = self.parameterAsEnum(parameters, self.EXECUTION_MODE, context)
        if mode_index < 0 or mode_index >= len(execution_mode_options):
            raise _QgsProcessingException("Invalid execution mode selection.")
        return execution_mode_options[mode_index]

    def _resolve_output_crs(
        self,
        parameters: dict[str, Any],
        context: Any,
        *,
        input_crs: Any = None,
    ) -> Any:
        """Resolve the output CRS based on user selection.

        Index mapping (matches the enum options in initAlgorithm):
            0 -> "Same as input raster" (use input_crs)
            1 -> EPSG:4326
            2 -> EPSG:3857
            3 -> EPSG:32618
            4 -> EPSG:32619
            5 -> Custom (read from OUTPUT_CRS_CUSTOM)
        """
        try:
            crs_index = int(self.parameterAsEnum(parameters, self.OUTPUT_CRS, context))
        except Exception:
            crs_index = 0

        try:
            custom_value = self.parameterAsString(parameters, self.OUTPUT_CRS_CUSTOM, context)
        except Exception:
            custom_value = ""

        return _resolve_crs_from_index(crs_index, custom_value, input_crs)

    def _validate_execution_mode_for_profile(self, execution_mode: str, profile_id: str) -> None:
        """Validate execution mode is supported for the given profile."""
        if execution_mode == "tiled" and profile_id != "regional-high-precision":
            raise _QgsProcessingException(
                "Tiled execution mode is only supported for 'regional-high-precision' profile. "
                "For edge/linear profiles, use 'auto' (recommended) or 'strict'."
            )

    @staticmethod
    def _parse_output_format_parameter(parameters: dict[str, Any], context: Any) -> str:
        """Parse output format from parameters.

        Handles both numeric indices (from QGIS enum) and string values
        (for backward compatibility and external API callers).
        """
        output_format_options = ["auto", "gpkg", "geojson", "shp"]
        output_format_value = parameters.get("OUTPUT_FORMAT", "auto")

        # If it's a string, check if it's a valid format
        if isinstance(output_format_value, str):
            if output_format_value in output_format_options:
                return output_format_value
            # If it's the full display name like "GeoPackage (.gpkg)", extract the format
            for opt in output_format_options:
                if opt in output_format_value or output_format_value in opt:
                    return opt
            return "auto"

        # If it's a numeric index
        try:
            index = int(output_format_value)
            if 0 <= index < len(output_format_options):
                return output_format_options[index]
        except (TypeError, ValueError):
            pass
        return "auto"

    def _resolve_output_format(self, parameters: dict[str, Any], context: Any) -> str:
        """Resolve output format from enum parameter using QGIS API."""
        return self._parse_output_format_parameter(parameters, context)

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
            raise _QgsProcessingException("Invalid profile selection.")
        profile_id = profile_options[profile_index]
        execution_mode = self._resolve_execution_mode_parameter(parameters, context)
        self._validate_execution_mode_for_profile(execution_mode, profile_id)
        raw_parameters = self.parameterAsString(parameters, self.PARAMETERS, context)

        layer_name = self.parameterAsString(parameters, self.LAYER_NAME, context)
        if not layer_name:
            layer_name = self._generate_default_layer_name(profile_id)
        output_format = self._resolve_output_format(parameters, context)
        profile_parameters = self._parse_parameters(raw_parameters)

        if profile_id == "edge-high-precision":
            canny_low = self.parameterAsString(parameters, self.EDGE_CANNY_LOW, context)
            if canny_low:
                profile_parameters["edge_canny_low"] = canny_low
            canny_high = self.parameterAsString(parameters, self.EDGE_CANNY_HIGH, context)
            if canny_high:
                profile_parameters["edge_canny_high"] = canny_high
            edge_blur = self.parameterAsString(parameters, self.EDGE_BLUR, context)
            if edge_blur:
                profile_parameters["edge_blur"] = edge_blur

        engine_options = ["auto", "classic", "opencv"]
        engine_index = self.parameterAsEnum(parameters, self.ENGINE, context)
        if 0 <= engine_index < len(engine_options):
            engine_name = engine_options[engine_index]
            if engine_name == "auto":
                # Pass "auto" so the registry can select the best available engine
                profile_parameters["engine_name"] = "auto"
            elif engine_name == "classic":
                profile_parameters["engine_name"] = "classic-local"
            elif engine_name == "opencv":
                profile_parameters["engine_name"] = "opencv-local"

        # Edge to polygon mode (for edge profile)
        edge_to_polygon_options = ["no", "yes"]
        edge_to_polygon_index = self.parameterAsEnum(parameters, self.EDGE_TO_POLYGON, context)
        if 0 <= edge_to_polygon_index < len(edge_to_polygon_options):
            if edge_to_polygon_options[edge_to_polygon_index] == "yes":
                profile_parameters["edge_to_polygon"] = True

        # Dissolve adjacent polygons (for regional profile)
        dissolve_options = ["no", "yes"]
        dissolve_index = self.parameterAsEnum(parameters, self.DISSOLVE_ADJACENT, context)
        if 0 <= dissolve_index < len(dissolve_options):
            if dissolve_options[dissolve_index] == "yes":
                profile_parameters["dissolve_adjacent"] = True

        # Simplify tolerance override
        simplify_tol = self.parameterAsString(parameters, self.SIMPLIFY_TOLERANCE, context)
        if simplify_tol:
            try:
                profile_parameters["simplify_tolerance"] = float(simplify_tol)
            except ValueError:
                pass

        raster_crs = raster_layer.crs()
        crs_is_valid = raster_crs is not None and raster_crs.isValid()
        if not crs_is_valid:
            fallback_crs = None
            try:
                fallback_crs = QgsCoordinateReferenceSystem.fromEpsgId(4326)
            except (AttributeError, TypeError):
                try:
                    fallback_crs = QgsCoordinateReferenceSystem("EPSG:4326")
                except Exception:
                    fallback_crs = None
            project_crs = None
            try:
                project = QgsProject.instance()
                if project is not None:
                    project_crs_obj = project.crs()
                    if project_crs_obj is not None and project_crs_obj.isValid():
                        fallback_crs = project_crs_obj
            except Exception:
                pass
            raster_crs = fallback_crs
            feedback.pushWarning(
                "Input raster has no CRS defined. Using "
                f"{fallback_crs.authid()} as fallback."
            )

        output_destination = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)
        if not output_destination:
            raise QgsProcessingException("Output destination is required.")

        output_path = Path(output_destination)
        inferred_format = output_format
        suffix = output_path.suffix.lower()
        if output_format == "auto":
            if suffix == ".gpkg":
                inferred_format = "gpkg"
            elif suffix in {".geojson", ".json"}:
                inferred_format = "geojson"

        if ":" in output_destination and not output_destination.startswith("/"):
            temp_extension = ".gpkg" if inferred_format == "gpkg" else ".geojson"
            output_path = Path(tempfile.gettempdir()) / f"vector_map_{profile_id}{temp_extension}"

        # Resolve output CRS based on user selection
        output_crs = self._resolve_output_crs(
            parameters, context, input_crs=fallback_crs
        )
        if output_crs is not None:
            feedback.pushInfo(
                f"Output layer CRS: {output_crs.authid() if hasattr(output_crs, 'authid') else output_crs}"
            )

        request = VectorizationRequest(
            source=input_path,
            profile_id=profile_id,
            output_path=output_path,
            output_format=inferred_format,
            layer_name=layer_name,
            parameters=profile_parameters,
            metadata={
                "processing_provider": "vector_map",
                "output_crs": output_crs.authid() if output_crs and hasattr(output_crs, "authid") else None,
            },
            execution_mode=execution_mode,
        )

        try:
            result = run_vectorization(
                request,
                progress_callback=lambda stage, progress, message: feedback.pushInfo(
                    f"[{stage.value}] {message} ({progress:.0%})"
                ),
                cancel_callback=getattr(feedback, "isCanceled", lambda: False),
            )
            for warning in result.warnings:
                feedback.pushWarning(warning)
        except VectorMapError as exc:
            raise _QgsProcessingException(str(exc)) from exc

        vector_layer = result.vector_layer
        if vector_layer.feature_count() == 0:
            feedback.pushWarning("Vectorization produced no features.")

        geometry_types = {f.geometry_type for f in vector_layer.features}
        wkb_type = _resolve_qgs_geometry_type(geometry_types)
        if len(geometry_types) > 1:
            feedback.pushWarning(
                f"Mixed geometry types detected: {sorted(geometry_types)}. "
                f"Output layer will use geometry type {wkb_type}. "
                f"Some geometry types may not display correctly."
            )

        fields = QgsFields()
        field_names = sorted(
            {str(key) for f in vector_layer.features for key in f.properties.keys()}
        )
        for field_name in field_names:
            fields.append(QgsField(field_name, QtVariantType.String))

        (sink, dest_id) = self.parameterAsSink(
            parameters,
            self.OUTPUT,
            context,
            fields,
            wkb_type,
            raster_crs,
            layer_name,
        )
        if sink is None:
            raise QgsProcessingException("Could not create output layer sink.")

        _write_features_to_sink(sink, fields, vector_layer, raster_crs, feedback)

        return {
            self.OUTPUT: dest_id,
            self.PROFILE: result.profile_id,
            self.LAYER_NAME: vector_layer.name,
            self.PARAMETERS: json.dumps(
                result.metadata.get("requested_parameters", {}), sort_keys=True
            ),
        }


class _LightweightCRS:
    """Fallback CRS wrapper used when QGIS is not available.

    Provides a small subset of the QGIS interface (authid, isValid, description)
    so the rest of the code can be tested without importing qgis.core.
    """

    def __init__(self, authid: str) -> None:
        self._authid = authid
        self._is_valid = authid.upper().startswith("EPSG:")

    def authid(self) -> str:
        return self._authid

    def isValid(self) -> bool:
        return self._is_valid

    def description(self) -> str:
        return f"Lightweight CRS ({self._authid})"

    def __repr__(self) -> str:
        return f"_LightweightCRS({self._authid!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, _LightweightCRS):
            return NotImplemented
        return self._authid == other._authid

    def __hash__(self) -> int:
        return hash(self._authid)


# CRS option index -> action
_CRS_OPTION_INPUT = 0
_CRS_OPTION_EPSG_4326 = 1
_CRS_OPTION_EPSG_3857 = 2
_CRS_OPTION_EPSG_32618 = 3
_CRS_OPTION_EPSG_32619 = 4
_CRS_OPTION_CUSTOM = 5

_CRS_PRESETS = {
    _CRS_OPTION_EPSG_4326: "EPSG:4326",
    _CRS_OPTION_EPSG_3857: "EPSG:3857",
    _CRS_OPTION_EPSG_32618: "EPSG:32618",
    _CRS_OPTION_EPSG_32619: "EPSG:32619",
}


def _resolve_crs_from_index(
    crs_index: int,
    custom_value: str,
    input_crs: Any,
) -> Any:
    """Pure-logic CRS resolution (no QGIS dependency).

    Separated from the algorithm wrapper so it can be unit-tested without
    instantiating the QGIS processing algorithm.

    Parameters
    ----------
    crs_index:
        The user-selected index from the OUTPUT_CRS enum.
    custom_value:
        The value of OUTPUT_CRS_CUSTOM (only used when index == CUSTOM).
    input_crs:
        The input raster CRS (returned when index == INPUT).
    """
    if crs_index < 0 or crs_index > _CRS_OPTION_CUSTOM:
        crs_index = _CRS_OPTION_INPUT

    if crs_index == _CRS_OPTION_INPUT:
        return input_crs

    if crs_index == _CRS_OPTION_CUSTOM:
        custom_value = (custom_value or "").strip()
        if not custom_value:
            return input_crs
        return _build_crs(custom_value)

    return _build_crs(_CRS_PRESETS[crs_index])


def _build_crs(authid: str) -> Any:
    """Build a CRS object. Uses QGIS if available, else _LightweightCRS."""
    if HAS_QGIS:
        try:
            from qgis.core import QgsCoordinateReferenceSystem
            crs_obj = QgsCoordinateReferenceSystem(authid)
            if crs_obj.isValid():
                return crs_obj
        except Exception:
            pass
    return _LightweightCRS(authid)
