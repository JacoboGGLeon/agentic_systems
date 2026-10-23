"""Current API adaptation; see README for its measured scope."""
import agentic_systems as toolkit

@toolkit.tool
def rank_options(input: dict) -> dict:
    scores = {name: values["quality"] - values["cost"] for name, values in input.items()}
    return {"scores": scores, "selected": max(scores, key=scores.get)}


capability = toolkit.skill(name="rank_options", tools=(rank_options,))
worker = toolkit.Agent("worker", toolkit.Action("rank_options", "rank_options"), skills=(capability,))
app = toolkit.System("application", toolkit.Sequence((worker,)))
sample = {'A': {'quality': 9, 'cost': 7}, 'B': {'quality': 8, 'cost': 3}}


def run():
    result = app.run({'input': sample})
    assert result.ok and result.data == {'scores': {'A': 2, 'B': 5}, 'selected': 'B'}, result.to_dict()
    return result
