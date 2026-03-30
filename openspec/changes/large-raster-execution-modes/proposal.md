## Why

El flujo actual falla temprano de forma correcta para rásteres muy grandes, pero deja al usuario con mitigaciones manuales y repetitivas (AOI, remuestreo, mosaicos) fuera del algoritmo. Necesitamos un camino operativo más guiado y un modo controlado para ejecutar escenas grandes sin romper los contratos de precisión/reproducibilidad.

## What Changes

- Incorporar un modo de ejecución explícito para memoria (`memory_policy`) con default conservador y opción experta controlada.
- Agregar preflight accionable con recomendaciones numéricas (factor mínimo de reducción y/o tamaño objetivo) para que el usuario pueda decidir rápidamente.
- Introducir estrategia de procesamiento por teselas para `regional-high-precision` que mantenga el contrato de salida en una capa única.
- Mantener guardrails por defecto (`max_pixels`, `max_estimated_bytes`) como comportamiento estándar del MVP.
- Extender documentación operativa para escenarios de ortomosaicos grandes (flujo recomendado y trade-offs de precisión).

## Capabilities

### New Capabilities

- `large-raster-operational-guidance`: guía operativa y recomendaciones cuantitativas para ejecutar rásteres grandes de forma reproducible.

### Modified Capabilities

- `local-image-vectorization`: se amplía el comportamiento de preflight para entregar recomendaciones numéricas y habilitar política de memoria explícita.
- `vectorization-profiles`: el perfil regional incorpora modo de ejecución por teselas para tamaños fuera de umbral manteniendo compatibilidad de salida.

## Impact

- Código afectado: `qgis_vector_map/core/raster.py`, `qgis_vector_map/core/pipeline.py`, `qgis_vector_map/core/models.py`, `qgis_vector_map/processing_profiles.py`, `qgis_vector_map/algorithms/vectorize_image_algorithm.py`.
- Pruebas afectadas: `tests/test_raster.py` y nuevas pruebas de integración para teselado/merge de salida regional.
- Documentación afectada: `docs/architecture.md`, `docs/mvp-strict-usage.md`, `docs/precision-baseline.md`.
- Riesgos: incremento de complejidad operativa y mayor costo de cómputo en modo teselado; mitigado con defaults estrictos y activación explícita de modo experto.
