## Context

El plugin corre con fallback sin QGIS instalado, pero falta control de tipos/imports en desarrollo.

## Goals / Non-Goals

**Goals**
- Bloquear commits con fallas de lint/tipado.
- Resolver `qgis.core` para type checking con stubs.
- Mantener flujo local reproducible.

**Non-Goals**
- No cambiar lógica de vectorización.
- No alterar baseline de precisión ni contratos de perfiles.

## Decisions

1. Usar `pre-commit` como gate principal local.
2. Usar Pyright (alineado con error de Pylance) + `qgis-stubs`.
3. Ejecutar ruff en `pre-commit`; pyright en `pre-push` o CI mientras se limpia deuda inicial.
4. Unificar criterio en CI con `pre-commit run --all-files`.

## Risks / Trade-offs

- Pyright puede fallar por deuda existente (ya detectada).
- Primer run más lento por bootstrap de entornos.
- Mitigación: rollout por fases + cache de pre-commit en CI.

## Migration Plan

1. Configurar tooling.
2. Habilitar gate sin romper pipeline.
3. Corregir deuda de tipos.
4. Endurecer regla (ratchet) cuando el baseline quede limpio.
