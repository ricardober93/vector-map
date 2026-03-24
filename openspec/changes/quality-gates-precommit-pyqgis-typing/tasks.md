## 1. Configuración de herramientas

- [x] 1.1 Crear `.pre-commit-config.yaml` con hooks de higiene, `ruff`, `ruff-format`, `pyright`.
- [x] 1.2 Agregar `pre-commit`, `pyright[nodejs]`, `qgis-stubs` a deps de desarrollo.
- [x] 1.3 Agregar `[tool.pyright]` en `pyproject.toml` con `pythonVersion=3.11` y scope del repo.

## 2. Integración de CI

- [x] 2.1 Ejecutar `pre-commit run --all-files` en CI (con cache).
- [x] 2.2 Ajustar timeout si es necesario.
- [x] 2.3 Evitar duplicación innecesaria con checks de ruff existentes.

## 3. Adopción faseada de tipado

- [x] 3.1 Registrar baseline inicial de errores pyright.
- [x] 3.2 Corregir errores de tipos/imports en módulos críticos de plugin.
- [x] 3.3 Elevar severidad de reglas cuando la deuda llegue a cero.

## 4. Documentación

- [x] 4.1 Documentar `pre-commit install` y ejecución local.
- [x] 4.2 Documentar política de bloqueo de commits/build por lint/tipos.
