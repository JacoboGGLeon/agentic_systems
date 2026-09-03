from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
from pydantic import ValidationError


ROOT = Path(__file__).resolve().parents[2]


def _builder():
    path = ROOT / "scripts" / "build_release_certification.py"
    spec = importlib.util.spec_from_file_location("release_certification_builder", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _route_spec(tmp_path: Path, *, key: str) -> Path:
    for name in ("attestation.json", "semantic.json", "review.md"):
        (tmp_path / name).write_text("{}", encoding="utf-8")
    path = tmp_path / f"{key}.json"
    path.write_text(
        json.dumps(
            {
                "key": key,
                "environment": "Managed test environment",
                "attestation": "attestation.json",
                "semantic_attestation": "semantic.json",
                "review": "review.md",
            }
        ),
        encoding="utf-8",
    )
    return path


def test_authentication_route_specs_are_typed_and_resolve_relative_paths(
    tmp_path: Path,
) -> None:
    module = _builder()

    (route,) = module._load_authentication_specs(
        [_route_spec(tmp_path, key="managed-test")]
    )

    assert route.key == "managed-test"
    assert route.environment == "Managed test environment"
    assert route.attestation == (tmp_path / "attestation.json").resolve()
    assert route.semantic_attestation == (tmp_path / "semantic.json").resolve()
    assert route.review == (tmp_path / "review.md").resolve()


def test_authentication_route_specs_reject_unknown_fields(tmp_path: Path) -> None:
    module = _builder()
    path = _route_spec(tmp_path, key="managed-test")
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["provider_specific_escape_hatch"] = True
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValidationError):
        module._load_authentication_specs([path])


def test_authentication_route_specs_reject_duplicate_identity(
    tmp_path: Path,
) -> None:
    module = _builder()
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()

    with pytest.raises(ValueError, match="Duplicate authentication route key"):
        module._load_authentication_specs(
            [
                _route_spec(first, key="same-route"),
                _route_spec(second, key="same-route"),
            ]
        )
