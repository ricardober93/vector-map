## Tasks for smart-engine-auto-selection

## 1. OpenCVVectorizationEngine - Add is_available()

- [x] 1.1 Add `is_opencv_available()` helper function in opencv.py
- [x] 1.2 Add `is_available()` static method to OpenCVVectorizationEngine class
- [x] 1.3 Check version >= 4.8.0 in availability check

## 2. EngineRegistry - Handle 'auto' engine selection

- [x] 2.1 Modify `resolve()` method to check for `engine_name == "auto"`
- [x] 2.2 Add `_resolve_best_available_engine()` private method
- [x] 2.3 Implement priority: OpenCV (if available) > Classic
- [x] 2.4 Add logging for engine selection decisions
- [x] 2.5 Handle fallback to classic when OpenCV not available

## 3. VectorizeImageAlgorithm - Pass 'auto' to profile

- [x] 3.1 Update logic to pass `"auto"` when user selects auto in dropdown
- [x] 3.2 Explicitly pass `"classic-local"` and `"opencv-local"` for explicit selections

## 4. Tests

- [x] 4.1 Test auto selects OpenCV when available
- [x] 4.2 Test auto falls back to classic when OpenCV unavailable
- [x] 4.3 Test explicit classic bypasses auto logic
- [x] 4.4 Test explicit opencv uses opencv
- [x] 4.5 Test version check (>= 4.8.0)
- [x] 4.6 Test version rejection (< 4.8.0)
- [x] 4.7 Test logging of engine selection
- [x] 4.8 Integration test with real registry

## 5. Documentation

- [ ] 5.1 Update `docs/architecture.md` with engine selection logic
- [ ] 5.2 Update `docs/mvp-strict-usage.md` if applicable