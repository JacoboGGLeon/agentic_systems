"""Minimal explicit Graph: amount -> fee Tool -> Agent -> RunResult."""

import pydantic
import agentic_systems as toolkit


class Quote(pydantic.BaseModel):
    amount: int = pydantic.Field(gt=0)
    fee: int | None = None


@toolkit.tool
def calculate_fee(amount: int) -> dict:
    return {"fee": amount // 100}


graph = toolkit.Graph(Quote)
graph.add_node("fee", calculate_fee)
graph.add_edge(toolkit.START, "fee")
graph.add_edge("fee", toolkit.END)
agent = toolkit.Agent("quote", graph)
result = agent.run({"amount": 5000})
assert result.ok and result.data == {"amount": 5000, "fee": 50}
print(result.human_results())
