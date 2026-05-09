## ADDED Requirements

### Requirement: Transformación de coordenadas pixel a mundo via geotransform

El sistema SHALL aplicar una transformación afín a todas las coordenadas de features vectoriales antes de la exportación, convirtiendo coordenadas pixel a coordenadas mundo usando el geotransform GDAL del raster de entrada.

#### Scenario: Geotransform estándar sin rotación
- **WHEN** un VectorLayer tiene features con coordenadas pixel y un geotransform con valores `(origin_x, pixel_w, 0, origin_y, 0, pixel_h)`
- **THEN** cada coordenada pixel `(col, row)` se transforma a `(origin_x + col * pixel_w, origin_y + row * pixel_h)`

#### Scenario: Geotransform con rotación
- **WHEN** un VectorLayer tiene features con coordenadas pixel y un geotransform con valores de rotación no nulos `(origin_x, pixel_w, rot_x, origin_y, rot_y, pixel_h)`
- **THEN** cada coordenada pixel `(col, row)` se transforma a `(origin_x + col * pixel_w + row * rot_x, origin_y + col * rot_y + row * pixel_h)`

#### Scenario: Geotransform ausente
- **WHEN** un VectorLayer tiene `geotransform = None`
- **THEN** las coordenadas permanecen sin transformar (pixel space) y el sistema SHALL registrar un warning

#### Scenario: Geometrías tipo Polygon
- **WHEN** se aplica geotransform a un VectorFeature con `geometry_type = "Polygon"`
- **THEN** todos los puntos de todos los anillos (exterior e interiores) se transforman a coordenadas mundo

#### Scenario: Geometrías tipo LineString
- **WHEN** se aplica geotransform a un VectorFeature con `geometry_type = "LineString"`
- **THEN** todos los puntos de la línea se transforman a coordenadas mundo

#### Scenario: Geometrías tipo Point
- **WHEN** se aplica geotransform a un VectorFeature con `geometry_type = "Point"`
- **THEN** la coordenada del punto se transforma a coordenadas mundo

#### Scenario: Geometrías tipo MultiPolygon y MultiLineString
- **WHEN** se aplica geotransform a un VectorFeature con `geometry_type = "MultiPolygon"` o `"MultiLineString"`
- **THEN** todos los puntos de todos los componentes se transforman a coordenadas mundo

### Requirement: Propagación del geotransform desde el raster al VectorLayer

El sistema SHALL propagar el geotransform del raster de entrada al VectorLayer resultante para que esté disponible durante la exportación.

#### Scenario: Pipeline estándar con geotransform
- **WHEN** se ejecuta el pipeline estándar y el raster de entrada tiene geotransform en su metadata
- **THEN** el VectorLayer resultante tiene `geotransform` con los mismos valores del raster

#### Scenario: Pipeline tiled con consolidación
- **WHEN** se ejecuta el pipeline tiled y el raster de entrada tiene geotransform
- **THEN** el VectorLayer consolidado tiene el geotransform del raster completo (no de cada tile)
- **AND** las coordenadas ya incluyen offsets de tile antes de aplicar geotransform