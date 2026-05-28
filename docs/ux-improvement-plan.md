# Plan de Mejoras de UX - Vector Map QGIS Plugin

## Resumen Ejecutivo

Este plan cubres las mejoras de UX identificadas para hacer el plugin más accesible y robusto para usuarios que procesan imágenes gigantes. Se prioriza el impacto en usabilidad vs esfuerzo de implementación.

---

## Mejoras Planificadas

### 🔴 PRIORIDAD ALTA

---

#### MEJORA 1: Validación de tiled+edge/linear

**Descripción:** Implementar la validación que rechaza `tiled` execution mode para perfiles no-regionales (edge/linear).

**Estado actual:**
```python
# vectorize_image_algorithm.py:463-464
def _validate_execution_mode_for_profile(self, execution_mode: str, profile_id: str) -> None:
    pass  # ← Vacío, no valida nada
```

**Estado esperado:**
- Si `execution_mode == "tiled"` Y `profile_id != "regional-high-precision"`
- → Emitir error claro: "Tiled execution mode is only supported for regional-high-precision profile. Please select 'auto' or 'strict' for edge/linear profiles."

**Archivos a modificar:**
- `qgis_vector_map/algorithms/vectorize_image_algorithm.py`

**Tests requeridos:**
- `test_tiled_rejected_for_edge_profile`
- `test_tiled_rejected_for_linear_profile`
- `test_tiled_accepted_for_regional_profile`

**Esfuerzo:** 🟢 Bajo (~30 min)
**Dependencies:** Ninguna

---

#### MEJORA 2: Output Format como dropdown

**Descripción:** Convertir el campo `OUTPUT_FORMAT` (string input) a un `QgsProcessingParameterEnum` con opciones claras.

**Estado actual:**
```python
# String input con default "auto"
QgsProcessingParameterString(
    self.OUTPUT_FORMAT,
    self._tr("Output format"),
    defaultValue="auto",
)
```

**Estado esperado:**
```python
QgsProcessingParameterEnum(
    self.OUTPUT_FORMAT,
    self._tr("Output format"),
    options=["auto", "GeoPackage (.gpkg)", "GeoJSON (.geojson)", "ESRI Shapefile (.shp)"],
    defaultValue=0,  # "auto"
)
```

**Opciones:**
| Index | Value | Comportamiento |
|-------|-------|----------------|
| 0 | `auto` | Detecta según extensión del OUTPUT |
| 1 | `gpkg` | Fuerza GeoPackage |
| 2 | `geojson` | Fuerza GeoJSON |
| 3 | `shp` | Fuerza Shapefile |

**Archivos a modificar:**
- `qgis_vector_map/algorithms/vectorize_image_algorithm.py`

**Tests requeridos:**
- `test_output_format_parses_enum`
- `test_output_format_gpkg_selected`
- `test_output_format_geojson_selected`

**Esfuerzo:** 🟢 Bajo (~20 min)
**Dependencies:** Ninguna

---

#### MEJORA 3: Ocultar parámetros de Canny para perfiles no-edge

**Descripción:** Los parámetros `EDGE_CANNY_LOW`, `EDGE_CANNY_HIGH`, `EDGE_BLUR` solo aplican al perfil `edge-high-precision`. Deben ocultarse para `regional` y `linear`.

**QGIS API approach:**
QGIS Processing no tiene visibilidad condicional nativa como los forms de Qt, pero podemos:
1. Agregar tooltip/help que explique cuándo aplica cada parámetro
2. Usar `QgsProcessingParameter flags` si disponibles
3. En `processAlgorithm`, solo inyectar estos parámetros si el perfil es edge

**Implementación propuesta:**
```python
def _apply_edge_parameters(self, profile_id: str, parameters: dict, context: Any) -> dict:
    """Only inject edge Canny parameters if profile is edge."""
    if profile_id != "edge-high-precision":
        return parameters
    
    # Read and inject edge parameters
    canny_low = self.parameterAsString(parameters, self.EDGE_CANNY_LOW, context)
    # ... etc
```

**Archivos a modificar:**
- `qgis_vector_map/algorithms/vectorize_image_algorithm.py`

**Tests requeridos:**
- `test_edge_params_not_injected_for_regional`
- `test_edge_params_injected_for_edge`

**Esfuerzo:** 🟢 Bajo (~30 min)
**Dependencies:** Ninguna

---

### 🟡 PRIORIDAD MEDIA

---

#### MEJORA 4: Toolbar button + diálogo simplificado

**Descripción:** Agregar un botón en la toolbar de QGIS que abra un diálogo UX-optimized (no el diálogo genérico del Processing Framework).

**Componentes:**
1. **Toolbar button** en `plugin.py`
   - Icono: usar resources/icons o generar SVG simple
   - Tooltip: "Vectorize Image"
   
