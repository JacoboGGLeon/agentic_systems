"""Visible conversation graph; the full Studio UI/controller has separate tests."""

import pydantic
import agentic_systems as toolkit


class Message(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="forbid")
    role: str
    content: str


class Conversation(pydantic.BaseModel):
    message: str
    history: list[Message] = pydantic.Field(default_factory=list)
    text: str | None = None
    history_turns: int | None = None


@toolkit.tool
def reply(message: str, history: list[Message]) -> dict:
    """A deterministic conversation fixture, not an LM response."""
    return {"text": "Python received: " + message, "history_turns": len(history)}


def build(framework):
    actor = toolkit.Agent(
        "conversation_actor",
        runtime=toolkit.runtime(provider="python-runtime"),
        framework=toolkit.framework(framework),
        skills=(toolkit.skill(name="conversation", tools=(reply,)),),
    )
    graph = toolkit.Graph(Conversation)
    graph.add_node("respond", actor)
    graph.add_edge(toolkit.START, "respond")
    graph.add_edge("respond", toolkit.END)
    return toolkit.System(
        "studio_conversation_grammar",
        graph=graph,
        context=toolkit.Context(
            {"history_policy": "explicit input, no inferred facts"}
        ),
        memory=toolkit.Memory(capacity=3),
    )


def run():
    rows = []
    for framework in ("native", "openai-agents", "strands"):
        app = build(framework)
        first = app.run({"message": "Hola", "history": []})
        assert first.ok, first.to_dict()
        second = app.run(
            {
                "message": "Continua",
                "history": [
                    {"role": "user", "content": "Hola"},
                    {"role": "assistant", "content": first.data["text"]},
                ],
            }
        )
        assert second.ok and second.data["history_turns"] == 2, second.to_dict()
        rows.append(
            {
                "framework": framework,
                "first": first.to_dict(),
                "second": second.to_dict(),
            }
        )
    return {
        "rows": rows,
        "scope": "visible SDK conversation composition; full Studio controller/UI tested separately",
        "inference_requests": 0,
    }
