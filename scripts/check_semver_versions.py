#!/usr/bin/env python3
"""Validate SemVer and version sync for plugin release files."""

from __future__ import annotations

import re
import sys
from pathlib import Path

SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|[0-9A-Za-z-][0-9A-Za-z-]*)"
    r"(?:\.(?:0|[1-9]\d*|[0-9A-Za-z-][0-9A-Za-z-]*))*))?"
    r"(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)


def _read_metadata_version(metadata_path: Path) -> str:
    for line in metadata_path.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("version="):
            return line.split("=", 1)[1].strip()
    raise ValueError(f"No 'version=' entry found in {metadata_path}.")


def _read_init_version(init_path: Path) -> str:
    content = init_path.read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*"([^"]+)"', content)
    if not match:
        raise ValueError(f'No __version__ = "..." entry found in {init_path}.')
    return match.group(1).strip()


def _is_semver(value: str) -> bool:
    return SEMVER_RE.fullmatch(value) is not None


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    metadata_path = root / "qgis_vector_map" / "metadata.txt"
    init_path = root / "qgis_vector_map" / "__init__.py"

    try:
        metadata_version = _read_metadata_version(metadata_path)
        init_version = _read_init_version(init_path)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    errors: list[str] = []
    if not _is_semver(metadata_version):
        errors.append(
            f"metadata.txt version is not valid SemVer: '{metadata_version}'."
        )
    if not _is_semver(init_version):
        errors.append(f"__init__.py __version__ is not valid SemVer: '{init_version}'.")
    if metadata_version != init_version:
        errors.append(
            "Version mismatch between metadata and package init: "
            f"metadata.txt='{metadata_version}' vs __init__.py='{init_version}'."
        )

    if errors:
        print("SemVer check failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"SemVer check passed: version {metadata_version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