2. **Diálogo VectorMapDialog** (nuevo)
   - Layout simplificado con parámetros visuales
   - Preview del raster seleccionado
   - Progress bar durante ejecución
   - Botón de cancelar visible

**Estructura de archivos:**
```
qgis_vector_map/
├── ui/
│   ├── __init__.py
│   └── vector_map_dialog.ui  (Qt Designer file)
└── dialog.py  (Python wrapper)
```

**Diálogo propuesto:**

```
┌─────────────────────────────────────────────────────────────┐
│  🗺️ Vector Map - Vectorize Image                       [X] │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  📁 Input Raster     [________________________] [Browse]    │
│                                                             │
│  📋 Profile          [regional-high-precision ▼]           │
│  ⚡ Engine           [auto ▼]                              │
│  🔄 Execution Mode   [auto ▼]                              │
│                                                             │
│  ─── Output ────────────────────────────────────────────   │
│  📦 Output Format   [auto ▼]                               │
│  📝 Layer Name      [vectorized____________]                │
│  💾 Output File     [________________________] [Browse]    │
│                                                             │
│  ─── Advanced (collapsible) ────────────────────────────   │
│  ▶ Show advanced parameters                                │
│                                                             │
│  [Preview raster info: 8192x8192, 67MP, ~150MB]           │
│                                                             │
│                        [Cancel]     [Vectorize ▶]          │
└─────────────────────────────────────────────────────────────┘
```

**Archivos a crear/modificar:**
- `qgis_vector_map/dialog.py` (nuevo)
- `qgis_vector_map/ui/__init__.py` (nuevo)
- `qgis_vector_map/ui/vector_map_dialog.ui` (nuevo, Qt Designer)
- `qgis_vector_map/plugin.py` (modificar)
- `qgis_vector_map/resources.qrc` (actualizar)

**Tests requeridos:**
- `test_dialog_opens`
- `test_dialog_validates_input`
- `test_dialog_runs_vectorization`

**Esfuerzo:** 🟡 Medio (~3-4 horas)
**Dependencies:** Mejora 1, 2 (los parámetros ya deben funcionar)

---

#### MEJORA 5: Estimación de recursos y preview

**Descripción:** Mostrar al usuario información útil antes de ejecutar:
- Tamaño del raster (pixels, MB estimada)
- Número de tiles si execution_mode=auto y raster > umbral
- Tiempo estimado (basado en benchmarks)
- Advertencias si el raster es muy grande

**Implementación:**
```python
def _get_raster_preview_info(self, raster_path: str) -> dict:
    """Get raster metadata for preview."""
    info = {
        "width": 0,
        "height": 0,
        "pixels": 0,
        "estimated_mb": 0,
        "tile_count": None,
        "warnings": [],
    }
    # Use GDAL to get metadata without loading pixels
    # Calculate tile count if > threshold
    return info
```

**UI en diálogo:**
```
┌────────────────────────────────────────┐
│ 📊 Raster Info:                        │
│    Size: 8192 × 8192 (67MP)            │
│    Est. Memory: ~200MB                │
│    Estimated Tiles: 16 (2048px)        │
│    ⚠️ Large raster - auto will use tiles │
└────────────────────────────────────────┘
```

**Archivos a modificar:**
- `qgis_vector_map/dialog.py` (nuevo)

**Tests requeridos:**
- `test_preview_info_calculates_correctly`
- `test_preview_warns_large_raster`

**Esfuerzo:** 🟡 Medio (~2 horas)
**Dependencies:** Mejora 4 (necesita el diálogo)

---

#### MEJORA 6: Smart output layer naming

**Descripción:** Generar nombres de layer más descriptivos por defecto.

**Current:** `"vectorized"` (static)

**Proposed:**
```python
def _generate_default_layer_name(self, profile_id: str) -> str:
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    profile_short = profile_id.replace("-high-precision", "").replace("-", "_")
    return f"vectorized_{profile_short}_{timestamp}"
    # Example: "vectorized_regional_20260528_103145"
```

**Archivo a modificar:**
- `qgis_vector_map/algorithms/vectorize_image_algorithm.py` (línea 395)

**Esfuerzo:** 🟢 Muy bajo (~10 min)
**Dependencies:** Ninguna

---

### 🟢 PRIORIDAD BAJA (Nice to have)

---

#### MEJORA 7: Guardar/cargar presets de parámetros

**Descripción:** Permitir al usuario guardar configuraciones favorites y reutilizarlas.

**JSON schema para presets:**
```json
{
  "name": "High-res Regional",
  "profile": "regional-high-precision",
  "engine": "opencv",
  "execution_mode": "auto",
  "parameters": {
    "max_colors": 12,
    "simplify_tolerance": 0.3,
    "dissolve_adjacent": true
  }
}
```

