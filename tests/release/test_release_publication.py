from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError

import pytest
from pydantic import ValidationError


def _module():
    spec = importlib.util.spec_from_file_location(
        "release_publication",
        Path(__file__).resolve().parents[2] / "scripts/release_publication.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def release(tmp_path):
    module = _module()
    artifacts = []
    for filename, kind in [
        ("example-1.2.3-py3-none-any.whl", "bdist_wheel"),
        ("example-1.2.3.tar.gz", "sdist"),
    ]:
        path = tmp_path / filename
        path.write_bytes(filename.encode())
        artifacts.append(
            {"filename": filename, "kind": kind, "sha256": module.sha256(path)}
        )
    manifest = module.ReleaseManifest(
        project="example", version="1.2.3", commit_sha="a" * 40, artifacts=artifacts
    )
    payload = {
        "info": {"name": "example", "version": "1.2.3"},
        "urls": [
            {
                "filename": a.filename,
                "packagetype": a.kind,
                "digests": {"sha256": a.sha256},
            }
            for a in manifest.artifacts
        ],
    }
    return module, manifest, payload, tmp_path


def test_absent_then_published_then_repeat_is_noop(release):
    module, manifest, payload, directory = release
    module.verify_artifacts(manifest, directory)
    assert module.reconcile(manifest, None).decision.value == "absent"
    for _ in range(2):
        assert module.reconcile(manifest, payload).decision.value == "matching"


@pytest.mark.parametrize(
    "change",
    ["partial", "hash", "name", "version", "duplicate", "extra", "yanked", "malformed"],
)
def test_conflicting_index_always_fails_closed(release, change):
    module, manifest, payload, _ = release
    if change == "partial":
        payload["urls"].pop()
    elif change == "hash":
        payload["urls"][0]["digests"]["sha256"] = "b" * 64
    elif change in {"name", "version"}:
        payload["info"][change] = "different"
    elif change == "duplicate":
        payload["urls"].append(payload["urls"][0])
    elif change == "extra":
        payload["urls"].append(
            {
                "filename": "extra.whl",
                "packagetype": "bdist_wheel",
                "digests": {"sha256": "a" * 64},
            }
        )
    elif change == "yanked":
        payload["urls"][0]["yanked"] = True
    else:
        payload["urls"] = "invalid"
    assert module.reconcile(manifest, payload).decision.value == "conflict"
    with pytest.raises(ValueError):
        module.check_index(manifest, fetch=lambda *a, **k: payload)


def test_manifest_and_artifact_tampering_rejected(release):
    module, manifest, _, directory = release
    path = directory / "manifest.json"
    path.write_text(manifest.model_dump_json(), encoding="utf-8")
    assert module.load_manifest(path, module.sha256(path)) == manifest
    with pytest.raises(ValueError, match="Manifest SHA256"):
        module.load_manifest(path, "a" * 64)
    (directory / manifest.artifacts[0].filename).write_bytes(b"tampered")
    with pytest.raises(ValueError, match="Artifact"):
        module.verify_artifacts(manifest, directory)


@pytest.mark.parametrize(
    "filename", ["../escape", "x/y.whl", "x\\y.whl", "bad\nname", "-flag"]
)
def test_manifest_rejects_unsafe_names(release, filename):
    module, _, _, _ = release
    with pytest.raises(ValidationError):
        module.ReleaseArtifactIdentity(filename=filename, kind="asset", sha256="a" * 64)


def test_eventual_visibility_and_transient_failure_are_bounded(release):
    module, manifest, payload, _ = release
    responses = iter(
        [HTTPError("url", 429, "busy", {}, None), URLError("temporary"), None, payload]
    )
    pauses = []

    def fetch(*args, **kwargs):
        value = next(responses)
        if isinstance(value, Exception):
            raise value
        return value

    assert (
        module.check_index(
            manifest, require_present=True, fetch=fetch, sleep=pauses.append
        ).decision.value
        == "matching"
    )
    assert pauses == [1, 2, 4]
    with pytest.raises(TimeoutError):
        module.check_index(
            manifest,
            require_present=True,
            attempts=2,
            fetch=lambda *a, **k: None,
            sleep=lambda _: None,
        )


@pytest.mark.parametrize("code", [401, 403, 400])
def test_permanent_http_failure_is_not_retried(release, code):
    module, manifest, _, _ = release

    def fetch(*args, **kwargs):
        raise HTTPError("url", code, "denied", {}, None)

    with pytest.raises(HTTPError):
        module.check_index(
            manifest, fetch=fetch, sleep=lambda _: pytest.fail("unexpected retry")
        )


def test_network_exhaustion_does_not_authorize_publication(release):
    module, manifest, _, _ = release

    def fetch(*args, **kwargs):
        raise TimeoutError("unavailable")

    with pytest.raises(TimeoutError):
        module.check_index(manifest, attempts=2, fetch=fetch, sleep=lambda _: None)
