## Context

El cambio `large-raster-execution-modes` (aún en progreso) introdujo tres políticas de memoria: `strict`, `expert-override` y `regional-tiles`. El pipeline de tiles ya está implementado en `_run_regional_tiled_pipeline()` con soporte completo de offset de coordenadas, merge de features y trazabilidad por tile.

El problema actual es de **UX y de routing**: el usuario no tiene forma visible de activar el modo tiled, y el preflight aborta antes de intentar la ruta alternativa.

**Constraints:**
- El pipeline de tiles ya existe y funciona (ver `pipeline.py:283-520`).
- El parámetro `memory_policy` ya se resuelve desde los parámetros del perfil.
- El algoritmo de QGIS expone un campo JSON oculto que el usuario no sabe usar.
- El umbral actual de preflight es `max_pixels = 200,000,000`.

## Goals / Non-Goals

**Goals:**
- El usuario no necesita escribir JSON para procesar imágenes grandes.
- El algoritmo detecta automáticamente cuándo activar tiles.
- Se mantiene la capacidad de forzar un modo explícito (strict/tiled).
- El preflight se convierte en un router inteligente, no solo en un guardrail.

**Non-Goals:**
- No cambiar la lógica interna del pipeline de tiles (ya implementado).
- No modificar los motores de vectorización (regional, edge, linear).
- No relajar los umbrales de memoria por defecto.
- No agregar soporte de tiles para perfiles edge/linear (solo regional por ahora).

## Decisions

### 1. Nuevo parámetro `EXECUTION_MODE` en la UI de QGIS

Se agrega un `QgsProcessingParameterEnum` con tres opciones:
- `auto` (default): el algoritmo decide basado en el tamaño del ráster.
- `strict`: carga completa en memoria, aborta si excede umbrales.
- `tiled`: procesamiento por mosaicos, solo para perfil regional.

**Rationale**: Un enum es el control más simple y visible en la UI de Processing. El usuario novato no toca nada (auto funciona), el experto puede forzar un modo.

**Alternativa considerada**: Un checkbox "Procesar imágenes grandes por mosaicos". Rechazada porque no escala si en el futuro se agregan más modos.

### 2. Resolución de modo auto en el pipeline

El `PipelineOrchestrator.run()` resuelve el modo antes de cargar el ráster:

```
run()
  ├─ execution_mode = resolve_execution_mode(request, profile)
  ├─ if execution_mode == "auto":
  │     ├─ preflight_check(raster_source)
  │     ├─ if exceeds_threshold(150M px):
  │     │     └─ effective_mode = "regional-tiles"
  │     └─ else:
  │           └─ effective_mode = "strict"
  ├─ if execution_mode == "strict":
  │     └─ standard pipeline (preflight abort si excede)
  └─ if execution_mode == "tiled":
        └─ regional-tiled pipeline
```

**Umbral de auto-detección**: `max_pixels * 0.75` = 150M píxeles. Esto da un margen del 25% antes del límite duro de 200M, evitando edge cases donde un ráster de 199M pasa el check pero consume memoria cercana al límite.

**Rationale**: Resolver antes de cargar evita leer datos innecesarios. El umbral con margen es más seguro que esperar al límite exacto.

**Alternativa considerada**: Auto-detección dentro del preflight de GDAL. Rechazada porque mezclaría routing con validación, violando SRP.

### 3. Conversión de execution_mode a memory_policy

El algoritmo de QGIS traduce el `EXECUTION_MODE` a `memory_policy` antes de crear el `VectorizationRequest`:

| execution_mode | memory_policy resultante |
|---|---|
| `auto` | Se resuelve en el pipeline (auto-detección) |
| `strict` | `strict` |
| `tiled` | `regional-tiles` |

**Rationale**: Mantener la semántica interna de `memory_policy` sin exponer los detalles de implementación en la UI. El usuario ve "modos de ejecución", el sistema usa "políticas de memoria".

### 4. Advertencia cuando strict fuerza un ráster grande

Si el usuario selecciona `strict` y el ráster excede el umbral de auto-detección (150M px), el algoritmo emite un warning en el log de Processing pero **no aborta**. El preflight interno sigue activo como guardrail final.

```
[WARNING] Raster exceeds auto-detection threshold (684M > 150M px).
          Strict mode may fail due to memory pressure.
          Consider switching to 'Tiled' execution mode.
```

**Rationale**: Respetar la decisión del usuario experto sin eliminar las protecciones.

### 5. Logging del modo auto activado

Cuando el modo `auto` selecciona tiled execution, se registra:

```
[INFO] Auto mode: tiled execution activated (684M px exceeds 150M threshold).
       Processing 182 tiles of size 2048x2048.
```

**Rationale**: Trazabilidad. El usuario entiende qué pasó y por qué.

## Risks / Trade-offs

- **[Riesgo]** El umbral de 150M px puede ser demasiado conservador para máquinas con mucha RAM.
  **Mitigación**: El usuario puede forzar `strict` explícitamente si sabe que su máquina lo soporta.

- **[Riesgo]** Confusión entre `execution_mode` (UI) y `memory_policy` (interno).
  **Mitigación**: La traducción es unidireccional y documentada. El usuario nunca ve `memory_policy`.

- **[Riesgo]** El modo `tiled` seleccionado para perfiles no-regionales (edge/linear).
  **Mitigación**: El algoritmo valida y emite error claro: "Tiled mode only supported for regional profile."

- **[Trade-off]** Un parámetro más en la UI aumenta la complejidad visual.
  **Mitigación**: El default `auto` funciona para el 95% de los casos. La mayoría de usuarios no lo tocará.
