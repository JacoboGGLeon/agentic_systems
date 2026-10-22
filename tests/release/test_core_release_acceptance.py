from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import importlib
import json
from pathlib import Path

import pytest


@pytest.fixture
def budget_module(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "scripts"))
    return importlib.import_module("live_release_budget")


def routes():
    return {
        "openai-runtime": {
            "model": "test",
            "endpoint": "https://api.openai.com/v1",
            "input_usd_per_million": 1,
            "output_usd_per_million": 4,
        }
    }


def request():
    return json.dumps({"model": "test", "max_tokens": 512}).encode()


def test_authorized_model_amendment_preserves_spend_and_rejects_old_model(
    budget_module, tmp_path
):
    import copy

    path = tmp_path / "requests.json"
    original_routes = routes()
    original_routes["ollama-runtime"] = {
        "model": "qwen3.5:397b-cloud",
        "endpoint": "https://ollama.com/v1",
        "input_usd_per_million": 1,
        "output_usd_per_million": 5,
    }
    original = budget_module.ReleaseBudget(path, original_routes, "pilot")
    original.reserve(
        "https://ollama.com/v1/chat/completions",
        json.dumps({"model": "qwen3.5:397b-cloud", "max_tokens": 512}).encode(),
    )
    previous = json.loads(path.read_text())
    replacement_routes = copy.deepcopy(original_routes)
    replacement_routes["ollama-runtime"].update(
        model="gemma4:31b-cloud", input_usd_per_million=0.25, output_usd_per_million=1
    )
    replacement = budget_module.ReleaseBudget(path, replacement_routes, "pilot-gemma")
    with pytest.raises(ValueError, match="Frozen"):
        replacement.reserve(
            "https://ollama.com/v1/chat/completions",
            json.dumps({"model": "gemma4:31b-cloud", "max_tokens": 512}).encode(),
        )
    replacement.amend_routes(reason="Owner explicitly selected Gemma after retirement")
    amended = json.loads(path.read_text())
    assert amended["attempts"] == previous["attempts"]
    assert amended["limits"] == previous["limits"]
    assert amended["route_history"][0]["routes"] == original_routes
    assert amended["route_history"][1]["start_attempt"] == 2
    with pytest.raises(ValueError, match="outside frozen"):
        replacement.reserve(
            "https://ollama.com/v1/chat/completions",
            json.dumps({"model": "qwen3.5:397b-cloud", "max_tokens": 512}).encode(),
        )
    replacement.reserve(
        "https://ollama.com/v1/chat/completions",
        json.dumps({"model": "gemma4:31b-cloud", "max_tokens": 512}).encode(),
    )
    assert len(json.loads(path.read_text())["attempts"]) == 2


def test_model_amendment_rejects_unapproved_provider_changes(budget_module, tmp_path):
    import copy

    path = tmp_path / "requests.json"
    original_routes = routes()
    original_routes["ollama-runtime"] = {
        "model": "qwen3.5:397b-cloud",
        "endpoint": "https://ollama.com/v1",
        "input_usd_per_million": 1,
        "output_usd_per_million": 5,
    }
    budget_module.ReleaseBudget(path, original_routes, "pilot").reserve(
        "https://api.openai.com/v1/responses", request()
    )
    before = path.read_bytes()
    modified = copy.deepcopy(original_routes)
    modified["openai-runtime"]["model"] = "another-model"
    modified["ollama-runtime"]["model"] = "gemma4:31b-cloud"
    with pytest.raises(ValueError, match="authorized"):
        budget_module.ReleaseBudget(path, modified, "pilot").amend_routes(
            reason="Not authorized"
        )
    assert path.read_bytes() == before


@pytest.mark.parametrize("change_case", [False, True])
def test_model_amendment_proves_unchanged_acceptance_code(
    budget_module, tmp_path, monkeypatch, change_case
):
    core = importlib.import_module("core_release_certification")
    path = tmp_path / "model-amendment.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "agentic_systems.model-amendment.v1",
                "previous_commit": "old",
                "replacement_commit": "new",
                "provider": "ollama-runtime",
                "previous_model": "qwen3.5:397b-cloud",
                "replacement_model": "gemma4:31b-cloud",
                "authorization": "Explicit owner selection",
            }
        )
    )

    def source(command, **kwargs):
        if command[1] == "rev-parse":
            return b"identical-core-tree"
        commit, name = command[2].split(":scripts/")
        if name == "run_core_acceptance.py":
            result = 2 if change_case and commit == "new" else 1
            return f"def routes_from_environment():\n return '{commit}'\ndef failure_case():\n return {result}\n".encode()
        if name == "live_release_budget.py":
            extra = " def amend_routes(self):\n  pass\n" if commit == "new" else ""
            return f"class ReleaseBudget:\n def reserve(self):\n  return 1\n{extra}".encode()
        return b"def canonical_semantics():\n return True\n"

    monkeypatch.setattr(core.subprocess, "check_output", source)
    if change_case:
        with pytest.raises(ValueError, match="acceptance behavior"):
            core.validate_model_amendment(path, "old")
    else:
        assert set(
            core.validate_model_amendment(path, "old")["verified_gate_hashes"]
        ) == {"old", "new"}


