# Vector Map

Vector Map is a QGIS plugin for local raster-to-vector processing focused on
high-precision profiles and reproducible outputs.

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

## Quick checks

```bash
python3 -m compileall qgis_vector_map scripts
python3 scripts/evaluate_regional_profile.py \
  data/reference/sample_runs/regional_pass.json \
  --baseline data/reference/baseline_thresholds.json
python3 scripts/compare_profile_runs.py \
  data/reference/sample_runs/profiles_comparison.json
```
