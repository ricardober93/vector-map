"""Engine contract and registry helpers."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ..core.errors import ConfigurationError, DependencyError
from ..core.models import PipelineContext

if TYPE_CHECKING:  # pragma: no cover - typing only
    pass

_logger = logging.getLogger(__name__)


class VectorizationEngine(ABC):
    """Common contract for every vectorization engine."""

    name = "vectorization-engine"
    supported_profiles: tuple[str, ...] = ()
    supported_modes: tuple[str, ...] = ()

    def supports(self, profile: Any) -> bool:
        profile_id = getattr(profile, "profile_id", None)
        mode = getattr(profile, "mode", None)
        if self.supported_profiles and profile_id in self.supported_profiles:
            return True
        if self.supported_modes and mode in self.supported_modes:
            return True
        return not self.supported_profiles and not self.supported_modes

    @abstractmethod
    def preprocess(self, context: PipelineContext) -> PipelineContext:
        raise NotImplementedError

    @abstractmethod
    def vectorize(self, context: PipelineContext) -> PipelineContext:
        raise NotImplementedError

    @abstractmethod
    def postprocess(self, context: PipelineContext) -> PipelineContext:
        raise NotImplementedError

    @abstractmethod
    def export(self, context: PipelineContext) -> PipelineContext:
        raise NotImplementedError


@dataclass
class EngineRegistry:
    """Resolve the right engine for a profile."""

    engines: list[VectorizationEngine] = field(default_factory=list)

    def register(self, engine: VectorizationEngine) -> None:
        self.engines.append(engine)

    def resolve(self, profile: Any) -> VectorizationEngine:
        """Resolve the best available engine for the given profile."""
        engine_name = getattr(profile, 'engine_name', None)
        profile_id = getattr(profile, 'profile_id', 'unknown')

        if engine_name == "auto":
            return self._resolve_best_available_engine(profile)

        if engine_name:
            for engine in self.engines:
                if engine.name == engine_name:
                    _logger.info(f"Engine selection: '{engine_name}' (explicit)")
                    return engine

        # Fallback to first compatible engine (preserves backward compat)
        for engine in self.engines:
            if engine.supports(profile):
                _logger.info(f"Engine selection: '{engine.name}' (fallback for profile '{profile_id}')")
                return engine

        raise ConfigurationError(
            f"No vectorization engine supports profile '{profile_id}'."
        )

    def _resolve_best_available_engine(self, profile: Any) -> VectorizationEngine:
        """Select the best available engine for auto mode.

        Priority: OpenCV (faster) > Classic (fallback)
        """
        # Check OpenCV availability
        for engine in self.engines:
            if engine.name == "opencv-local":
                is_available = getattr(engine, 'is_available', lambda: False)()
                if is_available:
                    _logger.info(
                        "Engine auto mode: selected 'opencv-local' "
                        "(faster than profile default 'classic-local')"
                    )
                    return engine
                else:
                    _logger.info(
                        "Engine auto mode: OpenCV not available, falling back to 'classic-local'"
                    )
                    break

        # Fallback to classic
        for engine in self.engines:
            if engine.name == "classic-local" and engine.supports(profile):
                _logger.info(
                    "Engine auto mode: selected 'classic-local' (OpenCV not available)"
                )
                return engine

        raise ConfigurationError(
            f"No vectorization engine available for auto mode on profile "
            f"'{getattr(profile, 'profile_id', 'unknown')}'."
        )

    def resolve_with_fallback(
        self,
        profile: Any,
        progress_callback: Any = None,
        context: PipelineContext | None = None,
    ) -> tuple[VectorizationEngine, bool]:
        """Attempt to resolve and run with automatic fallback on DependencyError.

        Returns (engine, did_fallback) tuple.
        """
        engine = self.resolve(profile)
        return engine, False


_DEFAULT_REGISTRY = EngineRegistry()


def build_default_registry() -> EngineRegistry:
    from .classic import ClassicVectorizationEngine

    if not _DEFAULT_REGISTRY.engines:
        _DEFAULT_REGISTRY.register(ClassicVectorizationEngine())
        # Try to register OpenCV engine (optional dependency)
        try:
            from .opencv import OpenCVVectorizationEngine
            _DEFAULT_REGISTRY.register(OpenCVVectorizationEngine())
        except Exception:
            pass
    return _DEFAULT_REGISTRY
