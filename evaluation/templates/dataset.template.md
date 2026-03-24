# Dataset Template

Use this template to define the reference dataset that is used to evaluate the MVP
baseline for the `regional-high-precision` profile.

## Dataset identity

- `dataset_id`: stable identifier for the reference dataset
- `dataset_name`: human readable name
- `version`: version string for change control
- `profile`: profile covered by the dataset

## Inclusion rules

- Keep the dataset focused on precision-sensitive regional shapes
- Include representative cases for clean fills, fragmented regions, and touching
  boundaries
- Store inputs and ground truth with stable relative paths under `data/reference/`
- Do not change the dataset without updating the baseline and the report history

## Case contract

Each case should include:

- `id`: unique case identifier
- `image_path`: raster source used by the evaluator
- `mask_path`: ground-truth mask or label map
- `vector_path`: canonical vector reference, when available
- `split`: `train`, `validation`, or `test`
- `notes`: optional human context

## Template

```json
{
  "schema_version": 1,
  "dataset_id": "regional-mvp-v1",
  "dataset_name": "Regional MVP reference dataset",
  "version": "1.0.0",
  "profile": "regional-high-precision",
  "cases": [
    {
      "id": "case-001",
      "image_path": "data/reference/images/case-001.png",
      "mask_path": "data/reference/masks/case-001.png",
      "vector_path": "data/reference/vectors/case-001.geojson",
      "split": "test",
      "notes": "Simple compact region"
    }
  ]
}
```
