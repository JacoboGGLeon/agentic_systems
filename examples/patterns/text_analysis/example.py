"""Current API adaptation; see README for its measured scope."""
import agentic_systems as toolkit

@toolkit.tool
def text_counts(input: dict) -> dict:
    words = input["text"].lower().split()
    return {"words": len(words), "unique": len(set(words)), "mentions": words.count("evidence")}


capability = toolkit.skill(name="text_counts", tools=(text_counts,))
worker = toolkit.Agent("worker", toolkit.Action("text_counts", "text_counts"), skills=(capability,))
app = toolkit.System("application", toolkit.Sequence((worker,)))
sample = {'text': 'evidence supports evidence'}


def run():
    result = app.run({'input': sample})
    assert result.ok and result.data == {'words': 3, 'unique': 2, 'mentions': 2}, result.to_dict()
    return result
