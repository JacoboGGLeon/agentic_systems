from __future__ import annotations

from dataclasses import dataclass

import agentic_systems as toolkit


@dataclass
class ExampleDataclass:
    name: str
    nested: dict[str, str]


class ModelDumpAndToDict:
    def model_dump(self, *, mode: str):
        assert mode == "json"
        return {"selected": "model_dump"}

    def to_dict(self):
        return {"selected": "to_dict"}


class HumanAndStructured:
    def human_text(self):
        return "human representation"

    def to_dict(self):
        return {"selected": "to_dict"}


def test_show_json_supports_dataclasses_and_masks_nested_secrets(capsys):
    toolkit.show_json(
        ExampleDataclass(
            name="demo",
            nested={"api_token": "secret-value-123456"},
        )
    )

    output = capsys.readouterr().out
    assert '\"name\": \"demo\"' in output
    assert "secret-value-123456" not in output


def test_show_json_prefers_model_dump_over_to_dict(capsys):
    toolkit.show_json(ModelDumpAndToDict())

    output = capsys.readouterr().out
    assert '\"selected\": \"model_dump\"' in output
    assert '\"selected\": \"to_dict\"' not in output


def test_show_prefers_human_text_over_structured_representation(capsys):
    toolkit.show(HumanAndStructured(), title="Inspection")

    output = capsys.readouterr().out
    assert "Inspection" in output
    assert "human representation" in output
    assert "to_dict" not in output


def test_show_json_keeps_structured_run_result_contract(capsys):
    result = toolkit.RunResult(
        text="answer",
        data={"value": 42},
        engine="python-runtime",
        model="deterministic",
        mode="deterministic",
        ok=True,
    )

    toolkit.show_json(result)

    output = capsys.readouterr().out
    assert '\"text\": \"answer\"' in output
    assert '\"value\": 42' in output
    assert '\"engine\": \"python-runtime\"' in output
