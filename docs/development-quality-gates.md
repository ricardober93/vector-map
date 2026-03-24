# Development Quality Gates

Este documento define el rollout de calidad estática para desarrollo local y CI.

## Herramientas

- `pre-commit` para ejecutar hooks locales reproducibles.
- `ruff` y `ruff-format` para lint/format.
- `pyright` + `qgis-stubs` + `PyQt5-stubs` para tipado de código PyQGIS.

## Flujo local

1. Instalar dependencias:

```bash
python3 -m pip install -r requirements-dev.txt
```

2. Instalar hooks:

```bash
python3 -m pre_commit install
python3 -m pre_commit install --hook-type pre-push
```

3. Validar manualmente antes de push:

```bash
python3 -m pre_commit run --all-files
python3 -m pre_commit run --all-files --hook-stage pre-push
```

## Política de bloqueo

- `pre-commit` bloquea commits cuando fallan checks de higiene/lint/formato.
- `pre-push` bloquea pushes cuando falla `pyright`.
- CI ejecuta ambos stages (`pre-commit` y `pre-push`) para mantener paridad local/CI.

## Baseline inicial de Pyright

Fecha de baseline inicial: 2026-03-24.

Comando:

```bash
python3 -m pre_commit run --all-files --hook-stage pre-push
```

Resultado inicial antes de corregir deuda:

- 14 errores de imports (`qgis.core` y `PyQt5.QtCore`) en:
  - `qgis_vector_map/algorithms/vectorize_image_algorithm.py`
  - `qgis_vector_map/background.py`
  - `qgis_vector_map/plugin.py`
  - `qgis_vector_map/provider.py`

Estado luego de la corrección de deuda:

- `pyright`: 0 errores, 0 warnings.
- Severidad elevada a `typeCheckingMode = "standard"` en `pyproject.toml`.

## Alcance faseado

Para evitar romper el repo por deuda histórica de lint fuera del scope de este cambio:

- hooks de `ruff`/`ruff-format` están acotados a módulos críticos del plugin:
  - `qgis_vector_map/algorithms/vectorize_image_algorithm.py`
  - `qgis_vector_map/background.py`
  - `qgis_vector_map/plugin.py`
  - `qgis_vector_map/provider.py`
  - `qgis_vector_map/core/raster.py`
  - `qgis_vector_map/engines/base.py`
  - `qgis_vector_map/engines/classic.py`
