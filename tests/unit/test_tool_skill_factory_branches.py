
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
import importlib

import pytest
from pydantic import BaseModel

import agentic_systems.factories as factories_module
from agentic_systems.chain import Chain
from agentic_systems.core.runtime import RuntimeConfig
from agentic_systems.expectations import expect
from agentic_systems.results import RunResult
from agentic_systems.skills.loader import SkillLoadError, load_skill as load_skill_from_path
from agentic_systems.skills.skill import Skill
from agentic_systems.tools import Tool, tool as tool_decorator
import agentic_systems.skills.loader as loader_module
tool_module = importlib.import_module("agentic_systems.tools.tool")


class PayloadModel(BaseModel):
    value: int


@dataclass
class DataConfig:
    path: Path


def test_tool_call_schema_alias_and_context_meta_edges():
    def one(payload: dict) -> dict:
        return {"seen": payload}

    def zero() -> dict:
        return {"ok": True}

    def multi_fn(a: int, b: int) -> dict:
        return {"sum": a + b}

    one_arg = Tool(name="one", function=one)
    assert one_arg.run({"a": 1}).data == {"seen": {"a": 1}}
    assert one_arg.run(PayloadModel(value=2)).data["seen"].value == 2

    no_arg = Tool(name="zero", function=zero)
    assert no_arg.run({"ignored": True}).data == {"ok": True}

    multi = Tool(name="multi", function=multi_fn)
    assert multi.run({"a": 2, "b": 3}).data == {"sum": 5}
    bad_result = multi.run("bad")
    assert bad_result.ok is False
    assert bad_result.data["error_type"] == "TypeError"

    class InSchema(BaseModel):
        x: int

    schema_tool = tool_decorator(name="schema", input_schema=InSchema, input_model=InSchema)(lambda x: {"x": x})
    assert schema_tool.input_schema is InSchema
    with pytest.raises(ValueError):
        tool_decorator(name="bad_schema", input_schema=InSchema, input_model=PayloadModel)(lambda x: {"x": x})
    with pytest.raises(TypeError):
        tool_decorator(name="bad_model", input_schema=dict)(lambda x: {"x": x})

    context_result = one_arg.run({"a": 1}, context={"user_prompt": "hello"})
    assert context_result.meta["input"] == "hello"


def test_skill_prompts_checks_json_like_and_errors():
    @tool_decorator(name="adder")
    def adder(a: int, b: int):
        return {"value": a + b}

    skill = Skill(
        name="math",
        version="1.2.3",
        description="fallback instructions",
        tools=[adder],
        prompts={"agent": "Use tools.", "user_prompt": "add"},
        metadata={"model": PayloadModel(value=1), "config": DataConfig(Path("x")), "cls": PayloadModel, "fn": adder.run},
    )
    assert skill.instructions == "Use tools."
    assert skill.prompt() == "add"
    assert skill.prompt("missing", default="default") == "default"
    with pytest.raises(KeyError):
        skill.prompt("missing")
    assert skill.tool("adder") is adder
    with pytest.raises(KeyError):
        skill.tool("missing")
    assert len(skill) == 1
    assert list(skill)[0] is adder
    info = skill.info()
    assert info["metadata"]["model"] == {"value": 1}
    assert info["metadata"]["config"]["path"] == "x"
    assert info["metadata"]["cls"] == "PayloadModel"
    assert isinstance(info["metadata"]["fn"], str)

    duplicate = Skill(name="dup", tools=[adder, adder])
    assert duplicate.check().ok is False

    class BadTool:
        name = "bad"
        def check(self):
            from agentic_systems.contracts import ValidationResult
            result = ValidationResult()
            result.add("bad_tool", "broken", path="x", meta={"m": 1})
            return result

    checked = Skill(name="checked", tools=[])
    checked._tools = (BadTool(),)
    assert checked.check().issues[0].path == "tools[0].x"

    assert Skill(name="desc", description="desc").instructions == "desc"
    with pytest.raises(TypeError):
        Skill(name="bad", tools="not-tools")
    with pytest.raises(TypeError):
        Skill(name="bad", tools=[object()])
    with pytest.raises(TypeError):
        Skill(name="bad", prompts=[])


