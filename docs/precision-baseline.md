# Baseline de Precisión

Este documento define la referencia mínima de calidad para aprobar el MVP estricto.
La baseline aplica al perfil `regional-high-precision`.

## Dataset de referencia

La evaluación debe correr sobre un conjunto pequeño pero representativo de escenas raster:

- Casos de regiones amplias y homogéneas.
- Casos con bordes irregulares.
- Casos con ruido moderado.
- Casos con huecos internos y discontinuidades.
- Casos con escala y contraste distintos.

La baseline debe mantenerse fija para evitar comparaciones sesgadas entre versiones.

## Métricas base

Medir, como mínimo:

- Validez geométrica de la salida.
- Cobertura espacial respecto a la referencia.
- Error de área relativo.
- Preservación de contornos.
- Tasa de objetos omitidos o fragmentados.

## Criterios de aceptación iniciales

Un build del MVP estricto pasa la baseline si cumple todo lo siguiente:

- 100% de las salidas principales quedan geométricamente válidas después del postproceso.
- No hay errores de ejecución en el dataset de referencia.
- El error de área medio se mantiene en un rango aceptable para uso GIS generalista.
- La cobertura y los contornos no muestran regresiones materiales frente a la versión base aprobada.
- No se introducen artefactos topológicos graves, como self-intersections o polígonos corruptos.

## Umbrales operativos

Usar estos umbrales iniciales para aprobar o bloquear releases:

- Error de área medio: <= 10%.
- Objetos omitidos: <= 5% sobre el dataset de referencia.
- Objetos fragmentados por rasterización o limpieza: <= 5%.
- Geometrías inválidas finales: 0.

Si un caso supera cualquiera de estos límites, la release queda bloqueada hasta revisar el cambio.

## Salida del reporte

Cada corrida de baseline debe registrar:

- Versión del plugin.
- Perfil usado.
- Parámetros efectivos.
- Tamaño del dataset.
- Métricas por caso.
- Resultado final: `pass` o `fail`.

## Regla de gobernanza

La baseline no se ajusta para justificar una regresión puntual.
Si cambian los umbrales, la decisión debe quedar registrada como nueva baseline aprobada.

