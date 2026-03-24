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