def test_skill_loader_edges(tmp_path):
    missing = tmp_path / "missing"
    with pytest.raises(SkillLoadError):
        load_skill_from_path(SimpleNamespace(), missing)

    no_md = tmp_path / "no_md"
    no_md.mkdir()
    with pytest.raises(SkillLoadError):
        load_skill_from_path(SimpleNamespace(), no_md)

    no_py = tmp_path / "no_py"
    no_py.mkdir()
    (no_py / "SKILL.md").write_text("Skill docs\n", encoding="utf-8")
    with pytest.raises(SkillLoadError):
        load_skill_from_path(SimpleNamespace(), no_py)

    not_callable = tmp_path / "not_callable"
    not_callable.mkdir()
    (not_callable / "SKILL.md").write_text("Skill docs\n", encoding="utf-8")
    (not_callable / "skill.py").write_text("register = 1\n", encoding="utf-8")
    with pytest.raises(SkillLoadError):
        load_skill_from_path(SimpleNamespace(), not_callable)

    bad_runtime = tmp_path / "bad_runtime"
    bad_runtime.mkdir()
    (bad_runtime / "SKILL.md").write_text("Skill docs\n", encoding="utf-8")
    (bad_runtime / "skill.py").write_text("def register(system):\n    return {'runtime_skill': object()}\n", encoding="utf-8")
    with pytest.raises(SkillLoadError):
        load_skill_from_path(SimpleNamespace(), bad_runtime)

    valid = tmp_path / "valid"
    valid.mkdir()
    (valid / "__init__.py").write_text("", encoding="utf-8")
    (valid / "SKILL.md").write_text("\n\nFirst description line\n", encoding="utf-8")
    (valid / "skill.py").write_text(
        "from agentic_systems.skills import Skill\n"
        "def register(system):\n"
        "    return {'runtime_skill': Skill(name='loaded', tools=[]), 'manifest': {'tools': []}}\n",
        encoding="utf-8",
    )
    loaded = load_skill_from_path(SimpleNamespace(tools=[], agents=[], public_tools={}, _skills=[]), valid)
    assert loaded.manifest.name == "loaded"
    assert isinstance(loaded.runtime_skill, Skill)


def test_chain_expectations_and_factories(monkeypatch, tmp_path):
    class FakeRuntime:
        def complete(self, prompt, *, instructions="", data=None, **kwargs):
            return RunResult(text=f"complete:{prompt}", data=data or {}, usage={"n": 1}, ok=True)

        def answer_from_markdown(self, *, path, question, instructions="", **kwargs):
            return RunResult(text=f"answer:{Path(path).name}:{question}", usage={"n": 2}, ok=True)

    chain = Chain(FakeRuntime(), instructions="base")
    assert chain.complete("p").text == "complete:p"
    assert "Traduce" in chain.translate("hola", target_language="en").text
    md = tmp_path / "doc.md"
    md.write_text("# Doc", encoding="utf-8")
    assert chain.answer_from_markdown(path=md, question="q").text == "answer:doc.md:q"
    assert len(chain.history()) == 3

    assert expect.allowed("a", "b") == {"allowed": ["a", "b"]}
    assert expect.at_least(2, ["a", "b"]) == {"min_count": 2, "allowed": ["a", "b"]}

    monkeypatch.setenv("BEDROCK_MODEL_ID", "bedrock-model")
    monkeypatch.setenv("OPENAI_MODEL", "openai-model")
    monkeypatch.setenv("AWS_REGION", "mx-test-1")
    assert factories_module.default_model_id() == "bedrock-model"
    assert factories_module.default_openai_model_id() == "openai-model"
    assert factories_module.default_region() == "mx-test-1"
    assert factories_module._default_agent_model("python-runtime") == "python-runtime"
    assert factories_module._default_agent_model("openai-runtime") == "openai-model"

    assert factories_module._merge_skill_inputs(None, "skills") == "skills"
    assert factories_module._merge_skill_inputs("skill", None) == ["skill"]
    assert factories_module._merge_skill_inputs("skill", ["a", "b"]) == ["skill", "a", "b"]
    assert factories_module._merge_skill_inputs("skill", "other") == ["skill", "other"]

    skill_dir = tmp_path / "skill_dir"
    skill_dir.mkdir()
    assert factories_module._resolve_skill_path("") is None
    assert factories_module._resolve_skill_path(str(skill_dir)) == skill_dir.resolve()
    packaged_fallback = tmp_path / "packaged_fallback"
    packaged_fallback.mkdir()
    original_resolve_packaged = factories_module._resolve_packaged_skill_path
    monkeypatch.setattr(factories_module, "_resolve_packaged_skill_path", lambda text: packaged_fallback.resolve())
    assert factories_module._resolve_skill_path("package/style") == packaged_fallback.resolve()
    monkeypatch.setattr(factories_module, "_resolve_packaged_skill_path", original_resolve_packaged)
    assert factories_module._resolve_packaged_skill_path("////") is None

    existing = Skill(name="existing")
    assert factories_module.load_skill(existing) is existing
    with pytest.raises(ValueError):
        factories_module.load_skill("not-a-real-skill")

    class FakeCreated:
        def __init__(self):
            self.metadata = {}

    class FakeWorkspace:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def agent(self, **kwargs):
            created = FakeCreated()
            created.kwargs = kwargs
            return created

    monkeypatch.setattr(factories_module, "AgenticSystem", FakeWorkspace)
    created = factories_module.agent(name="a", engine="python-runtime", skill="s", skills=["x"], metadata={"m": 1})
    assert created.metadata == {"m": 1}
    assert created.kwargs["skills"] == ["s", "x"]

    runtime_cfg = RuntimeConfig(provider="openai-runtime", model_id="runtime-model", region_name="us-test-1")
    created_runtime = factories_module.agent(name="b", runtime=runtime_cfg)
    assert created_runtime.kwargs["engine"] == "openai-runtime"
    assert created_runtime.kwargs["model"] == "runtime-model"



