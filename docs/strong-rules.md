# Reglas Fuertes del MVP

## Alcance y calidad

1. No se incluye IA en el MVP inicial.
2. Ningún cambio entra sin criterio de precisión definido.
3. Toda salida vectorial debe pasar validación geométrica.
4. Todo perfil debe tener defaults documentados.

## Ingeniería

1. Mantener contrato único de motores (entrada/salida/parámetros).
2. Evitar acoplar lógica de vectorización con la UI.
3. Exponer capacidades vía Processing Provider.
4. Ejecutar procesos pesados en background.
5. Registrar configuración efectiva en cada ejecución.

## Producto y gobernanza

1. Cambios de alcance solo mediante propuesta actualizada.
2. No mezclar optimizaciones de performance que degraden precisión.
3. Todo cambio de parámetros baseline debe justificar impacto en métricas.
4. Documentación y decisiones deben mantenerse al día en `docs/` y OpenSpec.
