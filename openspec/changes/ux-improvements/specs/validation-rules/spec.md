# validation-rules Specification

## Purpose

Define the validation rules for execution mode selection and parameter injection based on profile type.

## ADDED Requirements

### Requirement: Tiled execution mode validation

The system SHALL reject `tiled` execution mode when the selected profile is not `regional-high-precision`.

#### Scenario: Tiled rejected for edge profile
- **WHEN** user selects `tiled` execution mode with `edge-high-precision` profile
- **THEN** the system raises a clear error message
- **AND** does not execute the algorithm

#### Scenario: Tiled rejected for linear profile
- **WHEN** user selects `tiled` execution mode with `linear-high-precision` profile
- **THEN** the system raises a clear error message
- **AND** does not execute the algorithm

#### Scenario: Tiled accepted for regional profile
- **WHEN** user selects `tiled` execution mode with `regional-high-precision` profile
- **THEN** the system proceeds with tiled execution

#### Scenario: Auto mode for edge profile
- **WHEN** user selects `auto` execution mode with `edge-high-precision` profile
- **THEN** the system selects `strict` memory policy
- **AND** logs a warning about tiled not being available

### Requirement: Edge Canny parameters injection

The system SHALL only inject edge Canny parameters (`edge_canny_low`, `edge_canny_high`, `edge_blur`) when the selected profile is `edge-high-precision`.

#### Scenario: Canny params injected for edge profile
- **WHEN** user selects `edge-high-precision` profile
- **THEN** the system reads `EDGE_CANNY_LOW`, `EDGE_CANNY_HIGH`, `EDGE_BLUR` parameters
- **AND** injects them into profile_parameters

#### Scenario: Canny params not injected for regional profile
- **WHEN** user selects `regional-high-precision` profile
- **THEN** the system does not read or inject Canny parameters

#### Scenario: Canny params not injected for linear profile
- **WHEN** user selects `linear-high-precision` profile
- **THEN** the system does not read or inject Canny parameters

## Error Messages

### Tiled mode for non-regional profile
```
Tiled execution mode is only supported for 'regional-high-precision' profile.
For edge/linear profiles, use 'auto' (recommended) or 'strict'.
```