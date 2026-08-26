from __future__ import annotations

import asyncio
import importlib
import threading
import time

import pytest

from agentic_systems.contracts import RunPolicy
from agentic_systems.core.scheduler import (
    SchedulerConfig,
    SchedulerConfigError,
    SchedulerTimeoutError,
    execute_async,
    execute_sync,
    merge_policy_with_scheduler,
)
from agentic_systems.results import RunResult

system_module = importlib.import_module("agentic_systems.system")


class EchoEngine:
    def __init__(self, ok=True, fail=False):
        self.ok = ok
        self.fail = fail

    def run(self, agent, input, policy, *, mode="default"):
        if self.fail:
            raise RuntimeError("sync boom")
        return RunResult(
            text="sync", data={"input": input}, ok=self.ok, engine="echo", mode=mode
        )


class SyncOnlyEngine:
    def run(self, agent, input, policy, *, mode="default"):
        return RunResult(
            text="threaded",
            data={"input": input},
            ok=True,
            engine="sync-only",
            mode=mode,
        )


def test_scheduler_config_policy_retries_timeouts_and_async_paths():
    with pytest.raises(SchedulerConfigError):
        SchedulerConfig(timeout_s=0)
    with pytest.raises(SchedulerConfigError):
        SchedulerConfig(max_retries=-1)
    with pytest.raises(SchedulerConfigError):
        SchedulerConfig(max_tool_calls=-1)
    with pytest.raises(SchedulerConfigError):
        SchedulerConfig(max_turns=0)
    with pytest.raises(SchedulerConfigError):
        SchedulerConfig(max_concurrency=0)
    with pytest.raises(SchedulerConfigError):
        SchedulerConfig(backoff_s=-0.1)
    with pytest.raises(TypeError):
        SchedulerConfig.coerce("bad")

    scheduler = SchedulerConfig(
        timeout_s=None, max_retries=1, max_turns=3, max_tool_calls=2, backoff_s=0
    )
    assert scheduler.policy_overrides() == {"max_turns": 3, "max_tool_calls": 2}
    assert (
        merge_policy_with_scheduler(
            RunPolicy(max_turns=9, max_tool_calls=9), scheduler
        ).max_turns
        == 3
    )
    object_policy = object()
    assert (
        merge_policy_with_scheduler(
            object_policy, SchedulerConfig(max_turns=None, max_tool_calls=None)
        )
        is object_policy
    )

    calls = {"count": 0}

    def flaky_value():
        calls["count"] += 1
        return "bad" if calls["count"] == 1 else "ok"

    value, meta = execute_sync(
        flaky_value,
        SchedulerConfig(timeout_s=None, max_retries=1, backoff_s=0.001),
        is_success=lambda item: item == "ok",
    )
    assert value == "ok"
    assert meta["attempts"] == 2

    err_calls = {"count": 0}

    def flaky_exception():
        err_calls["count"] += 1
        if err_calls["count"] == 1:
            raise RuntimeError("first")
        return "ok"

    assert execute_sync(flaky_exception, scheduler)[0] == "ok"

    with pytest.raises(RuntimeError):
        execute_sync(
            lambda: (_ for _ in ()).throw(RuntimeError("always")),
            SchedulerConfig(max_retries=1, timeout_s=None),
        )

    with pytest.raises(SchedulerTimeoutError):
        execute_sync(
            lambda: time.sleep(0.05), SchedulerConfig(timeout_s=0.001, max_retries=0)
        )

    async def async_checks():
        async_calls = {"count": 0}

        async def flaky_async():
            async_calls["count"] += 1
            return "bad" if async_calls["count"] == 1 else "ok"

        value, async_meta = await execute_async(
            flaky_async,
            SchedulerConfig(timeout_s=None, max_retries=1, backoff_s=0.001),
            is_success=lambda item: item == "ok",
        )
        assert value == "ok"
        assert async_meta["attempts"] == 2

        async def async_error():
            raise RuntimeError("async boom")

        with pytest.raises(RuntimeError):
            await execute_async(
                async_error, SchedulerConfig(max_retries=0, timeout_s=None)
            )

        async def async_sleep():
            await asyncio.sleep(0.05)

        with pytest.raises(SchedulerTimeoutError):
            await execute_async(
                async_sleep, SchedulerConfig(timeout_s=0.001, max_retries=0)
            )

    asyncio.run(async_checks())


def test_sync_scheduler_reuses_one_execution_lane_without_serializing_resources():
    scheduler = SchedulerConfig(timeout_s=1, max_concurrency=1)

    first_thread = execute_sync(threading.get_ident, scheduler)[0]
    second_thread = execute_sync(threading.get_ident, scheduler)[0]

    assert first_thread == second_thread
    assert first_thread != threading.get_ident()
    inline_thread = execute_sync(threading.get_ident, scheduler, inline=True)[0]
    assert inline_thread == threading.get_ident()

    assert "_executor" not in scheduler.to_dict()


def test_sync_scheduler_executes_nested_work_inline_without_deadlock() -> None:
    scheduler = SchedulerConfig(timeout_s=1, max_concurrency=1)
    observed: dict[str, int] = {}

    def outer() -> int:
        observed["outer"] = threading.get_ident()
        observed["inner"] = execute_sync(threading.get_ident, scheduler)[0]
        return observed["inner"]

    assert execute_sync(outer, scheduler)[0] == observed["outer"]
    assert observed["inner"] == observed["outer"]
