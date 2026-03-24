## Context

El proyecto parte de un repositorio nuevo y busca construir un plugin de QGIS para vectorizar imágenes raster de forma local con prioridad en precisión máxima. El MVP debe ser generalista (usable en distintos tipos de imagen), evitar dependencia inicial de IA y dejar una arquitectura preparada para crecer por motores de vectorización.

Restricciones relevantes:
- Debe integrarse de forma nativa con QGIS para uso en interfaz, Processing Toolbox, modeler y batch.
- Debe ejecutarse en local, priorizando trazabilidad y control de parámetros.
- Debe sostener calidad geométrica y consistencia topológica en la salida.

Stakeholders principales:
- Equipo de producto técnico (define alcance/roadmap).
- Usuarios GIS (analistas/cartógrafos) que requieren precisión y repetibilidad.

## Goals / Non-Goals

**Goals:**
- Definir una arquitectura modular por etapas (`preprocess -> vectorize -> postprocess -> export`) y por motores intercambiables.
- Implementar un motor clásico de alta precisión con perfiles para regiones, bordes y líneas.
- Integrar el MVP como proveedor de Processing en QGIS.
- Establecer una base de evaluación de calidad para comparar perfiles y detectar regresiones.
- Preparar interfaces internas para incorporar motores IA en fases posteriores sin rediseño profundo.

**Non-Goals:**
- No incluir vectorización por IA en el MVP.
- No optimizar para tiempo de ejecución extremo a costa de precisión.
- No construir inicialmente sincronización cloud ni orquestación distribuida.

## Decisions

### 1) Arquitectura en plugin QGIS + Processing Provider
- Decisión: exponer capacidades en un plugin con `Processing Provider`.
- Rationale: permite reutilizar ejecución en toolbox, modelos y procesamiento por lotes.
- Alternativas evaluadas:
  - Plugin solo con UI: descartado por menor integración con flujos GIS existentes.
  - Script suelto fuera de QGIS: descartado por baja adopción y menor ergonomía.

### 2) Motor clásico modular sin IA para v1
- Decisión: iniciar con pipeline clásico local y perfiles especializados.
- Rationale: mayor control, transparencia, depuración y dependencia tecnológica acotada.
- Alternativas evaluadas:
  - Empezar con IA: descartado por complejidad de despliegue y menor control en etapa inicial.

### 3) Contrato único de motores
- Decisión: definir interfaz de motor común (entrada raster + parámetros + salida vectorial + métricas básicas).
- Rationale: facilita escalar con nuevos métodos sin romper UI ni procesos.
- Alternativas evaluadas:
  - Lógica acoplada por perfil dentro de una sola implementación: descartada por alto costo de mantenimiento.

### 4) Pipeline por perfiles de precisión
- Decisión: crear perfiles base orientados a comportamiento visual:
  - `regional-high-precision` (segmentación por regiones + polygonize).
  - `edge-high-precision` (bordes/contornos + cierre de huecos + polygonize).
  - `linear-high-precision` (esqueletización/centerline para objetos lineales).
- Rationale: reduce ajuste manual y permite estrategia generalista con control experto.

### 5) Calidad como requisito de arquitectura
- Decisión: definir desde MVP un conjunto mínimo de datasets de referencia y métricas.
- Rationale: la prioridad del producto es precisión, no solo funcionalidad.
- Alternativas evaluadas:
  - Validación solo visual: descartada por subjetividad y pobre repetibilidad.

## Risks / Trade-offs

- [Riesgo] Alta sensibilidad a ruido y variaciones de imagen en un enfoque generalista.
  - Mitigación: perfiles diferenciados + preproceso configurable + dataset representativo.
- [Riesgo] Incremento de latencia por priorizar precisión.
  - Mitigación: ejecución asíncrona en background, barras de progreso y cancelación.
- [Riesgo] Salidas topológicamente inválidas en casos complejos.
  - Mitigación: etapa obligatoria de limpieza/validación geométrica y reglas de QA.
- [Trade-off] Mayor complejidad inicial en arquitectura modular.
  - Mitigación: contrato de motor simple y documentación fuerte desde el inicio.

## Migration Plan

1. Crear estructura base del plugin y proveedor de Processing.
2. Implementar el pipeline clásico con un perfil inicial de precisión.
3. Añadir perfiles adicionales y evaluación comparativa.
4. Publicar versión MVP con documentación de uso y límites conocidos.
5. Preparar siguiente fase para incorporar IA como motor opcional.

Rollback strategy:
- Mantener versionado semántico del plugin y capacidad de volver a versión previa estable del paquete.

## Open Questions

- ¿Cuál será el conjunto mínimo obligatorio de datasets de referencia para aceptar cambios?
- ¿Qué umbrales exactos de precisión (por perfil) se exigirán para aprobar releases?
- ¿Qué dependencias opcionales se permitirán en el MVP sin comprometer instalación en diferentes SO?
- ¿Cómo se gobernará la evolución de perfiles para no romper reproducibilidad entre versiones?
