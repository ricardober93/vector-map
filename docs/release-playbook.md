# Release Playbook

Este playbook define el flujo mínimo para liberar una versión del MVP estricto.
El objetivo es que cada release sea reproducible, medible y trazable.

## Antes de liberar

1. Confirmar que el alcance sigue limitado al MVP estricto.
2. Verificar que `regional-high-precision` funciona con sus defaults documentados.
3. Correr la baseline de precisión.
4. Confirmar que la salida es válida en QGIS.
5. Revisar que la configuración efectiva quedó registrada.

## Criterio de go/no-go

La release solo avanza si:

- La baseline pasa completa.
- No hay geometrías inválidas finales.
- No hay regresiones respecto de la versión aprobada previa.
- No quedaron tareas abiertas que afecten precisión, exportación o trazabilidad.

## Secuencia de release

1. Congelar el cambio de comportamiento del perfil regional.
2. Ejecutar la baseline sobre el dataset de referencia.
3. Revisar el reporte de métricas.
4. Validar exportación GeoPackage y apertura en QGIS.
5. Generar paquete del plugin.
6. Etiquetar la versión con notas de release.
7. Publicar solo si el resultado es `pass`.

## Checklist de validación

- Entrada raster válida.
- Perfil regional seleccionado.
- Parámetros por defecto documentados.
- Postproceso topológico activo.
- Exportación GIS compatible.
- Trazabilidad de ejecución guardada.

## Manejo de fallas

- Si falla la validación geométrica, no publicar.
- Si sube el error de área o fragmentación, revisar parámetros y volver a correr baseline.
- Si el cambio afecta el contrato del motor, actualizar la documentación antes de liberar.
- Si el reporte no es reproducible, bloquear release hasta corregirlo.

## Qué documentar en cada release

- Qué cambió.
- Qué baseline se usó.
- Qué versión se aprobó.
- Qué limitaciones siguen abiertas.
- Qué queda para MVP+.
