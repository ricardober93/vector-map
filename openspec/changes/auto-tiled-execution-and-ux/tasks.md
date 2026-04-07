## 1. PipelineOrchestrator - Auto mode resolution

- [x] 1.1 Add `execution_mode` parameter to `PipelineOrchestrator.run()` method with default value `"auto"`
- [x] 1.2 Implement `_resolve_execution_mode()` method that translates execution_mode + raster size to effective memory_policy
- [x] 1.3 Implement `_check_auto_threshold()` method that reads GDAL metadata (width, height) without loading pixel data and compares against threshold (max_pixels * 0.75)
- [x] 1.4 Update `_resolve_memory_policy()` to accept the resolved execution_mode and handle `"auto"` case
- [x] 1.5 Add logging for auto mode decisions (tiled activation, strict selection for small rasters)

## 2. VectorizeImageAlgorithm - UI parameter

- [x] 2.1 Add `EXECUTION_MODE = "EXECUTION_MODE"` constant to `VectorizeImageAlgorithm`
- [x] 2.2 Add `QgsProcessingParameterEnum` for execution mode with options `["auto", "strict", "tiled"]` and default `0` (auto) in `initAlgorithm()`
- [x] 2.3 Implement `_resolve_execution_mode_parameter()` method to read the enum value and return the string
- [x] 2.4 Update `processAlgorithm()` to pass execution_mode to `VectorizationRequest` or merge into parameters
- [x] 2.5 Add validation: reject "tiled" mode for non-regional profiles with clear error message
- [x] 2.6 Add warning log when user selects "strict" mode for rasters exceeding auto threshold

## 3. VectorizationRequest model update

- [x] 3.1 Add `execution_mode: str = "auto"` field to `VectorizationRequest` model
- [x] 3.2 Ensure backward compatibility: default value maintains existing behavior

## 4. Specs validation

- [x] 4.1 Verify all spec scenarios from `auto-execution-mode/spec.md` are covered by implementation
- [x] 4.2 Verify all spec scenarios from `execution-mode-ui/spec.md` are covered by implementation
- [x] 4.3 Verify modified specs for `local-image-vectorization` and `vectorization-profiles` are satisfied

## 5. Tests

- [ ] 5.1 Add unit test for `_resolve_execution_mode()` with all combinations (auto/strict/tiled × small/large raster × regional/non-regional profile)
- [ ] 5.2 Add unit test for `_check_auto_threshold()` with rasters at, below, and above the 75% threshold
- [ ] 5.3 Add integration test for auto mode triggering tiled execution on large raster
- [ ] 5.4 Add test for strict mode warning on large raster (warning emitted, execution proceeds)
- [ ] 5.5 Add test for tiled mode rejection on edge/linear profiles
- [ ] 5.6 Add test for execution_mode parameter override of JSON memory_policy

## 6. Documentation

- [x] 6.1 Update `docs/mvp-strict-usage.md` with new execution mode parameter and auto-detection behavior
- [x] 6.2 Update `docs/architecture.md` with execution mode flow diagram
- [x] 6.3 Update `docs/processing-provider-benchmark.md` if applicable with auto vs strict vs tiled performance notes
