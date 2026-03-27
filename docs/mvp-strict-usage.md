# Uso Estricto del MVP

Este documento describe el uso operativo del MVP inicial del plugin QGIS Vector Map.
El alcance es solo el perfil `regional-high-precision`.

## Qué hace este perfil

`regional-high-precision` procesa un raster local, segmenta por regiones, vectoriza polígonos y ejecuta limpieza topológica antes de exportar.
Está pensado para casos generales donde la prioridad es precisión y trazabilidad, no velocidad máxima.

## Cómo ejecutarlo

1. Abrir el plugin en QGIS.
2. Seleccionar la imagen raster de entrada.
3. Elegir el perfil `regional-high-precision`.
4. Dejar los parámetros por defecto salvo que exista una razón clara para ajustar.
5. Ejecutar el proceso y revisar el reporte de salida.
6. Validar que el resultado exportado sea geométricamente válido antes de usarlo aguas abajo.

## Parámetros por defecto

Usar estos valores como punto de partida:

- `profile`: `regional-high-precision`
- `band`: `auto` o banda principal de intensidad
- `threshold`: `adaptive`
- `smoothing`: `medium`
- `min_region_area`: `small`
- `hole_filling`: `enabled`
- `topology_cleanup`: `enabled`
- `simplification`: `disabled` por defecto
- `output_format`: `GeoPackage`
- `background_execution`: `enabled`

## Cuándo ajustar parámetros

- Si el raster tiene ruido fuerte, subir `smoothing`.
- Si aparecen regiones fragmentadas, activar o reforzar `hole_filling` y limpieza topológica.
- Si la imagen tiene mucho detalle fino, reducir el nivel de suavizado con cuidado.
- Si hay pérdida de precisión visible, no aplicar simplificación automática.

## Límites del MVP estricto

- No incluye IA.
- No está optimizado para tiempo de ejecución agresivo.
- No cubre todavía flujos de bordes o líneas como perfiles propios.
- No debe usarse sin revisar la validez geométrica del resultado.
- No es una herramienta de edición manual; la salida debe tratarse como resultado de procesamiento reproducible.
- Para rásteres muy grandes, QGIS prioriza GDAL al cargar el archivo. El fallback con Pillow admite hasta `1_000_000_000` píxeles, pero la ejecución puede seguir siendo intensiva en memoria porque el pipeline actual carga la imagen completa.

## Reglas de uso

- Mantener la misma entrada y los mismos parámetros cuando se quiera comparar resultados.
- Registrar la configuración efectiva de cada ejecución.
- Bloquear cambios de parámetros que reduzcan precisión sin una justificación de baseline.
- Usar este perfil como referencia principal para releases del MVP estricto.
