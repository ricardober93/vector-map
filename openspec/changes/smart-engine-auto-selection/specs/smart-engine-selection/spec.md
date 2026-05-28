# smart-engine-selection Specification

## Purpose

Define how the system automatically selects the optimal vectorization engine when the user selects "auto" in the Engine dropdown, ensuring the best available performance without requiring manual configuration.

## ADDED Requirements

### Requirement: Auto engine selection prefers OpenCV when available

When the user selects "auto" in the Engine dropdown, the system SHALL select `opencv-local` if OpenCV is installed and functional, otherwise SHALL select `classic-local`.

#### Scenario: OpenCV available selects OpenCV
- **WHEN** user selects "auto" and OpenCV is installed (`import cv2` succeeds)
- **THEN** the system selects `opencv-local` engine
- **AND** logs: "Engine auto mode: selected 'opencv-local' (faster than profile default 'classic-local')"

#### Scenario: OpenCV unavailable selects classic
- **WHEN** user selects "auto" and OpenCV is not installed or fails to import
- **THEN** the system selects `classic-local` engine
- **AND** logs: "Engine auto mode: selected 'classic-local' (OpenCV not available)"

### Requirement: Explicit engine selection is respected

When the user explicitly selects "classic" or "opencv" in the dropdown (not "auto"), the system SHALL use exactly that engine, with no automatic fallback.

#### Scenario: Explicit classic selection
- **WHEN** user selects "classic" in the dropdown
- **THEN** the system uses `classic-local` engine
- **AND** logs: "Engine selection: 'classic-local' (explicit)"

#### Scenario: Explicit opencv selection
- **WHEN** user selects "opencv" in the dropdown
- **THEN** the system uses `opencv-local` engine
- **AND** logs: "Engine selection: 'opencv-local' (explicit)"

#### Scenario: Explicit opencv when unavailable raises error
- **WHEN** user selects "opencv" and OpenCV is not available
- **THEN** the system raises `DependencyError` with clear message
- **AND** does NOT fallback to classic (explicit selection means explicit failure)

### Requirement: Engine availability check

The system SHALL verify OpenCV availability by attempting `import cv2` and checking the version is >= 4.8.0.

#### Scenario: OpenCV version check passes
- **WHEN** `import cv2` succeeds and `cv2.__version__ >= "4.8.0"`
- **THEN** OpenCV is considered available

#### Scenario: OpenCV version check fails
- **WHEN** `import cv2` succeeds but `cv2.__version__ < "4.8.0"`
- **THEN** OpenCV is considered unavailable
- **AND** system falls back to classic with warning

#### Scenario: OpenCV import fails
- **WHEN** `import cv2` raises `ImportError` or any other exception
- **THEN** OpenCV is considered unavailable
- **AND** system falls back to classic

### Requirement: Runtime fallback for auto mode

If OpenCV is selected by auto mode but fails during execution, the system SHALL attempt to re-run with classic engine if the operation is idempotent (vectorization).

#### Scenario: OpenCV fails during vectorization
- **WHEN** `opencv-local` engine fails during preprocess/vectorize with `DependencyError`
- **THEN** the system retries the same operation with `classic-local` engine
- **AND** logs: "OpenCV engine failed, falling back to 'classic-local'"
- **AND** adds to warnings: "Engine fallback: OpenCV → classic (original error: ...)"

#### Scenario: OpenCV fails during non-idempotent operation
- **WHEN** `opencv-local` engine fails during export (idempotent guarantee broken)
- **THEN** the system does NOT fallback (export is stateful)
- **AND** raises the original error

## Error Handling

### OpenCV dependency error
```
DependencyError: OpenCV (opencv-python-headless) is required for the OpenCV 
vectorization engine. Install it with: pip install opencv-python-headless>=4.8.0
```

### No engine available
```
ConfigurationError: No vectorization engine supports profile '{profile_id}'.
```

## Logging

The system SHALL log engine selection decisions at INFO level:

| Scenario | Log Message |
|----------|-------------|
| auto → opencv | `[INFO] Engine auto mode: selected 'opencv-local' (faster than profile default 'classic-local')` |
| auto → classic (fallback) | `[INFO] Engine auto mode: selected 'classic-local' (OpenCV not available)` |
| explicit classic | `[INFO] Engine selection: 'classic-local' (explicit)` |
| explicit opencv | `[INFO] Engine selection: 'opencv-local' (explicit)` |
| fallback | `[INFO] OpenCV engine failed, falling back to 'classic-local'` |