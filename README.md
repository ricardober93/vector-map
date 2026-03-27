# Vector Map

Vector Map is a QGIS plugin for local raster-to-vector processing focused on
high-precision profiles and reproducible outputs.

Compatibility target: **QGIS 3.44+**.

## What is included

- QGIS plugin entry point via `classFactory`
- A `VectorMapPlugin` shell that registers and unregisters a Processing provider
- Processing algorithm `vectorize_image` with 3 profiles:
  - `regional-high-precision`
  - `edge-high-precision`
  - `linear-high-precision`
- Modular pipeline: `preprocess -> vectorize -> postprocess -> export`
- Baseline evaluator script for regression control:
  - `scripts/evaluate_regional_profile.py`
- Comparative evaluator across profiles:
  - `scripts/compare_profile_runs.py`
- Plugin metadata, resources, and SVG icon

## Import safety

The Python package is written to import cleanly even when QGIS is not installed.
That makes it safe to run packaging checks, unit tests, and static analysis in a
regular Python environment.

## Current scope

The repository ships a working local MVP/MVP+ baseline with classic engines.
IA-based vectorization remains intentionally out of scope for this phase.

## File layout

- `qgis_vector_map/__init__.py` - QGIS plugin entry point
- `qgis_vector_map/plugin.py` - plugin lifecycle and provider registration
- `qgis_vector_map/provider.py` - Processing provider and algorithm registration
- `qgis_vector_map/algorithms/vectorize_image_algorithm.py` - Processing algorithm wrapper
- `qgis_vector_map/core/` - contracts, models, raster/geometry/export helpers, orchestrator
- `qgis_vector_map/engines/` - classic local engines for regional/edge/linear profiles
- `qgis_vector_map/metadata.txt` - QGIS plugin metadata
- `qgis_vector_map/resources.qrc` - resource manifest for the plugin icon
- `qgis_vector_map/icon.svg` - plugin icon
- `evaluation/` and `data/reference/` - dataset/baseline templates and sample run

## Next step

Use the docs in `docs/` for strict MVP operation and roadmap to future phases.

## Project bootstrap (.venv)

Use a local virtual environment per project folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

If `python3` is not Python 3.11 on your machine, use `python3.11 -m venv .venv` instead.

Quick post-install validation:

```bash
python -m pre_commit --version
python -m pyright --version
python scripts/evaluate_regional_profile.py \
  data/reference/sample_runs/regional_pass.json \
  --baseline data/reference/baseline_thresholds.json
```

## Quick checks

```bash
python -m compileall qgis_vector_map scripts
python scripts/evaluate_regional_profile.py \
  data/reference/sample_runs/regional_pass.json \
  --baseline data/reference/baseline_thresholds.json
python scripts/compare_profile_runs.py \
  data/reference/sample_runs/profiles_comparison.json
```

## Development quality gates

```bash
python -m pre_commit install
python -m pre_commit install --hook-type pre-push
python -m pre_commit run --all-files
python -m pre_commit run --all-files --hook-stage pre-push
```

Policy:
- `pre-commit`: higiene + ruff/format.
- `pre-push`: pyright con `qgis-stubs` para bloquear errores de tipado/imports.

## Processing notes (QGIS 3.44+)

- `INPUT` uses `QgsProcessingParameterRasterLayer` (typed raster input).
- `OUTPUT` uses `QgsProcessingParameterVectorDestination` (typed vector output).
- Provider logs are emitted under `Log Messages > Plugins` with tag `Vector Map`.
- Technical references and benchmark notes are tracked in:
  - `docs/processing-provider-benchmark.md`

## Build e instalacion del plugin (macOS)

Paso a paso:

1. Dar permisos de ejecucion al script (solo la primera vez):

```bash
chmod +x scripts/build_and_install_qgis_plugin.sh
```

2. Ejecutar build + instalacion:

```bash
./scripts/build_and_install_qgis_plugin.sh
```

3. Verificar resultado:
- ZIP generado en `dist/qgis_vector_map-<version>.zip`
- Plugin instalado en:
  `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/qgis_vector_map`

4. Abrir QGIS y recargar el plugin:
- `Plugins > Manage and Install Plugins`
- Activar `Vector Map` (o desactivar/activar para recargar cambios)
