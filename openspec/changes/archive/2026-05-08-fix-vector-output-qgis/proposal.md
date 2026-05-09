## Why

El algoritmo de vectorización ejecuta correctamente el pipeline (preprocess → vectorize → postprocess → export) pero el resultado no se carga como capa vectorial funcional en QGIS. Dos bugs críticos lo causan: (1) el algoritmo nunca escribe features al `QgsFeatureSink` de QGIS, dejando la capa de salida vacía cuando el destino es `memory:`, y (2) las coordenadas de los features están en espacio pixel sin la transformación afín (geotransform) del raster, colocando las geometrías en posiciones geográficas incorrectas aún cuando la capa sí se carga. No corregir esto hace que el plugin sea inutilizable en cualquier flujo de trabajo real de QGIS.

## What Changes

- **BREAKING**: Reemplazar la escritura directa a archivo vía OGR con integración al `QgsFeatureSink` de QGIS Processing para que los features se escriban correctamente independientemente del tipo de destino (archivo, `memory:`, o temporal).
- Agregar transformación afín (geotransform GDAL) de coordenadas pixel→mundo antes de exportar features. El `geotransform` ya se lee del raster pero nunca se aplica.
- Separar features por tipo de geometría al exportar a GeoPackage para evitar perder features de tipos mixtos (Polygon + LineString en la misma capa OGR).
- Propagar el CRS correctamente cuando está ausente, registrando un warning y asignando CRS fallback consistente.
- Mejorar manejo del destino `memory:` en `processAlgorithm()` usando `parameterAsSink` en lugar de workaround con archivo temporal.

## Capabilities

### New Capabilities

- `geotransform-pixel-to-world`: Transformación afín de coordenadas pixel a coordenadas mundo usando el geotransform GDAL del raster de entrada. Aplica la transformación a todas las geometrías antes de la exportación.
- `qgis-feature-sink-integration`: Integración con `QgsFeatureSink` de QGIS Processing para escribir features directamente al destino de salida del algoritmo, soportando destinos `memory:`, archivo temporal y archivo explícito.

### Modified Capabilities

- `local-image-vectorization`: El requirement "Salida geoespacial válida para QGIS" cambia para garantizar que las coordenadas de los features estén en el sistema de referencia del raster (no en espacio pixel) y que la capa de salida se integre correctamente con el framework Processing de QGIS mediante `QgsFeatureSink`.
- `vectorization-profiles`: Sin cambios en los requisitos de perfiles; la transformación de coordenadas es transparente a los motores de vectorización.

## Impact

- **`qgis_vector_map/algorithms/vectorize_image_algorithm.py`**: Reescritura de `processAlgorithm()` para usar `parameterAsSink()` y crear features QGIS con coordenadas transformadas.
- **`qgis_vector_map/core/export.py`**: Extracción de lógica de transformación de coordenadas; `export_geopackage()` maneja geometrías mixtas creando sub-capas por tipo.
- **`qgis_vector_map/core/pipeline.py`**: Agregar etapa de transformación de coordenadas post-vectorización antes de exportar; `_offset_coordinates()` pasa a usar geotransform completo.
- **`qgis_vector_map/core/models.py`**: Agregar campo `geotransform` a `VectorLayer` para propagar la transformación desde el raster.
- **`qgis_vector_map/core/raster.py`**: Sin cambios (ya lee geotransform).
- **Tests**: Nuevos tests para la transformación afín y la integración con QgsFeatureSink.