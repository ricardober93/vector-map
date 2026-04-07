# local-image-vectorization Specification (delta)

## MODIFIED Requirements

### Requirement: Abort temprano por preflight de memoria
El sistema SHALL abortar el preflight cuando un ráster excede `max_pixels` o `max_estimated_bytes` DURANTE el modo `strict`, pero SHALL redirigir al pipeline de tiles cuando el modo de ejecución es `auto` y el perfil soporta ejecución por mosaicos.

#### Scenario: Abort temprano por preflight de memoria
- **WHEN** un ráster excede `max_pixels` o `max_estimated_bytes` durante el preflight de metadatos GDAL Y el modo de ejecución es `strict`
- **THEN** el sistema aborta antes de `ReadAsArray` y devuelve un mensaje accionable con dimensiones, estimación y recomendaciones de mitigación

#### Scenario: Auto-detección redirige a tiled execution
- **WHEN** un ráster excede el umbral de auto-detección (75% de `max_pixels`) Y el modo de ejecución es `auto` Y el perfil es `regional-high-precision`
- **THEN** el sistema redirige al pipeline de tiles sin abortar y registra la decisión en el log

#### Scenario: Auto-detección con perfil no-regional
- **WHEN** un ráster excede el umbral de auto-detección Y el modo de ejecución es `auto` Y el perfil NO es regional (edge/linear)
- **THEN** el sistema emite un warning y procede con strict mode (el preflight puede abortar si excede el límite duro)

#### Scenario: MemoryError en GDAL evita fallback redundante
- **WHEN** GDAL falla por `MemoryError` al leer el ráster
- **THEN** el sistema no intenta fallback con Pillow y devuelve un error explícito de presión de memoria con sugerencias operativas
