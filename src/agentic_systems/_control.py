"""Control flow is distinct from business errors; optional backend imports stay lazy."""
from ._context import _active_execution
from ._results import _json


class _PauseSignal(BaseException):
    def __init__(self, original):
        self.original = original


def _propagate_control(error):
    if type(error).__module__.startswith("langgraph"):
        from langgraph.errors import GraphBubbleUp
        if isinstance(error, GraphBubbleUp):
            raise _PauseSignal(error) from error


def pause(value):
    """Pause an orchestration action; resume through the same compiled program.

    The interrupted callable restarts, so place effects in separate actions.
    This local continuation API does not implement recovery across process restarts.
    """
    active = _active_execution.get()
    if active is not None and (not active.allow_pause or active.in_actor):
        raise ValueError("Place pause in an orchestration node outside actors and Eval")
    if active is None or active.backend != "langgraph":
        raise ValueError("pause requires an executing compiled Agent, System or Environment")
    active.check()
    from langgraph.types import interrupt
    try:
        return _json(interrupt(_json(value)))
    except Exception as exc:
        _propagate_control(exc)
        raise
