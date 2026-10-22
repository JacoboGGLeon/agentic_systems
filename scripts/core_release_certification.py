"""Validate the scoped public release; enterprise routes remain pending."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import subprocess

from release_publication import sha256


CORE_PROFILE = "core-12-live-v1"
PROVIDERS = {"python-runtime", "openai-runtime", "bedrock-runtime", "ollama-runtime"}
FRAMEWORKS = {"native", "langgraph", "openai-agents", "strands"}
PENDING = [
    "vllm-runtime/colab-gpu",
    "bedrock-runtime/iam/aws",
    "bedrock-runtime/iam/ada",
]


def validate_model_amendment(path, reference_commit: str) -> dict:
    """Verify a model-only operational amendment without changing the acceptance cases."""
    amendment = json.loads(path.read_text(encoding="utf-8"))
    if (
        amendment.get("schema_version") != "agentic_systems.model-amendment.v1"
        or amendment.get("previous_commit") != reference_commit
        or amendment.get("provider") != "ollama-runtime"
        or amendment.get("previous_model") != "qwen3.5:397b-cloud"
        or amendment.get("replacement_model") != "gemma4:31b-cloud"
        or not amendment.get("authorization")
    ):
        raise ValueError("Unrecognized model amendment")
    commits = (reference_commit, amendment["replacement_commit"])

    def git(*args):
        return subprocess.check_output(
            ["git", *args], cwd=Path(__file__).resolve().parents[1]
        ).strip()

    if git("rev-parse", f"{commits[0]}:src/agentic_systems") != git(
        "rev-parse", f"{commits[1]}:src/agentic_systems"
    ):
        raise ValueError("Model amendment changed the runtime core")
    verified = {}
    for filename in (
        "run_core_acceptance.py",
        "live_release_budget.py",
        "run_semantic_matrix.py",
        "semantic_e2e_application.py",
    ):
        sources = [git("show", f"{commit}:scripts/{filename}") for commit in commits]
        trees = []
        for source in sources:
            tree = ast.parse(source)
            if filename == "run_core_acceptance.py":
                tree.body = [
                    node
                    for node in tree.body
                    if getattr(node, "name", None) != "routes_from_environment"
                ]
            if filename == "live_release_budget.py":
                for node in tree.body:
                    if isinstance(node, ast.ClassDef) and node.name == "ReleaseBudget":
                        node.body = [
                            method
                            for method in node.body
                            if getattr(method, "name", None) != "amend_routes"
                        ]
            trees.append(ast.dump(tree))
        if trees[0] != trees[1]:
            raise ValueError(f"Model amendment changed acceptance behavior: {filename}")
        for commit, source in zip(commits, sources):
            # git output is stripped above; restore the tracked terminal newline.
            normalized = source.replace(b"\r\n", b"\n") + b"\n"
            verified.setdefault(commit, {})[filename] = {
                hashlib.sha256(normalized).hexdigest(),
                hashlib.sha256(normalized.replace(b"\n", b"\r\n")).hexdigest(),
            }
    amendment["verified_gate_hashes"] = verified
    return amendment


def validate_core_summary(summary: dict) -> None:
    if summary.get("acceptance_profile") != CORE_PROFILE:
        raise ValueError("Unexpected core acceptance profile")
    primary = summary.get("primary_matrix", {})
    if set(primary) != PROVIDERS or summary.get("pending_routes") != PENDING:
        raise ValueError("Core acceptance route scope differs")
    for provider, row in primary.items():
        if (
            set(row.get("frameworks", [])) != FRAMEWORKS
            or row.get("passed") != 4
            or row.get("failed") != 0
            or row.get("repetitions") != 2
        ):
            raise ValueError(f"Incomplete core acceptance: {provider}")
    if summary.get("totals", {}).get("certified_live_executions") != 12:
        raise ValueError("Core release must certify exactly twelve live combinations")


def build_core_summary(
    args, *, version: str, commit: str, assembly: str, tree: str
) -> dict:
    directory = args.core_evidence.resolve()
    digest = sha256(args.wheel)
    expected = {(p, f, r) for p in PROVIDERS for f in FRAMEWORKS for r in (1, 2)}
    seen = set()
    records = []
    assets = None
    routes = None
    dependencies = None
    amendment_path = directory / "model-amendment.json"
    amendment = (
        validate_model_amendment(amendment_path, commit)
        if amendment_path.exists()
        else None
    )
    provider_routes = {}
    for path in sorted(directory.glob("acceptance-*.json")):
        row = json.loads(path.read_text(encoding="utf-8"))
        key = (row.get("provider"), row.get("framework"), row.get("repetition"))
        if key not in expected or key in seen:
            raise ValueError(f"Unexpected or repeated core record: {path.name}")
        seen.add(key)
        if (
            row.get("phase") != "acceptance"
            or row.get("ok") is not True
            or row.get("schema_version") != "agentic_systems.core-acceptance.v1"
            or row.get("package_version") != version
            or row.get("wheel_sha256") != digest
            or row.get("commit_sha")
            not in (
                {commit, amendment["replacement_commit"]} if amendment else {commit}
            )
            or row.get("wheel_runtime_verified") is not True
        ):
            raise ValueError(f"Failed or mismatching acceptance: {path.name}")
        if assets is None:
            assets, routes = row["gate_assets"], row["routes"]
            dependencies = row.get("runtime_dependencies")
        if amendment:
            approved = amendment["verified_gate_hashes"][row["commit_sha"]]
            if set(row["gate_assets"]) != set(approved) or any(
                value not in approved[name]
                for name, value in row["gate_assets"].items()
            ):
                raise ValueError("Unverified acceptance assets after model amendment")
            if key[0] != "python-runtime":
                route = row["routes"][key[0]]
                if key[0] in provider_routes and provider_routes[key[0]] != route:
                    raise ValueError(
                        "Provider route changed within mandatory acceptance"
                    )
                provider_routes[key[0]] = route
                expected_model = (
                    amendment["replacement_model"]
                    if key[0] == "ollama-runtime"
                    else routes[key[0]]["model"]
                )
                if route["model"] != expected_model:
                    raise ValueError("Unapproved acceptance model")
        elif row["gate_assets"] != assets or row["routes"] != routes:
            raise ValueError("Acceptance assets or routes changed between runs")
        if not dependencies or row.get("runtime_dependencies") != dependencies:
            raise ValueError("Acceptance dependencies changed between runs")
        cell = row.get("semantic", {})
        episodes = cell.get("episodes", [])
        expected_names = {"calculation", "text_analysis", "out_of_scope"}
        if key[0] != "python-runtime":
            expected_names.add("poetic_calculation")
        if (
            cell.get("provider") != key[0]
            or cell.get("framework") != key[1]
            or cell.get("ok") is not True
            or len(episodes) != len(expected_names)
            or {e.get("name") for e in episodes} != expected_names
            or any(
                e.get("ok") is not True
                or e.get("deterministic_validation", {}).get("ok") is not True
                or e.get("judge", {}).get("ok") is not True
                or e.get("semantic_review", {}).get("ok") is not True
                for e in episodes
            )
            or row.get("failure_control", {}).get("ok") is not True
        ):
            raise ValueError(f"Incomplete semantic or failure evidence: {path.name}")
        records.append((path, row))
    if seen != expected:
        raise ValueError(f"Missing {len(expected - seen)} core acceptance records")
    offline = json.loads(args.offline_report.read_text(encoding="utf-8"))
    from run_release_offline import gate_commands

    if (
        offline.get("commit_sha") != commit
        or not offline.get("checks")
        or {c.get("name") for c in offline["checks"]} != set(gate_commands())
        or any(c.get("exit_code") != 0 for c in offline["checks"])
    ):
        raise ValueError("Offline gates missing, failed or from another commit")
    for check in offline["checks"]:
        path = args.offline_report.parent / check["log"]
        if path.name != check["log"] or sha256(path) != check["sha256"]:
            raise ValueError("Offline gate log missing or changed")
    ledger_path = directory / "requests.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    from decimal import Decimal

    reserved = sum(
        (Decimal(str(r["reserved_usd"])) for r in ledger["attempts"]), Decimal(0)
    )
    if (
        (not amendment and ledger.get("routes") != routes)
        or ledger.get("limits") != {"usd": 10, "requests": 1000}
        or len(ledger["attempts"]) > 1000
        or reserved > 10
    ):
        raise ValueError("Budget evidence is inconsistent or over limit")
    if amendment:
        history = ledger.get("route_history", [])
        backup_path = directory / amendment["previous_ledger_artifact"]
        if (
            backup_path.name != amendment["previous_ledger_artifact"]
            or sha256(backup_path) != amendment["previous_ledger_sha256"]
        ):
            raise ValueError("Original budget snapshot changed")
        original_ledger = json.loads(backup_path.read_text(encoding="utf-8"))
        if (
            len(history) != 2
            or history[0]["start_attempt"] != 1
            or history[0]["routes"] != routes
            or history[1]["routes"] != ledger["routes"]
            or history[1]["start_attempt"] != amendment["start_attempt"]
            or history[1]["routes"]["ollama-runtime"]["model"]
            != amendment["replacement_model"]
            or original_ledger["attempts"]
            != ledger["attempts"][: amendment["start_attempt"] - 1]
            or len(original_ledger["attempts"]) != amendment["start_attempt"] - 1
            or any(
                history[0]["routes"][p] != history[1]["routes"][p]
                for p in routes
                if p != "ollama-runtime"
            )
        ):
            raise ValueError("Budget route amendment history is inconsistent")
    primary = {}
    for provider in sorted(PROVIDERS):
        rows = [(p, r) for p, r in records if r["provider"] == provider]
        primary[provider] = {
            "frameworks": sorted(FRAMEWORKS),
            "passed": 4,
            "failed": 0,
            "repetitions": 2,
            "model": rows[0][1]["semantic"]["model"],
            "episodes_passed": sum(len(r["semantic"]["episodes"]) for _, r in rows),
            "episodes_failed": 0,
            "evidence_kind": "deterministic-control"
            if provider == "python-runtime"
            else "semantic-live",
        }
    inventory = {p.name: {"artifact": p.name, "sha256": sha256(p)} for p, _ in records}
    for path in (args.offline_report, ledger_path):
        inventory[path.name] = {"artifact": path.name, "sha256": sha256(path)}
    for path in [
        *directory.glob("pilot-*.json"),
        *([amendment_path] if amendment else []),
    ]:
        inventory[path.name] = {"artifact": path.name, "sha256": sha256(path)}
    if amendment:
        inventory[backup_path.name] = {
            "artifact": backup_path.name,
            "sha256": sha256(backup_path),
        }
    for check in offline["checks"]:
        path = args.offline_report.parent / check["log"]
        inventory[path.name] = {"artifact": path.name, "sha256": sha256(path)}
    episodes = sum(r["episodes_passed"] for r in primary.values())
    summary = {
        "schema_version": "agentic_systems.release-certification.v1",
        "acceptance_profile": CORE_PROFILE,
        "package_version": version,
        "commit_sha": commit,
        "assembly_commit_sha": assembly,
        "core_tree_sha": tree,
        "wheel_sha256": digest,
        "sdist_sha256": sha256(args.sdist),
        "no_fallback": True,
        "secrets_redacted": True,
        "primary_matrix": primary,
        "additional_authentication_routes": {},
        "pending_routes": PENDING,
        "evidence_inventory": inventory,
        "offline_gates": offline,
        "budget": {
            "requests": len(ledger["attempts"]),
            "reserved_usd": str(reserved),
            "billed_cost": None,
            "limits": ledger["limits"],
        },
        "model_amendment": {
            k: v for k, v in amendment.items() if k != "verified_gate_hashes"
        }
        if amendment
        else None,
        "totals": {
            "primary_combinations": 16,
            "primary_passed": 16,
            "primary_failed": 0,
            "certified_live_executions": 12,
            "certified_live_passed": 12,
            "certified_live_failed": 0,
            "semantic_episodes": episodes,
            "semantic_episodes_passed": episodes,
            "semantic_episodes_failed": 0,
            "total_semantic_episodes_reviewed": episodes,
            "total_semantic_episodes_passed": episodes,
            "total_semantic_episodes_failed": 0,
        },
    }
    validate_core_summary(summary)
    return summary
