## Why

Necesitamos un plugin de QGIS para vectorizar imágenes de forma local, con enfoque generalista y máxima precisión, porque hoy el flujo está fragmentado y depende de procesos manuales difíciles de repetir. Es prioritario crear una base técnica controlable (sin IA en el MVP) que permita escalar luego a múltiples métodos, incluyendo IA al final.

## What Changes

- Crear un plugin de QGIS orientado a vectorización de imágenes raster hacia capas vectoriales útiles en proyectos GIS.
- Implementar un motor clásico modular y local (sin servicios cloud) con pipeline de preproceso, vectorización y postproceso topológico.
- Exponer la funcionalidad como proveedor de Processing en QGIS para habilitar toolbox, batch y modeler.
- Definir perfiles de vectorización para distintos tipos de imagen (generalista por regiones, bordes/planos, lineal) con prioridad en precisión.
- Incorporar un marco de evaluación de calidad (dataset de referencia + métricas) para medir precisión y evitar regresiones.
- Dejar preparada la arquitectura para añadir motores alternos en el futuro, incluyendo IA como etapa posterior al MVP.

## Capabilities

### New Capabilities
- `local-image-vectorization`: Vectorización local raster->vector con pipeline configurable y salida geoespacial válida en QGIS.
- `vectorization-profiles`: Perfiles de vectorización de alta precisión para distintos patrones visuales (regiones, bordes, líneas).

### Modified Capabilities
- Ninguna (no existen capacidades previas en este repositorio).

## Impact

- Código afectado: nuevo plugin QGIS en Python con proveedor de Processing y estructura modular de motores.
- Dependencias técnicas esperadas: stack geoespacial local (QGIS/GDAL) y librerías opcionales de procesamiento clásico en CPU local.
- Impacto de producto: habilita vectorización repetible, auditable y más precisa para múltiples casos de uso.
- Impacto operativo: requiere política de pruebas con imágenes de referencia y criterios de aceptación por precisión.
