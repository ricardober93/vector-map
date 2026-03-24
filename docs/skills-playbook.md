# Skills Playbook para ejecutar el MVP con éxito

Este playbook define hábitos y capacidades de equipo para sostener calidad técnica y velocidad de aprendizaje.

## Skill 1: Pensamiento geoespacial aplicado

- Entender implicaciones de CRS, resolución, nodata y escala.
- Verificar coherencia espacial de entradas y salidas.

## Skill 2: Diseño de pipelines reproducibles

- Diseñar etapas con contratos claros.
- Evitar lógica oculta y parámetros implícitos.

## Skill 3: QA de precisión

- Trabajar con dataset de referencia.
- Medir y comparar resultados por perfil.
- Detectar regresiones temprano.

## Skill 4: Debug visual y topológico

- Identificar errores de contorno, huecos, slivers y geometrías inválidas.
- Aplicar limpieza postvectorización de forma sistemática.

## Skill 5: Gobernanza técnica ligera

- Documentar decisiones clave en OpenSpec y `docs/`.
- Separar claramente descubrimiento, propuesta e implementación.

## Ritual operativo recomendado

1. Definir hipótesis de mejora.
2. Ejecutar pruebas sobre dataset de referencia.
3. Comparar métricas y resultados visuales.
4. Decidir con evidencia.
5. Actualizar documentación y baseline.