def test_remaining_factories_loader_and_tool_edges(monkeypatch, tmp_path):
    monkeypatch.setattr(factories_module, "_load_dotenv", lambda: None)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    assert factories_module.default_openai_model_id() == "gpt-4o-mini"

    monkeypatch.setattr(factories_module, "resolve_auto_provider", lambda region, priority=None: "bedrock-runtime")
    monkeypatch.setattr(factories_module, "default_region", lambda: "bedrock-region")
    assert factories_module._default_runtime_region("auto") == "bedrock-region"
    assert factories_module._default_runtime_region("openai-runtime") is None

    skill_dir = tmp_path / "runtime_skill"
    skill_dir.mkdir()

    class Loaded:
        runtime_skill = Skill(name="runtime_loaded")

    class LoaderWorkspace:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def load_skill(self, path):
            assert path == skill_dir.resolve()
            return Loaded()

    monkeypatch.setattr(factories_module, "AgenticSystem", LoaderWorkspace)
    assert factories_module.load_skill(str(skill_dir)).name == "runtime_loaded"

    packaged_dir = tmp_path / "packaged"
    packaged_dir.mkdir()

    class FakeTraversable:
        def __init__(self, path):
            self.path = Path(path)

        def __truediv__(self, part):
            return FakeTraversable(self.path / part)

        def __str__(self):
            return str(self.path)

    calls = []

    def fake_files(package):
        calls.append(package)
        if package == "pkg":
            return FakeTraversable(packaged_dir.parent)
        raise ModuleNotFoundError(package)

    monkeypatch.setattr(factories_module.resources, "files", fake_files)
    assert factories_module._resolve_packaged_skill_path("pkg/packaged") == packaged_dir.resolve()

    class BadTraversable:
        def __truediv__(self, part):
            return self

        def __str__(self):
            raise TypeError("bad path")

    monkeypatch.setattr(factories_module.resources, "files", lambda package: BadTraversable())
    assert factories_module._resolve_packaged_skill_path("pkg/anything") is None

    assert factories_module._default_agent_model("bedrock-runtime") == factories_module.default_model_id()
    assert tool_module._ensure_model_schema(None, "field") is None

    original_spec = loader_module.importlib.util.spec_from_loader
    monkeypatch.setattr(loader_module.importlib.util, "spec_from_loader", lambda *args, **kwargs: None)
    no_init = tmp_path / "no_init_pkg"
    no_init.mkdir()
    with pytest.raises(SkillLoadError):
        loader_module._load_skill_module(no_init, "no_init_pkg")
    monkeypatch.setattr(loader_module.importlib.util, "spec_from_loader", original_spec)
