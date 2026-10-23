"""Current API adaptation; see README for its measured scope."""
import agentic_systems as toolkit

@toolkit.tool
def extract_sources(input: dict) -> dict:
    claims = input["claims"]
    sources = input["sources"]
    return {"supported": [c["text"] for c in claims if c["source"] in sources],
            "unverified": [c["text"] for c in claims if c["source"] not in sources]}


capability = toolkit.skill(name="extract_sources", tools=(extract_sources,))
worker = toolkit.Agent("worker", toolkit.Action("extract_sources", "extract_sources"), skills=(capability,))
app = toolkit.System("application", toolkit.Sequence((worker,)))
sample = {'claims': [{'text': 'Revenue grew 5%', 'source': 'report'}, {'text': 'It will double', 'source': 'unknown'}], 'sources': ['report']}


def run():
    result = app.run({'input': sample})
    assert result.ok and result.data == {'supported': ['Revenue grew 5%'], 'unverified': ['It will double']}, result.to_dict()
    return result
