# vectorization-profiles Specification

## Purpose
TBD - created by archiving change mvp-vectorizacion-imagenes-qgis. Update Purpose after archive.
## Requirements
### Requirement: Perfiles de vectorización orientados a precisión
El sistema SHALL ofrecer perfiles de vectorización predefinidos para casos de regiones, bordes y líneas, optimizados para máxima precisión sobre velocidad.

#### Scenario: Selección de perfil de regiones
- **WHEN** el usuario elige el perfil de regiones
- **THEN** el sistema aplica un pipeline enfocado en segmentación por regiones y polygonización de alta precisión

#### Scenario: Selección de perfil de bordes
- **WHEN** el usuario elige el perfil de bordes
- **THEN** el sistema aplica un pipeline de detección de contornos, cierre de discontinuidades y conversión vectorial

#### Scenario: Selección de perfil lineal
- **WHEN** el usuario elige el perfil lineal
- **THEN** el sistema aplica un pipeline orientado a extracción de entidades lineales con continuidad geométrica

### Requirement: Parametrización controlada por perfil
El sistema MUST definir parámetros por defecto específicos por perfil y SHALL permitir ajuste manual con trazabilidad de configuración usada.

#### Scenario: Parámetros por defecto consistentes
- **WHEN** el usuario ejecuta un perfil sin cambios manuales
- **THEN** el sistema usa el conjunto de parámetros por defecto documentado para ese perfil

#### Scenario: Trazabilidad de configuración
- **WHEN** el usuario modifica parámetros de un perfil
- **THEN** el sistema registra la configuración efectiva usada en la ejecución

#### Scenario: Parámetros internos de control de memoria
- **WHEN** el usuario define `max_pixels` y `max_estimated_bytes` en parámetros del perfil
- **THEN** el sistema aplica esos límites de carga raster sin cambiar el contrato externo del algoritmo Processing

#### Scenario: Carga regional por ventanas
- **WHEN** el perfil `regional-high-precision` se ejecuta con GDAL disponible
- **THEN** el sistema puede usar `chunk_size` para leer por ventanas y construir el insumo de preproceso de forma incremental

### Requirement: Evaluación de calidad por perfil
El sistema SHALL habilitar evaluación de precisión por perfil mediante métricas definidas y dataset de referencia para detectar regresiones.

#### Scenario: Comparación entre perfiles
- **WHEN** se ejecuta evaluación sobre un dataset de referencia
- **THEN** el sistema reporta métricas comparables por perfil y permite identificar el perfil con mayor precisión

#### Scenario: Control de regresión de precisión
- **WHEN** una actualización reduce métricas por debajo del umbral definido
- **THEN** el sistema marca la regresión y bloquea su aceptación como baseline del MVP
