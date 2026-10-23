"""Model-provider configuration independent from execution frameworks."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from ..engines.names import canonical_engine_name


@dataclass(frozen=True)
class ModelProviderConfig:
    """Declarative model/provider endpoint used by an execution runtime."""

    name: str
    model_id: str | None = None
    region_name: str | None = None
    endpoint: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", canonical_engine_name(self.name))
        object.__setattr__(self, "metadata", dict(self.metadata or {}))

    @property
    def identity(self) -> str:
        return self.name

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


__all__ = ["ModelProviderConfig"]
