"""Current API adaptation; see README for its measured scope."""
import agentic_systems as toolkit

@toolkit.tool
def profile_rows(input: dict) -> dict:
    rows = input["rows"]
    ids = [row["id"] for row in rows]
    return {"rows": len(rows), "duplicate_ids": len(ids) - len(set(ids)),
            "missing_amounts": sum(row.get("amount") is None for row in rows)}


capability = toolkit.skill(name="profile_rows", tools=(profile_rows,))
worker = toolkit.Agent("worker", toolkit.Action("profile_rows", "profile_rows"), skills=(capability,))
app = toolkit.System("application", toolkit.Sequence((worker,)))
sample = {'rows': [{'id': 1, 'amount': 10}, {'id': 1, 'amount': None}]}


def run():
    result = app.run({'input': sample})
    assert result.ok and result.data == {'rows': 2, 'duplicate_ids': 1, 'missing_amounts': 1}, result.to_dict()
    return result
