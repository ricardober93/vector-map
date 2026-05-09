## Context

El plugin QGIS `vector_map` vectoriza imágenes raster a través de un pipeline de 4 etapas (preprocess → vectorize → postprocess → export). El pipeline funciona internamente pero el resultado final no se integra correctamente con QGIS por dos razones:

1. **Sin QgsFeatureSink**: `processAlgorithm()` escribe a archivo vía OGR y devuelve un path. Cuando QGIS usa un destino `memory:` (default en Processing Toolbox), la capa queda vacía porque el algoritmo nunca escribe al sink que QGIS crea.

2. **Coordenadas en pixel space**: Los motores de vectorización producen geometrías en coordenadas pixel (0,0 a ancho×alto). El `geotransform` del raster se lee y almacena en metadata pero nunca se aplica. Las geometrías resultantes están en posiciones geográficas erróneas.

El código ya lee el geotransform en tres puntos (`raster.py:403-405`, `pipeline.py:409-414`, `raster.py:575-577`) y lo almacena en `RasterFrame.metadata["geotransform"]`.

## Goals / Non-Goals

**Goals:**
- Las geometrías de salida usen coordenadas mundo (georreferenciadas) en lugar de coordenadas pixel.
- El algoritmo se integre con `QgsFeatureSink` para que todos los destinos de QGIS Processing funcionen correctamente.
- Las geometrías mixtas (Polygon + LineString) se exporten sin pérdida de features.
- El CRS de la capa de salida coincida con el del raster de entrada, con fallback informado cuando esté ausente.
- El camino de exportación por archivo (OGR/GeoJSON) siga funcionando para tests sin QGIS.

**Non-Goals:**
- Reprojectar coordenadas entre CRSs diferentes (solo se aplica la transformación afín pixel→mundo).
- Cambiar el formato de almacenamiento interno de features (`VectorFeature` sigue con coordenadas GeoJSON).
- Optimizar rendimiento del pipeline (es out of scope).
- Soportar transformaciones afines con rotación no-trivial (no es un caso común en rasters geoespaciales).

## Decisions

### D1: Transformación afín como paso explícito del pipeline

**Decisión**: Agregar la transformación pixel→mundo como un paso explícito después de postprocess y antes de export, en lugar de modificar los motores de vectorización.

**Rationale**: Los motores producen coordenadas pixel naturalmente (operan sobre grids). La transformación es una preocupación de la capa de presentación, no del motor. Mantiene los motores simples y reutilizables.

**Alternativa considerada**: Transformar dentro de cada motor. Descartada porque duplica lógica y complica motores con conocimiento del geotransform.

### D2: Función `apply_geotransform()` en `geometry.py`

**Decisión**: Nueva función `apply_geotransform()` en el módulo existente `geometry.py`, no en un módulo nuevo.

**Rationale**: `geometry.py` ya maneja geometrías y coordenadas. La transformación es una operación geométrica natural. Evita crear módulos innecesarios.

### D3: `geotransform` propagado vía `VectorLayer`

**Decisión**: Agregar campo `geotransform: tuple[float, ...] | None` a `VectorLayer` ( modelos.py), propagado desde `RasterFrame.metadata` en el pipeline.

**Rationale**: Mantiene la transformación accesible tanto para el pipeline (que la aplica) como para el algoritmo QGIS (que puede usarla para construir `QgsGeometry`). El campo es opcional para mantener retrocompatibilidad con layers sin geotransform.

**Alternativa considerada**: Pasar geotransform como parámetro separado a la función de export. Descartada porque acopla la firma de export al geotransform y complica el pipeline tiled.

### D4: `QgsFeatureSink` como camino principal en `processAlgorithm()`

**Decisión**: Usar `self.parameterAsSink()` para obtener un `(sink, dest_id)` y escribir features directamente. Retornar `dest_id` como `OUTPUT`.

**Rationale**: Este es el patrón estándar de QGIS Processing. Soporta `memory:`, archivos temporales y archivos explícitos sin workarounds. Elimina la necesidad del hack de archivo temporal para destinos `memory:`.

**Alternativa considerada**: Mantener export por archivo y cargar después con `QgsVectorLayer`. Descartada porque no funciona con `memory:` y es menos eficiente.

### D5: Construcción de geometrías QGIS desde coordenadas transformadas

**Decisión**: Construir `QgsGeometry` usando `QgsPointXY` y `QgsPolygon`/`QgsPolyline` desde las coordenadas ya transformadas, en lugar de usar WKT o GeoJSON.

**Rationale**: Más directo y evita problemas de precisión con serialización/deserialización. También permite asignar CRS directamente al `QgsFeatureSink`.

**Alternativa considerada**: Usar `QgsGeometry.fromWkt()` o `QgsGeometry.fromJson()`. Descartada porque introduce paso de serialización innecesario.

### D6: Geometrías mixtas en GeoPackage

**Decisión**: Agrupar features por tipo de geometría y crear una sub-capa OGR por tipo en GeoPackage.

**Rationale**: GeoPackage permite múltiples capas. Cada tipo de geometría va en su propia capa (`name_polygons`, `name_lines`, `name_points`).

**Alternativa considerada**: Usar `wkbUnknown` como tipo de geometría. Descartada porque muchos clientes GIS (incluido QGIS) manejan mal capas con tipo desconocido y abre las geometrías de forma inconsistente.

### D7: CRS fallback con warning

**Decisión**: Cuando el raster no tiene CRS, usar `QgsProject.instance().crs()` como fallback si está disponible, sino EPSG:4326, siempre con `feedback.pushWarning()`.

**Rationale**: Una capa sin CRS en QGIS causa confusión y prompts al usuario. Es mejor asignar un CRS razonable con advertencia que dejarlo vacío.

## Risks / Trade-offs

- **[Riesgo] Cambio BREAKING en `processAlgorithm()`**: El nuevo código reemplaza la exportación directa a archivo con QgsFeatureSink. → **Mitigación**: Mantener el camino de exportación por archivo cuando `HAS_QGIS = False` (tests sin QGIS).

- **[Riesgo] Geotransform con rotación no-trivial**: Rasters con `gt[2]` o `gt[4]` distintos de 0 (rotación) producirán coordenadas incorrectas si la fórmula no aplica la rotación. → **Mitigación**: Usar la fórmula completa `x = gt[0] + col*gt[1] + row*gt[2]`, `y = gt[3] + col*gt[4] + row*gt[5]` que incluye rotación. La mayoría de rasters tienen `gt[2]=gt[4]=0`.

- **[Riesgo] Pipeline tiled y coordenadas**: En el pipeline tiled, los offsets de tile ya están en espacio pixel del raster completo. La transformación afín debe aplicarse sobre las coordenadas consolidadas (que ya incluyen offsets de tile). → **Mitigación**: Aplicar geotransform DESPUÉS de consolidar features, no dentro de cada tile.

- **[Trade-off] QGIS-only para el camino principal**: El camino con QgsFeatureSink solo funciona en runtime de QGIS. Tests unitarios sin QGIS usan el camino de exportación por archivo. → **Aceptable**: El camino de archivo sigue funcionando; los tests de integración de QGIS requieren un entorno QGIS.

- **[Trade-off] Sub-capas en GeoPackage**: Exportar tipos mixtos crea múltiples capas en un mismo archivo, lo que puede confundir herramientas simples. → **Aceptable**: Preferible a perder features. Los usuarios de QGIS manejan bien múltiples capas en un GPKG.