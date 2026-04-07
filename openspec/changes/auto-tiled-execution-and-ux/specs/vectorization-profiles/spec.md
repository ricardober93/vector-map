# vectorization-profiles Specification (delta)

## MODIFIED Requirements

### Requirement: Parametrización controlada por perfil
El sistema MUST definir parámetros por defecto específicos por perfil y SHALL permitir ajuste manual con trazabilidad de configuración usada. El perfil `regional-high-precision` SHALL soportar ejecución por mosaicos cuando el modo de ejecución lo requiera.

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

#### Scenario: Perfil regional soporta tiled execution
- **WHEN** el perfil `regional-high-precision` se ejecuta con modo de ejecución `tiled` o `auto` (con ráster grande)
- **THEN** el sistema activa el pipeline de mosaicos con `tile_size` configurado y consolida la salida en una sola capa
