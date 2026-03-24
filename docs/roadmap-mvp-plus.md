# Roadmap MVP+

Este roadmap cubre la expansión después del MVP estricto.
La prioridad es sumar perfiles `edge` y `linear` sin romper el contrato del motor ni la comparabilidad de métricas.

## Fase 1: estabilizar el MVP estricto

Antes de ampliar perfiles:

- Congelar el comportamiento de `regional-high-precision`.
- Mantener baseline y release gating.
- Consolidar exportación, validación y trazabilidad.
- Evitar refactors que mezclen UI con lógica de vectorización.

## Fase 2: perfil `edge-high-precision`

Objetivo:

- Vectorizar contornos y bordes con cierre de discontinuidades.

Capacidades esperadas:

- Detección de bordes.
- Cierre de huecos y gaps.
- Polygonize posterior.
- Validación topológica igual de estricta que el perfil regional.

Casos de uso:

- Mapas con límites bien marcados.
- Imágenes donde el contorno importa más que el relleno.

## Fase 3: perfil `linear-high-precision`

Objetivo:

- Extraer entidades lineales mediante esqueletización o centerline.

Capacidades esperadas:

- Extracción de ejes y líneas principales.
- Limpieza de ramificaciones espurias.
- Normalización topológica de redes lineales.

Casos de uso:

- Infraestructura.
- Drenajes.
- Vías.
- Estructuras alargadas o conectadas.

## Fase 4: evaluación comparativa multi-perfil

Agregar evaluación sobre los tres perfiles:

- `regional-high-precision`
- `edge-high-precision`
- `linear-high-precision`

Cada perfil debe medirse con métricas propias y con un reporte comparable.
La comparación debe servir para elegir perfil por tipo de imagen, no para mezclar resultados.

## Fase IA posterior

La IA entra después de consolidar los perfiles clásicos.
Requisitos mínimos para habilitarla:

- Mantener el mismo contrato de entrada y salida.
- No romper la reproducibilidad del flujo clásico.
- Poder apagarla y volver al motor clásico sin cambios estructurales.
- Validar que aporte valor real en precisión o robustez.

## Secuencia sugerida

1. Cerrar baseline del MVP estricto.
2. Publicar primera release estable.
3. Implementar `edge-high-precision`.
4. Implementar `linear-high-precision`.
5. Extender baseline comparativa.
6. Evaluar incorporación de IA como motor opcional.

