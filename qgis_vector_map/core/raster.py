"""Raster loading and normalization helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .errors import ConfigurationError, DependencyError

Pixel = Any
MAX_PILLOW_IMAGE_PIXELS = 1_000_000_000
DEFAULT_MAX_PIXELS = 200_000_000
DEFAULT_MAX_ESTIMATED_BYTES = 8 * 1024 * 1024 * 1024
DEFAULT_CHUNK_SIZE = 2048


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


def _coerce_positive_int(value: Any, *, field_name: str, default: int) -> int:
    if value is None:
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigurationError(
            f"Invalid raster loading option '{field_name}': {value!r}."
        ) from exc
    if parsed <= 0:
        raise ConfigurationError(
            f"Invalid raster loading option '{field_name}': {parsed}. Expected > 0."
        )
    return parsed


def _format_bytes(value: int) -> str:
    gib = value / (1024**3)
    return f"{value:,} bytes (~{gib:.2f} GiB)"


def _pixel_to_grayscale(pixel: Pixel) -> int:
    if isinstance(pixel, tuple):
        channels = tuple(int(channel) for channel in pixel[:3])
        if len(channels) == 1:
            gray = int(channels[0])
        else:
            r, g, b = (channels + (0, 0, 0))[:3]
            gray = int(round(0.299 * r + 0.587 * g + 0.114 * b))
    else:
        gray = int(pixel)
    return max(0, min(255, gray))


@contextmanager
def _temporary_max_image_pixels(image_module: Any):
    """Temporarily raise Pillow's decompression-bomb threshold for controlled fallback loads."""

    previous_value = getattr(image_module, "MAX_IMAGE_PIXELS", None)
    image_module.MAX_IMAGE_PIXELS = MAX_PILLOW_IMAGE_PIXELS
    try:
        yield
    finally:
        image_module.MAX_IMAGE_PIXELS = previous_value


