# Report Format Template

The evaluator prints a JSON report that can be stored in CI artifacts or used by
release tooling.

## Top-level fields

- `schema_version`: report schema version
- `status`: `pass` or `fail`
- `baseline`: baseline metadata used for the comparison
- `run_count`: number of evaluated runs
- `runs`: per-run comparison results
- `regressions`: flattened list of every failing check

## Per-run fields

- `source`: original file or directory that produced the run
- `run_id`: run identifier from the input, when available
- `profile`: profile name from the input
- `dataset_id`: dataset identifier from the input
- `status`: `pass` or `fail`
- `checks`: metric-by-metric comparison details
- `regressions`: failing checks for that run

## Example

```json
{
  "schema_version": 1,
  "status": "fail",
  "baseline": {
    "baseline_name": "regional-high-precision-mvp",
    "profile": "regional-high-precision",
    "dataset_id": "regional-mvp-v1",
    "source": "data/reference/baseline_thresholds.json"
  },
  "run_count": 1,
  "runs": [
    {
      "source": "artifacts/run-output.json",
      "run_id": "regional-001",
      "profile": "regional-high-precision",
      "dataset_id": "regional-mvp-v1",
      "status": "fail",
      "checks": [
        {
          "metric": "mean_iou",
          "value": 0.89,
          "threshold": 0.9,
          "direction": "gte",
          "status": "fail"
        }
      ],
      "regressions": [
        {
          "metric": "mean_iou",
          "value": 0.89,
          "threshold": 0.9,
          "direction": "gte",
          "reason": "value below threshold"
        }
      ]
    }
  ],
  "regressions": [
    {
      "run_id": "regional-001",
      "metric": "mean_iou",
      "value": 0.89,
      "threshold": 0.9,
      "direction": "gte",
      "reason": "value below threshold"
    }
  ]
}
```
