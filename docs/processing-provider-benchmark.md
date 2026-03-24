# Processing Provider Benchmark Notes

This note records decisions used to stabilize `Vector Map` for QGIS 3.44+.

## Official references

- PyQGIS Developer Cookbook: Processing provider and algorithm patterns.
- QGIS API docs: `QgsProcessingParameterFile`, `QgsProcessingParameterRasterLayer`,
  and `QgsProcessingParameterVectorDestination`.

## Public plugin references reviewed

- ProcessX (QGIS Plugin Repository) as a Processing-provider style reference.
- QGIS Processing provider examples from the PyQGIS cookbook.

## Decisions applied

1. Use typed raster input via `QgsProcessingParameterRasterLayer`.
2. Use typed vector output via `QgsProcessingParameterVectorDestination`.
3. Keep `PROFILE` and JSON `PARAMETERS` controls for profile-specific behavior.
4. Keep provider diagnostics in QGIS logs to simplify support/debugging.
5. Declare compatibility target explicitly as QGIS 3.44+.

## Why these decisions

- Prevent parameter-signature mismatches in modern QGIS runtimes.
- Improve Toolbox/Modeler/Batch UX consistency with native providers.
- Reduce plugin load-time failures caused by legacy parameter signatures.
