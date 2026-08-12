from __future__ import annotations

from agentic_systems.providers.bedrock.converse import _ConverseMixin
from agentic_systems.providers.bedrock.direct import _DirectRunner
from agentic_systems.providers.bedrock.tools import _ToolsMixin


class DirectRuntime(_ConverseMixin, _ToolsMixin):
    model_id = "model-a"

    def __init__(self, responses=()):
        self._tools = {}
        self.responses = list(responses)
        self.calls = []

    def converse(self, **kwargs):
        self.calls.append(kwargs)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _runner(runtime, **overrides):
    options = {
        "instructions": None,
        "model_id": None,
        "tool_choice": "auto",
        "tool_names": None,
        "max_turns": 2,
        "max_tool_calls": None,
        "max_tokens": None,
        "temperature": None,
        "retry_tool_errors": True,
        "max_tool_error_repairs": 2,
        "synthesize_final_on_max_turns": True,
        "required_tools": None,
        "stop_when_required_tools_ok": False,
    }
    options.update(overrides)
    return _DirectRunner(runtime, "prompt", **options)


def _response(*blocks, stop_reason="end_turn"):
    return {
        "output": {"message": {"content": list(blocks)}},
        "stopReason": stop_reason,
    }


def test_invalid_tool_use_stops_without_resending_invalid_history():
    runtime = DirectRuntime([_response({"toolUse": {"name": "", "input": {}}})])
    result = _runner(runtime, max_turns=1).run()
    assert result.tool_calls[0].ok is False
    assert "toolUse" in result.final_text
    assert len(runtime.calls) == 1


def test_recoverable_validation_error_forces_retry_then_finishes():
    runtime = DirectRuntime(
        [
            _response(
                {
                    "toolUse": {
                        "toolUseId": "c1",
                        "name": "lookup",
                        "input": {},
                    }
                },
                stop_reason="tool_use",
            ),
            _response({"text": "done"}),
        ]
    )

    @runtime.tool
    def lookup(value: int):
        return {"value": value}

    result = _runner(runtime).run()
    assert result.final_text == "done"
    assert result.tool_calls[0].ok is False
    assert runtime.calls[1]["tool_choice"] == {"any": {}}
    assert (
        "repair instruction" in runtime.calls[1]["messages"][-1]["content"][-1]["text"]
    )


def test_required_tool_success_synthesizes_final_answer_immediately():
    runtime = DirectRuntime(
        [
            _response(
                {
                    "toolUse": {
                        "toolUseId": "c1",
                        "name": "lookup",
                        "input": {"value": 2},
                    }
                },
                stop_reason="tool_use",
            ),
            _response({"text": "synthesized"}),
        ]
    )

    @runtime.tool
    def lookup(value: int):
        return {"value": value}

    result = _runner(
        runtime,
        required_tools=["lookup", ""],
        stop_when_required_tools_ok=True,
    ).run()
    assert result.final_text == "synthesized"
    assert result.tool_calls[0].ok is True
    assert runtime.calls[1]["tools"] is None


def test_max_turn_synthesis_success_failure_and_empty_response():
    success = _runner(DirectRuntime([_response({"text": "final"})]), max_turns=0)
    assert success.run().final_text == "final"

    failed = _runner(DirectRuntime([RuntimeError("offline")]), max_turns=0)
    assert failed.run().final_text == ""

    empty = _runner(DirectRuntime([_response()]), max_turns=0)
    assert empty.run().final_text == ""


def test_direct_runner_private_contracts_for_choices_failures_and_required_tools():
    runtime = DirectRuntime()

    @runtime.tool(name="public.lookup")
    def lookup(value: int):
        return {"value": value}

    runner = _runner(
        runtime, tool_choice="public.lookup", required_tools=["public.lookup"]
    )
    alias = runner.canonical_to_bedrock["public.lookup"]
    assert runner._choice_for_turn(0) == {"tool": {"name": alias}}
    runner.force_tool_retry_next_turn = True
    assert runner._choice_for_turn(1) == {"any": {}}

    no_tools = _runner(DirectRuntime())
    assert no_tools._choice_for_turn(0) is None
    assert no_tools._required_tools_are_ok() is False

    good = runtime.to_envelope({"value": 1}, tool_name="public.lookup").model_dump(
        mode="json"
    )
    bad = runtime.to_envelope(
        {"error_type": "ValidationError", "message": "bad"},
        tool_name="public.lookup",
        ok=False,
    ).model_dump(mode="json")
    assert runner._recoverable_failure("c1", "public.lookup", {}, good) is None
    assert (
        runner._recoverable_failure(
            "c2", "public.lookup", {}, {"ok": False, "data": "raw"}
        )
        is None
    )
    assert (
        runner._recoverable_failure("c3", "public.lookup", {}, bad)["error_type"]
        == "ValidationError"
    )
    assert runner._tool_error_type({"data": {}}) is None
    assert runner._tool_error_type({"data": "raw"}) is None

    blocks, failures = runner._execute_tool_uses(
        [
            {"toolUseId": "ok", "name": alias, "input": {"value": 1}},
            {"toolUseId": "bad", "name": alias, "input": {}},
        ]
    )
    assert len(blocks) == 2
    assert len(failures) == 1
    assert runner._required_tools_are_ok() is True
    assert "Failed calls" in runner._repair_instruction(failures)["text"]
    limited = _runner(runtime, max_tool_calls=0)
    block, failure = limited._execute_tool_use(
        {"toolUseId": "limited", "name": alias, "input": {"value": 1}}
    )
    assert block["toolResult"]["status"] == "error"
    assert failure is None
