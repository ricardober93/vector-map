#!/usr/bin/env python3
"""Compare vectorization profiles using JSON run outputs."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Sequence


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def discover_json(inputs: list[Path]) -> list[Path]:
    files: list[Path] = []
    for item in inputs:
        if not item.exists():
            raise FileNotFoundError(f"missing input: {item}")
        if item.is_dir():
            files.extend(sorted(p for p in item.rglob("*.json") if p.is_file()))
        else:
            files.append(item)
    return files


def normalize_runs(document: Any, source: Path) -> list[dict[str, Any]]:
    if isinstance(document, list):
        candidates = document
    elif isinstance(document, dict) and isinstance(document.get("runs"), list):
        candidates = document["runs"]
    else:
        candidates = [document]

    runs: list[dict[str, Any]] = []
    for idx, item in enumerate(candidates, start=1):
        if not isinstance(item, dict):
            continue
        metrics = item.get("metrics") or item.get("summary", {}).get("metrics")
        if not isinstance(metrics, dict):
            continue
        profile = item.get("profile")
        if not profile:
            continue
        runs.append(
            {
                "id": item.get("run_id") or f"{source.stem}#{idx}",
                "profile": profile,
                "dataset_id": item.get("dataset_id"),
                "metrics": metrics,
                "source": str(source),
            }
        )
    return runs


def to_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def aggregate(runs: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    counts: dict[str, int] = defaultdict(int)

    for run in runs:
        profile = str(run["profile"])
        counts[profile] += 1
        for metric_name, metric_value in run["metrics"].items():
            value = to_float(metric_value)
            if value is not None:
                grouped[profile][str(metric_name)].append(value)

    summary: dict[str, Any] = {}
    for profile, metrics in grouped.items():
        summary[profile] = {
            "run_count": counts[profile],
            "metrics_mean": {
                metric: round(sum(values) / len(values), 6)
                for metric, values in metrics.items()
                if values
            },
        }
    return summary


def score_profile(metrics_mean: dict[str, float]) -> float:
    weights = {
        "mean_iou": 0.35,
        "boundary_f1": 0.3,
        "precision": 0.2,
        "recall": 0.1,
        "geometry_valid_ratio": 0.05,
    }
    score = 0.0
    for metric, weight in weights.items():
        score += float(metrics_mean.get(metric, 0.0)) * weight
    return round(score, 6)


def rank(summary: dict[str, Any]) -> list[dict[str, Any]]:
    ranking: list[dict[str, Any]] = []
    for profile, payload in summary.items():
        metrics_mean = payload.get("metrics_mean", {})
        ranking.append(
            {
                "profile": profile,
                "score": score_profile(metrics_mean),
                "run_count": payload.get("run_count", 0),
                "metrics_mean": metrics_mean,
            }
        )
    return sorted(ranking, key=lambda item: item["score"], reverse=True)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", help="Run output JSON files or directories")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        files = discover_json([Path(item) for item in args.inputs])
        runs: list[dict[str, Any]] = []
        for file_path in files:
            runs.extend(normalize_runs(read_json(file_path), file_path))
        if not runs:
            raise ValueError("no comparable runs found (require profile + metrics)")

        summary = aggregate(runs)
        ranking = rank(summary)
        report = {
            "schema_version": 1,
            "run_count": len(runs),
            "profiles": summary,
            "ranking": ranking,
            "winner": ranking[0]["profile"] if ranking else None,
        }
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    json.dump(report, sys.stdout, indent=2, sort_keys=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
