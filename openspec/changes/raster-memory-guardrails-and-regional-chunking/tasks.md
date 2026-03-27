## 1. Guardas de memoria en carga raster

- [x] 1.1 Implementar preflight GDAL con `RasterXSize`, `RasterYSize`, `RasterCount`.
- [x] 1.2 Aplicar thresholds por defecto (`max_pixels`, `max_estimated_bytes`) con override por parámetros.
- [x] 1.3 Emitir error accionable con tamaño, estimación y recomendaciones.
- [x] 1.4 Omitir fallback a Pillow cuando GDAL falla por `MemoryError`.

## 2. Carga regional por ventanas

- [x] 2.1 Implementar lectura GDAL por ventanas para `regional-high-precision`.
- [x] 2.2 Exponer `chunk_size` como parámetro interno con default `2048`.
- [x] 2.3 Preservar metadatos geoespaciales (CRS y geotransform) en la carga chunked.

## 3. Validación y documentación

- [x] 3.1 Ampliar pruebas en `tests/test_raster.py` para oversize, `MemoryError`, y chunked regional.
- [x] 3.2 Actualizar `docs/architecture.md` y `docs/mvp-strict-usage.md`.
- [x] 3.3 Actualizar specs OpenSpec afectadas (`local-image-vectorization`, `vectorization-profiles`).
