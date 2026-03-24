## Why

El repo hoy no tiene `pre-commit` ni chequeo de tipos, y los imports de `qgis.core` generan errores de resolución en tooling estático. Esto permite que errores de calidad lleguen a build/CI.

## What Changes

- Agregar gate local con `pre-commit` (ruff + pyright).
- Adoptar `qgis-stubs` para resolver tipado de `qgis.core` en análisis estático.
- Alinear CI con la misma política de checks.
- Documentar flujo de desarrollo para instalar y correr hooks.

## Capabilities

### New Capabilities

- `development-quality-gates`: Validación automática local/CI de lint + tipado.

### Modified Capabilities

- Ninguna funcional del plugin (sin cambios en contratos `regional`, `edge`, `linear`).

## Impact

- Código afectado: configuración de tooling (`.pre-commit-config.yaml`, `pyproject.toml`, `requirements-dev.txt`, CI, docs).
- Riesgo: pyright actualmente reporta errores existentes; adopción debe ser faseada.
