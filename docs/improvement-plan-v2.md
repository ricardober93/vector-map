# Vector Map — Plan de Mejora v2

## Resumen

Este plan aborda dos problemas core: **algoritmos de vectorización lentos** y **manejo deficiente de imágenes grandes**. Se introduce OpenCV como engine alternativo, se moderniza la representación interna de rasters a numpy, y se implementa tiled processing real.

**Compatibilidad**: El engine clásico (`classic-local`) permanece intacto. Todos los cambios son aditivos.

---

## Fase 1 — Infraestructura numpy en RasterFrame

**Items:** #8, #10

### 1.1 Convertir representación interna a numpy

**Archivo:** `core/raster.py`

- Reemplazar `pixels: tuple[tuple[Pixel, ...], ...]` por `_array: numpy.ndarray` (uint8 para 1 banda, uint8 shape (H,W,3) para RGB)
- Mantener `pixels` como `@property` que convierte on-demand para backward compatibility
- Añadir `_bands: int` private, exponer vía `.bands` existente
- Constructor `__init__` acepta tanto ndarray como las secuencias actuales

```python
class RasterFrame:
    def __init__(self, pixels, width, height, bands, source_name=None, metadata=None):
        if isinstance(pixels, numpy.ndarray):
            self._array = pixels
        else:
            self._array = numpy.array(pixels, dtype=numpy.uint8)
        # ... rest same

    @property
    def pixels(self):
        """Backward-compatible pixel access. Avoid in hot paths."""
        return tuple(tuple(row) for row in self._array)
```

### 1.2 Grayscale sin duplicación

**Archivo:** `core/raster.py`

- `grayscale_matrix()` → si `bands == 1`, retornar `self._array` directamente (view, no copia)
- Si `bands > 1`, usar `cv2.cvtColor` o `numpy.dot` para convertir en una pasada
- Eliminar la conversión pixel-a-pixel actual

### 1.3 GDAL load ya en grayscale cuando sea posible

**Archivo:** `core/raster.py` — `_load_with_gdal`

- Si `profile_mode == "regional"` y dataset tiene 1 banda, almacenar el array directo de `ReadAsArray`
- Si multibanda, convertir a grayscale en el momento de carga usando GDAL band math, no post-carga

### 1.4 Tests para RasterFrame numpy

**Archivo:** `tests/test_raster.py`

- Verificar que `pixels` property retorna mismos valores que antes
- Verificar que `grayscale_matrix()` no copia cuando band=1
- Verificar conversión RGB→grayscale consistente
- Tests existentes no deben romperse

---

## Fase 2 — Engine OpenCV

**Items:** #1, #2, #3, #4, #5, #6, #7, #14, #16

### 2.1 Crear engine OpenCV

**Archivo nuevo:** `engines/opencv.py`

```python
class OpenCVVectorizationEngine(VectorizationEngine):
    name = "opencv-local"
    supported_modes = ("regional", "edge", "linear")
```

Implementar los 4 stages usando OpenCV:

