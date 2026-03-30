## Context

El cambio `raster-memory-guardrails-and-regional-chunking` resolvió correctamente el fallo tardío por memoria con abort temprano, pero para ortomosaicos grandes el usuario aún debe salir del algoritmo para preparar AOI/teselas/remuestreo manualmente. Esto genera fricción operativa y dificulta estandarizar ejecuciones reproducibles en equipos.

El repositorio prioriza precisión y ejecución local, por lo que cualquier mejora debe:
- conservar defaults conservadores;
- no romper contratos de perfiles (`regional`, `edge`, `linear`);
- mantener trazabilidad de parámetros efectivos.

## Goals / Non-Goals

**Goals:**
- Mantener el comportamiento actual como default seguro.
- Permitir un modo explícito para escenas grandes sin cambiar el contrato externo de Processing.
- Reducir trial-and-error del usuario con recomendaciones de preflight cuantitativas.
- Introducir procesamiento regional por teselas con salida única reproducible.

**Non-Goals:**
- No rediseñar motores `edge` y `linear` para streaming completo.
- No reemplazar toda la arquitectura raster por ejecución out-of-core general.
- No relajar globalmente guardrails por defecto del MVP.

## Decisions

1. **Nueva política explícita de memoria (`memory_policy`)**
   - Valores propuestos:
     - `strict` (default): comportamiento actual.
     - `expert-override`: permite exceder umbral de píxeles bajo parámetros explícitos del usuario.
     - `regional-tiles`: activa estrategia de teselado para `regional-high-precision`.
   - Rationale (KISS + SRP): separar política operativa del mecanismo de lectura evita condicionales dispersos y conserva un flujo por defecto simple.

2. **Preflight con recomendaciones numéricas**
   - Extender el mensaje de abort para incluir:
     - factor mínimo de reducción lineal;
     - dimensión objetivo aproximada para cumplir `max_pixels`;
     - sugerencia de número de teselas según `chunk_size` o tamaño de tile.
   - Rationale: mejora UX sin cambiar semántica de guardrails.

3. **Estrategia de teselado para perfil regional**
   - Implementar mediante composición:
     - `RasterLoadStrategy` (strict vs tiled),
     - `TileVectorizationRunner`,
     - `TileMergeStage`.
   - Rationale (composition over inheritance): encapsular cada responsabilidad facilita pruebas aisladas y rollback parcial.

4. **Trazabilidad reforzada en metadata**
   - Registrar política usada, tamaño de tesela, conteo de teselas y estadísticas por tesela.
   - Rationale: reproducibilidad y soporte post-mortem.

## Risks / Trade-offs

- **[Riesgo]** Mayor tiempo de ejecución en modo teselado.
  **Mitigación**: activar solo bajo `memory_policy=regional-tiles` y documentar costo esperado.

- **[Riesgo]** Inconsistencias geométricas en bordes de tesela.
  **Mitigación**: introducir solape configurable y etapa de post-merge topológico.

- **[Riesgo]** Uso inapropiado del modo experto.
  **Mitigación**: mantener `strict` como default, validar overrides y emitir advertencia explícita en logs/reportes.

- **[Riesgo]** Complejidad incremental en pipeline.
  **Mitigación**: aplicar Rule of Three y limitar abstracciones a componentes donde ya existen al menos tres puntos de variación (preflight, load strategy, run mode).

## Migration Plan

1. Agregar nuevos parámetros con defaults backward-compatible.
2. Implementar flujo `strict` sin cambios funcionales.
3. Implementar flujo `regional-tiles` detrás de bandera de política.
4. Activar pruebas de regresión de precisión y memoria.
5. Actualizar documentación operativa y baseline esperado.
6. Habilitar adopción gradual en entornos reales.

Rollback:
- Revertir a `memory_policy=strict` para todos los perfiles.
- Mantener disponibles guardrails previos sin pérdida de compatibilidad.

## Open Questions

- ¿Cuál tamaño de tesela por defecto optimiza mejor precisión/tiempo para ortomosaicos RGB/RGBA?
- ¿El merge debe disolver por clase/color antes o después de la limpieza topológica global?
- ¿Debemos bloquear `expert-override` cuando la estimación exceda un límite duro absoluto (por ejemplo, 16 GiB)?
