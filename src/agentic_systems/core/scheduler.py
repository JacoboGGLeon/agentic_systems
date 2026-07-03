"""Scheduler configuration and lightweight execution guards.

Checkpoint 1 wires these objects into Agentic Systems execution. The scheduler is
intentionally small: it adds notebook-friendly limits, retries and timeouts
without replacing ``RunPolicy`` or provider-specific semantics.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import time
from dataclasses import asdict, dataclass
from typing import Any, Awaitable, Callable, TypeVar

T = TypeVar("T")


class SchedulerTimeoutError(TimeoutError):
    """Raised when a scheduler timeout is reached."""


class SchedulerConfigError(ValueError):
    """Raised when scheduler limits are invalid."""


@dataclass(frozen=True)
class SchedulerConfig:
    """Declarative execution limits used by runtimes and providers.

    Defaults are conservative for notebooks/sandboxes. ``max_concurrency`` is
    stored for runtime metadata in Checkpoint 1; single sync tool calls are still
    executed one-at-a-time by the local providers.
    """

    timeout_s: float | None = 60.0
    max_retries: int = 0
    max_tool_calls: int | None = 5
    max_turns: int | None = 6
    max_concurrency: int = 1
    backoff_s: float = 0.0

    def __post_init__(self) -> None:
        if self.timeout_s is not None and float(self.timeout_s) <= 0:
            raise SchedulerConfigError("timeout_s must be positive or None.")
        if int(self.max_retries) < 0:
            raise SchedulerConfigError("max_retries must be >= 0.")
        if self.max_tool_calls is not None and int(self.max_tool_calls) < 0:
            raise SchedulerConfigError("max_tool_calls must be >= 0 or None.")
        if self.max_turns is not None and int(self.max_turns) <= 0:
            raise SchedulerConfigError("max_turns must be positive or None.")
        if int(self.max_concurrency) <= 0:
            raise SchedulerConfigError("max_concurrency must be positive.")
        if float(self.backoff_s) < 0:
            raise SchedulerConfigError("backoff_s must be >= 0.")

    @classmethod
    def coerce(cls, value: "SchedulerConfig | dict[str, Any] | None") -> "SchedulerConfig":
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

        return asdict(self)

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
        overrides["max_turns"] = min(int(current), int(scheduler.max_turns)) if current is not None else int(scheduler.max_turns)
    if scheduler.max_tool_calls is not None:
        current = getattr(policy, "max_tool_calls", None)
        overrides["max_tool_calls"] = min(int(current), int(scheduler.max_tool_calls)) if current is not None else int(scheduler.max_tool_calls)
    if not overrides:
        return policy
    return policy.merge(overrides) if hasattr(policy, "merge") else policy


def execute_sync(
    fn: Callable[[], T],
    scheduler: SchedulerConfig,
    *,
    is_success: Callable[[T], bool] | None = None,
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

    for attempt in range(1, attempts + 1):
        try:
            value = _call_with_timeout(fn, scheduler.timeout_s)
            last_value = value
            if success_check(value) or attempt == attempts:
                return value, _scheduler_meta(scheduler, attempt, started, timed_out=False)
        except SchedulerTimeoutError:
            last_exc = SchedulerTimeoutError(f"Execution exceeded timeout_s={scheduler.timeout_s}.")
            if attempt == attempts:
                raise last_exc
        except BaseException as exc:  # noqa: BLE001 - scheduler retries arbitrary runtime callables.
            last_exc = exc
            if attempt == attempts:
                raise
        if scheduler.backoff_s:
            time.sleep(float(scheduler.backoff_s))

    if last_value is not None:  # pragma: no cover - defensive fallback.
        return last_value, _scheduler_meta(scheduler, attempts, started, timed_out=False)
    if last_exc is not None:  # pragma: no cover - defensive fallback.
        raise last_exc
    raise RuntimeError("Scheduler execution ended without a value or exception.")  # pragma: no cover


async def execute_async(
    fn: Callable[[], Awaitable[T]],
    scheduler: SchedulerConfig,
    *,
    is_success: Callable[[T], bool] | None = None,
) -> tuple[T, dict[str, Any]]:
    """Async variant of ``execute_sync`` for async agent runs."""

    started = time.perf_counter()
    attempts = int(scheduler.max_retries) + 1
    success_check = is_success or (lambda _: True)
    last_exc: BaseException | None = None
    for attempt in range(1, attempts + 1):
        try:
            if scheduler.timeout_s is None:
                value = await fn()
            else:
                value = await asyncio.wait_for(fn(), timeout=float(scheduler.timeout_s))
            if success_check(value) or attempt == attempts:
                return value, _scheduler_meta(scheduler, attempt, started, timed_out=False)
        except TimeoutError as exc:
            last_exc = SchedulerTimeoutError(f"Execution exceeded timeout_s={scheduler.timeout_s}.")
            if attempt == attempts:
                raise last_exc from exc
        except BaseException as exc:  # noqa: BLE001 - scheduler retries arbitrary runtime callables.
            last_exc = exc
            if attempt == attempts:
                raise
        if scheduler.backoff_s:
            await asyncio.sleep(float(scheduler.backoff_s))
    if last_exc is not None:  # pragma: no cover - defensive fallback.
        raise last_exc
    raise RuntimeError("Async scheduler execution ended without a value or exception.")  # pragma: no cover


def _call_with_timeout(fn: Callable[[], T], timeout_s: float | None) -> T:
    if timeout_s is None:
        return fn()
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = executor.submit(fn)
    try:
        return future.result(timeout=float(timeout_s))
    except concurrent.futures.TimeoutError as exc:
        future.cancel()
        raise SchedulerTimeoutError(f"Execution exceeded timeout_s={timeout_s}.") from exc
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def _scheduler_meta(scheduler: SchedulerConfig, attempt: int, started: float, *, timed_out: bool) -> dict[str, Any]:
    return {
        "scheduler": scheduler.to_dict(),
        "attempts": attempt,
        "retries": max(0, attempt - 1),
        "timed_out": timed_out,
        "latency_ms": round((time.perf_counter() - started) * 1000, 3),
    }


__all__ = [
    "SchedulerConfig",
    "DEFAULT_SCHEDULER_CONFIG",
    "SchedulerConfigError",
    "SchedulerTimeoutError",
    "execute_async",
    "execute_sync",
    "merge_policy_with_scheduler",
]
