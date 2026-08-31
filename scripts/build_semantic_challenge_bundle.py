"""Build the portable Strands protocol semantic-challenge bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
CHALLENGE = ROOT / "semantic_challenges" / "strands_protocol_graph"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _challenge_sha256() -> str:
    digest = hashlib.sha256()
    files = sorted(
        path
        for path in CHALLENGE.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix in {".py", ".json", ".md", ".txt", ".example"}
    )
    for path in files:
        relative = path.relative_to(CHALLENGE).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        content = path.read_bytes()
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def _copy_tree(source: Path, destination: Path) -> None:
    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "outputs"),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--wheel",
        type=Path,
        default=ROOT / "dist" / "agentic_systems-2.1.1-py3-none-any.whl",
    )
    parser.add_argument(
        "--evidence",
        type=Path,
        default=ROOT / "outputs" / "strands-protocol-graph-wheel-final",
    )
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    wheel = args.wheel.resolve()
    if not wheel.is_file():
        raise FileNotFoundError(wheel)
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    bundle_name = "agentic-systems-2.1.1-strands-protocol-challenge"
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / f"{bundle_name}.zip"
    with tempfile.TemporaryDirectory(prefix="agentic-systems-challenge-") as temp:
        bundle = Path(temp) / bundle_name
        bundle.mkdir()
        _copy_tree(ROOT / "semantic_challenges", bundle / "semantic_challenges")
        shutil.copy2(CHALLENGE / ".env.example", bundle / ".env.example")
        shutil.copy2(CHALLENGE / "requirements.txt", bundle / "requirements.txt")
        shutil.copy2(CHALLENGE / "README.md", bundle / "README.md")
        shutil.copy2(
            ROOT / "docs" / "semantic-certification.md",
            bundle / "SEMANTIC_CERTIFICATION.md",
        )
        artifacts = bundle / "artifacts"
        artifacts.mkdir()
        shutil.copy2(wheel, artifacts / wheel.name)
        if args.evidence.is_dir():
            shutil.copytree(args.evidence, bundle / "certified-local-evidence")
        manifest = {
            "schema_version": "agentic_systems.semantic-challenge-bundle.v1",
            "challenge": "strands-protocol-graph",
            "commit": commit,
            "wheel": wheel.name,
            "wheel_sha256": _sha256(wheel),
            "challenge_sha256": _challenge_sha256(),
            "contains_local_live_evidence": args.evidence.is_dir(),
            "external_targets": ["vllm-colab", "bedrock-iam-sagemaker-ada"],
        }
        (bundle / "BUNDLE_MANIFEST.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        files = sorted(path for path in bundle.rglob("*") if path.is_file())
        checksums = [
            f"{_sha256(path)}  {path.relative_to(bundle).as_posix()}" for path in files
        ]
        (bundle / "SHA256SUMS.txt").write_text(
            "\n".join(checksums) + "\n", encoding="utf-8"
        )
        archive = shutil.make_archive(
            str(output.with_suffix("")),
            "zip",
            root_dir=Path(temp),
            base_dir=bundle_name,
        )
    print(json.dumps({"bundle": archive, "sha256": _sha256(output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
