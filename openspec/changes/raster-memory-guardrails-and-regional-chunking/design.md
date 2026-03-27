## Context

El runtime de QGIS prioriza GDAL para rásteres en disco, pero la lectura completa (`ReadAsArray`) puede disparar `MemoryError` en escenas de alta resolución. El fallback a Pillow no es efectivo en ese escenario porque también implica carga completa.

## Goals / Non-Goals

**Goals**
- Fallar temprano y de forma accionable cuando el ráster es inviable por memoria.
- Evitar fallback redundante tras `MemoryError` en GDAL.
- Reducir presión de memoria en perfil regional con lectura por ventanas.

**Non-Goals**
- No rediseñar todavía `edge` y `linear` para streaming.
- No cambiar el contrato externo del algoritmo Processing de QGIS.

## Decisions

1. Preflight GDAL con defaults:
   - `max_pixels=200_000_000`
   - `max_estimated_bytes=8 GiB`
2. Si preflight falla: abort temprano con guía (AOI, remuestreo, mosaicos).
3. Si GDAL lanza `MemoryError`: no fallback a Pillow.
4. Perfil regional usa `chunk_size=2048` por defecto para lectura por ventanas y construcción incremental de escala de grises.

## Risks / Trade-offs

- Aunque la lectura por chunks reduce picos, la representación interna sigue en memoria Python para etapas posteriores.
- Hay costo computacional adicional al convertir ventanas a escala de grises por software.

## Validation Plan

1. Pruebas unitarias de preflight sobredimensionado.
2. Pruebas unitarias de skip de Pillow ante `MemoryError`.
3. Pruebas unitarias de lectura regional por ventanas (sin llamada full-array).
