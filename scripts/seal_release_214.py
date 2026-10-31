"""Seal quality-built distributions under the explicitly approved equivalence policy."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile

from release_publication import ReleaseManifest, ReleaseArtifactIdentity, sha256, verify_artifacts

ROOT = Path(__file__).resolve().parents[1]


def verify_logic(wheel, policy):
    with zipfile.ZipFile(wheel) as archive:
        actual = {name: archive.read(name) for name in archive.namelist()
                  if name.startswith("agentic_systems/") and name.endswith(".py")}
    expected = policy["reference_python_sha256"]
    if set(actual) != set(expected):
        raise ValueError("Executable payload file set changed")
    for name, content in actual.items():
        if name == "agentic_systems/__init__.py":
            observed = hashlib.sha256(content.replace(b"\r\n", b"\n")).hexdigest()
            wanted = policy["stable_init_sha256"]
        else:
            observed, wanted = hashlib.sha256(content).hexdigest(), expected[name]
        if observed != wanted:
            raise ValueError("Unapproved executable difference: " + name)
    return len(actual)


def bundle(destination, sources):
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for root, prefix in sources:
            if root.is_file():
                archive.write(root, prefix / root.name)
                continue
            for path in root.rglob("*"):
                if not path.is_file() or any(part in path.parts for part in ("__pycache__", "build", "dist", ".pytest_cache", ".ipynb_checkpoints")):
                    continue
                if path.name.startswith(".env") or path.suffix == ".pyc":
                    continue
                archive.write(path, prefix / path.relative_to(root))


def seal(distributions, output):
    policy = json.loads((ROOT / "release/policy-2.1.4.json").read_text(encoding="utf-8"))
    sdk = distributions / "agentic_systems-2.1.4-py3-none-any.whl"
    checked = verify_logic(sdk, policy)
    live_path = ROOT / policy["reference_live_summary"]
    live = json.loads(live_path.read_text(encoding="utf-8"))
    if not live["passed"] or live["wheel_sha256"] != policy["reference_wheel_sha256"]:
        raise ValueError("Reference live acceptance does not match the pinned development artifact")
    output.mkdir(parents=True, exist_ok=False)
    for name in (sdk.name, "agentic_systems-2.1.4.tar.gz"):
        shutil.copyfile(distributions / name, output / name)
    bundle(output / "agentic-systems-skill-2.1.4.zip", [(ROOT / "skills/agentic-systems", Path("agentic-systems"))])
    studio = distributions / "agentic_systems_studio-2.1.4-py3-none-any.whl"
    bundle(output / "agentic-systems-studio-2.1.4.zip", [(ROOT / "examples/agentic_systems_studio", Path("studio")), (studio, Path("studio/wheels"))])
    ada = distributions / "agentic_systems_ada-2.1.4-py3-none-any.whl"
    bundle(output / "agentic-systems-ada-2.1.4.zip", [(ROOT / "integrations/ada", Path("ada")), (ada, Path("ada/wheels"))])
    bundle(output / "agentic-systems-learning-2.1.4.zip", [(ROOT / "tutorials", Path("tutorials")), (ROOT / "examples", Path("examples")), (ROOT / "docs", Path("docs"))])
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    acceptance = {"version": "2.1.4", "commit_sha": commit, "wheel_sha256": sha256(sdk),
                  "offline_passed": True, "python_versions": ["3.10", "3.11", "3.12", "3.13", "3.14"],
                  "live_passed_on_this_artifact": False,
                  "acceptance_mode": policy["mode"], "new_inference": False,
                  "executable_files_compared": checked, "reference_wheel_sha256": policy["reference_wheel_sha256"],
                  "known_limitations": policy["known_limitations"], "authorization": policy["authorization"]}
    (output / "acceptance.json").write_text(json.dumps(acceptance, indent=2) + "\n", encoding="utf-8")
    shutil.copyfile(ROOT / "docs/RELEASE_NOTES_214.md", output / "release-notes.md")
    shutil.copyfile(ROOT / "release/validation-evidence-2.1.4.zip", output / "validation-evidence-2.1.4.zip")
    manifest = ReleaseManifest(project="agentic-systems", version="2.1.4", commit_sha=commit,
        artifacts=tuple(ReleaseArtifactIdentity(filename=path.name, sha256=sha256(path),
                    kind="bdist_wheel" if path.suffix == ".whl" else "sdist" if path.name.endswith(".tar.gz") else "asset")
                        for path in sorted(output.iterdir())))
    path = output / "release-manifest.json"
    path.write_text(manifest.model_dump_json(indent=2) + "\n", encoding="utf-8")
    verify_artifacts(manifest, output)
    print("Manifest SHA256:", sha256(path))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--distributions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    seal(args.distributions, args.output)
