# Metrics Thresholds Template

This template defines the official baseline used to block regressions in the MVP.

## Rules

- Use `gte` when larger values are better.
- Use `lte` when smaller values are better.
- Keep thresholds tied to the dataset version and profile version.
- Update the baseline only when the change is intentional and documented.

## Recommended metrics

- `mean_iou`: average overlap score
- `boundary_f1`: boundary quality score
- `precision`: predicted geometry precision
- `recall`: reference coverage score
- `geometry_valid_ratio`: fraction of outputs that pass geometry validation
- `invalid_geometry_count`: hard fail count for invalid geometries

## Template

```json
{
  "schema_version": 1,
  "baseline_name": "regional-high-precision-mvp",
  "profile": "regional-high-precision",
  "dataset_id": "regional-mvp-v1",
  "metrics": {
    "mean_iou": {
      "direction": "gte",
      "threshold": 0.9,
      "unit": "ratio"
    },
    "boundary_f1": {
      "direction": "gte",
      "threshold": 0.88,
      "unit": "ratio"
    },
    "precision": {
      "direction": "gte",
      "threshold": 0.95,
      "unit": "ratio"
    },
    "recall": {
      "direction": "gte",
      "threshold": 0.9,
      "unit": "ratio"
    },
    "geometry_valid_ratio": {
      "direction": "gte",
      "threshold": 1.0,
      "unit": "ratio"
    },
    "invalid_geometry_count": {
      "direction": "lte",
      "threshold": 0,
      "unit": "count"
    }
  }
}
```
