## ADDED Requirements

### Requirement: Ejecución regional por teselas para escenas fuera de umbral
El sistema SHALL soportar un modo de ejecución por teselas para `regional-high-precision` cuando la política de memoria lo solicite, preservando una única salida vectorial compatible con QGIS.

#### Scenario: Activación de modo regional por teselas
- **WHEN** el usuario ejecuta `regional-high-precision` con `memory_policy=regional-tiles`
- **THEN** el sistema procesa el ráster por teselas, integra los resultados y exporta una sola capa de salida

#### Scenario: Trazabilidad de ejecución teselada
- **WHEN** una ejecución usa modo por teselas
- **THEN** el sistema registra en metadatos la configuración efectiva (tamaño de tesela, número de teselas y política aplicada)

### Requirement: Compatibilidad de contratos de perfil
La introducción del modo por teselas MUST conservar el contrato de parámetros y salida de perfiles existentes sin cambiar el comportamiento por defecto de `edge-high-precision` y `linear-high-precision`.

#### Scenario: Perfiles no regionales sin regresión
- **WHEN** el usuario ejecuta `edge-high-precision` o `linear-high-precision` sin política especial
- **THEN** el sistema mantiene el comportamiento actual y los mismos defaults de carga raster
