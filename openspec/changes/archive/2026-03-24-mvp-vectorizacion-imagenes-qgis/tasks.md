## 1. Base del plugin y estructura modular

- [x] 1.1 Crear la estructura base del plugin QGIS con metadata y puntos de entrada.
- [x] 1.2 Registrar el Processing Provider y exponer los algoritmos iniciales en Toolbox.
- [x] 1.3 Definir contrato común de motores (entrada, parámetros, salida, estado).
- [x] 1.4 Implementar orquestador del pipeline por etapas (preprocess, vectorize, postprocess, export).

## 2. Baseline de precisión (antes de implementar perfiles)

- [x] 2.1 Definir dataset mínimo de referencia para casos generalistas del MVP.
- [x] 2.2 Definir métricas de precisión y umbrales de aceptación del MVP estricto.
- [x] 2.3 Definir formato de reporte de resultados y criterio de aprobación/rechazo.

## 3. Motor clásico MVP estricto (perfil regional)

- [x] 3.1 Implementar perfil `regional-high-precision` con segmentación por regiones y polygonización.
- [x] 3.2 Agregar parametrización del perfil regional con valores por defecto y ajustes manuales.
- [x] 3.3 Implementar validación y corrección topológica obligatoria postvectorización.
- [x] 3.4 Estandarizar exportación en formato geoespacial compatible con QGIS (prioridad GeoPackage).
- [x] 3.5 Registrar configuración efectiva y metadatos de ejecución para trazabilidad.
- [x] 3.6 Implementar ejecución asíncrona en background con progreso y cancelación.

## 4. Evaluación y control de regresión (MVP estricto)

- [x] 4.1 Implementar flujo de evaluación del perfil regional sobre dataset de referencia.
- [x] 4.2 Establecer baseline oficial de precisión para la versión MVP.
- [x] 4.3 Implementar criterio de bloqueo ante regresión de precisión respecto al baseline.
- [x] 4.4 Integrar validación automática de regresión de precisión en el pipeline de release.

## 5. Documentación y preparación de release

- [x] 5.1 Documentar uso del perfil regional, parámetros y limitaciones conocidas del MVP estricto.
- [x] 5.2 Consolidar reglas operativas y gobernanza en `docs/`.
- [x] 5.3 Preparar pipeline de empaquetado/publicación del plugin.
- [x] 5.4 Definir roadmap explícito para MVP+ (`edge`, `linear`) y fase IA posterior.

## 6. MVP+ (fuera del MVP estricto)

- [x] 6.1 Implementar perfil `edge-high-precision` con detección de contornos y cierre de discontinuidades.
- [x] 6.2 Implementar perfil `linear-high-precision` para extracción de entidades lineales.
- [x] 6.3 Extender evaluación comparativa entre perfiles (`regional`, `edge`, `linear`).
