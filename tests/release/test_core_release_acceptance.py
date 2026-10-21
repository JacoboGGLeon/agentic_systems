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
