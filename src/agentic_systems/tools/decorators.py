"""Public decorators for tool creation.

The module-level :func:`tool` decorator is the lightest way to define a
portable Agentic Systems tool. Unlike ``AgenticSystem.tool``, it does not
register the function into a cloud/runtime system. It returns a validated
:class:`~agentic_systems.tools.tool.Tool` object that can be run locally or
passed to higher-level APIs as they are introduced.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, overload

from pydantic import BaseModel

from .tool import Tool


@overload
def tool(function: Callable[..., Any], /) -> Tool:
    ...


@overload
def tool(
    function: None = None,
    /,
    *,
    name: str | None = None,
    description: str | None = None,
    input_schema: type[BaseModel] | None = None,
    output_schema: type[BaseModel] | None = None,
    input_model: type[BaseModel] | None = None,
    output_model: type[BaseModel] | None = None,
    input: type[BaseModel] | None = None,  # noqa: A002 - public ergonomic alias.
    output: type[BaseModel] | None = None,
    metadata: dict[str, Any] | None = None,
    strict: bool = True,
) -> Callable[[Callable[..., Any]], Tool]:
    ...


def tool(
    function: Callable[..., Any] | None = None,
    /,
    *,
    name: str | None = None,
    description: str | None = None,
    input_schema: type[BaseModel] | None = None,
    output_schema: type[BaseModel] | None = None,
    input_model: type[BaseModel] | None = None,
    output_model: type[BaseModel] | None = None,
    input: type[BaseModel] | None = None,  # noqa: A002 - public ergonomic alias.
    output: type[BaseModel] | None = None,
    metadata: dict[str, Any] | None = None,
    strict: bool = True,
) -> Tool | Callable[[Callable[..., Any]], Tool]:
    """Create a public :class:`Tool` from a Python function.

    Examples
    --------
    .. code-block:: python

        class SumInput(BaseModel):
            a: int
            b: int

        class SumOutput(BaseModel):
            result: int

        @tool(input=SumInput, output=SumOutput)
        def sumar(data: SumInput) -> SumOutput:
            return SumOutput(result=data.a + data.b)

        result = sumar.run({"a": 17, "b": 25})

    The decorated symbol is a ``Tool`` instance, not the original callable.
    Use ``AgenticSystem.tool`` when you need to register a function directly
    into an existing ``AgenticSystem`` runtime.
    """

    def _decorate(fn: Callable[..., Any]) -> Tool:
        return Tool(
            fn,
            name=name or fn.__name__,
            description=description,
            input_schema=input_schema,
            output_schema=output_schema,
            input_model=input_model,
            output_model=output_model,
            input=input,
            output=output,
            metadata=metadata,
            strict=strict,
        )

    if function is None:
        return _decorate
    if not callable(function):
        raise TypeError("@tool can only decorate callables.")
    return _decorate(function)


__all__ = ["tool"]
