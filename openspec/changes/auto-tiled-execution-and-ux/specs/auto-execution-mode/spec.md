# auto-execution-mode Specification

## Purpose

Auto-detect the optimal execution mode (strict vs tiled) based on raster size, eliminating the need for users to manually configure memory policies.

## ADDED Requirements

### Requirement: Auto-detection threshold evaluation
The system SHALL evaluate raster size against an auto-detection threshold before loading data, and SHALL select tiled execution when the raster exceeds the threshold.

#### Scenario: Raster below threshold selects strict mode
- **WHEN** the raster has fewer pixels than the auto-detection threshold (150M px)
- **THEN** the system selects strict execution mode for full in-memory processing

#### Scenario: Raster above threshold selects tiled mode
- **WHEN** the raster exceeds the auto-detection threshold (150M px) and the profile supports tiled execution
- **THEN** the system selects tiled execution mode and logs the decision

#### Scenario: Raster above threshold with non-regional profile
- **WHEN** the raster exceeds the auto-detection threshold but the profile does not support tiled execution (edge/linear)
- **THEN** the system falls back to strict mode and warns the user that tiled mode is not available for this profile

### Requirement: Auto-detection threshold configuration
The auto-detection threshold SHALL be computed as 75% of the profile's `max_pixels` parameter, providing a 25% safety margin before the hard limit.

#### Scenario: Default threshold calculation
- **WHEN** a profile has `max_pixels` of 200,000,000
- **THEN** the auto-detection threshold is 150,000,000 pixels (75%)

#### Scenario: Custom threshold with overridden max_pixels
- **WHEN** the user overrides `max_pixels` in profile parameters
- **THEN** the auto-detection threshold is recalculated based on the overridden value

### Requirement: Informative logging for auto mode decisions
The system SHALL log the auto-detection decision with the raster size, threshold, and selected mode when auto mode triggers a mode switch.

#### Scenario: Logging tiled activation
- **WHEN** auto mode selects tiled execution for a 684M px raster
- **THEN** the system logs: "Auto mode: tiled execution activated (684M px exceeds 150M threshold). Processing N tiles of size 2048x2048."

#### Scenario: Logging strict selection for small raster
- **WHEN** auto mode selects strict execution for a 50M px raster
- **THEN** the system does not log a mode switch notification (normal path, no noise)

### Requirement: Strict mode warning for large rasters
When the user explicitly selects strict mode and the raster exceeds the auto-detection threshold, the system SHALL emit a warning but SHALL proceed with execution (the internal preflight remains as final guardrail).

#### Scenario: Warning for large raster in strict mode
- **WHEN** the user selects strict mode and the raster exceeds 150M px
- **THEN** the system logs a warning suggesting tiled mode but proceeds with strict execution

#### Scenario: No warning for small raster in strict mode
- **WHEN** the user selects strict mode and the raster is below 150M px
- **THEN** the system proceeds without any warning
