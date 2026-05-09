## ADDED Requirements

### Requirement: Integración con QgsFeatureSink de QGIS Processing

El sistema SHALL usar `parameterAsSink()` de QGIS Processing para escribir features directamente al destino de salida, soportando destinos `memory:`, archivo temporal y archivo explícito.

#### Scenario: Destino memory: (capa temporal)
- **WHEN** el usuario ejecuta el algoritmo desde Processing Toolbox con destino temporal
- **THEN** la capa vectorial se carga en QGIS como capa temporal con geometrías válidas y CRS correcto
- **AND** los features aparecen en la capa con coordenadas georreferenciadas

#### Scenario: Destino archivo GeoPackage
- **WHEN** el usuario especifica un archivo `.gpkg` como destino
- **THEN** se crea un GeoPackage con features georreferenciados y CRS declarado

#### Scenario: Destino archivo GeoJSON
- **WHEN** el usuario especifica un archivo `.geojson` como destino
- **THEN** se crea un archivo GeoJSON con features georreferenciados y CRS declarado

#### Scenario: Destino memory: sin archivo temporal intermedio
- **WHEN** el destino de salida es `memory:` o un URI con provider (contiene `:` y no empieza con `/`)
- **THEN** el algoritmo usa `parameterAsSink()` en lugar de crear archivos temporales

### Requirement: CRS de la capa de salida coincide con el raster de entrada

El sistema SHALL asignar el CRS del raster de entrada a la capa de salida. Cuando el raster no tiene CRS, el sistema SHALL usar un fallback con advertencia.

#### Scenario: CRS presente en el raster de entrada
- **WHEN** el raster de entrada tiene un CRS válido
- **THEN** la capa de salida usa el mismo CRS del raster

#### Scenario: CRS ausente en el raster de entrada
- **WHEN** el raster de entrada no tiene CRS definido
- **THEN** la capa usa el CRS del proyecto QGIS como fallback si está disponible, sino EPSG:4326
- **AND** se registra un warning via `feedback.pushWarning()`

## MODIFIED Requirements

### Requirement: Salida geoespacial válida para QGIS

El sistema MUST generar una capa vectorial compatible con QGIS y SHALL garantizar geometrías válidas tras el postproceso. La capa de salida SHALL usar coordenadas georreferenciadas (no coordenadas pixel) y SHALL integrarse con el framework Processing de QGIS mediante QgsFeatureSink.

#### Scenario: Exportación de capa utilizable
- **WHEN** la vectorización finaliza exitosamente
- **THEN** el sistema exporta una capa vectorial con coordenadas en el sistema de referencia del raster de entrada que puede cargarse en QGIS sin errores críticos de geometría

#### Scenario: Corrección de geometrías inválidas
- **WHEN** la etapa de vectorización produce geometrías inválidas
- **THEN** el sistema ejecuta rutinas de corrección y solo publica salida marcada como válida

#### Scenario: Coordenadas georreferenciadas en la capa de salida
- **WHEN** el raster de entrada tiene un geotransform válido
- **THEN** las coordenadas de los features en la capa de salida están en espacio mundo (coordenadas geográficas o proyectadas), no en espacio pixel

### Requirement: Manejo de geometrías mixtas en exportación por archivo

El sistema SHALL agrupar features por tipo de geometría al exportar a GeoPackage, creando sub-capas separadas para cada tipo.

#### Scenario: Features Polygon y LineString en la misma capa
- **WHEN** se exportan features de tipos mixtos a GeoPackage
- **THEN** las features Polygon se exportan en una sub-capa y las features LineString en otra
- **AND** no se pierden features de ningún tipo