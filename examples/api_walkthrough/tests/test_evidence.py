import agentic_systems as toolkit
from examples.api_214.application import demonstrate, domain


def test_integrated_results_are_serializable_and_linked():
    report = demonstrate()
    assert report["output"]["environment"]["state"] == {"sum": 348}
    for payload in report["run_results"]:
        result = toolkit.RunResult(**payload)
        assert result.check_invariants().ok and result.lineage().render()


def test_domain_snapshot_is_immutable():
    copy = domain.data
    copy["tax_percent"] = 999
    assert domain.data["tax_percent"] == 16
