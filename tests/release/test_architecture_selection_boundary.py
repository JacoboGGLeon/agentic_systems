from __future__ import annotations

import ast
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _gate():
    path = ROOT / "scripts" / "check_architecture.py"
    spec = importlib.util.spec_from_file_location("architecture_gate", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_attestation_identity_checks_are_validation_not_runtime_selection() -> None:
    module = _gate()
    attestation = ROOT / "src" / "agentic_systems" / "schemas" / "attestation.py"

    assert module._selection_allowed(attestation) is True


def test_provider_branch_remains_rejected_outside_explicit_boundaries(
    tmp_path: Path,
) -> None:
    module = _gate()
    leaked = module.SOURCE / "application.py"
    tree = ast.parse("if provider == 'openai-runtime':\n    pass\n")

    assert module._selection_violations(leaked, tree) == [
        "application.py:1: concrete selection outside boundary"
    ]
