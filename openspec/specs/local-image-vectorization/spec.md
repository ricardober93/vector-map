# local-image-vectorization Specification

## Purpose
TBD - created by archiving change mvp-vectorizacion-imagenes-qgis. Update Purpose after archive.
## Requirements
### Requirement: Vectorización local y determinística
El sistema MUST ejecutar la vectorización de imágenes raster en entorno local sin requerir servicios cloud, y SHALL producir resultados reproducibles con la misma entrada y parámetros.

#### Scenario: Ejecución local sin servicios externos
- **WHEN** el usuario ejecuta una vectorización con una imagen válida y parámetros válidos
- **THEN** el sistema completa el procesamiento localmente sin llamadas obligatorias a APIs externas

#### Scenario: Reproducibilidad de resultados
- **WHEN** el usuario repite el proceso con la misma imagen, perfil y configuración
- **THEN** el sistema genera la misma geometría de salida dentro de tolerancias numéricas definidas

### Requirement: Pipeline de procesamiento por etapas
El sistema SHALL ejecutar la vectorización usando etapas explícitas de preproceso, vectorización y postproceso topológico antes de exportar resultados.

#### Scenario: Secuencia obligatoria de etapas
- **WHEN** se inicia un job de vectorización
- **THEN** el sistema ejecuta preproceso, vectorización y postproceso en ese orden y registra el estado de cada etapa

### Requirement: Salida geoespacial válida para QGIS
El sistema MUST generar una capa vectorial compatible con QGIS y SHALL garantizar geometrías válidas tras el postproceso.

#### Scenario: Exportación de capa utilizable
- **WHEN** la vectorización finaliza exitosamente
- **THEN** el sistema exporta un resultado vectorial que puede cargarse en QGIS sin errores críticos de geometría

#### Scenario: Corrección de geometrías inválidas
- **WHEN** la etapa de vectorización produce geometrías inválidas
- **THEN** el sistema ejecuta rutinas de corrección y solo publica salida marcada como válida

### Requirement: Integración con Processing de QGIS
El sistema SHALL exponer la capacidad de vectorización como algoritmo(s) en Processing para permitir uso en toolbox, modeler y batch.

#### Scenario: Disponibilidad en Processing Toolbox
- **WHEN** el plugin está instalado y habilitado
- **THEN** el usuario encuentra los algoritmos de vectorización en Processing Toolbox

#### Scenario: Ejecución por lotes
- **WHEN** el usuario ejecuta un batch con múltiples imágenes
- **THEN** el sistema procesa cada entrada bajo el mismo contrato de parámetros y genera salidas separadas

### Requirement: Carga robusta de rásteres locales grandes
El sistema SHALL priorizar GDAL para cargar rásteres locales en disco dentro de QGIS y MAY usar Pillow como fallback controlado para compatibilidad local.

#### Scenario: Raster geoespacial grande en QGIS
- **WHEN** el usuario ejecuta la vectorización con un raster local grande compatible con GDAL
- **THEN** el sistema intenta primero la carga con GDAL y evita fallar prematuramente por el límite de descompresión de Pillow

#### Scenario: Fallback de dependencias con límite explícito
- **WHEN** GDAL no está disponible o no puede abrir el archivo y el sistema recurre a Pillow
- **THEN** el sistema aplica un límite operativo explícito de `1_000_000_000` píxeles y devuelve un error accionable si la carga no puede completarse

#### Scenario: Abort temprano por preflight de memoria
- **WHEN** un ráster excede `max_pixels` o `max_estimated_bytes` durante el preflight de metadatos GDAL
- **THEN** el sistema aborta antes de `ReadAsArray` y devuelve un mensaje accionable con dimensiones, estimación y recomendaciones de mitigación

#### Scenario: MemoryError en GDAL evita fallback redundante
- **WHEN** GDAL falla por `MemoryError` al leer el ráster
- **THEN** el sistema no intenta fallback con Pillow y devuelve un error explícito de presión de memoria con sugerencias operativas
