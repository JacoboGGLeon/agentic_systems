"""Explicit migrations for payloads persisted by Agentic Systems 2.1."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any, Literal

from .execution import RuntimeConfigSchema


SPEC_SCHEMA_VERSION = "agentic_systems.spec.v1"
LegacySpecKind = Literal[
    "tool", "skill", "agent", "system", "environment", "eval", "framework"
]


class SchemaMigrationError(ValueError):
    """Raised when no explicit migration path exists."""


def migrate_spec_payload(
    kind: LegacySpecKind,
    payload: Mapping[str, Any],
    *,
    target_version: str = SPEC_SCHEMA_VERSION,
) -> dict[str, Any]:
    """Migrate an unversioned/2.0 persisted Spec to the v1 schema envelope."""

    migrated = deepcopy(dict(payload))
    source_version = str(
        migrated.pop("version", "") or migrated.get("schema_version") or "2.0"
    )
    if source_version == target_version:
        return migrated
    if source_version not in {"2.0", "2.0.0"}:
        raise SchemaMigrationError(
            f"No {kind} migration from {source_version!r} to {target_version!r}."
        )
    if target_version != SPEC_SCHEMA_VERSION:
        raise SchemaMigrationError(f"Unsupported target schema {target_version!r}.")
    if "id" in migrated and "name" not in migrated:
        migrated["name"] = migrated.pop("id")
    migrated["schema_version"] = SPEC_SCHEMA_VERSION
    return migrated


def migrate_runtime_payload(payload: Mapping[str, Any]) -> RuntimeConfigSchema:
    """Parse legacy RuntimeConfig aliases into the closed canonical schema."""

    migrated = deepcopy(dict(payload))
    if "model" in migrated and "model_id" not in migrated:
        migrated["model_id"] = migrated.pop("model")
    if "region" in migrated and "region_name" not in migrated:
        migrated["region_name"] = migrated.pop("region")
    if "scheduler" in migrated and "limits" not in migrated:
        migrated["limits"] = migrated.pop("scheduler")
    return RuntimeConfigSchema.model_validate(migrated)


__all__ = [
    "SPEC_SCHEMA_VERSION",
    "LegacySpecKind",
    "SchemaMigrationError",
    "migrate_runtime_payload",
    "migrate_spec_payload",
]
