# AGENTS

Guía rápida para cualquier agente o colaborador que trabaje en este repositorio.

## Fuente de verdad

- Antes de cambiar código, revisar primero la carpeta [`docs/`](./docs).
- Documentos clave:
  - `docs/architecture.md`
  - `docs/mvp-strict-usage.md`
  - `docs/precision-baseline.md`
  - `docs/release-playbook.md`
  - `docs/roadmap-mvp-plus.md`

## Alcance técnico actual

- Plugin QGIS en `qgis_vector_map/`.
- Algoritmo principal: `qgis_vector_map/algorithms/vectorize_image_algorithm.py`.
- Proveedor Processing: `qgis_vector_map/provider.py`.
- Evaluación de precisión: `scripts/evaluate_regional_profile.py`.

## Build del plugin QGIS

1. Instalar dependencias de desarrollo:
   - `python3 -m pip install -r requirements-dev.txt`
2. Bump de versión (SemVer) sincronizado en `qgis_vector_map/metadata.txt` y `qgis_vector_map/__init__.py`.
3. Empaquetar plugin en `dist/`:
   - `mkdir -p dist && qgis-plugin-ci package <VERSIÓN> && mv qgis_vector_map.<VERSIÓN>.zip dist/`
4. Validar baseline de precisión:
   - `python3 scripts/evaluate_regional_profile.py data/reference/sample_runs/regional_pass.json --baseline data/reference/baseline_thresholds.json`

## Reglas de trabajo

- Mantener compatibilidad local (sin dependencias cloud obligatorias).
- Priorizar precisión y reproducibilidad.
- No romper contratos de perfiles (`regional`, `edge`, `linear`).
- Si cambias comportamiento esperado, actualizar `docs/` y OpenSpec specs.
- Toda versión publicada debe cumplir SemVer (`MAJOR.MINOR.PATCH`) y mantenerse sincronizada entre `qgis_vector_map/metadata.txt` y `qgis_vector_map/__init__.py`.
