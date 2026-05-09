## 1. Modelo de datos

- [x] 1.1 Agregar campo `geotransform: tuple[float, ...] | None = None` a `VectorLayer` en `qgis_vector_map/core/models.py`
- [x] 1.2 Propagar `geotransform` desde `RasterFrame.metadata` al `VectorLayer` en `_run_standard_pipeline()` en `qgis_vector_map/core/pipeline.py`
- [x] 1.3 Propagar `geotransform` desde `source_metadata` al `VectorLayer` consolidado en `_run_regional_tiled_pipeline()` en `qgis_vector_map/core/pipeline.py`

## 2. Transformación de coordenadas

- [x] 2.1 Implementar `apply_geotransform(geometry_type, coordinates, geotransform)` en `qgis_vector_map/core/geometry.py` que aplique la fórmula afín GDAL a cada punto
- [x] 2.2 Agregar llamada a `apply_geotransform()` en el pipeline estándar, después de postprocess y antes de export, usando el `geotransform` del `VectorLayer`
- [x] 2.3 Agregar llamada a `apply_geotransform()` en el pipeline tiled, sobre las coordenadas consolidadas (que ya incluyen offsets de tile)
- [x] 2.4 Manejar caso `geotransform = None`: registrar warning y dejar coordenadas sin transformar

## 3. Integración con QgsFeatureSink

- [x] 3.1 Reescribir `processAlgorithm()` para obtener CRS del raster de entrada via `QgsRasterLayer.crs()`
- [x] 3.2 Reescribir `processAlgorithm()` para resolver tipo de geometría predominante y crear `QgsFields` con los atributos de los features
- [x] 3.3 Reescribir `processAlgorithm()` para usar `self.parameterAsSink()` obteniendo `(sink, dest_id)` con campos, tipo de geometría y CRS
- [x] 3.4 Implementar conversión de `VectorFeature` a `QgsFeature` con `QgsGeometry` construida desde coordenadas transformadas y CRS
- [x] 3.5 Escribir cada `QgsFeature` al sink y retornar `{self.OUTPUT: dest_id}`
- [x] 3.6 Manejar CRS ausente: usar CRS del proyecto QGIS como fallback con `feedback.pushWarning()`
- [x] 3.7 Mantener camino de exportación por archivo (OGR/GeoJSON) como fallback cuando `HAS_QGIS = False`

## 4. Geometrías mixtas en exportación por archivo

- [x] 4.1 Modificar `export_geopackage()` para agrupar features por tipo de geometría y crear sub-capas separadas (ej: `name_polygons`, `name_lines`, `name_points`)
- [x] 4.2 Modificar `export_geojson()` para manejar grupos de geometría si es necesario (GeoJSON soporta un solo tipo por FeatureCollection, mantener comportamiento actual si todos son del mismo tipo)

## 5. Tests

- [x] 5.1 Tests unitarios para `apply_geotransform()`: identity transform, standard affine, rotation, None case, cada tipo de geometría (Point, LineString, Polygon, MultiPolygon, MultiLineString)
- [x] 5.2 Tests unitarios para propagación de `geotransform` en `VectorLayer` en pipeline estándar y tiled
- [x] 5.3 Tests de integración para geometrías mixtas en `export_geopackage()` verificando sub-capas separadas
- [x] 5.4 Tests para verificación de que coordenadas transformadas son correctas para un raster con geotransform conocido