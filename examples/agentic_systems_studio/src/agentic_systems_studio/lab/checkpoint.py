import pydantic
import agentic_systems as toolkit


def run():
    class State(pydantic.BaseModel):
        amount: int
        approved: bool | None = None

    graph = toolkit.Graph(State)
    graph.add_node(
        "approval",
        lambda state: {
            "approved": toolkit.pause(
                {"amount": state.amount, "question": "Approve?"}
            )
        },
    )
    graph.add_edge(toolkit.START, "approval")
    graph.add_edge("approval", toolkit.END)
    program = toolkit.Agent("approval", graph=graph).compile()
    waiting = program.run({"amount": 280})
    final = program.resume(waiting, True)
    assert waiting.status == "paused" and final.ok and final.data["approved"]
    return {
        "paused": waiting.to_dict(),
        "resumed": final.to_dict(),
        "inference_requests": 0,
    }
