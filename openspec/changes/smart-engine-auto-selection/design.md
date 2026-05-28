## Context

El motor `opencv-local` es significativamente más rápido que `classic-local` para imágenes grandes, especialmente en:
- **Regional**: k-means segmentation con OpenCV es 5-10x más rápido que el classic basado en pure Python
- **Edge**: Canny edge detection con OpenCV es 3-5x más rápido
- **Linear**: skeletonization con OpenCV (`cv2.ximgproc.thinning`) es 2-3x más rápido

Sin embargo, cuando el usuario deja el dropdown en `auto` (el default), el sistema usa `classic-local` porque el perfil tiene `engine_name = "classic-local"` como default.

**Constraints:**
- El dropdown ya tiene opciones `["auto", "classic", "opencv"]`
- Los perfiles ya tienen `engine_name = "classic-local"` como default
- Ambos motores soportan los tres modos (regional, edge, linear)
- El registry ya busca por nombre exacto antes de usar `supports()`

## Goals / Non-Goals

**Goals:**
- El modo `auto` selecciona inteligentemente el mejor motor disponible
- OpenCV se selecciona por defecto cuando está disponible
- Fallback automático a classic si OpenCV falla en runtime
- Logging claro de la decisión del motor

**Non-Goals:**
- No cambiar el comportamiento de `classic` y `opencv` explícitos
- No agregar nuevos motores en esta change
- No cambiar la arquitectura de motores (registry ya existe)

## Decisions

### 1. Modificar `EngineRegistry.resolve()` para manejar `engine_name = "auto"`

El registry busca por nombre exacto. Si `engine_name = "auto"`, debe evaluar la disponibilidad y elegir el mejor.

```python
def resolve(self, profile: Any) -> VectorizationEngine:
    engine_name = getattr(profile, 'engine_name', None)
    if engine_name == "auto":
        return self._resolve_best_available_engine(profile)
    if engine_name:
        for engine in self.engines:
            if engine.name == engine_name:
                return engine
    for engine in self.engines:
        if engine.supports(profile):
            return engine
```

**Rationale**: Centralizar la lógica de selección en el registry, no en cada call site.

### 2. `_resolve_best_available_engine()` selecciona OpenCV si está disponible

```python
def _resolve_best_available_engine(self, profile: Any) -> VectorizationEngine:
    # Check availability and performance characteristics
    for engine in self.engines:
        if engine.name == "opencv-local" and engine.is_available():
            return engine
    # Fallback to classic
    for engine in self.engines:
        if engine.name == "classic-local" and engine.supports(profile):
            return engine
    raise ConfigurationError("No engine available.")
```

**Criterios de selección:**
1. OpenCV disponible → usar OpenCV
2. Solo classic disponible → usar classic
3. Ninguno disponible → error

**Rationale**: OpenCV es más rápido para todos los perfiles. No hay razón para preferir classic por default.

### 3. `OpenCVVectorizationEngine.is_available()` check

```python
@staticmethod
def is_available() -> bool:
    """Check if OpenCV is installed and functional."""
    try:
        import cv2
        return cv2.__version__ is not None
    except Exception:
        return False
```

**Rationale**: Permite verificar disponibilidad sin importar excepciones en el import.

### 4. Actualizar el algoritmo QGIS para pasar `engine_name = "auto"` cuando auto está seleccionado

En `vectorize_image_algorithm.py` línea 514-515:

```python
if engine_name != "auto":
    profile_parameters["engine_name"] = f"{engine_name}-local"
# Si engine_name == "auto", se pasa "auto" literalmente al profile
```

El algoritmo debe pasar `"auto"` al profile parameters cuando el usuario selecciona `auto`:

```python
if engine_name == "auto":
    profile_parameters["engine_name"] = "auto"
```

**Rationale**: Actualmente el código solo setea cuando NO es auto, lo que resulta en que el perfil use su default (`classic-local`). Necesitamos pasar "auto" explícitamente para que el registry lo interprete.

### 5. Logging de selección de motor

Cuando el registry selecciona un motor diferente al default del perfil (ej: auto→opencv), registrar:

```
[INFO] Engine auto mode: selected "opencv-local" (faster than profile default "classic-local")
```

**Rationale**: El usuario debe saber qué motor se usó y por qué.

## Risks / Trade-offs

- **[Riesgo]** OpenCV podría estar disponible pero con una versión más lenta.
  **Mitigación**: Verificar versión mínima (>= 4.8.0) en `is_available()`.

- **[Riesgo]** El fallback a classic podría ser lento en imágenes muy grandes.
  **Mitigación**: Documentar que para imágenes > 100M px se recomienda usar OpenCV explícitamente.

- **[Trade-off]** Cambiar el default de `auto` puede romper tests existentes que asumen `classic`.
  **Mitigación**: Los tests explícitos de `classic` o `opencv` no cambian. Solo `auto` cambia.

## Implementation Plan

1. **OpenCVVectorizationEngine**: agregar método estático `is_available()`
2. **EngineRegistry**: modificar `resolve()` para manejar `"auto"` y agregar `_resolve_best_available_engine()`
3. **VectorizeImageAlgorithm**: pasar `"auto"` cuando el usuario selecciona auto
4. **Tests**: agregar tests para selección automática de motor
5. **Docs**: actualizar `docs/architecture.md` con la lógica de selección de motor