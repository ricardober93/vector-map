# Arquitectura MVP (sin IA)

## Principios

- Prioridad absoluta: precisión máxima.
- Ejecución local y reproducible.
- Arquitectura modular para escalar motores sin romper contratos.

## Vista de alto nivel

```text
Raster Input
   |
   v
[Preprocess] -> [Vectorization Engine] -> [Topology Cleanup] -> [Export]
                     |
                     +--> Profile: regional-high-precision
                     +--> Profile: edge-high-precision
                     +--> Profile: linear-high-precision
```

## Componentes

1. UI de plugin QGIS
- Selección de imagen, perfil y parámetros.
- Lanzamiento de proceso y visualización de progreso.

2. Processing Provider
- Exposición de algoritmos para toolbox, modeler y batch.

3. Orquestador de pipeline
- Ejecuta etapas secuenciales y maneja errores.

4. Motores de vectorización
- Implementaciones clásicas locales.
- Contrato de entrada/salida común.

### Política de carga raster

- En runtime de QGIS, los archivos raster en disco se cargan con GDAL como ruta preferida.
- Pillow queda como fallback para compatibilidad local cuando GDAL no está disponible o no puede abrir el archivo.
- Antes de leer el arreglo completo con GDAL, se ejecuta un **preflight de memoria** usando metadatos (`RasterXSize`, `RasterYSize`, `RasterCount`).
- Umbrales por defecto del preflight:
  - `max_pixels = 200_000_000`
  - `max_estimated_bytes = 8 GiB`
- `memory_policy` controla el comportamiento operativo:
  - `strict` (default): aplica guardrails y abort temprano.
  - `expert-override`: requiere overrides explícitos de límites y registra advertencia operativa.
  - `regional-tiles`: para `regional-high-precision`, procesa por teselas y consolida salida en una capa única.

### Flujo de Execution Mode

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Execution Mode Decision Flow                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  VectorizationRequest.execution_mode                                │
│          │                                                           │
│          ├─ "auto"  ──► Check raster size (GDAL metadata only)      │
│          │                │                                          │
│          │                ├─ ≤ 150M px  ──► memory_policy = "strict"│
│          │                │                                           │
│          │                └─ > 150M px ──► memory_policy =          │
│          │                               "regional-tiles" (regional)│
│          │                                            │              │
│          │                                            └─ strict      │
│          │                                                (non-      │
│          │                                                 regional) │
│          │                                                           │
│          ├─ "strict" ──► memory_policy = "strict"                   │
│          │                      (con warning si raster > 150M px)    │
│          │                                                           │
│          └─ "tiled" ──► memory_policy = "regional-tiles"             │
│                             (solo para perfil regional)              │
│                                                                      │
│  UI Parameter: execution_mode dropdown (auto/strict/tiled)           │
│  Default: auto                                                       │
│  Auto-detection threshold: max_pixels * 0.75 (150M px default)     │
└─────────────────────────────────────────────────────────────────────┘
```
- Si el preflight supera umbrales en modo `strict`, el proceso aborta temprano con mensaje accionable (recorte AOI, remuestreo, procesamiento por mosaicos), incluyendo recomendaciones cuantitativas (factor de reducción y tamaño objetivo).
- Si GDAL falla con `MemoryError`, el sistema no intenta Pillow para evitar una segunda carga completa en memoria.
- El fallback con Pillow permite hasta `1_000_000_000` píxeles.
- Este ajuste evita el bloqueo temprano por `DecompressionBombError`, pero no cambia el hecho de que el pipeline actual materializa el raster completo en memoria.
- En perfil `regional-high-precision`, la carga GDAL usa lectura por ventanas (`chunk_size` por defecto `2048`) para construir escala de grises de forma incremental.
- En modo `regional-tiles`, cada tesela se vectoriza con el mismo motor y luego se ejecuta limpieza topológica posterior sobre la capa consolidada.

5. Postproceso topológico
- Validación/corrección geométrica.
- Simplificación y limpieza configurable.

6. Exportador GIS
- Salidas compatibles con QGIS (prioridad: GeoPackage).

## Escalabilidad prevista

- Agregar nuevos motores como módulos enchufables.
- Agregar IA como motor opcional en fase posterior, reutilizando el mismo contrato.
- Mantener comparabilidad por perfil mediante métricas y dataset de referencia.
