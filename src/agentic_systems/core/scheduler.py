"""Scheduler configuration and lightweight execution guards.

Agentic Systems execution consumes these scheduler objects. The scheduler is
intentionally small: it adds notebook-friendly limits, retries and timeouts
without replacing ``RunPolicy`` or provider-specific semantics.
"""

from __future__ import annotations
from contextvars import ContextVar, copy_context

import asyncio
import concurrent.futures
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, TypeVar

from pydantic import ValidationError

from agentic_systems.schemas.execution import ExecutionLimits

T = TypeVar("T")
_ACTIVE_SYNC_SCHEDULERS: ContextVar[frozenset[int]] = ContextVar(
    "agentic_systems_active_sync_schedulers", default=frozenset()
)


class SchedulerTimeoutError(TimeoutError):
    """Raised when a scheduler timeout is reached."""


class SchedulerConfigError(ValueError):
    """Raised when scheduler limits are invalid."""


@dataclass(frozen=True)
class SchedulerConfig:
    """Declarative execution limits used by runtimes and providers.

    Defaults are conservative for notebooks/sandboxes. ``max_concurrency`` is
    stored in runtime metadata; single synchronous Tool calls are still
    executed one-at-a-time by the local providers.
    """

    timeout_s: float | None = 60.0
    max_retries: int = 0
    max_tool_calls: int | None = 5
    max_turns: int | None = 6
    max_concurrency: int = 1
    backoff_s: float = 0.0
    _executor: concurrent.futures.ThreadPoolExecutor | None = field(
        init=False, default=None, repr=False, compare=False
    )
    _executor_lock: threading.Lock = field(
        init=False, default_factory=threading.Lock, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        try:
            schema = ExecutionLimits.model_validate(
                {
                    "timeout_s": self.timeout_s,
                    "max_retries": self.max_retries,
                    "max_tool_calls": self.max_tool_calls,
                    "max_turns": self.max_turns,
                    "max_concurrency": self.max_concurrency,
                    "backoff_s": self.backoff_s,
                }
            )
        except ValidationError as exc:
            raise SchedulerConfigError(str(exc)) from exc
        for name in (
            "timeout_s",
            "max_retries",
            "max_tool_calls",
            "max_turns",
            "max_concurrency",
            "backoff_s",
        ):
            object.__setattr__(self, name, getattr(schema, name))

    @classmethod
    def coerce(
        cls, value: "SchedulerConfig | dict[str, Any] | None"
    ) -> "SchedulerConfig":
        """Return a scheduler config from a config object, dict, or None."""

        if isinstance(value, cls):
            return value
        if value is None:
            return DEFAULT_SCHEDULER_CONFIG
        if isinstance(value, dict):
            return cls(**value)
        raise TypeError("scheduler must be a SchedulerConfig, dict, or None.")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly representation."""

        return self.execution_limits().model_dump(
            mode="json", exclude={"max_tokens", "max_repairs"}
        )

    def execution_limits(self) -> ExecutionLimits:
        """Return the canonical limits contract behind this compatibility facade."""

        return ExecutionLimits(
            timeout_s=self.timeout_s,
            max_retries=self.max_retries,
            max_tool_calls=self.max_tool_calls,
            max_turns=self.max_turns,
            max_concurrency=self.max_concurrency,
            backoff_s=self.backoff_s,
        )

    def policy_overrides(self) -> dict[str, Any]:
        """Return RunPolicy-compatible loop limits from this scheduler."""

        overrides: dict[str, Any] = {}
        if self.max_turns is not None:
            overrides["max_turns"] = int(self.max_turns)
        if self.max_tool_calls is not None:
            overrides["max_tool_calls"] = int(self.max_tool_calls)
        return overrides


DEFAULT_SCHEDULER_CONFIG = SchedulerConfig()


def merge_policy_with_scheduler(policy: Any, scheduler: SchedulerConfig | None) -> Any:
    """Apply scheduler loop limits to a ``RunPolicy`` without changing its type.

    Scheduler limits are guardrails. When the existing policy is stricter, the
    stricter value wins; otherwise the scheduler supplies the missing/safer cap.
    """

    if scheduler is None:
        return policy

    overrides: dict[str, Any] = {}
    if scheduler.max_turns is not None:
        current = getattr(policy, "max_turns", None)
        overrides["max_turns"] = (
            min(int(current), int(scheduler.max_turns))
            if current is not None
            else int(scheduler.max_turns)
        )
    if scheduler.max_tool_calls is not None:
        current = getattr(policy, "max_tool_calls", None)
        overrides["max_tool_calls"] = (
            min(int(current), int(scheduler.max_tool_calls))
            if current is not None
            else int(scheduler.max_tool_calls)
        )
    if not overrides:
        return policy
    return policy.merge(overrides) if hasattr(policy, "merge") else policy


def execute_sync(
    fn: Callable[[], T],
    scheduler: SchedulerConfig,
    *,
    is_success: Callable[[T], bool] | None = None,
    inline: bool = False,
    should_retry_value: Callable[[T], bool] | None = None,
    should_retry_exception: Callable[[BaseException], bool] | None = None,
) -> tuple[T, dict[str, Any]]:
    """Execute ``fn`` with scheduler retry/timeout guards.

    ``is_success`` lets callers retry normalized failure results, for example a
    ``RunResult`` with ``ok=False``. Exceptions are retried and then re-raised.
    """

    started = time.perf_counter()
    attempts = int(scheduler.max_retries) + 1
    last_exc: BaseException | None = None
    last_value: T | None = None
    success_check = is_success or (lambda _: True)
    retry_value = should_retry_value or (lambda _: True)
    retry_exception = should_retry_exception or (lambda _: True)

    for attempt in range(1, attempts + 1):
        try:
            value = _call_with_timeout(fn, scheduler, inline=inline)
            last_value = value
            if success_check(value) or attempt == attempts:
                return value, _scheduler_meta(
                    scheduler, attempt, started, timed_out=False
                )
            if not retry_value(value):
                return value, _scheduler_meta(
                    scheduler, attempt, started, timed_out=False
                )
        except SchedulerTimeoutError:
            last_exc = SchedulerTimeoutError(
                f"Execution exceeded timeout_s={scheduler.timeout_s}."
            )
            if attempt == attempts:
                raise last_exc
        except BaseException as exc:  # noqa: BLE001 - scheduler retries arbitrary runtime callables.
            last_exc = exc
            if attempt == attempts or not retry_exception(exc):
                _annotate_exception(exc, attempt, timed_out=False)
                raise
        if scheduler.backoff_s:
            time.sleep(float(scheduler.backoff_s))

    if last_value is not None:  # pragma: no cover - defensive fallback.
        return last_value, _scheduler_meta(
            scheduler, attempts, started, timed_out=False
        )
    if last_exc is not None:  # pragma: no cover - defensive fallback.
        raise last_exc
    raise RuntimeError(
        "Scheduler execution ended without a value or exception."
    )  # pragma: no cover


async def execute_async(
    fn: Callable[[], Awaitable[T]],
    scheduler: SchedulerConfig,
    *,
    is_success: Callable[[T], bool] | None = None,
    should_retry_value: Callable[[T], bool] | None = None,
    should_retry_exception: Callable[[BaseException], bool] | None = None,
) -> tuple[T, dict[str, Any]]:
    """Async variant of ``execute_sync`` for async agent runs."""

    started = time.perf_counter()
    attempts = int(scheduler.max_retries) + 1
    success_check = is_success or (lambda _: True)
    retry_value = should_retry_value or (lambda _: True)
    retry_exception = should_retry_exception or (lambda _: True)
    last_exc: BaseException | None = None
    for attempt in range(1, attempts + 1):
        try:
            if scheduler.timeout_s is None:
                value = await fn()
            else:
                value = await asyncio.wait_for(fn(), timeout=float(scheduler.timeout_s))
            if success_check(value) or attempt == attempts:
                return value, _scheduler_meta(
                    scheduler, attempt, started, timed_out=False
                )
            if not retry_value(value):
                return value, _scheduler_meta(
                    scheduler, attempt, started, timed_out=False
                )
        except (TimeoutError, asyncio.TimeoutError) as exc:
            last_exc = SchedulerTimeoutError(
                f"Execution exceeded timeout_s={scheduler.timeout_s}."
            )
            if attempt == attempts:
                raise last_exc from exc
        except BaseException as exc:  # noqa: BLE001 - scheduler retries arbitrary runtime callables.
            last_exc = exc
            if attempt == attempts or not retry_exception(exc):
                _annotate_exception(exc, attempt, timed_out=False)
                raise
        if scheduler.backoff_s:
            await asyncio.sleep(float(scheduler.backoff_s))
    if last_exc is not None:  # pragma: no cover - defensive fallback.
        raise last_exc
    raise RuntimeError(
        "Async scheduler execution ended without a value or exception."
    )  # pragma: no cover


def _call_with_timeout(
    fn: Callable[[], T], scheduler: SchedulerConfig, *, inline: bool = False
) -> T:
    if inline or id(scheduler) in _ACTIVE_SYNC_SCHEDULERS.get():
        return fn()
    timeout_s = scheduler.timeout_s
    if timeout_s is None:
        return fn()
    executor = _scheduler_executor(scheduler)
    context = copy_context()

    def invoke() -> T:
        active = _ACTIVE_SYNC_SCHEDULERS.get()
        token = _ACTIVE_SYNC_SCHEDULERS.set(active | {id(scheduler)})
        try:
            return fn()
        finally:
            _ACTIVE_SYNC_SCHEDULERS.reset(token)

    future = executor.submit(context.run, invoke)

    try:
        return future.result(timeout=float(timeout_s))
    except concurrent.futures.TimeoutError as exc:
        future.cancel()
        raise SchedulerTimeoutError(
            f"Execution exceeded timeout_s={timeout_s}."
        ) from exc


def _scheduler_executor(
    scheduler: SchedulerConfig,
) -> concurrent.futures.ThreadPoolExecutor:
    """Return the stable synchronous execution lane owned by ``scheduler``.

    Some framework SDKs keep per-thread runner state. Reusing the lane preserves
    that state across sequential candidate, delegation, and judge calls while
    still applying the configured timeout at the caller boundary.
    """

    executor = scheduler._executor
    if executor is not None:
        return executor
    with scheduler._executor_lock:
        executor = scheduler._executor
        if executor is None:
            executor = concurrent.futures.ThreadPoolExecutor(
                max_workers=int(scheduler.max_concurrency),
                thread_name_prefix="agentic-systems",
            )
            object.__setattr__(scheduler, "_executor", executor)
    return executor


def _scheduler_meta(
    scheduler: SchedulerConfig, attempt: int, started: float, *, timed_out: bool
) -> dict[str, Any]:
    return {
        "scheduler": scheduler.to_dict(),
        "attempts": attempt,
        "retries": max(0, attempt - 1),
        "timed_out": timed_out,
        "latency_ms": round((time.perf_counter() - started) * 1000, 3),
    }


def _annotate_exception(exc: BaseException, attempts: int, *, timed_out: bool) -> None:
    """Attach scheduler evidence without wrapping provider exception identities."""

    try:
        setattr(exc, "_agentic_scheduler_attempts", attempts)
        setattr(exc, "_agentic_scheduler_timed_out", timed_out)
    except Exception:
        return


__all__ = [
    "SchedulerConfig",
    "DEFAULT_SCHEDULER_CONFIG",
    "SchedulerConfigError",
    "SchedulerTimeoutError",
    "execute_async",
    "execute_sync",
    "merge_policy_with_scheduler",
]
