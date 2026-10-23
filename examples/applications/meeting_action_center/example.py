"""Current API adaptation; see README for its measured scope."""
import agentic_systems as toolkit

@toolkit.tool
def extract_actions(input: dict) -> dict:
    actions = []
    for line in input["notes"]:
        owner, task, due = line.split(" | ")
        actions.append({"owner": owner, "task": task, "due": due})
    return {"actions": actions}


capability = toolkit.skill(name="extract_actions", tools=(extract_actions,))
worker = toolkit.Agent("worker", toolkit.Action("extract_actions", "extract_actions"), skills=(capability,))
app = toolkit.System("application", toolkit.Sequence((worker,)))
sample = {'notes': ['Ana | Review budget | Friday']}


def run():
    result = app.run({'input': sample})
    assert result.ok and result.data == {'actions': [{'owner': 'Ana', 'task': 'Review budget', 'due': 'Friday'}]}, result.to_dict()
    return result
