"""Vector layer export helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .errors import DependencyError, ExportError
from .models import VectorFeature, VectorLayer


def _json_safe(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {str(key): _json_safe(inner) for key, inner in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return str(value)


def _feature_to_geojson(feature: VectorFeature) -> dict[str, Any]:
    return {
        "type": "Feature",
        "geometry": {
            "type": feature.geometry_type,
            "coordinates": _json_safe(feature.coordinates),
        },
        "properties": _json_safe(dict(feature.properties)),
    }


def export_geojson(layer: VectorLayer, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "type": "FeatureCollection",
        "features": [_feature_to_geojson(feature) for feature in layer.features],
    }
    if layer.crs:
        payload["crs"] = {
            "type": "name",
            "properties": {"name": layer.crs},
        }
    payload["metadata"] = _json_safe(layer.metadata)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def _gpkg_available() -> bool:
    try:
        from osgeo import ogr  # type: ignore  # noqa: F401
        return True
    except Exception:
        try:
            from qgis.core import QgsVectorFileWriter  # type: ignore  # noqa: F401
            return True
        except Exception:
            return False


def _resolve_export_format(output_path: Path | None, requested_format: str) -> str:
    requested = requested_format.lower().strip() if requested_format else "auto"
    if requested != "auto":
        return requested
    if output_path is not None:
        suffix = output_path.suffix.lower()
        if suffix == ".gpkg":
            return "gpkg"
        if suffix in {".json", ".geojson"}:
            return "geojson"
    return "gpkg" if _gpkg_available() else "geojson"


def export_vector_layer(
    layer: VectorLayer,
    output_path: str | Path | None,
    *,
    requested_format: str = "auto",
) -> Path:
    resolved_path = Path(output_path) if output_path is not None else None
    resolved_format = _resolve_export_format(resolved_path, requested_format)
    if resolved_path is None:
        suffix = ".gpkg" if resolved_format == "gpkg" else ".geojson"
        resolved_path = Path.cwd() / f"{layer.name}{suffix}"
    if resolved_format == "geojson":
        return export_geojson(layer, resolved_path)
    if resolved_format != "gpkg":
        raise ExportError(f"Unsupported export format: {resolved_format}")
    return export_geopackage(layer, resolved_path)


def _ogr_geometry_type_for(feature_type: str, ogr_module: Any) -> int:
    mapping = {
        "Point": ogr_module.wkbPoint,
        "MultiPoint": ogr_module.wkbMultiPoint,
        "LineString": ogr_module.wkbLineString,
        "MultiLineString": ogr_module.wkbMultiLineString,
        "Polygon": ogr_module.wkbPolygon,
        "MultiPolygon": ogr_module.wkbMultiPolygon,
    }
    return mapping.get(feature_type, ogr_module.wkbUnknown)


def _group_features_by_type(
    features: list[VectorFeature],
) -> list[tuple[str, list[VectorFeature]]]:
    groups: dict[str, list[VectorFeature]] = {}
    order: list[str] = []
    for feature in features:
        gt = feature.geometry_type
        if gt not in groups:
            groups[gt] = []
            order.append(gt)
        groups[gt].append(feature)
    return [(gt, groups[gt]) for gt in order]


def export_geopackage(layer: VectorLayer, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        from osgeo import ogr, osr  # type: ignore
    except Exception as exc:
        raise DependencyError(
            "GeoPackage export requires GDAL/OGR (osgeo). Install the dependency or request GeoJSON export instead."
        ) from exc

    if path.exists():
        path.unlink()

    driver = ogr.GetDriverByName("GPKG")
    if driver is None:
        raise ExportError("OGR could not find the GeoPackage driver.")
    datasource = driver.CreateDataSource(str(path))
    if datasource is None:
        raise ExportError(f"OGR could not create GeoPackage file: {path}")

    srs = None
    if layer.crs:
        srs = osr.SpatialReference()
        if layer.crs.upper().startswith("EPSG:"):
            epsg_code = int(layer.crs.split(":", 1)[1])
            srs.ImportFromEPSG(epsg_code)
        else:
            srs.ImportFromWkt(layer.crs)

    feature_groups = _group_features_by_type(layer.features)
    single_group = len(feature_groups) == 1
    main_type = feature_groups[0][0] if feature_groups else "Polygon"
    main_ogr_type = _ogr_geometry_type_for(main_type, ogr)

    if single_group or not feature_groups:
        ogr_layer = datasource.CreateLayer(layer.name, srs=srs, geom_type=main_ogr_type)
        if ogr_layer is None:
            raise ExportError("OGR could not create the output layer.")
        _write_features_to_ogr_layer(ogr_layer, layer.features, ogr)
    else:
        type_suffixes = {
            "Point": "_points",
            "MultiPoint": "_points",
            "LineString": "_lines",
            "MultiLineString": "_lines",
            "Polygon": "_polygons",
            "MultiPolygon": "_polygons",
        }
        for geometry_type, group_features in feature_groups:
            suffix = type_suffixes.get(geometry_type, f"_{geometry_type.lower()}")
            sub_layer_name = f"{layer.name}{suffix}"
            group_ogr_type = _ogr_geometry_type_for(geometry_type, ogr)
            ogr_layer = datasource.CreateLayer(sub_layer_name, srs=srs, geom_type=group_ogr_type)
            if ogr_layer is None:
                raise ExportError(f"OGR could not create sub-layer '{sub_layer_name}'.")
            _write_features_to_ogr_layer(ogr_layer, group_features, ogr)

    datasource.FlushCache()
    datasource = None
    return path


def _write_features_to_ogr_layer(
    ogr_layer: Any, features: list[VectorFeature], ogr: Any
) -> None:
    field_names = sorted({str(key) for feature in features for key in feature.properties.keys()})
    for field_name in field_names:
        field_defn = ogr.FieldDefn(field_name, ogr.OFTString)
        ogr_layer.CreateField(field_defn)

    for feature in features:
        ogr_feature = ogr.Feature(ogr_layer.GetLayerDefn())
        for field_name in field_names:
            value = feature.properties.get(field_name)
            if value is not None:
                ogr_feature.SetField(field_name, str(value))
        geometry = ogr.CreateGeometryFromJson(
            json.dumps(
                {
                    "type": feature.geometry_type,
                    "coordinates": _json_safe(feature.coordinates),
                }
            )
        )
        if geometry is None:
            raise ExportError(f"OGR could not convert geometry to GeoPackage format: {feature.geometry_type}")
        ogr_feature.SetGeometry(geometry)
        if ogr_layer.CreateFeature(ogr_feature) != 0:
            raise ExportError("OGR failed while writing a feature.")
        ogr_feature = None
