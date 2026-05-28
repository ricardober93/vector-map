## Context

El plan de UX improvements cubre 4 mejoras de prioridad alta que no requieren cambios en la arquitectura del pipeline:

1. **Validación tiled+edge/linear**: El método `_validate_execution_mode_for_profile` está vacío
2. **Output Format dropdown**: Actualmente es un string input sin opciones
3. **Canny params filtering**: Los parámetros de edge se inyectan para todos los perfiles
4. **Smart naming**: El nombre del layer no tiene contexto

## Decisions

### 1. Validación de tiled+edge/linear

```python
def _validate_execution_mode_for_profile(self, execution_mode: str, profile_id: str) -> None:
    if execution_mode == "tiled" and profile_id != "regional-high-precision":
        raise _QgsProcessingException(
            "Tiled execution mode is only supported for 'regional-high-precision' profile. "
            "For edge/linear profiles, use 'auto' (recommended) or 'strict'."
        )
```

**Rationale**: Error claro y accionable cuando el usuario selecciona mal.

### 2. Output Format dropdown

Cambio de `QgsProcessingParameterString` a `QgsProcessingParameterEnum`:

```python
self.addParameter(
    _QgsProcessingParameterEnum(
        self.OUTPUT_FORMAT,
        self._tr("Output format"),
        options=["auto", "GeoPackage (.gpkg)", "GeoJSON (.geojson)", "ESRI Shapefile (.shp)"],
        defaultValue=0,
    )
)
```

Mapeo en `processAlgorithm`:
| Index | Value | Formato |
|-------|-------|---------|
| 0 | `auto` | Detecta por extensión |
| 1 | `gpkg` | GeoPackage |
| 2 | `geojson` | GeoJSON |
| 3 | `shp` | Shapefile |

**Rationale**: Elimina la ambigüedad del string input.

### 3. Filtrado de parámetros de Canny

Solo inyectar parámetros de Canny cuando el perfil es `edge-high-precision`:

```python
if profile_id == "edge-high-precision":
    canny_low = self.parameterAsString(parameters, self.EDGE_CANNY_LOW, context)
    if canny_low:
        profile_parameters["edge_canny_low"] = canny_low
    # ... etc
```

**Rationale**: Reduce ruido visual y evita confusión.

### 4. Smart output naming

```python
def _generate_default_layer_name(self, profile_id: str) -> str:
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    profile_short = profile_id.replace("-high-precision", "").replace("-", "_")
    return f"vectorized_{profile_short}_{timestamp}"
    # Example: "vectorized_regional_20260528_103145"
```

**Rationale**: Nombres únicos y descriptivos facilitan identificar resultados.

## Risks / Trade-offs

- **[Riesgo]** El dropdown de output format requiere cambiar cómo se parsea
  **Mitigación**: Mantener compatibilidad con valores string para APIs externas

- **[Trade-off]** El smart naming genera nombres largos
  **Mitigación**: El timestamp ayuda a identificar ejecuciones únicas