**UI:** Botón "Save Preset" / Dropdown "Load Preset" en el diálogo

**Esfuerzo:** 🟡 Medio (~2 horas)
**Dependencies:** Mejora 4

---

#### MEJORA 8: Batch processing

**Descripción:** Procesar múltiples imágenes secuencialmente con el mismo perfil.

**UI:**
- Dropzone o file selector múltiple
- Progress bar con contador "Processing 3/10..."
- Resultados consolidados al final

**Esfuerzo:** 🟡 Medio-Alto (~4 horas)
**Dependencies:** Mejora 4, 5

---

#### MEJORA 9: CRS output selector

**Descripción:** Permitir al usuario especificar/confirmar el CRS del layer de salida.

**UI:** Dropdown con opciones comunes + opción de "Same as input raster"

**Esfuerzo:** 🟢 Bajo (~30 min)
**Dependencies:** Ninguna

---

## Roadmap de Implementación

```
Semana 1 (Día 1-2):
├── 🔴 Mejora 1: Validación tiled+edge/linear
├── 🔴 Mejora 2: Output Format dropdown
├── 🔴 Mejora 3: Ocultar Canny params no-edge
└── 🟢 Mejora 6: Smart output naming

Semana 1 (Día 3-5):
└── 🟡 Mejora 4: Toolbar + Dialog básico

Semana 2 (Día 1-3):
└── 🟡 Mejora 5: Preview info + warnings

Semana 2 (Día 4-5):
└── 🟡 Mejora 7: Presets (si hay tiempo)

Post-semana 2:
└── 🟡 Mejoras 8, 9 (batch + CRS selector)
```

---

## Resumen de Archivos

### Archivos a MODIFICAR:

| Archivo | Cambios |
|---------|---------|
| `qgis_vector_map/algorithms/vectorize_image_algorithm.py` | Mejoras 1, 2, 3, 6 |
| `qgis_vector_map/plugin.py` | Mejora 4 (toolbar) |

### Archivos a CREAR:

| Archivo | Descripción |
|---------|-------------|
| `qgis_vector_map/dialog.py` | Wrapper del diálogo Qt |
| `qgis_vector_map/ui/__init__.py` | Package init |
| `qgis_vector_map/ui/vector_map_dialog.ui` | Qt Designer UI file |
| `qgis_vector_map/resources.qrc` | Resource definitions |

### Archivos a CREAR (OpenSpec):

| Archivo | Descripción |
|---------|-------------|
| `openspec/changes/ux-improvements/proposal.md` | Propuesta |
| `openspec/changes/ux-improvements/design.md` | Diseño técnico |
| `openspec/changes/ux-improvements/tasks.md` | Checklist |

---

## Tests a Agregar

Total: ~15 tests nuevos

| Mejora | Tests |
|--------|-------|
| 1 | 3 tests (rechazo tiled para edge/linear) |
| 2 | 3 tests (output format parsing) |
| 3 | 2 tests (edge params filtering) |
| 4 | 3 tests (dialog behavior) |
| 5 | 2 tests (preview info) |
| 6 | 2 tests (naming convention) |

---

## Dependencias Entre Mejoras

```
[Mejora 6] ──┐
             ├──> [Mejora 4] ──> [Mejora 5]
[Mejora 1] ──┤                  │
             │                  └──> [Mejora 7]
[Mejora 2] ──┤                  │
             │                  └──> [Mejora 8]
[Mejora 3] ──┘                  │
                                 └──> [Mejora 9]
```

---

## Notas de Implementación

### Para el diálogo Qt:
1. Usar `QtWidgets.QDialog` como base
2. El archivo `.ui` se genera con Qt Designer
3. `dialog.py` hace el binding con `uic.loadUi()`
4. Conectar signals/slots para botones

### Para la toolbar:
1. Agregar `QAction` en `plugin.py initGui()`
2. Usar icono del recurso o uno simple
3. Conectar al slot que abre el diálogo

### Para el preview:
1. Usar GDAL para metadata (no cargar pixels)
2. `dataset.RasterXSize`, `dataset.RasterYSize`
3. Calcular `estimated_mb = pixels * bands * bytes_per_sample / (1024*1024)`

---

## Decisiones Pendientes

1. **¿Icono del toolbar?** ¿Usar uno existente de QGIS o crear SVG propio?
2. **¿Ubicación de presets?** ¿En el home del usuario (~/.qgis_vector_map/presets/) o en el proyecto?
3. **¿Idioma del diálogo?** ¿Solo español, o i18n con inglés fallback?

---

¿Quieres que empiece con las mejoras de prioridad alta (1, 2, 3, 6)? Son rápidas y establecen la base para el resto.