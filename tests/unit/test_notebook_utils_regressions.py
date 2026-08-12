import os
import sys


from agentic_systems import (
    AgenticSystem,
    RunResult,
)
from tests.api._controlled_bedrock_runtime import (
    ControlledBedrockRuntime,
    attach_controlled_runtime,
)
from agentic_systems.utils import (
    _discover_repo_root,
    _to_jsonable,
    configure_notebook_environment,
    show_json,
)


def build_system(strict=True, defaults=None):
    import os

    os.environ.setdefault("AWS_EC2_METADATA_DISABLED", "true")
    os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
    os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")
    return AgenticSystem(
        model="demo-model", region="us-east-1", strict=strict, defaults=defaults
    )


def test_notebook_utils_show_json_environment_and_controlled_runtime(
    tmp_path, capsys, monkeypatch
):
    repo = tmp_path / "repo"
    src = repo / "src"
    tutorials = repo / "tutorials"
    src.mkdir(parents=True)
    tutorials.mkdir()
    (repo / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")

    root = configure_notebook_environment(repo)
    assert root == repo
    assert str(src) in sys.path
    assert os.environ.get("AWS_ACCESS_KEY_ID") != "test"
    assert os.environ.get("AWS_SECRET_ACCESS_KEY") != "test"

    assert _discover_repo_root(tutorials) == repo
    assert _discover_repo_root(src) == repo
    orphan = tmp_path / "orphan"
    orphan.mkdir()
    assert _discover_repo_root(orphan) == orphan

    result = RunResult(text="ok", data={"nested": [1]})
    assert _to_jsonable(result)["text"] == "ok"
    assert _to_jsonable({"r": result})["r"]["data"] == {"nested": [1]}
    assert _to_jsonable((result,))[0]["text"] == "ok"

    class Dictable:
        def to_dict(self):
            return {"kind": "dictable"}

    assert _to_jsonable(Dictable()) == {"kind": "dictable"}
    assert _to_jsonable("plain") == "plain"

    show_json(result, title="Result")
    output = capsys.readouterr().out
    assert "=== Result ===" in output
    assert '"text": "ok"' in output

    runtime = ControlledBedrockRuntime(tool_name="lookup", tool_input={"id": "1"})
    tool_response = runtime.converse(toolConfig={"tools": []}, messages=[])
    assert tool_response["stopReason"] == "tool_use"
    assert (
        tool_response["output"]["message"]["content"][0]["toolUse"]["name"] == "lookup"
    )

    final_response = runtime.converse(
        messages=[{"role": "user", "content": [{"toolResult": {"toolUseId": "1"}}]}]
    )
    assert final_response["stopReason"] == "end_turn"
    assert (
        final_response["output"]["message"]["content"][0]["text"] == runtime.final_text
    )

    synthesis_response = runtime.converse(
        toolConfig={"tools": []},
        messages=[
            {
                "role": "user",
                "content": [{"text": "BedrockRuntime final synthesis instruction"}],
            }
        ],
    )
    assert synthesis_response["stopReason"] == "end_turn"

    system = build_system()
    attached = attach_controlled_runtime(system, runtime)
    assert attached is runtime
    assert system._runtime.runtime is runtime
    default_attached = attach_controlled_runtime(system)
    assert isinstance(default_attached, ControlledBedrockRuntime)

    mapped = ControlledBedrockRuntime(
        tool_input_mapper=lambda kwargs: {"id": kwargs.get("id", "x")}
    )
    assert mapped._resolve_tool_input({"id": "mapped"}) == {"id": "mapped"}
    scalar_mapped = ControlledBedrockRuntime(tool_input_mapper=lambda kwargs: "scalar")
    assert scalar_mapped._resolve_tool_input({}) == {"value": "scalar"}
