## Why

El motor `opencv-local` es significativamente más rápido que `classic-local` para imágenes grandes (especialmente en vectorización regional con k-means). Sin embargo, el dropdown de "Engine" en la UI de QGIS tiene `auto` como default, y cuando el usuario deja `auto`, el sistema usa `classic-local` (el default del perfil).

Necesitamos que el modo `auto` intelligently seleccione el mejor motor disponible basándose en criterios objetivos.

## What Changes

- **Selección inteligente de motor en modo `auto`**: cuando el usuario selecciona `auto` en el dropdown de Engine, el sistema evalúa criterios (tamaño de imagen, disponibilidad de OpenCV, GPU disponible) y selecciona el motor óptimo.
- **Criterios de selección**: OpenCV se selecciona por defecto cuando está disponible, a menos que haya razones para preferir classic (ej: debugging, reproducibilidad exacta).
- **Fallback robusto**: si OpenCV falla en runtime, el sistema hace fallback automático a classic.
- **Logging de decisión**: se registra qué motor fue seleccionado y por qué.

## Capabilities

### New Capabilities

- `smart-engine-selection`: el modo `auto` del dropdown de Engine selecciona automáticamente OpenCV (si está disponible) o classic como fallback, basándose en criterios de disponibilidad y rendimiento.

### Modified Capabilities

- `local-image-vectorization`: la selección de motor ahora es inteligente en modo `auto`, no solo el default del perfil.

## Impact

- **Código afectado**:
  - `qgis_vector_map/engines/base.py`: lógica de `EngineRegistry.resolve()` actualizada para manejar `auto` como nombre de motor.
  - `qgis_vector_map/processing_profiles.py`: el perfil ya tiene `engine_name = "classic-local"`, se mantiene como fallback.
  - `qgis_vector_map/algorithms/vectorize_image_algorithm.py`: cuando se selecciona `auto`, se pasa `"auto"` en lugar de omitir el parámetro.
- **Pruebas afectadas**: `tests/test_pipeline.py`, nuevos tests de selección de motor.
- **Breaking**: No. El comportamiento de `classic` y `opencv` explícitos no cambia.