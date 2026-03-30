## 1. Política de memoria y preflight accionable

- [x] 1.1 Agregar parámetro `memory_policy` al contrato de parámetros y resolver defaults sin romper compatibilidad.
- [x] 1.2 Extender preflight para emitir recomendaciones cuantitativas (factor de escala y tamaño objetivo).
- [x] 1.3 Registrar en metadatos/reportes la política efectiva y advertencias de modo experto.

## 2. Ejecución regional por teselas

- [x] 2.1 Implementar runner de teselas para `regional-high-precision` con tamaño configurable.
- [x] 2.2 Implementar merge de resultados por tesela con limpieza topológica posterior.
- [x] 2.3 Garantizar salida única compatible con QGIS y preservar trazabilidad de configuración.

## 3. Calidad, regresión y documentación

- [x] 3.1 Añadir pruebas unitarias para `memory_policy` (`strict`, `expert-override`, `regional-tiles`).
- [x] 3.2 Añadir pruebas de integración de precisión para ejecución por teselas frente a baseline regional.
- [x] 3.3 Actualizar `docs/architecture.md`, `docs/mvp-strict-usage.md` y `docs/precision-baseline.md` con el nuevo flujo operativo.
- [ ] 3.4 Actualizar OpenSpec final de capacidades afectadas al archivar el cambio.
