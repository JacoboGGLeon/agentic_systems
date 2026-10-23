"""Current API adaptation; see README for its measured scope."""
import agentic_systems as toolkit

from pydantic import BaseModel, ConfigDict


class Claim(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    text: str
    source: str


@toolkit.tool(input_schema=Claim)
def inspect_claim(text: str, source: str) -> dict:
    return {"text": text, "source": source, "has_source": bool(source)}


app = toolkit.Agent("typed_review", toolkit.Action("inspect", inspect_claim))


def run():
    result = app.run({"text": "Revenue rose", "source": "report"})
    invalid = app.run({"text": 12, "source": "report"})
    assert result.ok and not invalid.ok
    return {"valid": result.to_dict(), "invalid": invalid.to_dict(), "scope": "types and source presence; not natural-language entailment"}
