## Why

El cambio `large-raster-execution-modes` introdujo la política `memory_policy` con modos `strict`, `expert-override` y `regional-tiles`, pero requiere que el usuario escriba manualmente `{"memory_policy": "regional-tiles"}` en un campo JSON oculto. Cuando un ráster grande excede los umbrales, el usuario recibe un error críptico sin una ruta clara de resolución. Necesitamos que el algoritmo **detecte automáticamente** cuándo usar tiles y que la UI **exponga esta opción de forma visible**.

## What Changes

- **Auto-detección de modo de ejecución**: cuando el preflight detecta que un ráster excede `max_pixels`, el algoritmo cambia automáticamente a `regional-tiles` en lugar de abortar.
- **Nuevo parámetro de UI `EXECUTION_MODE`**: dropdown visible en el diálogo de QGIS con opciones `auto`, `strict`, `tiled`. Default: `auto`.
- **Logging informativo**: cuando el modo `auto` activa tiled execution, se registra en el log del algoritmo para trazabilidad.
- **Respeto a la elección del usuario**: si el usuario fuerza `strict` en un ráster grande, se emite un warning pero se respeta la decisión (el preflight sigue activo como guardrail final).
- **Umbral de auto-detección con margen**: el umbral es `max_pixels * 0.75` (150M píxeles) para activar tiled antes de llegar al límite duro, dando margen de seguridad.

## Capabilities

### New Capabilities

- `auto-execution-mode`: detección automática del modo de ejecución basada en el tamaño del ráster, con fallback a tiled cuando excede umbrales seguros.
- `execution-mode-ui`: parámetro visible en la interfaz de QGIS para seleccionar el modo de ejecución (auto/strict/tiled) sin necesidad de editar JSON.

### Modified Capabilities

- `local-image-vectorization`: el preflight ya no aborta cuando el modo es `auto`, sino que redirige al pipeline de tiles. El comportamiento de abort se mantiene solo para modo `strict` explícito.
- `vectorization-profiles`: el perfil `regional-high-precision` activa tiled automáticamente bajo modo `auto` cuando el ráster supera el umbral de margen.

## Impact

- **Código afectado**:
  - `qgis_vector_map/algorithms/vectorize_image_algorithm.py`: nuevo parámetro `EXECUTION_MODE`, lógica de resolución de modo.
  - `qgis_vector_map/core/pipeline.py`: resolución de modo auto en `run()`, redirección a tiled pipeline.
  - `qgis_vector_map/core/raster.py`: ajuste del umbral de preflight para modo auto (no abortar, solo reportar).
  - `qgis_vector_map/processing_profiles.py`: actualización de parámetros por defecto si aplica.
- **Pruebas afectadas**: `tests/test_pipeline.py`, `tests/test_raster.py`, nuevas pruebas de auto-detección.
- **Documentación afectada**: `docs/mvp-strict-usage.md`, `docs/architecture.md`.
- **Breaking**: No. Modo `auto` es el nuevo default y es backward-compatible con el comportamiento actual para rásteres pequeños.
