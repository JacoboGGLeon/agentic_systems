from __future__ import annotations

import importlib
import json
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def delivery(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "scripts"))
    publication = importlib.import_module("release_publication")
    finalizer = importlib.import_module("finalize_release")
    artifacts = []
    for filename, kind in [
        ("example-1.2.3-py3-none-any.whl", "bdist_wheel"),
        ("example-1.2.3.tar.gz", "sdist"),
    ]:
        path = tmp_path / filename
        path.write_bytes(filename.encode())
        artifacts.append(
            dict(filename=filename, kind=kind, sha256=publication.sha256(path))
        )
    manifest = publication.ReleaseManifest(
        project="example", version="1.2.3", commit_sha="a" * 40, artifacts=artifacts
    )
    path = tmp_path / "release-manifest.json"
    path.write_text(manifest.model_dump_json(), encoding="utf-8")
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/example")
    return finalizer, tmp_path, publication.sha256(path)


class GitHubDouble:
    """Stateful remote double: uploads and downloads exercise real local bytes."""

    def __init__(self):
        self.release = None
        self.tag_commit = None
        self.assets = {}
        self.mutations = []
        self.corrupt_upload = False
        self.interrupt_upload = False

    def command(self, *args):
        if args[:2] == ("git", "ls-remote"):
            return f"{self.tag_commit}\trefs/tags/v1.2.3" if self.tag_commit else ""
        if args[:2] == ("gh", "api"):
            return json.dumps([[self.release] if self.release else []])
        assert args[:2] == ("gh", "release"), args
        operation = args[2]
        if operation == "download":
            name = args[args.index("--pattern") + 1]
            destination = Path(args[args.index("--dir") + 1]) / name
            destination.write_bytes(self.assets[name])
            return ""
        self.mutations.append(args)
        if operation == "create":
            self.release = {
                "tag_name": "v1.2.3",
                "target_commitish": "a" * 40,
                "draft": True,
                "prerelease": False,
                "assets": [],
            }
        elif operation == "upload":
            if self.interrupt_upload and self.assets:
                self.interrupt_upload = False
                raise subprocess.CalledProcessError(1, args)
            path = Path(args[4])
            assert path.name not in self.assets, (
                "existing bytes must never be uploaded again"
            )
            self.assets[path.name] = (
                b"corrupt" if self.corrupt_upload else path.read_bytes()
            )
            self.release["assets"].append({"name": path.name})
        elif operation == "edit":
            self.release["draft"] = False
            self.release["prerelease"] = False
            self.tag_commit = self.release["target_commitish"]
        else:
            pytest.fail(f"Unexpected command: {args}")
        return ""


def test_first_publish_verifies_remote_bytes_and_repeat_has_no_mutations(
    delivery, monkeypatch
):
    module, directory, digest = delivery
    remote = GitHubDouble()
    monkeypatch.setattr(module, "command", remote.command)
    module.finalize(directory, digest)
    assert remote.release["draft"] is False
    assert len(remote.assets) == 3
    mutations = list(remote.mutations)
    module.finalize(directory, digest)
    assert remote.mutations == mutations


def test_interrupted_draft_resumes_only_missing_assets(delivery, monkeypatch):
    module, directory, digest = delivery
    remote = GitHubDouble()
    remote.interrupt_upload = True
    monkeypatch.setattr(module, "command", remote.command)
    with pytest.raises(subprocess.CalledProcessError):
        module.finalize(directory, digest)
    assert remote.release["draft"] is True
    module.finalize(directory, digest)
    assert len(remote.assets) == 3
    assert remote.release["draft"] is False


def test_corrupt_new_upload_is_never_promoted(delivery, monkeypatch):
    module, directory, digest = delivery
    remote = GitHubDouble()
    remote.corrupt_upload = True
    monkeypatch.setattr(module, "command", remote.command)
    with pytest.raises(ValueError, match="conflicts"):
        module.finalize(directory, digest)
    assert remote.release["draft"] is True
    assert not any(call[2] == "edit" for call in remote.mutations)


@pytest.mark.parametrize("fault", ["tag", "bytes", "missing", "extra", "duplicate"])
def test_existing_final_release_conflict_never_mutates(delivery, monkeypatch, fault):
    module, directory, digest = delivery
    remote = GitHubDouble()
    monkeypatch.setattr(module, "command", remote.command)
    module.finalize(directory, digest)
    before = list(remote.mutations)
    name = next(iter(remote.assets))
    if fault == "tag":
        remote.tag_commit = "b" * 40
    elif fault == "bytes":
        remote.assets[name] = b"changed"
    elif fault == "missing":
        remote.release["assets"].pop()
    elif fault == "extra":
        remote.release["assets"].append({"name": "unexpected.zip"})
    else:
        remote.release["assets"].append(remote.release["assets"][0])
    with pytest.raises(ValueError):
        module.finalize(directory, digest)
    assert remote.mutations == before


def test_annotated_tag_uses_peeled_commit(delivery, monkeypatch):
    module, _, _ = delivery
    monkeypatch.setattr(
        module,
        "command",
        lambda *a: (
            "b" * 40 + "\trefs/tags/v1.2.3\n" + "a" * 40 + "\trefs/tags/v1.2.3^{}"
        ),
    )
    assert module.remote_tag_commit("v1.2.3") == "a" * 40


def test_unknown_index_cannot_silently_select_testpypi(delivery):
    publication = importlib.import_module("release_publication")
    _, directory, digest = delivery
    manifest = publication.load_manifest(directory / "release-manifest.json", digest)
    with pytest.raises(ValueError, match="Unsupported package index"):
        publication.check_index(manifest, index="production-typo")


def test_changed_draft_target_cannot_be_published(delivery, monkeypatch):
    module, directory, digest = delivery
    remote = GitHubDouble()

    def command(*args):
        result = remote.command(*args)
        if args[:3] == ("gh", "release", "upload"):
            remote.release["target_commitish"] = "b" * 40
        return result

    monkeypatch.setattr(module, "command", command)
    with pytest.raises(ValueError, match="Draft target changed"):
        module.finalize(directory, digest)
    assert remote.release["draft"] is True
