# development-quality-gates Specification

## Purpose
Asegurar que el plugin mantenga calidad estática mínima (lint + tipado) antes de llegar a build/release.

## Requirements
### Requirement: Gate local de calidad
El sistema de desarrollo MUST ejecutar validaciones automáticas en `git commit` para lint/formato y SHALL bloquear el commit si falla alguna.

#### Scenario: Commit bloqueado por lint/tipo
- **WHEN** un archivo incumple reglas de lint o tipado
- **THEN** el hook de `pre-commit` falla y el commit no se completa

### Requirement: Tipado de PyQGIS resoluble
El entorno de desarrollo MUST resolver referencias de `qgis.core` para análisis estático usando stubs compatibles.

#### Scenario: Imports de `qgis.core` validados
- **WHEN** se corre el checker de tipos en el repo
- **THEN** los imports de PyQGIS se analizan usando stubs y no fallan por módulo no encontrado (salvo error real de configuración)

### Requirement: Paridad local/CI
La CI SHALL aplicar las mismas validaciones definidas para desarrollo local.

#### Scenario: Build falla por regla de calidad
- **WHEN** un PR introduce incumplimientos de lint/tipado
- **THEN** la CI marca fallo y bloquea merge/release

### Public APIs / Interfaces
- Sin cambios en APIs funcionales del plugin.
- Solo contrato nuevo de calidad en tooling de desarrollo.

### Test Plan
1. `pre-commit install` y `pre-commit run --all-files`.
2. Falla controlada: introducir import inválido y validar bloqueo.
3. CI ejecuta mismo set de hooks y falla en los mismos casos.

### Assumptions
- Se mantiene estrategia elegida: Pyright + `qgis-stubs`.
- Adopción de pyright será faseada porque el baseline actual ya presenta errores.
