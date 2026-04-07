# execution-mode-ui Specification

## Purpose

Expose the execution mode selection as a visible, user-friendly parameter in the QGIS Processing dialog, eliminating the need to edit raw JSON.

## ADDED Requirements

### Requirement: Execution mode parameter in Processing dialog
The algorithm SHALL expose an `EXECUTION_MODE` parameter as an enum dropdown with three options: `auto` (default), `strict`, and `tiled`.

#### Scenario: Default execution mode is auto
- **WHEN** the user opens the algorithm dialog
- **THEN** the execution mode dropdown shows "Auto" as the selected option

#### Scenario: User can select strict mode
- **WHEN** the user changes the execution mode dropdown to "Strict"
- **THEN** the algorithm will use strict memory policy for execution

#### Scenario: User can select tiled mode
- **WHEN** the user changes the execution mode dropdown to "Tiled"
- **THEN** the algorithm will use regional-tiles memory policy for execution

### Requirement: Execution mode to memory policy translation
The algorithm SHALL translate the user-visible execution mode to the internal memory_policy before creating the VectorizationRequest.

#### Scenario: Auto mode translation
- **WHEN** the user selects "Auto" execution mode
- **THEN** the system passes execution_mode="auto" to the pipeline, which resolves the actual memory_policy at runtime

#### Scenario: Strict mode translation
- **WHEN** the user selects "Strict" execution mode
- **THEN** the system sets memory_policy="strict" in the request parameters

#### Scenario: Tiled mode translation
- **WHEN** the user selects "Tiled" execution mode
- **THEN** the system sets memory_policy="regional-tiles" in the request parameters

### Requirement: Tiled mode validation for non-regional profiles
When the user selects "Tiled" execution mode with a non-regional profile (edge/linear), the algorithm SHALL display a clear error message.

#### Scenario: Tiled mode with edge profile
- **WHEN** the user selects "Tiled" mode with "edge-high-precision" profile
- **THEN** the algorithm raises an error: "Tiled execution mode is only supported for the regional profile."

#### Scenario: Tiled mode with linear profile
- **WHEN** the user selects "Tiled" mode with "linear-high-precision" profile
- **THEN** the algorithm raises an error: "Tiled execution mode is only supported for the regional profile."

### Requirement: Backward compatibility with JSON parameters
The execution mode parameter SHALL work alongside the existing JSON parameters field. If `memory_policy` is explicitly set in JSON, the execution mode parameter takes precedence.

#### Scenario: Execution mode overrides JSON memory_policy
- **WHEN** the user selects "Tiled" mode but JSON contains `{"memory_policy": "strict"}`
- **THEN** the system uses "regional-tiles" (execution mode parameter wins)

#### Scenario: JSON parameters without memory_policy
- **WHEN** the user selects "Auto" mode and JSON contains `{"smoothing_radius": 2}`
- **THEN** the system combines auto execution mode with the smoothing parameter
