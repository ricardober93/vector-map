#!/usr/bin/env python3
"""Evaluate regional profile run outputs against the reference baseline.

The script is intentionally stdlib-only so it can run in CI, locally, or inside a
release hook without extra dependencies.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable, Sequence


def repo_root() -> Path:
    """Return the repository root based on this script location."""

    return Path(__file__).resolve().parent.parent


def default_baseline_path() -> Path:
    """Return the default baseline threshold file."""

    return repo_root() / "data" / "reference" / "baseline_thresholds.json"


def read_json(path: Path) -> Any:
    """Read and decode JSON from a file."""

    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def discover_json_files(inputs: Sequence[Path]) -> list[Path]:
    """Expand input paths into a deterministic list of JSON files."""

    discovered: list[Path] = []
    for path in inputs:
        if not path.exists():
            raise FileNotFoundError(f"input path does not exist: {path}")
        if path.is_dir():
            discovered.extend(sorted(candidate for candidate in path.rglob("*.json") if candidate.is_file()))
        else:
            discovered.append(path)
    unique: list[Path] = []
    seen: set[Path] = set()
    for path in discovered:
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(path)
    return unique


def coerce_number(value: Any) -> float:
    """Convert a JSON value to a float, rejecting booleans and non-numeric values."""

    if isinstance(value, bool):
        raise ValueError("boolean values are not valid numeric metrics")
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        return float(value.strip())
    raise ValueError(f"expected a numeric value, got {type(value).__name__}")


def extract_metric_map(record: dict[str, Any]) -> dict[str, Any]:
    """Extract the metric mapping from a single run record."""

    summary = record.get("summary")
    if isinstance(summary, dict):
        metrics = summary.get("metrics")
        if isinstance(metrics, dict):
            return metrics
        if summary and all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in summary.values()):
            return summary

    metrics = record.get("metrics")
    if isinstance(metrics, dict):
        return metrics

    results = record.get("results")
    if isinstance(results, dict):
        return results

    raise ValueError("run output does not contain metrics at summary.metrics or metrics")


def extract_run_records(document: Any, source: Path) -> list[dict[str, Any]]:
    """Normalize a JSON document into a list of run records."""

    if isinstance(document, list):
        items = document
        parent_profile = None
        parent_dataset_id = None
    elif isinstance(document, dict) and isinstance(document.get("runs"), list):
        items = document["runs"]
        parent_profile = document.get("profile")
        parent_dataset_id = document.get("dataset_id")
    else:
        items = [document]
        parent_profile = None
        parent_dataset_id = None

    runs: list[dict[str, Any]] = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"{source}: run entry #{index} is not a JSON object")
        runs.append(
            {
                "source": str(source),
                "run_id": item.get("run_id") or item.get("id") or f"{source.stem}#{index}",
                "profile": item.get("profile") or item.get("profile_name") or parent_profile,
                "dataset_id": item.get("dataset_id") or parent_dataset_id,
                "metrics": extract_metric_map(item),
            }
        )
    return runs


def normalize_direction(direction: str) -> str:
    """Normalize a direction keyword."""

    value = direction.strip().lower()
    aliases = {
        "ge": "gte",
        "gte": "gte",
        "greater_or_equal": "gte",
        "greater_equal": "gte",
        "le": "lte",
        "lte": "lte",
        "less_or_equal": "lte",
        "less_equal": "lte",
        "gt": "gt",
        "lt": "lt",
        "eq": "eq",
    }
    if value not in aliases:
        raise ValueError(f"unsupported threshold direction: {direction!r}")
    return aliases[value]


def compare_metric(value: Any, rule: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    """Compare a single metric value with its baseline rule."""

    direction = normalize_direction(str(rule["direction"]))
    threshold = coerce_number(rule["threshold"])
    actual = coerce_number(value)

    if direction == "gte":
        passed = actual >= threshold
    elif direction == "gt":
        passed = actual > threshold
    elif direction == "lte":
        passed = actual <= threshold
    elif direction == "lt":
        passed = actual < threshold
    elif direction == "eq":
        passed = actual == threshold
    else:
        raise ValueError(f"unsupported direction: {direction}")

    if direction in {"gte", "gt"}:
        delta = actual - threshold
    elif direction in {"lte", "lt"}:
        delta = threshold - actual
    else:
        delta = actual - threshold

    detail = {
        "value": actual,
        "threshold": threshold,
        "direction": direction,
        "status": "pass" if passed else "fail",
        "delta": delta,
    }
    return passed, detail


def compare_run(run: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    """Compare one run against the baseline and build a report entry."""

    checks: list[dict[str, Any]] = []
    regressions: list[dict[str, Any]] = []
    status = "pass"

    if baseline.get("profile") is not None and run.get("profile") != baseline.get("profile"):
        status = "fail"
        regression = {
            "metric": "profile",
            "value": run.get("profile"),
            "expected": baseline.get("profile"),
            "reason": "profile does not match baseline",
        }
        checks.append({"metric": "profile", "value": run.get("profile"), "expected": baseline.get("profile"), "status": "fail"})
        regressions.append(regression)

    if baseline.get("dataset_id") is not None and run.get("dataset_id") != baseline.get("dataset_id"):
        status = "fail"
        regression = {
            "metric": "dataset_id",
            "value": run.get("dataset_id"),
            "expected": baseline.get("dataset_id"),
            "reason": "dataset does not match baseline",
        }
        checks.append(
            {
                "metric": "dataset_id",
                "value": run.get("dataset_id"),
                "expected": baseline.get("dataset_id"),
                "status": "fail",
            }
        )
        regressions.append(regression)

    thresholds = baseline["metrics"]
    for metric_name, rule in thresholds.items():
        if metric_name not in run["metrics"]:
            status = "fail"
            check = {
                "metric": metric_name,
                "status": "fail",
                "reason": "metric is missing from run output",
                "threshold": coerce_number(rule["threshold"]),
                "direction": normalize_direction(str(rule["direction"])),
            }
            checks.append(check)
            regressions.append(
                {
                    "metric": metric_name,
                    "reason": "metric is missing from run output",
                    "threshold": coerce_number(rule["threshold"]),
                    "direction": normalize_direction(str(rule["direction"])),
                }
            )
            continue

        passed, detail = compare_metric(run["metrics"][metric_name], rule)
        check = {"metric": metric_name, **detail}
        checks.append(check)
        if not passed:
            status = "fail"
            regressions.append(
                {
                    "metric": metric_name,
                    "value": detail["value"],
                    "threshold": detail["threshold"],
                    "direction": detail["direction"],
                    "reason": "value below threshold" if detail["direction"] in {"gte", "gt"} else "value above threshold" if detail["direction"] in {"lte", "lt"} else "value does not match threshold",
                }
            )

    return {
        "source": run["source"],
        "run_id": run["run_id"],
        "profile": run.get("profile"),
        "dataset_id": run.get("dataset_id"),
        "status": status,
        "checks": checks,
        "regressions": regressions,
    }


def load_baseline(path: Path) -> dict[str, Any]:
    """Load and validate the baseline threshold file."""

    document = read_json(path)
    if not isinstance(document, dict):
        raise ValueError(f"baseline file must be a JSON object: {path}")
    if int(document.get("schema_version", 0)) != 1:
        raise ValueError(f"unsupported baseline schema version in {path}")
    metrics = document.get("metrics")
    if not isinstance(metrics, dict) or not metrics:
        raise ValueError(f"baseline file must define a non-empty metrics object: {path}")
    for metric_name, rule in metrics.items():
        if not isinstance(rule, dict):
            raise ValueError(f"baseline rule for {metric_name!r} must be an object")
        if "direction" not in rule or "threshold" not in rule:
            raise ValueError(f"baseline rule for {metric_name!r} must define direction and threshold")
    return document


def build_report(baseline: dict[str, Any], runs: list[dict[str, Any]], baseline_source: Path) -> dict[str, Any]:
    """Build the final report structure."""

    run_reports = [compare_run(run, baseline) for run in runs]
    regressions: list[dict[str, Any]] = []
    for run_report in run_reports:
        for regression in run_report["regressions"]:
            entry = dict(regression)
            entry["run_id"] = run_report["run_id"]
            entry["source"] = run_report["source"]
            regressions.append(entry)
    status = "fail" if regressions else "pass"
    return {
        "schema_version": 1,
        "status": status,
        "baseline": {
            "baseline_name": baseline.get("baseline_name"),
            "profile": baseline.get("profile"),
            "dataset_id": baseline.get("dataset_id"),
            "source": str(baseline_source),
        },
        "run_count": len(run_reports),
        "runs": run_reports,
        "regressions": regressions,
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "inputs",
        nargs="+",
        help="JSON run output files or directories containing JSON run outputs",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=default_baseline_path(),
        help="Path to the baseline threshold JSON file",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the evaluator and return an exit code."""

    args = parse_args(argv)
    try:
        baseline = load_baseline(args.baseline)
        json_files = discover_json_files([Path(item) for item in args.inputs])
        if not json_files:
            raise ValueError("no JSON run outputs were found")

        runs: list[dict[str, Any]] = []
        for path in json_files:
            document = read_json(path)
            runs.extend(extract_run_records(document, path))

        report = build_report(baseline, runs, args.baseline)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    json.dump(report, sys.stdout, indent=2, sort_keys=False)
    sys.stdout.write("\n")
    return 1 if report["status"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