#### Regional profile
- **Preprocess:** `cv2.kmeans` (#16) para cuantización de colores → label map
- **Vectorize:** `cv2.findContours` (#5) con jerarquía exterior/hole
- **Postprocess:** `cv2.approxPolyDP` (#6) para simplificación, filtro por área
- **Export:** Reutilizar `export_vector_layer` existente

#### Edge profile
- **Preprocess:** `cv2.cvtColor` + `cv2.Canny` (#2) → binarización
- **Vectorize:** `cv2.findContours` (#5) → LineStrings
- **Postprocess:** `cv2.approxPolyDP` (#6), filtro por largo

#### Linear profile
- **Preprocess:** `cv2.threshold` (#2) + `cv2.morphologyEx` (#4) + `cv2.ximgproc.thinning` (#1)
- **Vectorize:** `cv2.findContours` (#5) o tracer sobre skeleton
- **Postprocess:** `cv2.approxPolyDP` (#6), filtro por largo

### 2.2 Progreso granular (#15)

**Archivo:** `engines/opencv.py`

- Para `cv2.findContours`: no es directamente interrumpible, pero se puede:
  - Dividir imagen en strips horizontales antes de llamar contours
  - Reportar progreso por strip al `progress_callback`
  - Unir features con offset de coordenadas (similar al tiled pipeline actual)
- Para `cv2.Canny`: strip-based progress similar

### 2.3 Registro condicional del engine (#7, #14)

**Archivo:** `engines/base.py` — `build_default_registry()`

```python
def build_default_registry() -> EngineRegistry:
    if not _DEFAULT_REGISTRY.engines:
        from .classic import ClassicVectorizationEngine
        _DEFAULT_REGISTRY.register(ClassicVectorizationEngine())

        try:
            from .opencv import OpenCVVectorizationEngine
            _DEFAULT_REGISTRY.register(OpenCVVectorizationEngine())
        except ImportError:
            pass  # OpenCV not available, classic-only mode

    return _DEFAULT_REGISTRY
```

**Archivo:** `requirements-dev.txt` — agregar `opencv-python-headless` como dependencia opcional

### 2.4 Tests del engine OpenCV

**Archivo nuevo:** `tests/test_opencv_engine.py`

- Test paramétrico: para cada input pequeño, comparar output OpenCV vs Classic
  - No deben ser idénticos (algoritmos diferentes), pero:
    - Mismo número de features (± tolerancia)
    - Mismos geometry types
    - Áreas/largos similares (± 10%)
- Test con imagen grande (sintética): verificar que completa en <5s
- Test graceful fallback cuando cv2 no está disponible

---

## Fase 3 — Tiled Processing Real

**Items:** #9, #11

### 3.1 True tiled en raster loading

**Archivo:** `core/raster.py` — nueva método `iter_regional_chunks`

Actual: `_load_regional_with_gdal_chunks` acumula todos los chunks en `rows: list[tuple[int, ...]]`
Nuevo: context manager / generator que yield chunks y permite procesar y liberar:

```python
@classmethod
def iter_regional_chunks(cls, *, dataset, path, chunk_size, width, height, bands):
    """Generator that yields (y_offset, numpy_chunk_array) tuples."""
    for y_off in range(0, height, chunk_size):
        y_size = min(chunk_size, height - y_off)
        window = dataset.ReadAsArray(0, y_off, width, y_size)
        yield y_off, cls._window_to_grayscale_ndarray(window, width, y_size)
```

### 3.2 Actualizar pipeline tiled para usar chunks como generator

**Archivo:** `core/pipeline.py` — `_run_regional_tiled_pipeline`

- Usar `RasterFrame.iter_regional_chunks` en vez de `_load_regional_with_gdal_chunks`
- Cada chunk se procesa → vectoriza → features se acumulan → chunk se libera
- El RasterFrame del context es placeholder minimal (metadata only)

### 3.3 Subir límites de memoria (#11)

**Archivo:** `processing_profiles.py`

```python
# Antes
DEFAULT_MAX_PIXELS = 200_000_000        # 200MP
DEFAULT_MAX_ESTIMATED_BYTES = 8 * 1024**3  # 8GB

# Después
DEFAULT_MAX_PIXELS = 500_000_000        # 500MP
DEFAULT_MAX_ESTIMATED_BYTES = 16 * 1024**3  # 16GB
```

Y en los profiles, hacerlos configurables via parámetro sin requerir `expert-override`.

### 3.4 Tests de tiled real

**Archivo:** `tests/test_pipeline.py`

- Test que imagen 10K×10K no carga todo en memoria (verificar peak memory < umbral)
- Test que tiled + opencv produce features correctos con coordenadas offset
- Test cancel_callback interrumpe entre tiles

---

## Fase 4 — Optimización del engine clásico (shapely)

**Items:** #12

### 4.1 Shapely como acelerador selectivo

**Archivo:** `core/geometry.py`

- Agregar `_shapely_available` flag al import
- `point_in_polygon` → usar `shapely.prepared.prep(polygon).contains(point)` si disponible
- `polygon_area` → usar `shapely.Polygon(ring).area` si disponible
- `simplify_path` → usar `shapely.LineString(points).simplify(tolerance)` si disponible
- Fallback a implementación pure-Python actual si shapely no está instalado

### 4.2 Tests

**Archivo:** `tests/test_geometry.py` (nuevo)

- Verificar que resultados shapely == pure-Python para inputs pequeños
- Verificar que fallback funciona sin shapely

---

## Fase 5 — Integración y profiles

**Items:** #13

### 5.1 Profiles para engine OpenCV

**Archivo:** `processing_profiles.py`

No se necesitan profiles nuevos — los existentes funcionan con ambos engines. Se agrega soporte para seleccionar engine via parámetro:

```python
# El usuario puede pasar:
{"engine_name": "opencv"}
# o dejar vacío para usar el primero disponible (classic → opencv)
```

### 5.2 Actualizar algoritmo QGIS

**Archivo:** `algorithms/vectorize_image_algorithm.py`

- Agregar parámetro `ENGINE` (enum) en `initAlgorithm` con opciones:
  - `auto` (default) — usa OpenCV si disponible, si no classic
  - `classic` — fuerza engine clásico
  - `opencv` — fuerza engine OpenCV (falla si no disponible)

### 5.3 Backward compatibility (#13)

- Todos los tests existentes deben seguir pasando sin cambios
- El engine clásico no se modifica en absoluto en las fases 1-4
- Fase 2 es un archivo nuevo (`engines/opencv.py`)
- Fase 4 es opt-in (shapely)

---

## Orden de ejecución

| Fase | Items | Estimación | Dependencias |
|------|-------|-----------|--------------|
| 1 | #8, #10 | 2-3h | Ninguna |
| 2 | #1-7, #14, #16 | 4-6h | Fase 1 (numpy RasterFrame) |
| 3 | #9, #11 | 2-3h | Fase 1 (numpy chunks) |
| 4 | #12 | 1-2h | Ninguna |
| 5 | #13 | 1-2h | Fases 1-4 |

**Total estimado:** ~10-16h de desarrollo

---

## Resultado esperado

| Métrica | Antes | Después |
|---------|-------|---------|
| Tiempo vectorización 5K×5K | ~30-120s | ~1-5s (OpenCV) |
| Tiempo vectorización 10K×10K | ~minutos-horas | ~3-15s (OpenCV) |
| Memory peak imagen 20K×20K | ~3.2GB (tuples) | ~400MB (numpy) |
| Límite preflight | 200MP / 8GB | 500MP / 16GB |
| Tiled processing | Acumula todo | True tile-and-discard |
| Regresión tests | Baseline (15 pass) | 15+ pass (sin cambios) |
