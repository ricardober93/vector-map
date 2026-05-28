## Why

El plugin Vector Map tiene varios problemas de UX identificados que afectan la usabilidad, especialmente para usuarios que procesan imágenes gigantes:

1. **Validación incompleta**: El modo `tiled` no se valida para perfiles no-regionales
2. **Output Format confuso**: Campo string con solo "auto" disponible
3. **Parámetros confusos**: Los parámetros de Canny se muestran para todos los perfiles aunque solo aplican a `edge`
4. **Naming sin contexto**: El nombre del layer de salida es siempre "vectorized" sin información del perfil o timestamp

## What Changes

- **MEJORA 1**: Validación estricta de `tiled` execution mode para perfiles edge/linear
- **MEJORA 2**: Output Format como dropdown con opciones claras (auto, GeoPackage, GeoJSON, Shapefile)
- **MEJORA 3**: Parámetros de Canny solo inyectados para perfil edge
- **MEJORA 6**: Smart output naming con timestamp y perfil

## Capabilities

### New Capabilities

- `ux-output-format-dropdown`: Output format expuesto como enum con opciones claras
- `ux-smart-naming`: Nombre de layer de salida incluye perfil y timestamp

### Modified Capabilities

- `validation-rules`: Nueva validación tiled+edge/linear
- `local-image-vectorization`: Parámetros de Canny filtrados por perfil

## Impact

- **Código afectado**:
  - `qgis_vector_map/algorithms/vectorize_image_algorithm.py`
- **Pruebas afectadas**: Nuevos tests unitarios
- **Breaking**: No. Cambios backward-compatible.