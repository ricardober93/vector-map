## Why

La carga raster actual puede agotar memoria en ortomosaicos grandes porque materializa arreglos completos en memoria Python. Esto genera fallos tardíos y poco accionables en QGIS.

## What Changes

- Agregar preflight de memoria basado en metadatos GDAL antes de `ReadAsArray`.
- Definir abort temprano con diagnóstico accionable cuando se exceden umbrales.
- Evitar fallback a Pillow cuando GDAL falla por `MemoryError`.
- Incorporar carga regional por ventanas (`chunk_size`) para reducir presión de memoria en el perfil regional.
- Documentar defaults y comportamiento operativo.

## Capabilities

### Modified Capabilities

- `local-image-vectorization`: la carga de rásteres grandes ahora tiene guardas de memoria y errores más accionables.
- `vectorization-profiles`: el perfil regional puede cargar datos GDAL por chunks controlados.

## Impact

- Código afectado: `qgis_vector_map/core/raster.py`, `qgis_vector_map/core/pipeline.py`, `qgis_vector_map/processing_profiles.py`, `tests/test_raster.py`.
- Riesgo: cambios en flujo de carga para rásteres en disco; mitigado con pruebas unitarias de no-regresión y casos de error.
