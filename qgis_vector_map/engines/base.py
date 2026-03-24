"""Engine contract and registry helpers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ..core.errors import ConfigurationError
from ..core.models import PipelineContext

if TYPE_CHECKING:  # pragma: no cover - typing only
    pass


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
        for engine in self.engines:
            if engine.supports(profile):
                return engine
        raise ConfigurationError(
            f"No vectorization engine supports profile {getattr(profile, 'profile_id', profile)!r}."
        )


_DEFAULT_REGISTRY = EngineRegistry()


def build_default_registry() -> EngineRegistry:
    from .classic import ClassicVectorizationEngine

    if not _DEFAULT_REGISTRY.engines:
        _DEFAULT_REGISTRY.register(ClassicVectorizationEngine())
    return _DEFAULT_REGISTRY
