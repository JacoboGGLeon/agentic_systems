from __future__ import annotations

import os
from types import SimpleNamespace

import pytest
import agentic_systems as toolkit
from agentic_systems.tools import ToolEvent

from agentic_systems_studio.conversation import (
    _contains_public_value,
    ConversationConfig,
    build_conversational_system,
    ConversationalStudio,
    hello_world,
    inspect_agentic_systems_grammar,
    prepare_conversation_context,
    safe_calculate,
)
from agentic_systems_studio.environment import load_studio_environment


def test_conversation_config_uses_canonical_dotenv_without_secrets(
    monkeypatch, tmp_path
):
    environment = tmp_path / ".env"
    environment.write_text(
        "AGENTIC_SYSTEMS_PROVIDER=bedrock-runtime\n"
        "AGENTIC_SYSTEMS_FRAMEWORK=strands\n"
        "AGENTIC_SYSTEMS_MODEL=test-model\n"
        "AGENTIC_SYSTEMS_TIMEOUT_S=45\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("AGENTIC_SYSTEMS_ENV_FILE", str(environment))
    monkeypatch.setenv("AGENTIC_SYSTEMS_PROVIDER", "stale-runtime-value")
    monkeypatch.setenv("AWS_CONTAINER_CREDENTIALS_RELATIVE_URI", "/managed/role")

    config = ConversationConfig.from_environment()

    assert config.provider == "bedrock-runtime"
    assert config.framework == "strands"
    assert config.framework_value == "strands"
    assert config.model == "test-model"
    assert config.timeout_s == 45
    assert os.environ["AWS_CONTAINER_CREDENTIALS_RELATIVE_URI"] == "/managed/role"
    assert ConversationConfig(framework="native").framework_value is None


def test_conversation_config_resolves_model_from_provider_registry(
    monkeypatch, tmp_path
):
    environment = tmp_path / ".env"
    environment.write_text(
        "AGENTIC_SYSTEMS_PROVIDER=bedrock-runtime\n"
        "AGENTIC_SYSTEMS_FRAMEWORK=native\n"
        "AGENTIC_SYSTEMS_MODEL=\n"
        "BEDROCK_MODEL_ID=provider-owned-model\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("AGENTIC_SYSTEMS_ENV_FILE", str(environment))
    monkeypatch.delenv("AGENTIC_SYSTEMS_MODEL", raising=False)
    monkeypatch.delenv("BEDROCK_MODEL_ID", raising=False)

    config = ConversationConfig.from_environment()

    assert config.provider == "bedrock-runtime"
    assert config.framework == "native"
    assert config.model == "provider-owned-model"


def test_conversation_config_materializes_auto_provider_without_hardcoding(
    monkeypatch, tmp_path
):
    environment = tmp_path / ".env"
    environment.write_text(
        "AGENTIC_SYSTEMS_PROVIDER=auto\n"
        "AGENTIC_SYSTEMS_PROVIDER_PRIORITY=openai-runtime\n"
        "AGENTIC_SYSTEMS_MODEL=\n"
        "OPENAI_API_KEY=test-key\n"
        "OPENAI_MODEL=provider-owned-model\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("AGENTIC_SYSTEMS_ENV_FILE", str(environment))

    config = ConversationConfig.from_environment()

    assert config.provider == "openai-runtime"
    assert config.model == "provider-owned-model"


def test_load_studio_environment_reports_the_resolved_contract(monkeypatch, tmp_path):
    environment = tmp_path / ".env"
    environment.write_text("RUN_STUDIO_LIVE=1\n", encoding="utf-8")
    monkeypatch.setenv("AGENTIC_SYSTEMS_ENV_FILE", str(environment))
    monkeypatch.setenv("RUN_STUDIO_LIVE", "0")

    resolved = load_studio_environment()

    assert resolved == environment.resolve()
    assert os.environ["RUN_STUDIO_LIVE"] == "1"


def test_conversational_tools_are_bounded_and_deterministic():
    calculation = safe_calculate.run({"expression": "17 * 19"})
    assert calculation.ok is True
    assert calculation.data["result"] == 323

    context = prepare_conversation_context.run(
        {
            "messages": [
                {"role": "system", "content": "private"},
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "hi"},
            ],
            "message": "next",
        }
    )
    assert context.ok is True
    assert context.data["history_turns"] == 2
    assert all(item["role"] != "system" for item in context.data["history"])
    assert context.data["memory"] == {
        "kind": "bounded-public-history",
        "maximum_messages": 12,
        "maximum_user_characters": 2000,
        "maximum_assistant_characters": 1200,
        "maximum_current_message_characters": 8000,
        "truncated_messages": 0,
    }

    long_context = prepare_conversation_context.run(
        {
            "messages": [
                {"role": "assistant", "content": "x" * 5000},
                {"role": "user", "content": "y" * 5000},
            ],
            "message": "z" * 9000,
        }
    )
    assert len(long_context.data["history"][0]["content"]) == 1200
    assert len(long_context.data["history"][1]["content"]) == 2000
    assert len(long_context.data["message"]) == 8000
    assert long_context.data["memory"]["truncated_messages"] == 2

    greeting = hello_world.run({"message": "hola"})
    assert greeting.ok is True
    assert greeting.data["execution_kind"] == "deterministic-mock"
    assert "yo sólo trabajar" in greeting.data["message"]
    assert "no tengo mente ni modelo de lenguaje" in greeting.data["message"]

    grammar = inspect_agentic_systems_grammar.run(
        {"request": "Generate an Agentic Systems application"}
    )
    assert grammar.ok is True
    assert grammar.data["version"] == "2.1.2"
    assert all(grammar.data["public_symbols"].values())
    assert grammar.data["contracts"]["tool_output"].endswith("a dictionary.")
    assert "import agentic_systems as toolkit" in grammar.data["canonical_example"]


def test_python_runtime_is_an_explicit_deterministic_studio_mock():
    studio = build_conversational_system(
        ConversationConfig(provider="python-runtime", framework="native")
    )

    result = studio.run("hola")

    assert result.ok is True
    assert result.engine == "python-runtime"
    assert result.meta["framework"] == "native"
    assert [event.name for event in result.tool_events] == [
        "prepare_conversation_context",
        "hello_world",
    ]
    assert "yo sólo trabajar" in result.text
    assert "no tengo mente ni modelo de lenguaje" in result.text
    result.check_invariants().raise_if_failed()


def test_mixed_grammar_and_calculation_request_composes_required_evidence():
    context_payload = {
        "message": "Explain Agentic Systems using verified 17 * 19.",
        "history": [],
        "history_turns": 0,
        "policy": {"reasoning_is_private": True},
    }
    context_result = toolkit.RunResult(
        text="context",
        engine="python-runtime",
        model="python-runtime",
        data=context_payload,
        tool_events=[
            ToolEvent(
                id="context-1",
                name="prepare_conversation_context",
                input={},
                output=context_payload,
                ok=True,
            )
        ],
    )
    calculation_result = toolkit.RunResult(
        text="Verified result: 323",
        engine="bedrock-runtime",
        model="test-model",
        tool_events=[
            ToolEvent(
                id="calculate-1",
                name="safe_calculate",
                input={"expression": "17 * 19"},
                output={"result": 323},
                ok=True,
            )
        ],
    )
    final_result = toolkit.RunResult(
        text="Agentic Systems can compose deterministic evidence; the verified result is 323.",
        engine="bedrock-runtime",
        model="test-model",
    )
    calls: list[str] = []

    def calculate(prompt: str):
        calls.append(f"calculate:{prompt}")
        return calculation_result

    def synthesize(prompt: str):
        calls.append(f"synthesize:{prompt}")
        return final_result

    def unexpected(_prompt: str):
        raise AssertionError(
            "The optional assistant must not bypass evidence synthesis."
        )

    grammar = inspect_agentic_systems_grammar.run({"request": "validation"}).data
    studio = ConversationalStudio(
        config=ConversationConfig(provider="bedrock-runtime"),
        reasoning_system=object(),
        deterministic_system=object(),
        assistant=SimpleNamespace(run=unexpected),
        context_agent=SimpleNamespace(run=lambda *_args: context_result),
        calculation_agent=SimpleNamespace(run=calculate),
        grounded_assistant=SimpleNamespace(run=synthesize),
        grammar_contract=grammar,
    )

    result = studio.run(context_payload["message"])

    assert result.ok is True
    assert result.text.endswith("verified result is 323.")
    assert [event.name for event in result.tool_events] == [
        "prepare_conversation_context",
        "inspect_agentic_systems_grammar",
        "safe_calculate",
    ]
    assert [call.split(":", 1)[0] for call in calls] == ["calculate", "synthesize"]
    assert result.data["response_validation"]["ok"] is True
    result.check_invariants().raise_if_failed()


def test_calculation_evidence_intent_is_explicit_and_history_safe():
    studio = ConversationalStudio(
        config=ConversationConfig(provider="openai-runtime"),
        reasoning_system=object(),
        deterministic_system=object(),
        assistant=object(),
        context_agent=object(),
    )

    assert studio._requests_new_calculation_evidence(
        "Usa la calculadora para verificar 17 por 19."
    )
    assert studio._requests_new_calculation_evidence("Explain 17 * 19.")
    assert not studio._requests_new_calculation_evidence(
        "Convierte el cálculo anterior en una Skill reutilizable."
    )

    assert studio._requested_public_omissions(
        "El proyecto se llama Boreal; confirma sin repetirlo."
    ) == ("Boreal",)
    assert studio._requested_public_omissions(
        "El número base es 17; confirma sin repetirlo."
    ) == ("17",)
    assert _contains_public_value("Ann received the context.", "Ann")
    assert not _contains_public_value("Planning is complete.", "Ann")
    assert not _contains_public_value("The result is 170.", "17")
    assert studio._public_omissions_for_turn(
        message="Ahora diseña la Tool.",
        context={
            "history": [
                {
                    "role": "user",
                    "content": "El proyecto se llama Boreal; confirma sin repetirlo.",
                },
                {
                    "role": "user",
                    "content": "El número base es 17; confirma sin repetirlo.",
                },
            ]
        },
    ) == ("Boreal",)


@pytest.mark.parametrize(
    ("message", "initial_answer", "repaired_answer"),
    [
        (
            "El proyecto se llama Boreal; confirma sin repetirlo.",
            "Confirmo que el proyecto se llama Boreal.",
            "Confirmo que recibí el contexto.",
        ),
        (
            "Explica el resultado en lenguaje natural.",
            '{"answer": "El resultado es 323."}',
            "El resultado es 323.",
        ),
    ],
)
def test_public_response_boundary_performs_one_bounded_repair(
    message: str,
    initial_answer: str,
    repaired_answer: str,
):
    initial_result = toolkit.RunResult(
        text=initial_answer,
        engine="ollama-runtime",
        model="test-model",
    )
    repair_result = toolkit.RunResult(
        text=repaired_answer,
        engine="ollama-runtime",
        model="test-model",
    )
    studio = ConversationalStudio(
        config=ConversationConfig(provider="ollama-runtime"),
        reasoning_system=object(),
        deterministic_system=object(),
        assistant=object(),
        context_agent=object(),
    )

    answer, results, validation = studio._validate_or_repair_response(
        message=message,
        context={"message": message},
        assistant_result=initial_result,
        execution_agent=SimpleNamespace(run=lambda _prompt: repair_result),
    )

    assert answer == repaired_answer
    assert results == [initial_result, repair_result]
    assert validation["ok"] is True
    assert validation["repairs"] == 1
    assert validation["initial_error"]
    assert validation["final_error"] is None


def test_response_repair_budget_can_use_a_second_bounded_attempt():
    initial_result = toolkit.RunResult(
        text='{"answer": "technical"}',
        engine="ollama-runtime",
        model="test-model",
    )
    still_invalid = toolkit.RunResult(
        text='{"answer": "still technical"}',
        engine="ollama-runtime",
        model="test-model",
    )
    repaired = toolkit.RunResult(
        text="La respuesta pública ya es natural.",
        engine="ollama-runtime",
        model="test-model",
    )
    repairs = iter((still_invalid, repaired))
    studio = ConversationalStudio(
        config=ConversationConfig(
            provider="ollama-runtime",
            max_response_repairs=2,
        ),
        reasoning_system=object(),
        deterministic_system=object(),
        assistant=object(),
        context_agent=object(),
    )

    answer, results, validation = studio._validate_or_repair_response(
        message="Responde en lenguaje natural.",
        context={"message": "Responde en lenguaje natural."},
        assistant_result=initial_result,
        execution_agent=SimpleNamespace(run=lambda _prompt: next(repairs)),
    )

    assert answer == repaired.text
    assert results == [initial_result, still_invalid, repaired]
    assert validation["ok"] is True
    assert validation["repairs"] == 2
    assert validation["final_error"] is None


def test_calculation_response_repairs_unsolicited_unsafe_code():
    initial_result = toolkit.RunResult(
        text=(
            "```python\n"
            "def calculate(expression: str) -> dict:\n"
            '    return {"result": eval(expression)}\n'
            "```\n\nLe résultat est 13."
        ),
        engine="bedrock-runtime",
        model="test-model",
    )
    repaired = toolkit.RunResult(
        text="Le résultat de 3 + 5 × 2 est 13.",
        engine="bedrock-runtime",
        model="test-model",
    )
    evidence = toolkit.RunResult(
        text="13",
        engine="python-runtime",
        tool_events=[
            ToolEvent(
                id="calculate-unsafe-code",
                name="safe_calculate",
                input={"expression": "3 + 5 * 2"},
                output={"result": 13},
                ok=True,
            )
        ],
    )
    studio = ConversationalStudio(
        config=ConversationConfig(provider="bedrock-runtime"),
        reasoning_system=object(),
        deterministic_system=object(),
        assistant=object(),
        context_agent=object(),
    )

    answer, results, validation = studio._validate_or_repair_response(
        message='Calcule "3 + 5 * 2" et réponds en français.',
        context={"message": 'Calcule "3 + 5 * 2" et réponds en français.'},
        assistant_result=initial_result,
        evidence_results=[evidence],
        execution_agent=SimpleNamespace(run=lambda _prompt: repaired),
    )

    assert answer == repaired.text
    assert results == [initial_result, repaired]
    assert validation["ok"] is True
    assert validation["repairs"] == 1
    assert "eval(" not in answer
    assert "```" not in answer


def test_explicit_safe_code_request_is_accepted():
    answer_result = toolkit.RunResult(
        text="```python\nresult = 3 + 5 * 2\n```\n\nEl resultado es 13.",
        engine="openai-runtime",
        model="test-model",
    )
    evidence = toolkit.RunResult(
        text="13",
        engine="python-runtime",
        tool_events=[
            ToolEvent(
                id="calculate-safe-code",
                name="safe_calculate",
                input={"expression": "3 + 5 * 2"},
                output={"result": 13},
                ok=True,
            )
        ],
    )
    studio = ConversationalStudio(
        config=ConversationConfig(provider="openai-runtime"),
        reasoning_system=object(),
        deterministic_system=object(),
        assistant=object(),
        context_agent=object(),
    )

    answer, results, validation = studio._validate_or_repair_response(
        message="Dame código Python para calcular 3 + 5 * 2.",
        context={"message": "Dame código Python para calcular 3 + 5 * 2."},
        assistant_result=answer_result,
        evidence_results=[evidence],
    )

    assert answer == answer_result.text
    assert results == [answer_result]
    assert validation["ok"] is True
    assert validation["repairs"] == 0


def test_context_agent_run_uses_public_default_mode_and_public_data():
    studio = build_conversational_system(
        ConversationConfig(provider="openai-runtime", model="offline-contract-model")
    )

    result = studio.context_agent.run(
        {
            "tool": "prepare_conversation_context",
            "input": {"messages": [], "message": "hola"},
        }
    )

    assert result.ok is True
    assert result.data["message"] == "hola"
    assert result.data["history_turns"] == 0


def test_conversational_studio_inspect_uses_public_report_projection():
    studio = build_conversational_system(
        ConversationConfig(provider="openai-runtime", model="offline-contract-model")
    )

    report = studio.inspect()

    assert report["deterministic_system"]["ok"] is True
    assert report["reasoning_system"]["ok"] is True
    assert report["configuration"]["provider"] == "openai-runtime"
    assert [agent["name"] for agent in report["agents"]] == [
        "conversation.context",
        "conversation.assistant",
        "conversation.calculation_evidence",
        "conversation.grounded_assistant",
    ]
    assert (
        "incorporate its relevant returned evidence"
        in report["agents"][1]["instructions"]
    )


@pytest.mark.parametrize(
    "framework", ["native", "langgraph", "openai-agents", "strands"]
)
def test_conversational_studio_composes_real_run_results(framework, capsys):
    context_payload = {
        "message": "17 * 19",
        "history": [],
        "history_turns": 0,
        "policy": {"reasoning_is_private": True},
    }
    context_result = toolkit.RunResult(
        text="context",
        engine="python-runtime",
        model="python-runtime",
        mode="default",
        data=context_payload,
        tool_events=[
            ToolEvent(
                id="context-1",
                name="prepare_conversation_context",
                input={},
                output={"data": context_payload},
                ok=True,
            )
        ],
    )
    answer_result = toolkit.RunResult(
        text="323",
        engine="vllm-runtime",
        model="qwen-test",
        mode="default",
        usage={"total_tokens": 12},
    )
    studio = ConversationalStudio(
        config=ConversationConfig(provider="vllm-runtime", framework=framework),
        reasoning_system=object(),
        deterministic_system=object(),
        assistant=SimpleNamespace(run=lambda *_args: answer_result),
        context_agent=SimpleNamespace(run=lambda *_args: context_result),
    )

    result = studio.run("17 * 19")

    assert result.ok is True
    assert result.text == "323"
    assert result.final == {"text": "323"}
    assert result.engine == "vllm-runtime"
    assert result.meta["framework"] == framework
    assert result.meta["engines_used"] == ["python-runtime", "vllm-runtime"]
    assert result.data["context_summary"] == {
        "history_turns": 0,
        "memory": {},
        "policy": {"reasoning_is_private": True},
    }

    toolkit.human_result(result, pretty=False)
    rendered = capsys.readouterr().out
    assert "Respuesta:\n323" in rendered
    assert 'Respuesta:\n{"answer"' not in rendered


def test_conversational_studio_repairs_invalid_public_grammar_once():
    context_payload = {
        "message": "Package the Tool into a Skill.",
        "history": [],
        "history_turns": 0,
        "policy": {"reasoning_is_private": True},
    }
    context_result = toolkit.RunResult(
        text="context",
        engine="python-runtime",
        model="python-runtime",
        data=context_payload,
    )
    invalid = toolkit.RunResult(
        text=(
            "```python\nimport agentic_systems as toolkit\n"
            "@toolkit.skill\nclass CalculatorSkill:\n    pass\n```"
        ),
        engine="openai-runtime",
        model="test-model",
        usage={"total_tokens": 10},
    )
    repaired = toolkit.RunResult(
        text=(
            "```python\nimport agentic_systems as toolkit\n"
            "@toolkit.tool\ndef multiply(a: int, b: int) -> dict:\n"
            "    return {'result': a * b}\n\n"
            "calculator = toolkit.skill(name='calculator', tools=[multiply])\n```"
        ),
        engine="openai-runtime",
        model="test-model",
        usage={"total_tokens": 20},
    )
    responses = iter((invalid, repaired))
    grammar = inspect_agentic_systems_grammar.run({"request": "validation"}).data
    studio = ConversationalStudio(
        config=ConversationConfig(provider="openai-runtime", max_response_repairs=1),
        reasoning_system=object(),
        deterministic_system=object(),
        assistant=SimpleNamespace(run=lambda *_args: next(responses)),
        context_agent=SimpleNamespace(run=lambda *_args: context_result),
        grammar_contract=grammar,
    )

    result = studio.run("Package the Tool into a Skill.")

    assert "toolkit.skill(" in result.text
    assert result.data["response_validation"] == {
        "ok": True,
        "repairs": 1,
        "required_factories": ["tool", "skill"],
        "initial_error": (
            "toolkit.skill is a factory, not a decorator; use "
            "toolkit.skill(name=..., tools=[...])."
        ),
        "final_error": None,
    }
    assert result.usage["total_tokens"] == 30
    result.check_invariants().raise_if_failed()


def test_conversational_studio_fails_invalid_code_when_repairs_are_disabled():
    context_result = toolkit.RunResult(
        text="context",
        engine="python-runtime",
        model="python-runtime",
        data={"message": "Build a Skill", "history_turns": 0},
    )
    invalid = toolkit.RunResult(
        text="```python\n@toolkit.skill\nclass Invalid:\n    pass\n```",
        engine="openai-runtime",
        model="test-model",
    )
    grammar = inspect_agentic_systems_grammar.run({"request": "validation"}).data
    studio = ConversationalStudio(
        config=ConversationConfig(provider="openai-runtime", max_response_repairs=0),
        reasoning_system=object(),
        deterministic_system=object(),
        assistant=SimpleNamespace(run=lambda *_args: invalid),
        context_agent=SimpleNamespace(run=lambda *_args: context_result),
        grammar_contract=grammar,
    )

    result = studio.run("Build a Skill")

    assert result.ok is False
    assert result.data["response_validation"]["repairs"] == 0
    assert "factory, not a decorator" in result.errors[-1]["message"]
    result.check_invariants().raise_if_failed()


def test_conversational_studio_repairs_omitted_scalar_tool_evidence():
    context_result = toolkit.RunResult(
        text="context",
        engine="python-runtime",
        model="python-runtime",
        data={"message": "Calculate", "history_turns": 0},
    )
    unsupported_answer = toolkit.RunResult(
        text="I completed the calculation.",
        engine="openai-runtime",
        model="test-model",
        tool_events=[
            ToolEvent(
                id="multiply-1",
                name="multiply",
                input={"a": 17, "b": 19},
                output={"result": 323},
                ok=True,
            )
        ],
    )
    repaired = toolkit.RunResult(
        text="The verified result is 323.",
        engine="openai-runtime",
        model="test-model",
    )
    responses = iter((unsupported_answer, repaired))
    studio = ConversationalStudio(
        config=ConversationConfig(provider="openai-runtime"),
        reasoning_system=object(),
        deterministic_system=object(),
        assistant=SimpleNamespace(run=lambda *_args: next(responses)),
        context_agent=SimpleNamespace(run=lambda *_args: context_result),
    )

    result = studio.run("Calculate")

    assert result.ok is True
    assert result.text == "The verified result is 323."
    assert result.data["response_validation"]["repairs"] == 1
    assert (
        "omitted scalar Tool evidence"
        in result.data["response_validation"]["initial_error"]
    )
