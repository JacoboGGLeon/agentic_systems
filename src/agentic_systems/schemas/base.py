"""Shared Pydantic foundations for portable, versioned contracts."""

from __future__ import annotations

from typing import TypeAlias

from pydantic import BaseModel, ConfigDict, JsonValue


JsonScalar: TypeAlias = None | bool | int | float | str


class ContractModel(BaseModel):
    """Closed, immutable contract suitable for JSON Schema generation."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class PersistedSpec(ContractModel):
    """Base for data that can cross process or release boundaries."""

    schema_version: str


__all__ = ["ContractModel", "JsonScalar", "JsonValue", "PersistedSpec"]
