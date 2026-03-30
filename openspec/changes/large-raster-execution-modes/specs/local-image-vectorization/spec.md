## ADDED Requirements

### Requirement: Política explícita para ejecución de rásteres grandes
El sistema SHALL permitir una política explícita de memoria (`memory_policy`) y MUST mantener `strict` como default para preservar seguridad operativa y reproducibilidad.

#### Scenario: Modo estricto por defecto
- **WHEN** el usuario no define `memory_policy`
- **THEN** el sistema aplica `strict` y mantiene los guardrails de preflight existentes

#### Scenario: Modo experto activado explícitamente
- **WHEN** el usuario define `memory_policy=expert-override` con límites válidos
- **THEN** el sistema permite la ejecución bajo los límites provistos y registra advertencia operativa en metadatos/reportes

### Requirement: Diagnóstico cuantitativo en preflight abortado
Cuando el preflight rechaza un ráster por umbrales de memoria, el sistema MUST incluir recomendaciones cuantitativas accionables además del mensaje cualitativo.

#### Scenario: Mensaje con factor de reducción
- **WHEN** un ráster excede `max_pixels` o `max_estimated_bytes`
- **THEN** el error incluye factor mínimo de reducción lineal y dimensión objetivo aproximada para cumplir el umbral de píxeles
