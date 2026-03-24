# Reference Data

This directory stores the official baseline inputs used by the evaluation tooling.

## Files

- `baseline_thresholds.json`: acceptance thresholds for the MVP baseline.
- `dataset_manifest.template.json`: dataset manifest template for the reference set.

## Change control

- Update the dataset manifest and baseline thresholds together.
- Keep the `dataset_id` and `profile` values aligned across all reference files.
- Regenerate evaluation evidence before changing baseline thresholds.
