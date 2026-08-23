from __future__ import annotations

from pydantic import ValidationError
import pytest

from agentic_systems.schemas.migrations import (
    SPEC_SCHEMA_VERSION,
    SchemaMigrationError,
    migrate_runtime_payload,
    migrate_spec_payload,
)


def test_v2_spec_migration_is_explicit_idempotent_and_non_mutating() -> None:
    legacy = {"version": "2.0", "id": "calculator", "tool_names": ["math.add"]}
    migrated = migrate_spec_payload("agent", legacy)
    assert legacy == {
        "version": "2.0",
        "id": "calculator",
        "tool_names": ["math.add"],
    }
    assert migrated == {
        "schema_version": SPEC_SCHEMA_VERSION,
        "name": "calculator",
        "tool_names": ["math.add"],
    }
    assert migrate_spec_payload("agent", migrated) == migrated


def test_unknown_schema_migrations_fail_early() -> None:
    with pytest.raises(SchemaMigrationError, match="No system migration"):
        migrate_spec_payload("system", {"schema_version": "0.9", "name": "old"})
    with pytest.raises(SchemaMigrationError, match="Unsupported target"):
        migrate_spec_payload("tool", {"name": "x"}, target_version="spec.v2")


def test_runtime_2_0_aliases_migrate_to_closed_schema() -> None:
    runtime = migrate_runtime_payload(
        {
            "provider": "python-runtime",
            "model": "deterministic",
            "region": "local",
            "scheduler": {"max_tool_calls": 0},
        }
    )
    assert runtime.model_id == "deterministic"
    assert runtime.region_name == "local"
    assert runtime.limits.max_tool_calls == 0
    with pytest.raises(ValidationError):
        migrate_runtime_payload({"provider": "python-runtime", "unknown": True})