def test_price_revision_preserves_all_existing_reservations(budget_module, tmp_path):
    import copy

    path = tmp_path / "requests.json"
    original_routes = routes()
    original = budget_module.ReleaseBudget(path, original_routes, "pilot")
    original.reserve("https://api.openai.com/v1/responses", request())
    before = json.loads(path.read_text())
    reviewed = copy.deepcopy(original_routes)
    reviewed["openai-runtime"].update(
        input_usd_per_million=0.4, output_usd_per_million=1.6
    )
    current = budget_module.ReleaseBudget(path, reviewed, "acceptance-v2")
    current.amend_price_ceiling(
        reason="Reviewed standard prices, 25% ledger margin remains"
    )
    after = json.loads(path.read_text())
    assert after["attempts"] == before["attempts"]
    assert after["limits"] == before["limits"]
    current.reserve("https://api.openai.com/v1/responses", request())
    assert len(json.loads(path.read_text())["attempts"]) == 2
    reviewed["openai-runtime"]["model"] = "not-approved"
    with pytest.raises(ValueError, match="preserve"):
        budget_module.ReleaseBudget(path, reviewed, "bad").amend_price_ceiling(
            reason="bad"
        )


def test_budget_serializes_concurrent_attempts_and_resumes(budget_module, tmp_path):
    path = tmp_path / "requests.json"
    first = budget_module.ReleaseBudget(path, routes(), "pilot")
    second = budget_module.ReleaseBudget(path, routes(), "acceptance")
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(
            pool.map(
                lambda i: (first if i % 2 else second).reserve(
                    "https://api.openai.com/v1/chat/completions", request()
                ),
                range(20),
            )
        )
    ledger = json.loads(path.read_text())
    assert [r["attempt"] for r in ledger["attempts"]] == list(range(1, 21))
    assert all("body" not in r for r in ledger["attempts"])
    assert {r["phase"] for r in ledger["attempts"]} == {"pilot", "acceptance"}


@pytest.mark.parametrize("limit", ["requests", "usd"])
def test_budget_stops_before_transport_and_does_not_reset(
    budget_module, tmp_path, limit
):
    path = tmp_path / "requests.json"
    budget = budget_module.ReleaseBudget(path, routes(), "pilot")
    budget.reserve("https://api.openai.com/v1/responses", request())
    ledger = json.loads(path.read_text())
    if limit == "requests":
        ledger["attempts"] *= 1000
    else:
        ledger["attempts"][0]["reserved_usd"] = "10"
    path.write_text(json.dumps(ledger))
    original = path.read_bytes()
    with pytest.raises(budget_module.BudgetExceeded):
        budget.reserve("https://api.openai.com/v1/responses", request())
    assert path.read_bytes() == original


@pytest.mark.parametrize(
    "payload,url",
    [
        ({"model": "other", "max_tokens": 5}, "https://api.openai.com/v1/responses"),
        ({"model": "test"}, "https://api.openai.com/v1/responses"),
        ({"model": "test", "max_tokens": 5000}, "https://api.openai.com/v1/responses"),
        ({"model": "test", "max_tokens": 5}, "https://unapproved.example/v1/responses"),
    ],
)
def test_budget_rejects_unapproved_requests_without_reservation(
    budget_module, tmp_path, payload, url
):
    path = tmp_path / "requests.json"
    with pytest.raises(ValueError):
        budget_module.ReleaseBudget(path, routes(), "pilot").reserve(
            url, json.dumps(payload).encode()
        )
    assert not path.exists()


def test_budget_hooks_count_sync_async_and_late_worker(
    budget_module, tmp_path, monkeypatch
):
    import asyncio
    import httpx

    path = tmp_path / "requests.json"
    monkeypatch.setattr(
        httpx.Client, "_send_single_request", lambda *a: httpx.Response(200)
    )

    async def async_send(*a):
        return httpx.Response(200)

    monkeypatch.setattr(httpx.AsyncClient, "_send_single_request", async_send)
    # Restore hooks after the test only; production never uninstalls them.
    from botocore.httpsession import URLLib3Session

    monkeypatch.setattr(URLLib3Session, "send", URLLib3Session.send)
    budget_module.ReleaseBudget(path, routes(), "pilot").install()
    with httpx.Client() as client:
        client.post("https://api.openai.com/v1/responses", content=request())

    async def call():
        async with httpx.AsyncClient() as client:
            await client.post("https://api.openai.com/v1/responses", content=request())

    asyncio.run(call())
    with ThreadPoolExecutor() as pool:
        pool.submit(
            lambda: httpx.Client().post(
                "https://api.openai.com/v1/responses", content=request()
            )
        ).result()
    assert len(json.loads(path.read_text())["attempts"]) == 3


