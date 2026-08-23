"""Small structural interfaces used by the Agentic Systems domain."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator, Mapping, Sequence
from typing import Any, Protocol, TypeVar, runtime_checkable

from .results import RunResult
from .tools import Tool


InputT = TypeVar("InputT", contravariant=True)


@runtime_checkable
class SyncRunner(Protocol[InputT]):
    def run(self, input: InputT, **kwargs: Any) -> RunResult: ...


@runtime_checkable
class AsyncRunner(Protocol[InputT]):
    async def arun(self, input: InputT, **kwargs: Any) -> RunResult: ...


@runtime_checkable
class ToolCallingProvider(Protocol):
    @property
    def capabilities(self) -> frozenset[str]: ...

    def run(self, input: Any, *, tools: Sequence[Tool], **kwargs: Any) -> RunResult: ...


@runtime_checkable
class StreamingProvider(Protocol[InputT]):
    def stream(self, input: InputT, **kwargs: Any) -> Iterator[Mapping[str, Any]]: ...


@runtime_checkable
class AsyncStreamingProvider(Protocol[InputT]):
    def astream(
        self, input: InputT, **kwargs: Any
    ) -> AsyncIterator[Mapping[str, Any]]: ...


@runtime_checkable
class EmbeddingProvider(Protocol):
    def embed(
        self, texts: Sequence[str], **kwargs: Any
    ) -> Sequence[Sequence[float]]: ...


@runtime_checkable
class FrameworkAdapter(Protocol):
    name: str

    def prepare(self, agent: Any, engine: Any) -> Any: ...

    def run(self, agent: Any, engine: Any, input: Any, **kwargs: Any) -> RunResult: ...

    async def arun(
        self, agent: Any, engine: Any, input: Any, **kwargs: Any
    ) -> RunResult: ...


__all__ = [
    "AsyncRunner",
    "AsyncStreamingProvider",
    "EmbeddingProvider",
    "FrameworkAdapter",
    "StreamingProvider",
    "SyncRunner",
    "ToolCallingProvider",
]
