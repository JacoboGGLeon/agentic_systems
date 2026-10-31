"""Agentic Systems 2.1.4; explicit LangGraph and deterministic business rules."""

import pydantic
from typing import Any
import agentic_systems as toolkit


class Closed(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(strict=True, extra="forbid")


class Row(Closed):
    id: int
    amount: int | None


class Payload(Closed):
    rows: list[Row]


@toolkit.tool
def profile_rows(rows: list[Row]) -> dict:
    """Count duplicates and missing amounts in the supplied rows without changing them.

    Every row must contain both id and amount. A missing amount is represented
    by explicit JSON null, never by omitting the required amount field.
    """
    input = Payload(rows=rows).model_dump(mode="python")
    rows = input["rows"]
    ids = [row["id"] for row in rows]
    return {
        "rows": len(rows),
        "duplicate_ids": len(ids) - len(set(ids)),
        "missing_amounts": sum((row.get("amount") is None for row in rows)),
    }


capability = toolkit.skill(name="profile_rows", tools=(profile_rows,))


class WorkState(pydantic.BaseModel):
    input: dict
    rows: Any | None = None
    duplicate_ids: Any | None = None
    missing_amounts: Any | None = None


class Output(pydantic.BaseModel):
    rows: Any
    duplicate_ids: Any
    missing_amounts: Any


graph = toolkit.Graph(WorkState, output_schema=Output)
def profile_rows_step(state):
    return profile_rows.run(state.input)
graph.add_node(
    "profile_rows",
    profile_rows_step,
)
graph.add_edge(toolkit.START, "profile_rows")
graph.add_edge("profile_rows", toolkit.END)
app = toolkit.Agent("profile_rows", graph=graph, skills=(capability,))
sample = {"rows": [{"id": 1, "amount": 10}, {"id": 1, "amount": None}]}


def run():
    result = app.run({"input": sample})
    assert result.ok and result.data == {
        "rows": 2,
        "duplicate_ids": 1,
        "missing_amounts": 1,
    }, result.to_dict()
    return result
