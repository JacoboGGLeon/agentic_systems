import pytest
from scripts.semantic_judge_probes import probe_cases, run_probe


def test_probe_pairs_share_evidence_and_hide_expected_verdict():
    cases = probe_cases()
    assert len({case["id"] for case in cases}) == 6
    for positive, negative in zip(cases[::2], cases[1::2]):
        assert positive["expected_supported"] is True
        assert negative["expected_supported"] is False
        assert positive["packet"]["evidence"] == negative["packet"]["evidence"]
        assert positive["packet"]["assertion"] != negative["packet"]["assertion"]
        assert set(positive["packet"]) == {"evidence", "assertion", "obligation"}


def test_python_control_cannot_certify_semantic_judge():
    with pytest.raises(ValueError, match="a_model_is_required"):
        run_probe("python-runtime", "native", "python-runtime", probe_cases()[0])
