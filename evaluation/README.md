# Evaluation Toolkit

This directory contains the reference templates and the lightweight tooling used to
check the `regional-high-precision` profile against the official baseline.

## What lives here

- `templates/dataset.template.md`: dataset manifest template and field contract.
- `templates/metrics_thresholds.template.md`: baseline metrics and acceptance rules.
- `templates/report_format.template.md`: JSON report shape emitted by the evaluator.

## Reference files

- `data/reference/baseline_thresholds.json`: baseline thresholds used by the script.
- `data/reference/dataset_manifest.template.json`: dataset manifest template.

## Runner

Use the script from the repository root:

```bash
python3 scripts/evaluate_regional_profile.py path/to/run-output.json
```

The script:

- reads one or more JSON run outputs, including directories of `*.json` files
- compares each run against the baseline thresholds
- prints a JSON report to stdout
- exits with a nonzero status when any regression is detected

## Expected run output shape

The evaluator expects each run to expose metrics either at `summary.metrics` or
directly under `metrics`.

```json
{
  "run_id": "regional-001",
  "profile": "regional-high-precision",
  "dataset_id": "regional-mvp-v1",
  "summary": {
    "metrics": {
      "mean_iou": 0.93,
      "boundary_f1": 0.91
    }
  }
}
```
