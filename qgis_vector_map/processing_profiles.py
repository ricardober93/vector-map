"""Profile registry for vectorization strategies."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from .core.errors import ConfigurationError


@dataclass(frozen=True)
class ResolvedProfile:
    """Profile definition with merged effective parameters."""

    profile_id: str
    display_name: str
    mode: str
    description: str
    parameters: dict[str, Any]
    engine_name: str = "classic-local"
    export_format: str = "auto"

    def parameter(self, key: str, default: Any = None) -> Any:
        return self.parameters.get(key, default)


@dataclass(frozen=True)
class ProfileDefinition:
    """Immutable profile template used by the registry."""

    profile_id: str
    display_name: str
    mode: str
    description: str
    default_parameters: Mapping[str, Any] = field(default_factory=dict)
    engine_name: str = "classic-local"
    export_format: str = "auto"

    def resolve(self, overrides: Mapping[str, Any] | None = None) -> ResolvedProfile:
        parameters = dict(self.default_parameters)
        effective_engine_name = self.engine_name
        effective_export_format = self.export_format
        if overrides:
            for key, value in dict(overrides).items():
                if key == 'engine_name':
                    effective_engine_name = str(value)
                elif key == 'export_format':
                    effective_export_format = str(value)
                else:
                    parameters[key] = value
        return ResolvedProfile(
            profile_id=self.profile_id,
            display_name=self.display_name,
            mode=self.mode,
            description=self.description,
            parameters=parameters,
            engine_name=effective_engine_name,
            export_format=effective_export_format,
        )


PROFILE_REGISTRY: dict[str, ProfileDefinition] = {
    "regional-high-precision": ProfileDefinition(
        profile_id="regional-high-precision",
        display_name="Regional High Precision",
        mode="regional",
        description="Segmentacion por regiones y polygonizacion de alta precision.",
        default_parameters={
            "max_colors": 8,
            "background_policy": "dominant",
            "drop_background": True,
            "smoothing_radius": 0,
            "min_region_area": 4,
            "min_hole_area": 4,
            "simplify_tolerance": 0.0,
            "connectivity": 4,
            "max_pixels": 500_000_000,
            "max_estimated_bytes": 16 * 1024 * 1024 * 1024,
            "chunk_size": 2048,
            "tile_size": 2048,
            "memory_policy": "strict",
        },
        export_format="auto",
    ),
    "edge-high-precision": ProfileDefinition(
        profile_id="edge-high-precision",
        display_name="Edge High Precision",
        mode="edge",
        description="Deteccion de contornos y conversion a trazos vectoriales.",
        default_parameters={
            "edge_threshold": 0,
            "close_radius": 1,
            "min_line_length": 2,
            "simplify_tolerance": 0.5,
            "max_pixels": 500_000_000,
            "max_estimated_bytes": 16 * 1024 * 1024 * 1024,
            "memory_policy": "strict",
        },
        export_format="auto",
    ),
    "linear-high-precision": ProfileDefinition(
        profile_id="linear-high-precision",
        display_name="Linear High Precision",
        mode="linear",
        description="Extraccion de entidades lineales con esqueletizacion.",
        default_parameters={
            "foreground_threshold": None,
            "foreground_polarity": "dark",
            "open_radius": 1,
            "close_radius": 1,
            "skeletonize": True,
            "min_line_length": 2,
            "simplify_tolerance": 0.5,
            "max_pixels": 500_000_000,
            "max_estimated_bytes": 16 * 1024 * 1024 * 1024,
            "memory_policy": "strict",
        },
        export_format="auto",
    ),
}


def available_profiles() -> tuple[str, ...]:
    return tuple(sorted(PROFILE_REGISTRY.keys()))


def get_profile_definition(profile_id: str) -> ProfileDefinition:
    try:
        return PROFILE_REGISTRY[profile_id]
    except KeyError as exc:
        profiles = ", ".join(available_profiles())
        raise ConfigurationError(
            f"Unknown profile '{profile_id}'. Available profiles: {profiles}."
        ) from exc


def resolve_profile(profile_id: str, overrides: Mapping[str, Any] | None = None) -> ResolvedProfile:
    return get_profile_definition(profile_id).resolve(overrides)


def list_profiles() -> tuple[ProfileDefinition, ...]:
    return tuple(PROFILE_REGISTRY[profile_id] for profile_id in available_profiles())
