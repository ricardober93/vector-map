## Tasks for ux-improvements

## MEJORA 6: Smart Output Naming

- [ ] 6.1 Add `_generate_default_layer_name()` method
- [ ] 6.2 Update default layer name in initAlgorithm
- [ ] 6.3 Add tests for naming convention

## MEJORA 1: Validación tiled+edge/linear

- [ ] 1.1 Implement `_validate_execution_mode_for_profile()` 
- [ ] 1.2 Add error message for tiled+edge rejection
- [ ] 1.3 Add error message for tiled+linear rejection
- [ ] 1.4 Add tests for rejection scenarios
- [ ] 1.5 Add test for acceptance (regional)

## MEJORA 2: Output Format dropdown

- [ ] 2.1 Change OUTPUT_FORMAT from String to Enum in initAlgorithm
- [ ] 2.2 Implement output format parsing in processAlgorithm
- [ ] 2.3 Handle enum index to format mapping
- [ ] 2.4 Add tests for format parsing
- [ ] 2.5 Update tests to check enum behavior

## MEJORA 3: Ocultar Canny params para no-edge

- [ ] 3.1 Wrap Canny parameter injection in profile check
- [ ] 3.2 Add tests for edge params filtering
- [ ] 3.3 Verify params NOT injected for regional
- [ ] 3.4 Verify params NOT injected for linear

## Tests

- [ ] Add tests for each improvement
- [ ] Run full test suite
- [ ] Verify no regressions