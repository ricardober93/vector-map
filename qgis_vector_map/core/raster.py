"""Raster loading and normalization helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .errors import ConfigurationError, DependencyError

Pixel = Any


def _is_sequence_like(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def _normalize_pixel(pixel: Any) -> Pixel:
    if isinstance(pixel, bool):
        return int(pixel)
    if isinstance(pixel, int):
        return pixel
    if _is_sequence_like(pixel):
        normalized = tuple(int(channel) for channel in pixel)
        if not normalized:
            raise ConfigurationError("Pixel tuples cannot be empty.")
        return normalized
    raise ConfigurationError(f"Unsupported pixel value: {pixel!r}")


@dataclass(frozen=True)
class RasterFrame:
    """In-memory raster representation used by the engines."""

    pixels: tuple[tuple[Pixel, ...], ...]
    width: int
    height: int
    bands: int
    source_name: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_matrix(
        cls,
        matrix: Sequence[Sequence[Any]],
        *,
        source_name: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> "RasterFrame":
        rows: list[tuple[Pixel, ...]] = []
        expected_width: int | None = None
        inferred_bands: int | None = None

        for row in matrix:
            normalized_row = tuple(_normalize_pixel(pixel) for pixel in row)
            if expected_width is None:
                expected_width = len(normalized_row)
            elif len(normalized_row) != expected_width:
                raise ConfigurationError("Raster rows must have consistent width.")
            rows.append(normalized_row)
            if normalized_row and inferred_bands is None:
                first = normalized_row[0]
                inferred_bands = len(first) if isinstance(first, tuple) else 1

        if expected_width is None:
            raise ConfigurationError("Raster matrix cannot be empty.")
        if inferred_bands is None:
            inferred_bands = 1

        return cls(
            pixels=tuple(rows),
            width=expected_width,
            height=len(rows),
            bands=inferred_bands,
            source_name=source_name,
            metadata=dict(metadata or {}),
        )

    @classmethod
    def load(cls, source: Any) -> "RasterFrame":
        if isinstance(source, RasterFrame):
            return source
        if isinstance(source, (str, Path)):
            return cls._load_from_path(Path(source))
        if _is_sequence_like(source):
            return cls.from_matrix(source)
        if isinstance(source, Mapping) and "pixels" in source:
            return cls.from_matrix(source["pixels"], source_name=str(source.get("source_name") or source.get("name") or ""))
        raise ConfigurationError(
            "Unsupported raster source. Provide a RasterFrame, a matrix of pixels, or a path to a raster file."
        )

    @classmethod
    def _load_from_path(cls, path: Path) -> "RasterFrame":
        if not path.exists():
            raise ConfigurationError(f"Raster input does not exist: {path}")

        pillow_error: Exception | None = None
        try:
            from PIL import Image  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dependency
            pillow_error = exc
        else:
            with Image.open(path) as image:  # type: ignore[union-attr]
                image = image.convert("RGB")
                width, height = image.size
                pixels = tuple(tuple(tuple(int(channel) for channel in image.getpixel((x, y))) for x in range(width)) for y in range(height))
                return cls(
                    pixels=pixels,
                    width=width,
                    height=height,
                    bands=3,
                    source_name=path.name,
                    metadata={"source_path": str(path)},
                )

        gdal_error: Exception | None = None
        try:
            from osgeo import gdal  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dependency
            gdal_error = exc
        else:
            dataset = gdal.Open(str(path))  # type: ignore[union-attr]
            if dataset is None:
                raise ConfigurationError(f"GDAL could not open raster file: {path}")
            array = dataset.ReadAsArray()
            if array is None:
                raise ConfigurationError(f"GDAL returned no data for raster file: {path}")
            if getattr(array, "ndim", 0) == 2:
                pixels = tuple(tuple(int(value) for value in row) for row in array.tolist())
                bands = 1
            else:
                bands = int(array.shape[0])
                height = int(array.shape[1])
                width = int(array.shape[2])
                pixels = tuple(
                    tuple(tuple(int(array[band, y, x]) for band in range(bands)) for x in range(width))
                    for y in range(height)
                )
            metadata: dict[str, Any] = {"source_path": str(path)}
            projection = dataset.GetProjection()
            if projection:
                metadata["crs_wkt"] = projection
            geotransform = dataset.GetGeoTransform(can_return_null=True)
            if geotransform:
                metadata["geotransform"] = tuple(float(value) for value in geotransform)
            return cls(
                pixels=pixels,
                width=width,
                height=height,
                bands=bands,
                source_name=path.name,
                metadata=metadata,
            )

        raise DependencyError(
            "Loading raster files requires Pillow or GDAL. "
            f"Missing Pillow import error: {pillow_error!r}; GDAL import error: {gdal_error!r}."
        )

    def pixel(self, x: int, y: int) -> Pixel:
        return self.pixels[y][x]

    def grayscale_matrix(self) -> tuple[tuple[int, ...], ...]:
        gray_rows: list[tuple[int, ...]] = []
        for row in self.pixels:
            gray_row: list[int] = []
            for pixel in row:
                if isinstance(pixel, tuple):
                    channels = pixel[:3]
                    if len(channels) == 1:
                        gray = int(channels[0])
                    else:
                        r, g, b = (channels + (0, 0, 0))[:3]
                        gray = int(round(0.299 * r + 0.587 * g + 0.114 * b))
                else:
                    gray = int(pixel)
                gray_row.append(max(0, min(255, gray)))
            gray_rows.append(tuple(gray_row))
        return tuple(gray_rows)

    def rgb_matrix(self) -> tuple[tuple[tuple[int, int, int], ...], ...]:
        rgb_rows: list[tuple[tuple[int, int, int], ...]] = []
        for row in self.pixels:
            rgb_row: list[tuple[int, int, int]] = []
            for pixel in row:
                if isinstance(pixel, tuple):
                    channels = tuple(int(channel) for channel in (pixel[:3] + (0, 0, 0))[:3])
                    rgb_row.append(channels)
                else:
                    value = max(0, min(255, int(pixel)))
                    rgb_row.append((value, value, value))
            rgb_rows.append(tuple(rgb_row))
        return tuple(rgb_rows)
