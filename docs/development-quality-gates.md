# Development Quality Gates

Este documento define el rollout de calidad estática para desarrollo local y CI.

## Herramientas

- `pre-commit` para ejecutar hooks locales reproducibles.
- `ruff` y `ruff-format` para lint/format.
- `pyright` + `qgis-stubs` + `PyQt5-stubs` para tipado de código PyQGIS.

## Flujo local

1. Crear y activar entorno virtual local del proyecto:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Si `python3` no resuelve a Python 3.11 en tu entorno, usa `python3.11 -m venv .venv`.

2. Instalar dependencias:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

3. Validar toolchain base:

```bash
python -m pre_commit --version
python -m pyright --version
python scripts/evaluate_regional_profile.py \
  data/reference/sample_runs/regional_pass.json \
  --baseline data/reference/baseline_thresholds.json
```

4. Instalar hooks:

```bash
python -m pre_commit install
python -m pre_commit install --hook-type pre-push
```

5. Validar manualmente antes de push:

```bash
python -m pre_commit run --all-files
python -m pre_commit run --all-files --hook-stage pre-push
```

## Política de bloqueo

- `pre-commit` bloquea commits cuando fallan checks de higiene/lint/formato.
- `pre-push` bloquea pushes cuando falla `pyright`.
- CI ejecuta ambos stages (`pre-commit` y `pre-push`) para mantener paridad local/CI.

## Baseline inicial de Pyright

Fecha de baseline inicial: 2026-03-24.

Comando:

```bash
python -m pre_commit run --all-files --hook-stage pre-push
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