@pytest.fixture
def core_evidence(tmp_path, monkeypatch):
    from argparse import Namespace

    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "scripts"))
    core = importlib.import_module("core_release_certification")
    offline = importlib.import_module("run_release_offline")
    wheel = tmp_path / "wheel.whl"
    sdist = tmp_path / "source.tar.gz"
    wheel.write_bytes(b"synthetic wheel")
    sdist.write_bytes(b"synthetic sdist")
    for provider in core.PROVIDERS:
        for framework in core.FRAMEWORKS:
            for repetition in (1, 2):
                names = ["calculation", "text_analysis", "out_of_scope"]
                if provider != "python-runtime":
                    names.append("poetic_calculation")
                row = {
                    "schema_version": "agentic_systems.core-acceptance.v1",
                    "phase": "acceptance",
                    "provider": provider,
                    "framework": framework,
                    "repetition": repetition,
                    "ok": True,
                    "package_version": "2.1.2",
                    "wheel_sha256": core.sha256(wheel),
                    "commit_sha": "a" * 40,
                    "wheel_runtime_verified": True,
                    "runtime_dependencies": {"synthetic-sdk": "1.0"},
                    "gate_assets": {"runner": "frozen"},
                    "routes": routes(),
                    "semantic": {
                        "provider": provider,
                        "framework": framework,
                        "ok": True,
                        "model": "synthetic",
                        "episodes": [
                            {
                                "name": name,
                                "ok": True,
                                "judge": {"ok": True},
                                "deterministic_validation": {"ok": True},
                                "semantic_review": {"ok": True},
                            }
                            for name in names
                        ],
                    },
                    "failure_control": {"ok": True},
                }
                path = tmp_path / f"acceptance-{provider}-{framework}-{repetition}.json"
                path.write_text(json.dumps(row))
    report = {"commit_sha": "a" * 40, "checks": []}
    for name in offline.gate_commands():
        log = tmp_path / f"{name}.log"
        log.write_bytes(b"synthetic successful gate log")
        report["checks"].append(
            {"name": name, "exit_code": 0, "log": log.name, "sha256": core.sha256(log)}
        )
    report_path = tmp_path / "offline-gates.json"
    report_path.write_text(json.dumps(report))
    (tmp_path / "requests.json").write_text(
        json.dumps(
            {
                "routes": routes(),
                "limits": {"usd": 10, "requests": 1000},
                "attempts": [{"reserved_usd": "0.1"}],
            }
        )
    )
    args = Namespace(
        core_evidence=tmp_path, wheel=wheel, sdist=sdist, offline_report=report_path
    )
    return core, args


def test_core_certification_requires_every_cell_and_both_passes(core_evidence):
    core, args = core_evidence
    summary = core.build_core_summary(
        args, version="2.1.2", commit="a" * 40, assembly="a" * 40, tree="b" * 40
    )
    assert summary["totals"]["certified_live_executions"] == 12
    assert summary["totals"]["total_semantic_episodes_reviewed"] == 120
    assert summary["pending_routes"] == core.PENDING
    next(args.core_evidence.glob("acceptance-*.json")).unlink()
    with pytest.raises(ValueError, match="Missing"):
        core.build_core_summary(
            args, version="2.1.2", commit="a" * 40, assembly="a" * 40, tree="b" * 40
        )


@pytest.mark.parametrize(
    "fault", ["wheel", "judge", "tool_failure", "offline", "budget", "assets"]
)
def test_core_certification_cannot_promote_failed_or_changed_evidence(
    core_evidence, fault
):
    core, args = core_evidence
    path = next(args.core_evidence.glob("acceptance-*.json"))
    row = json.loads(path.read_text())
    if fault == "wheel":
        row["wheel_sha256"] = "wrong"
    elif fault == "judge":
        row["semantic"]["episodes"][0]["judge"]["ok"] = False
    elif fault == "tool_failure":
        row["failure_control"]["ok"] = False
    elif fault == "assets":
        row["gate_assets"] = {"runner": "changed"}
    elif fault == "offline":
        args.offline_report.write_text(
            json.dumps({"commit_sha": "a" * 40, "checks": []})
        )
    else:
        ledger_path = args.core_evidence / "requests.json"
        ledger = json.loads(ledger_path.read_text())
        ledger["attempts"][0]["reserved_usd"] = "10.01"
        ledger_path.write_text(json.dumps(ledger))
    path.write_text(json.dumps(row))
    with pytest.raises(ValueError):
        core.build_core_summary(
            args, version="2.1.2", commit="a" * 40, assembly="a" * 40, tree="b" * 40
        )
