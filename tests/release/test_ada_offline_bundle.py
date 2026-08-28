from __future__ import annotations

import hashlib
import importlib.util
import json
import zipfile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]


def _builder():
    path = ROOT / "scripts" / "build_ada_offline_bundle.py"
    spec = importlib.util.spec_from_file_location("ada_bundle_builder", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_ada_bundle_is_reproducible_certified_and_offline(tmp_path: Path):
    module = _builder()
    first = module.build_bundle(tmp_path / "first", enforce_materials_clean=False)
    second = module.build_bundle(tmp_path / "second", enforce_materials_clean=False)
    assert first.read_bytes() == second.read_bytes()

    root = "agentic-systems-2.1.0-ada-offline/"
    with zipfile.ZipFile(first) as archive:
        names = set(archive.namelist())
        manifest = json.loads(archive.read(root + "manifest.json"))
        assert manifest["schema_version"] == "agentic-systems.ada-offline-bundle/v1"
        assert manifest["certification"]["total"] == "24/24"
        assert manifest["certification"]["semantic_episodes"] == "76/76"
        assert manifest["certification"]["no_fallback"] is True
        assert manifest["provenance"]["core_source_equivalent"] is True
        assert manifest["tutorial_notebooks"] == 21
        assert manifest["cli_tutorials"] == 0
        assert root + ".env.example" in names
        env_examples = {name for name in names if Path(name).name == ".env.example"}
        assert env_examples == {root + ".env.example"}
        assert root + "studio/app.py" in names
        assert root + "studio/notebooks/00_conversational_system.ipynb" in names
        assert root + "studio/notebooks/01_launch_studio.ipynb" in names
        assert root + "evidence/bedrock-iam-attestation.json" in names
        assert root + "evidence/vllm-attestation.json" in names
        assert root + "evidence/local-semantic-attestation.json" in names
        assert root + "evidence/local-semantic-review.md" in names
        assert root + "evidence/vllm-semantic-review.md" in names
        assert not any(Path(name).name == ".env" for name in names)
        assert not any("/cli/" in name.lower() for name in names)

        checksums = archive.read(root + "SHA256SUMS").decode().splitlines()
        for row in checksums:
            expected, relative = row.split("  ", 1)
            observed = hashlib.sha256(archive.read(root + relative)).hexdigest()
            assert observed == expected


def test_certified_wheel_identity_matches_summary():
    module = _builder()
    certification = module._load_certification()
    assert module.sha256(module.WHEEL) == certification["wheel_sha256"]
    assert certification["totals"]["certified_live_executions"] == 24
    assert certification["totals"]["certified_live_failed"] == 0
    assert certification["totals"]["semantic_episodes_passed"] == 76
    assert certification["totals"]["semantic_episodes_failed"] == 0


def test_certification_rejects_semantic_false_positive(tmp_path: Path):
    module = _builder()
    certification = module._load_certification()
    source = module.EVIDENCE / "local-semantic-attestation.json"
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload["cells"][0]["episodes"][0]["judge"]["ok"] = False
    evidence = tmp_path / source.name
    evidence.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="Semantic evidence is incomplete"):
        module._validate_semantic_evidence(
            evidence,
            provider="python-runtime",
            certification=certification,
            row=certification["primary_matrix"]["python-runtime"],
        )


def test_certification_rejects_iam_fallback(tmp_path: Path):
    module = _builder()
    certification = module._load_certification()
    source = module.EVIDENCE / "bedrock-iam-attestation.json"
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload["cases"][0]["scenarios"][1]["details"]["fallback_provider"] = (
        "openai-runtime"
    )
    evidence = tmp_path / source.name
    evidence.write_text(json.dumps(payload), encoding="utf-8")
    row = certification["additional_authentication_routes"][
        "bedrock-runtime/aws-credential-chain"
    ]

    with pytest.raises(ValueError, match="Authentication evidence used fallback"):
        module._validate_authentication_evidence(
            evidence,
            certification=certification,
            row=row,
        )