@dataclass(frozen=True)
class RasterFrame:
    """In-memory raster representation used by the engines."""

    pixels: tuple[tuple[Pixel, ...], ...]
    width: int
    height: int
    bands: int
    source_name: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @dataclass(frozen=True)
    class LoadOptions:
        """Configurable limits for raster loading in local runtimes."""

        max_pixels: int = DEFAULT_MAX_PIXELS
        max_estimated_bytes: int = DEFAULT_MAX_ESTIMATED_BYTES
        profile_mode: str | None = None
        chunk_size: int = DEFAULT_CHUNK_SIZE

        @classmethod
        def from_parameters(
            cls,
            parameters: Mapping[str, Any] | None = None,
            *,
            profile_mode: str | None = None,
        ) -> RasterFrame.LoadOptions:
            values = dict(parameters or {})
            return cls(
                max_pixels=_coerce_positive_int(
                    values.get("max_pixels"),
                    field_name="max_pixels",
                    default=DEFAULT_MAX_PIXELS,
                ),
                max_estimated_bytes=_coerce_positive_int(
                    values.get("max_estimated_bytes"),
                    field_name="max_estimated_bytes",
                    default=DEFAULT_MAX_ESTIMATED_BYTES,
                ),
                profile_mode=profile_mode,
                chunk_size=_coerce_positive_int(
                    values.get("chunk_size"),
                    field_name="chunk_size",
                    default=DEFAULT_CHUNK_SIZE,
                ),
            )

    @classmethod
    def from_matrix(
        cls,
        matrix: Sequence[Sequence[Any]],
        *,
        source_name: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> RasterFrame:
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
    def load(
        cls,
        source: Any,
        *,
        options: RasterFrame.LoadOptions | None = None,
    ) -> RasterFrame:
        load_options = options or cls.LoadOptions()
        if isinstance(source, RasterFrame):
            return source
        if isinstance(source, (str, Path)):
            return cls._load_from_path(Path(source), options=load_options)
        if _is_sequence_like(source):
            return cls.from_matrix(source)
        if isinstance(source, Mapping) and "pixels" in source:
            return cls.from_matrix(
                source["pixels"],
                source_name=str(source.get("source_name") or source.get("name") or ""),
            )
        raise ConfigurationError(
            "Unsupported raster source. Provide a RasterFrame, "
            "a matrix of pixels, or a path to a raster file."
        )

    @classmethod
    def _load_from_path(
        cls, path: Path, *, options: RasterFrame.LoadOptions
    ) -> RasterFrame:
        if not path.exists():
            raise ConfigurationError(f"Raster input does not exist: {path}")

        try:
            return cls._load_with_gdal(path, options=options)
        except Exception as gdal_error:
            if cls._is_preflight_error(gdal_error):
                raise gdal_error
            if cls._is_memory_error(gdal_error):
                raise DependencyError(
                    cls._build_memory_error_message(path=path, gdal_error=gdal_error)
                ) from gdal_error
            try:
                return cls._load_with_pillow(path)
            except Exception as pillow_error:
                raise DependencyError(
                    "Raster loading failed. "
                    f"GDAL path error: {gdal_error!r}. "
                    f"Pillow fallback error: {pillow_error!r}. "
                    "In QGIS, local rasters are loaded with GDAL first; "
                    "the Pillow fallback currently allows up to "
                    f"{MAX_PILLOW_IMAGE_PIXELS:,} pixels."
                ) from pillow_error

    @classmethod
    def _load_with_pillow(cls, path: Path) -> RasterFrame:
        try:
            from PIL import Image  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dependency
            raise DependencyError(
                "Pillow is not available for raster fallback loading."
            ) from exc

        try:
            with _temporary_max_image_pixels(Image):
                with Image.open(path) as image:  # type: ignore[union-attr]
                    image = image.convert("RGB")
                    width, height = image.size
                    pixels = tuple(
                        tuple(
                            tuple(int(channel) for channel in image.getpixel((x, y)))
                            for x in range(width)
                        )
                        for y in range(height)
                    )
        except Exception as exc:
            raise ConfigurationError(
                "Pillow could not load the raster file. "
                f"The fallback limit is {MAX_PILLOW_IMAGE_PIXELS:,} pixels."
            ) from exc

        return cls(
            pixels=pixels,
            width=width,
            height=height,
            bands=3,
            source_name=path.name,
            metadata={"source_path": str(path)},
        )

    @classmethod
    def _load_with_gdal(
        cls, path: Path, *, options: RasterFrame.LoadOptions
    ) -> RasterFrame:
        gdal_error: Exception | None = None
        try:
            from osgeo import gdal  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dependency
            gdal_error = exc
        else:
            dataset = gdal.Open(str(path))  # type: ignore[union-attr]
            if dataset is None:
                raise ConfigurationError(f"GDAL could not open raster file: {path}")
            preflight = cls._preflight_gdal_dataset(dataset, gdal, path=path, options=options)
            if options.profile_mode == "regional":
                return cls._load_regional_with_gdal_chunks(
                    dataset=dataset,
                    path=path,
                    chunk_size=options.chunk_size,
                    width=preflight["width"],
                    height=preflight["height"],
                    bands=preflight["bands"],
                )
            array = dataset.ReadAsArray()
            if array is None:
                raise ConfigurationError(f"GDAL returned no data for raster file: {path}")
            if getattr(array, "ndim", 0) == 2:
                pixels = tuple(tuple(int(value) for value in row) for row in array.tolist())
                bands = 1
                height = len(pixels)
                width = len(pixels[0]) if pixels else 0
            else:
                bands = int(array.shape[0])
                height = int(array.shape[1])
                width = int(array.shape[2])
                pixels = tuple(
                    tuple(
                        tuple(int(array[band, y, x]) for band in range(bands)) for x in range(width)
                    )
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

        raise DependencyError(f"GDAL is not available for raster loading: {gdal_error!r}.")

    @classmethod
    def _is_memory_error(cls, exc: Exception) -> bool:
        current: Exception | None = exc
        seen: set[int] = set()
        while current is not None:
            if isinstance(current, MemoryError):
                return True
            marker = id(current)
            if marker in seen:
                break
            seen.add(marker)
            next_exc = getattr(current, "__cause__", None) or getattr(current, "__context__", None)
            if next_exc is current:
                break
            current = next_exc if isinstance(next_exc, Exception) else None
        return False

    @classmethod
    def _is_preflight_error(cls, exc: Exception) -> bool:
        return isinstance(exc, ConfigurationError) and str(exc).startswith(
            "Raster preflight aborted due to estimated memory pressure."
        )

    @classmethod
    def _build_memory_error_message(cls, *, path: Path, gdal_error: Exception) -> str:
        return (
            "Raster loading failed due to memory pressure while reading with GDAL. "
            f"Source: {path}. Error: {gdal_error!r}. "
            "Pillow fallback was skipped to avoid repeating a high-memory full-image load. "
            "Try clipping the raster to an AOI, downsampling, or processing tiled chunks."
        )

    @classmethod
    def _preflight_gdal_dataset(
        cls,
        dataset: Any,
        gdal_module: Any,
        *,
        path: Path,
        options: RasterFrame.LoadOptions,
    ) -> Mapping[str, int]:
        width = int(getattr(dataset, "RasterXSize", 0) or 0)
        height = int(getattr(dataset, "RasterYSize", 0) or 0)
        bands = max(1, int(getattr(dataset, "RasterCount", 1) or 1))
        if width <= 0 or height <= 0:
            raise ConfigurationError(
                f"GDAL returned invalid raster dimensions for '{path}': {width}x{height}."
            )

        bytes_per_sample = 8
        try:
            first_band = dataset.GetRasterBand(1)
            data_type = getattr(first_band, "DataType", None)
            bits = int(gdal_module.GetDataTypeSize(data_type))
            if bits > 0:
                bytes_per_sample = max(1, bits // 8)
        except Exception:
            bytes_per_sample = 8

        pixels = width * height
        estimated_bytes = pixels * bands * bytes_per_sample
        if pixels > options.max_pixels or estimated_bytes > options.max_estimated_bytes:
            raise ConfigurationError(
                "Raster preflight aborted due to estimated memory pressure. "
                f"Size={width}x{height}, bands={bands}, pixels={pixels:,}, "
                f"estimated={_format_bytes(estimated_bytes)}. "
                f"Thresholds: max_pixels={options.max_pixels:,}, "
                f"max_estimated_bytes={_format_bytes(options.max_estimated_bytes)}. "
                "Recommended actions: clip AOI, downsample, or process in smaller tiles."
            )
        return {
            "width": width,
            "height": height,
            "bands": bands,
            "estimated_bytes": estimated_bytes,
        }

    @classmethod
    def _load_regional_with_gdal_chunks(
        cls,
        *,
        dataset: Any,
        path: Path,
        chunk_size: int,
        width: int,
        height: int,
        bands: int,
    ) -> RasterFrame:
        rows: list[tuple[int, ...]] = []
        for y_off in range(0, height, chunk_size):
            y_size = min(chunk_size, height - y_off)
            window = dataset.ReadAsArray(0, y_off, width, y_size)
            if window is None:
                raise ConfigurationError(
                    f"GDAL returned no data for raster window y={y_off}:{y_off + y_size}."
                )
            ndim = int(getattr(window, "ndim", 0))
            if ndim == 2:
                chunk_rows = window.tolist()
                for row in chunk_rows:
                    rows.append(tuple(max(0, min(255, int(value))) for value in row))
                continue
            if ndim != 3:
                raise ConfigurationError(
                    f"Unsupported GDAL array shape for regional chunk load: ndim={ndim}."
                )

            chunk = window.tolist()
            chunk_band_count = len(chunk)
            if chunk_band_count == 0:
                raise ConfigurationError(
                    "GDAL returned an empty band stack for regional chunk load."
                )
            chunk_height = len(chunk[0])
            for y_idx in range(chunk_height):
                row: list[int] = []
                for x_idx in range(width):
                    if chunk_band_count == 1:
                        gray = int(chunk[0][y_idx][x_idx])
                    else:
                        gray = _pixel_to_grayscale(
                            tuple(int(chunk[band][y_idx][x_idx]) for band in range(chunk_band_count))
                        )
                    row.append(max(0, min(255, gray)))
                rows.append(tuple(row))

        metadata: dict[str, Any] = {
            "source_path": str(path),
            "load_strategy": "gdal-regional-chunked",
            "chunk_size": chunk_size,
            "source_bands": bands,
        }
        projection = dataset.GetProjection()
        if projection:
            metadata["crs_wkt"] = projection
        geotransform = dataset.GetGeoTransform(can_return_null=True)
        if geotransform:
            metadata["geotransform"] = tuple(float(value) for value in geotransform)

        return cls(
            pixels=tuple(rows),
            width=width,
            height=height,
            bands=1,
            source_name=path.name,
            metadata=metadata,
        )

    def pixel(self, x: int, y: int) -> Pixel:
        return self.pixels[y][x]

    def grayscale_matrix(self) -> tuple[tuple[int, ...], ...]:
        gray_rows: list[tuple[int, ...]] = []
        for row in self.pixels:
            gray_row: list[int] = []
            for pixel in row:
                gray_row.append(_pixel_to_grayscale(pixel))
            gray_rows.append(tuple(gray_row))
        return tuple(gray_rows)

    def rgb_matrix(self) -> tuple[tuple[tuple[int, int, int], ...], ...]:
        rgb_rows: list[tuple[tuple[int, int, int], ...]] = []
        for row in self.pixels:
            rgb_row: list[tuple[int, int, int]] = []
            for pixel in row:
                if isinstance(pixel, tuple):
                    channel_values = [int(channel) for channel in pixel[:3]]
                    while len(channel_values) < 3:
                        channel_values.append(0)
                    rgb_row.append((channel_values[0], channel_values[1], channel_values[2]))
                else:
                    value = max(0, min(255, int(pixel)))
                    rgb_row.append((value, value, value))
            rgb_rows.append(tuple(rgb_row))
        return tuple(rgb_rows)
